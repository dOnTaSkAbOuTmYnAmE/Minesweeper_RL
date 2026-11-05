import torch
import pygame
from pygame.event import Event

from UIElements.UIElement import UIElement
from UIElements.DropdownMenu import DropdownMenu
from UIElements.Window import Window

from Minesweeper.minesweeper_board import MinesweeperBoard, COVERED_FIELD, MINED

from Minesweeper.model import MinesweeperModel, get_action, get_action_index, get_action_distribution

WINDOW_SIZE = (1280, 960)
SPRITE_SIZE = 8
TILESET_PATH = "Minesweeper/assets/Minesweeper_tiles_smol.png"
FONT_PATH = "RPS/assets/BoldPixels.ttf"
MODEL_PATH = "./Minesweeper/8_8_trans_flag/model.pth"

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
HINT_NEUTRAL = (240, 240, 240)
HINT_GREEN = (140, 255, 140)

DIFFICULTIES = [
    (8, 8, 12),
    (18, 14, 40),
    (24, 20, 99),
]

model = MinesweeperModel(5)
model.load_state_dict( torch.load("./Minesweeper/multi_train_multi_test/model.pth") )

pygame.init()

torch.set_printoptions(linewidth=10000)

class Rect(UIElement):
    def __init__(self, x: int, y: int, width: int, height: int, image: pygame.Surface, board_x: int, board_y: int) -> None:
        super(Rect, self).__init__(x, y, width, height)

        self.img = image
        self.clr = WHITE
        self.background = image.copy()

        self.board_x = board_x
        self.board_y = board_y
        self.text: pygame.Surface | None = None

        self.__update_background__()

    @property
    def image(self):
        return self.img
    
    @image.setter
    def image(self, image):
        self.img = image
        self.__update_background__()

    @property
    def color(self):
        return self.clr

    @color.setter
    def color(self, color):
        self.clr = color
        self.__update_background__()


    def __update_background__(self):
        color_image = pygame.Surface(self.image.get_size())
        color_image.fill(self.clr)

        self.background = self.img.copy()
        self.background.blit(color_image, (0, 0), special_flags = pygame.BLEND_RGB_MULT)


    def draw(self, surface: pygame.Surface):
        surface.blit(self.background, (self.x, self.y), special_flags=pygame.BLEND_RGB_MULT)

        if self.text != None:
            surface.blit(self.text, ( self.x + 15, self.y + 5))



class MinesweeperWindow(Window):
    def __init__(self) -> None:
        super(MinesweeperWindow, self).__init__(*WINDOW_SIZE, resizable=True)

        self.board_x = 0
        self.board_y = 0
        self.mines = 0

        self.scale = 48

        self.padding_x = 10
        self.padding_y = 50

        self.board_offset_x = 0
        self.board_offset_y = 0

        self.is_ctrl_pressed = False

        self.is_auto_solving = False
        self.solve_cooldown = 0
        self.next_solve_id = (-1, -1)
        self.next_solve_action = -1

        self.font = pygame.font.Font('RPS/assets/BoldPixels.ttf', int(self.scale * 0.8))
        self.font_smol = pygame.font.Font('RPS/assets/BoldPixels.ttf', int(self.scale * 0.4))

        self.tiles_scale = 8
        spritesheet = pygame.image.load("Minesweeper/assets/Minesweeper_tiles_smol.png")
        self.tiles = [
            pygame.Surface((self.tiles_scale, self.tiles_scale)),
            pygame.Surface((self.tiles_scale, self.tiles_scale)),
            pygame.Surface((self.tiles_scale, self.tiles_scale)),
            pygame.Surface((self.tiles_scale, self.tiles_scale))
        ]


        for y in range(2):
            for x in range(2):
                index = y * 2 + x
                self.tiles[index].blit( spritesheet, (0, 0), (self.tiles_scale * x, self.tiles_scale * y, self.tiles_scale, self.tiles_scale) )


        self.scaled_tiles = []
        self.__rescale_tiles__()


        self.board = MinesweeperBoard()

        self.squares: list[list[Rect]] = []
        self.probability_labels: list[list[list[pygame.Surface]]] = []

        self.mines_text = self.font.render(f"{self.mines}", False, (0, 0, 0))

        self.difficulty = DropdownMenu(
            200, 20, 200, 50, ["Mała", "Średnia", "Duża"], self.font, self.on_difficulty_change, start_value=0
        )
        self.network_show_mode = DropdownMenu(450, 20, 200, 50, ["Nic", "Kliknięcie", "Flaga"], self.font, self.get_network_data, start_value=1)

        self.auto_solve_switch = Rect(700, 20, 40, 40, pygame.transform.scale_by(self.tiles[0], 6), 0, 0)

        self.on_difficulty_change(0)


    def __update__(self, delta: float):
        self.screen.fill((255, 255, 255))

        for row in self.squares:
            for rect in row:
                rect.draw(self.screen)

        # for y, row in enumerate(self.probability_labels):
        #     for x, labels in enumerate(row):
        #         if self.board.discovered_fields[y][x] == COVERED_FIELD:
        #             self.screen.blit( labels[0], (self.padding_x + x * self.scale, self.padding_y + y * self.scale + 45 ) )
        #             self.screen.blit( labels[1], (self.padding_x + x * self.scale, self.padding_y + (y + 0.5) * self.scale + 45 ) )

                # square.x = int(self.padding_x + (self.scale + self.gap) * x - self.gap)
                # square.y = int(
                #     self.padding_y + 45 + (self.scale + self.gap) * y - self.gap
                # )

        self.auto_solve_switch.draw(self.screen)

        self.screen.blit(self.mines_text, (self.padding_x, self.padding_y))

        self.difficulty.draw(self.screen)
        self.network_show_mode.draw(self.screen)

        if self.is_auto_solving and self.next_solve_action != -1 and self.next_solve_id != -1:
            self.solve_cooldown += delta

            if self.solve_cooldown >= 1:
                x = self.next_solve_id[0]
                y = self.next_solve_id[1]
                
                if self.next_solve_action == 0:
                    self.board.click_field(x, y)
                else:
                    self.board.toggle_flag(x, y)

                self.update_squares()
                self.get_network_data()
                
                self.solve_cooldown = 0


    def __handle_events__(self, event: Event):
        if event.type == pygame.QUIT:
                self.running = False

        elif event.type in (pygame.VIDEORESIZE, pygame.VIDEOEXPOSE):
            self.on_resize()
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.on_click(event.button, True)

        elif event.type == pygame.MOUSEBUTTONUP:
            self.on_click(event.button, False)

        elif event.type == pygame.KEYDOWN and event.key == pygame.K_LCTRL:
            self.is_ctrl_pressed = True
        elif event.type == pygame.KEYUP and event.key == pygame.K_LCTRL:
            self.is_ctrl_pressed = False


    def on_click(self, button, is_pressed):

        if not is_pressed:
            return

        if button in (4, 5):
            if self.is_ctrl_pressed and is_pressed:
                self.scale = max(8, self.scale + (0.5 if button == 4 else -0.5))
                self.on_scale_change()
            return

        mouse_pos = pygame.mouse.get_pos()
        if self.difficulty.on_click(mouse_pos) or self.network_show_mode.on_click(mouse_pos):
            return

        if self.auto_solve_switch.contains(mouse_pos):
            self.is_auto_solving = not self.is_auto_solving
            self.solve_cooldown = 0

        for row in self.squares:
            for square in row:
                if not square.contains(mouse_pos):
                    continue


                if button == 1:
                    self.board.click_field(square.board_x, square.board_y)

                elif button == 2:
                    self.board.play_multi_move(square.board_x, square.board_y)

                elif button == 3:
                    self.board.toggle_flag(square.board_x, square.board_y)
                else:
                    return

                self.update_squares()
                self.get_network_data()
                return


    def update_squares(self):
        board_state = self.board.get_board()

        for y, row in enumerate(board_state):
            for x, state in enumerate(row):
                square = self.squares[y][x]
                square.color = WHITE
                square.text = None

                if state == "w":
                    square.color = HINT_GREEN
                    continue
                if state == "x":
                    square.image = self.scaled_tiles[0]
                elif state == "f":
                    square.image = self.scaled_tiles[1]
                elif state == "m":
                    square.image = self.scaled_tiles[3]
                else:
                    square.image = self.scaled_tiles[2]
                    if state != "0":
                        square.text = self.font.render(state, False, BLACK)
        
        mines = self.board.number_of_mines - self.board.flag_count
        self.mines_text = self.font.render(f"{mines}", False, (0, 0, 0))


    def get_network_data(self, *args):
        if self.board.game_over:
            for y in range(self.board_y):
                for x in range(self.board_x):
                    if self.board.discovered_fields[ y ][ x ] == COVERED_FIELD or self.board.mines[ y ][ x ] == MINED:

                        if not self.board.has_won:
                            self.squares[y][x].color = HINT_NEUTRAL
                        self.squares[y][x].text = None


            self.next_solve_id = (-1, -1)
            self.next_solve_action = -1

            return
            

        try:
            encode = self.board.encode(True)
            mask = self.board.get_mask().unsqueeze(0)
        except:
            print("error")
            return

        with torch.inference_mode():
            logits, value = model(encode)
            index = get_action_index(logits, mask, False)
            dist = get_action_distribution(logits, mask)
            probs = dist.probs.squeeze(0)


        for i in range(self.board_x * self.board_y):
            y = i // self.board_x
            x = i % self.board_x
            if self.board.discovered_fields[ y ][ x ] != COVERED_FIELD:
                continue

            prob_click = probs[i].item()
            prob_flag = probs[i + self.board_x * self.board_y] + probs[i + self.board_x * self.board_y * 2].item()
            # self.squares[y][x].text = self.font_smol.render(f"{prob_click*100:.1f}\n{probs_flag*100:.1f}", False, BLACK)

            self.probability_labels[y][x] = [
                self.font_smol.render(f"{prob_click*100:.1f}", False, BLACK),
                self.font_smol.render(f"{prob_flag*100:.1f}", False, BLACK)
            ]

            if prob_click >= prob_flag:
                self.squares[y][x].color = ( 240 * (1 - prob_click), 240, 240 * (1 - prob_click) )
            else:
                self.squares[y][x].color = ( 240, 240 * (1 - prob_flag), 240 * (1 - prob_flag) )

            # if self.network_show_mode.chosen == 1:
            #     self.squares[y][x].color = ( 240 * (1 - prob_click), 240, 240 * (1 - prob_click) )

            #     self.squares[y][x].text = self.font_smol.render(f"{prob_click*100:.1f}", False, BLACK)
            
            # elif self.network_show_mode.chosen == 2:
            #     self.squares[y][x].color = ( 240, 240 * (1 - probs_flag), 240 * (1 - probs_flag) )

            #     self.squares[y][x].text = self.font_smol.render(f"{probs_flag*100:.1f}", False, BLACK)
            
            # else:
            #     self.squares[y][x].color = HINT_NEUTRAL
            #     self.squares[y][x].text = None

        # for plane in dist.probs.reshape([3, self.board_y, self.board_x]):
        #     for row in plane:
        #         for value in row:
        #             print(f"{value * 100:.2f}\t", end="")
        #         print()
        #     print()

        actions = ["Click", "Flag", "Unflag"]
        ind, action = get_action(index, self.board_x, self.board_y)
        print(f"{value.detach()[0].item():.3f}")
        print(actions[action], (ind % self.board_x) + 1, (ind // self.board_x) + 1)

        self.next_solve_id = (ind % self.board_x, ind // self.board_x)
        self.next_solve_action = action

        


    def on_resize(self):
        width, height = self.screen.get_size()

        board_width = self.board_x * self.scale
        board_height = self.board_y * self.scale

        self.padding_x = (width - board_width) / 2
        self.padding_y = (height - board_height) / 2 - 45

        for y, row in enumerate(self.squares):
            for x, square in enumerate(row):
                square.x = int(self.padding_x + self.scale * x)
                square.y = int(
                    self.padding_y + 45 + self.scale * y
                )


    def on_scale_change(self):
        self.__rescale_tiles__()

        for row in self.squares:
            for square in row:
                square.width = int(self.scale)
                square.height = int(self.scale)

        self.update_squares()
        self.on_resize()


    def on_difficulty_change(self, option):
        self.board_x, self.board_y, self.mines = DIFFICULTIES[option]

        self.board.start_game(self.board_x, self.board_y, self.mines)

        self.mines_text = self.font.render(f"{self.mines}", False, (0, 0, 0))

        self.squares = [[
            Rect( int( x * self.scale + self.padding_x ),
                 int(y * self.scale + self.padding_y ), 
                 int(self.scale),
                 int(self.scale),
                 self.scaled_tiles[0],
                 x, y)
            for x in range(self.board_x)]
            for y in range(self.board_y)]

        self.probability_labels = [[[] for _ in range(self.board_x)] for _ in range(self.board_y)]

        self.on_resize()
        self.update_squares()
        self.get_network_data()

        self.solve_cooldown = 0

    def __rescale_tiles__(self):
        factor = self.scale / SPRITE_SIZE
        self.scaled_tiles = [
            pygame.transform.scale_by(tile, factor) for tile in self.tiles
        ]
        

if __name__ == "__main__":
    window = MinesweeperWindow()
    window.activate()

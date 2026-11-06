import torch
import pygame
from pygame.event import Event

from UIElements.UIElement import UIElement
from UIElements.DropdownMenu import DropdownMenu
from UIElements.Window import Window
from UIElements.Checkbox import Checkbox
from UIElements.Label import Label

from Minesweeper.minesweeper_board import MinesweeperBoard, COVERED_FIELD, MINED

from Minesweeper.model import MinesweeperModel, get_action, get_action_index, get_action_distribution

WINDOW_SIZE = (1280, 960)
SPRITE_SIZE = 8
TILESET_PATH = "Minesweeper/assets/Minesweeper_tiles_smol.png"
FONT_PATH = "Minesweeper/assets/BoldPixels.ttf"
TEST_NAME = "exp_multi_train_multi_test"

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

NUMBER_COLORS = [
    (0, 0, 0),
    (0, 0, 0),
    (0, 0, 0),
    (0, 0, 0),
    (0, 0, 0),
    (0, 0, 0),
    (0, 0, 0),
    (0, 0, 0),
]

PANEL_BG = WHITE
GAME_BG = (240, 240, 240)

SQUARE_NEUTRAL = WHITE
SQUARE_WIN = (140, 255, 140)

DIFFICULTIES = [
    (8, 8, 12),
    (18, 14, 40),
    (24, 20, 99),
]

model = MinesweeperModel(5)
model.load_state_dict( torch.load(f"./Minesweeper/{TEST_NAME}/model.pth") )

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
        self.label: Label | None = None

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

    def set_position(self, x, y):
        self.x = x
        self.y = y

        if self.label != None:
            self.label.set_center(self.x + self.width / 2, self.y + self.height / 2) 

    def set_text(self, font, text, color = (0, 0, 0)):
        if self.label == None:
            self.label = Label(self.x, self.y, font, text, color)

        self.label.set_center(self.x + self.width / 2, self.y + self.height / 2) 



    def __update_background__(self):
        color_image = pygame.Surface(self.image.get_size())
        color_image.fill(self.clr)

        self.background = self.img.copy()
        self.background.blit(color_image, (0, 0), special_flags = pygame.BLEND_RGB_MULT)


    def draw(self, surface: pygame.Surface):
        surface.blit(self.background, (self.x, self.y), special_flags=pygame.BLEND_RGB_MULT)

        if self.label != None:
            self.label.draw(surface)



class MinesweeperWindow(Window):
    def __init__(self) -> None:
        super(MinesweeperWindow, self).__init__(*WINDOW_SIZE, resizable=True)

        self.board_x = 0
        self.board_y = 0
        self.mines = 0

        self.scale = 48

        self.panel_width = 450
        self.scroll_speed = 1

        self.padding_x = 10
        self.padding_y = 50

        self.board_offset_x = 0
        self.board_offset_y = 0

        self.is_ctrl_pressed = False

        self.solve_cooldown = 0
        self.next_solve_id = (-1, -1)
        self.next_solve_action = -1

        self.font = pygame.font.Font(FONT_PATH, int(self.scale * 0.8))
        self.font_smol = pygame.font.Font(FONT_PATH, int(self.scale * 0.4))

        self.tiles_scale = 8
        spritesheet = pygame.image.load(TILESET_PATH)
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

        self.mines_text = Label(0, 0, self.font, "0")

        self.difficulty = DropdownMenu(
            200, 20, 300, 50, ["Mała", "Średnia", "Duża"], self.font, self.on_difficulty_change, start_value=0
        )

        self.show_output_label = Label(0, 0, self.font, "Pokaż wyjście agenta")
        self.show_network_output = Checkbox(0, 0, 50, 50, on_value_changed=self.get_network_data)

        self.auto_solve_label = Label(0, 0, self.font, "Auto rozwiązywanie")
        self.auto_solve_switch = Checkbox(0, 0, 50, 50)


        self.panel_elements = [[self.auto_solve_label, self.auto_solve_switch], [self.show_output_label, self.show_network_output], [self.difficulty]]

        self.on_difficulty_change(0)


    def __update__(self, delta: float):
        self.screen.fill(GAME_BG)

        for row in self.squares:
            for rect in row:
                rect.draw(self.screen)

        self.mines_text.draw(self.screen)


        pygame.draw.rect(self.screen, PANEL_BG, (0, 0, self.panel_width,  self.screen.get_size()[1]))

        for group in self.panel_elements:
            for element in group:
                element.draw(self.screen)


        if self.auto_solve_switch.checked and self.next_solve_action != -1 and self.next_solve_id != -1:
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
                self.scale = max(8, self.scale + (self.scroll_speed if button == 4 else -self.scroll_speed))
                self.on_scale_change()
            return

        mouse_pos = pygame.mouse.get_pos()
        if self.difficulty.on_click(mouse_pos) or self.show_network_output.on_click(mouse_pos) or self.auto_solve_switch.on_click(mouse_pos):
            return


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
                square.label = None

                if state == "w":
                    square.color = SQUARE_WIN
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
                        # square.label = self.font.render(state, False, BLACK)
                        square.set_text(self.font, state, NUMBER_COLORS[ int(state) ])
        
        mines = self.board.number_of_mines - self.board.flag_count
        # self.mines_text = self.font.render(f"{mines}", False, (0, 0, 0))
        self.mines_text.set_text(f"{mines}")


    def get_network_data(self, *args):
        if self.board.game_over:
            for y in range(self.board_y):
                for x in range(self.board_x):
                    if self.board.discovered_fields[ y ][ x ] == COVERED_FIELD or self.board.mines[ y ][ x ] == MINED:

                        if not self.board.has_won:
                            self.squares[y][x].color = SQUARE_NEUTRAL
                        self.squares[y][x].label = None


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


        if self.show_network_output.checked:
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
                    self.squares[y][x].color = ( SQUARE_NEUTRAL[0] * (1 - prob_click), SQUARE_NEUTRAL[1], SQUARE_NEUTRAL[2] * (1 - prob_click) )
                else:
                    self.squares[y][x].color = ( SQUARE_NEUTRAL[0], SQUARE_NEUTRAL[1] * (1 - prob_flag), SQUARE_NEUTRAL[2] * (1 - prob_flag) )
        else:
            for x in range(self.board_x):
                for y in range(self.board_y):
                    self.squares[y][x].color = SQUARE_NEUTRAL

        # for plane in dist.probs.reshape([3, self.board_y, self.board_x]):
        #     for row in plane:
        #         for value in row:
        #             print(f"{value * 100:.2f}\t", end="")
        #         print()
        #     print()

        actions = ["Click", "Flag", "Unflag"]
        ind, action = get_action(index, self.board_x, self.board_y)
        # print(f"{value.detach()[0].item():.3f}")
        # print(actions[action], (ind % self.board_x) + 1, (ind // self.board_x) + 1)

        self.next_solve_id = (ind % self.board_x, ind // self.board_x)
        self.next_solve_action = action

        


    def on_resize(self):
        width, height = self.screen.get_size()

        board_width = self.board_x * self.scale
        board_height = self.board_y * self.scale

        self.padding_x = (width - board_width) / 2
        self.padding_y = (height - board_height) / 2 

        for y, row in enumerate(self.squares):
            for x, square in enumerate(row):
                square.set_position(self.padding_x + self.scale * x + self.panel_width / 2, self.padding_y + self.scale * y)

        pad_x = 25
        pad_y = 10
        pos_x = pad_x
        pos_y = pad_y


        self.auto_solve_switch.x = self.panel_width - 50 - 10
        self.auto_solve_switch.y = pad_y
        self.auto_solve_label.set_position(pad_x, pad_y)


        self.show_network_output.x = self.panel_width - 50 - 10
        self.show_network_output.y = pad_y + 60
        self.show_output_label.set_position(pad_x, pad_y + 60)

        self.difficulty.x = (self.panel_width - self.difficulty.width) / 2
        self.difficulty.y = pad_y + 120



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

        self.mines_text.set_text(f"{self.mines}")

        self.squares = [[
            Rect( int( x * self.scale + self.padding_x + self.panel_width / 2),
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

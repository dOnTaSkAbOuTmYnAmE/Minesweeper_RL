import torch
import random

UNCOVERED_FIELD = UNFLAGGED = UNMINED = 0
COVERED_FIELD = FLAGGED = MINED = 1

class MinesweeperBoard:
    def __init__(self) -> None:
        self.size_x: int = 0
        self.size_y: int = 0

        self.are_mines_spawned = False
        self.game_over = True
        self.has_won = False

        self.number_of_mines = 0
        self.mines: list[list[int]] = [[]]
        self.proximity_numbers: list[list[int]] = [[]]
        self.discovered_fields: list[list[int]] = [[COVERED_FIELD] * self.size_x for _ in range(self.size_y)]
        self.flags: list[list[int]] = [[UNFLAGGED] * self.size_x for _ in range(self.size_y)]
        # self.mask: list[list[int]] = [[]]
    
    @property
    def flag_count(self):
        return sum( row.count(FLAGGED) for row in self.flags )

    @property
    def correct_flag_count(self):
        return [ self.flags[i // self.size_x][i % self.size_x] == self.mines[i // self.size_x][i % self.size_x] for i in range(self.size_y * self.size_x) ].count(True)

    @property
    def discovered_fields_count(self):
        return sum( row.count(UNCOVERED_FIELD) for row in self.flags )

    def spawn_mines(self, mines, excluded_x, excluded_y):
        num_mines = 0
        while num_mines < mines:
            x = random.randint(0, self.size_x - 1)
            y = random.randint(0, self.size_y - 1)

            if abs(x - excluded_x) <= 1 and abs(y - excluded_y) <= 1:
                continue

            if self.mines[y][x] == MINED:
                continue

            self.mines[y][x] = MINED
            num_mines += 1

        self.set_proximity_numbers()


    def set_proximity_numbers(self):

        def count_mines(self: MinesweeperBoard, pos_x, pos_y):
            count = 0
            for y in range( max(0, pos_y-1), min(pos_y + 2, self.size_y) ):
                for x in range( max(0, pos_x-1), min(pos_x + 2, self.size_x) ):
                    count += self.mines[y][x]

            return count

        self.proximity_numbers = [[count_mines(self, x, y) for x in range(self.size_x)] for y in range(self.size_y)]


    def start_game(self, size_x, size_y, mines):
        self.size_x = size_x
        self.size_y = size_y

        self.discovered_fields = [[COVERED_FIELD for _ in range(size_x)] for _ in range(self.size_y)]
        self.flags = [[UNFLAGGED for _ in range(size_x)] for _ in range(self.size_y)]
        self.mines = [[UNMINED for _ in range(size_x)] for _ in range(self.size_y)]
        self.proximity_numbers = [[0 for _ in range(size_x)] * self.size_x] * self.size_y

        self.number_of_mines = mines
        self.game_over = False
        self.has_won = False
        self.are_mines_spawned = False


    def toggle_flag(self, x, y):
        if self.game_over:
            return

        if not self.are_mines_spawned:
            self.spawn_mines(self.number_of_mines, x, y)

            self.are_mines_spawned = True

        if self.discovered_fields[y][x] == COVERED_FIELD:
            self.flags[y][x] = FLAGGED if self.flags[y][x] == UNFLAGGED else UNFLAGGED


    def click_field(self, x, y ):
        try:
            if self.game_over:
                return
            
            if not self.are_mines_spawned:
                self.spawn_mines(self.number_of_mines, x, y)

                self.are_mines_spawned = True


            if self.flags[y][x] == FLAGGED:
                self.flags[y][x] = UNFLAGGED

            if self.discovered_fields[y][x] == UNCOVERED_FIELD:
                return

            if self.mines[y][x] == MINED:
                self.game_over = True
                self.has_won = False

                for pos_y in range(0, self.size_y):
                    for pos_x in range(0, self.size_x):
                        if self.mines[pos_y][pos_x] == MINED:
                            self.discovered_fields[pos_y][pos_x] = UNCOVERED_FIELD

                return

            def propagete(self: MinesweeperBoard, pos_x, pos_y):
                if self.discovered_fields[pos_y][pos_x] == UNCOVERED_FIELD:
                    return
                if self.flags[pos_y][pos_x] == FLAGGED:
                    return
                
                self.discovered_fields[pos_y][pos_x] = UNCOVERED_FIELD

                if self.proximity_numbers[pos_y][pos_x] != 0:
                    return
                
                for y in range( max(0, pos_y-1), min(pos_y + 2, self.size_y)):
                    for x in range( max(0, pos_x-1), min(pos_x + 2, self.size_x)):
                        if x == pos_x and y == pos_y:
                            continue

                        propagete(self, x, y)


            # self.discovered_fields
            propagete(self, x, y)
            self.check_win()

        except IndexError as e:
            # print(y, x, self.size_y, self.size_x)
            print(f"x: {x} | {self.size_x}", f"y: {y} | {self.size_y}", sep="\n")

            raise e

    def play_multi_move(self, x, y):
        if self.game_over:
            return

        if self.discovered_fields[y][x] == COVERED_FIELD:
            return

        flags = 0
        # Count flags
        for pos_y in range( max(0, y-1), min(y + 2, self.size_y)):
            for pos_x in range( max(0, x-1), min(x + 2, self.size_x)):
                if x == pos_x and y == pos_y:
                        continue

                flags += self.flags[pos_y][pos_x]

        # Play unflagged mines
        if flags == self.proximity_numbers[y][x]:
            for pos_y in range( max(0, y-1), min(y + 2, self.size_y)):
                for pos_x in range( max(0, x-1), min(x + 2, self.size_x)):
                    if x == pos_x and y == pos_y:
                        continue

                    if self.flags[pos_y][pos_x] == FLAGGED:
                        continue

                    if self.mines[pos_y][pos_x] == MINED:
                        self.click_field(pos_x, pos_y)
        
        
        # Uncover fields
        if flags == self.proximity_numbers[y][x]:
            for pos_y in range( max(0, y-1), min(y + 2, self.size_y)):
                for pos_x in range( max(0, x-1), min(x + 2, self.size_x)):
                    if x == pos_x and y == pos_y:
                        continue

                    if self.flags[pos_y][pos_x] == FLAGGED:
                        continue

                    self.click_field(pos_x, pos_y)


    def check_win(self):
        for y in range(self.size_y):
            for x in range(self.size_x):
                if self.mines[y][x] == MINED:
                    continue

                if self.discovered_fields[y][x] == COVERED_FIELD:
                    return

        self.has_won = True
        self.game_over = True
        


    def get_board(self):
        def get_board_symbol(self: MinesweeperBoard, x, y):
            if self.game_over and self.has_won:
                if self.mines[y][x] == MINED:
                    return 'w'

            if self.flags[y][x] == FLAGGED:
                return 'f'
            
            if self.discovered_fields[y][x] == COVERED_FIELD:
                return 'x'

            if self.mines[y][x] == MINED:
                return 'm'

            return f'{self.proximity_numbers[y][x]}'

        state = [[ get_board_symbol(self, x, y) for x in range(self.size_x)] for y in range(self.size_y)]

        return state
            

    def is_game_over(self) -> bool:
        return self.game_over


    def encode(self, combined_numbers: bool) -> torch.Tensor:
        stacked_board = [ [[1] * self.size_x] * self.size_y, 
                         [[self.number_of_mines / (self.size_x * self.size_y)] * self.size_x] * self.size_y, 
                         self.discovered_fields, 
                         self.flags ]

        if self.are_mines_spawned:
            discovered_numbers = [
                [self.proximity_numbers[y][x] if self.discovered_fields[y][x] == UNCOVERED_FIELD else 0 for x in range(self.size_x)]
                for y in range(self.size_y)
            ]
        else:
            discovered_numbers = [[0] * self.size_x] * self.size_y


        if combined_numbers:
            stacked_board.append(discovered_numbers)
        else:            
            planes = [
                [
                    [
                        1 if discovered_numbers[y][x] == z else 0 for x in range(self.size_x)
                    ] 
                    for y in range(self.size_y)
                ] 
                for z in range(1, 9)
            ] 

            stacked_board.extend(planes)


        return torch.tensor(stacked_board, dtype=torch.float)


    def padded_encode(self, combined_numbers: bool, pad_size: int):
        def expand(mask: list[list[int]]):
            return [[ mask[y][x] if  y < self.size_y and x < self.size_x  else 0  for x in range(pad_size) ] for y in range(pad_size)]


        mask = [[ 1 if x < self.size_x else 0  for x in range(pad_size)] for y in range(self.size_y)]
        mask.extend( [[0] * pad_size] * (pad_size - self.size_y))


        # mines_ratio = (self.number_of_mines - self.flag_count) / self.number_of_mines
        mines_ratio = self.number_of_mines / (self.size_x * self.size_y)
        mines = [[mines_ratio] * pad_size] * pad_size


        discovered_fields = expand( self.discovered_fields )
        flags = expand(self.flags)

        stacked_board = [mask, mines, discovered_fields, flags]

        if self.are_mines_spawned:
            discovered_numbers = [
                [self.proximity_numbers[y][x] if self.discovered_fields[y][x] == UNCOVERED_FIELD else 0 for x in range(self.size_x)]
                for y in range(self.size_y)
            ]
        else:
            discovered_numbers = [[0] * self.size_x] * self.size_y


        discovered_numbers = expand(discovered_numbers)


        if combined_numbers:
            stacked_board.append(discovered_numbers)
        else:            
            planes = [
                [
                    [
                        1 if discovered_numbers[y][x] == z else 0 for x in range(pad_size)
                    ] 
                    for y in range(pad_size)
                ] 
                for z in range(1, 9)
            ] 

            stacked_board.extend(planes)


        try:
            return torch.tensor(stacked_board, dtype=torch.float)
        except:
            for plane in stacked_board:
                for row in plane:
                    print(row)
                print()

            print(self.size_y, self.size_x)
            exit()

    def get_mask(self, pad_size: int | None = None):
        mask_y = self.size_y if pad_size is None else pad_size
        mask_x = self.size_x if pad_size is None else pad_size

        click_mask = [[
                0 if y < self.size_y and x < self.size_x and self.discovered_fields[y][x] == COVERED_FIELD else -torch.inf
             for x in range(mask_x)]
            for y in range(mask_y)]
        # click_mask = [[
        #         0 if y < self.size_y and x < self.size_x else -torch.inf
        #      for x in range(mask_x)]
        #     for y in range(mask_y)]

        flag_mask = [[
                0 if y < self.size_y and x < self.size_x and self.discovered_fields[y][x] == COVERED_FIELD and self.flags[y][x] == UNFLAGGED
                else -torch.inf
             for x in range(mask_x)]
            for y in range(mask_y)]

        unflag_mask = [[
            0 if y < self.size_y and x < self.size_x and self.flags[y][x] == FLAGGED else -torch.inf
             for x in range(mask_x)]
            for y in range(mask_y)]

        return torch.tensor( [click_mask, flag_mask, unflag_mask], dtype=torch.float)



if __name__ == "__main__":
    import sys

    board = MinesweeperBoard()
    board.start_game(6, 9, 15)

    print(sys.getsizeof(board))

    
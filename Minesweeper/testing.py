from parameters import *
from model import MinesweeperModel, get_action
from minesweeper_board import MinesweeperBoard, MINED
# from bit_minesweeper_board import MinesweeperBoard
from data_collection import game_data

import random
import numpy as np

def test_model(model: MinesweeperModel):
    span = MAX_TEST_SIZE - MIN_TEST_SIZE + 1

    won = [[0 for _ in range(span)] for _ in range(span)]
    lenghts = [[[] for _ in range(span)] for _ in range(span)]


    iter_range = range(MIN_TEST_SIZE, MAX_TEST_SIZE + 1)

    correct_clicks = 0
    mine_clicks = 0

    correct_flags = 0
    incorrect_flags = 0
    flags_removed = 0

    rewards_per_game = []

    for Y in iter_range:
        for X in iter_range:
            games = GAMES_PER_TEST
            while games > 0:                
                boards = [MinesweeperBoard() for _ in range( min(games, PARALLEL_TRAINING_GAMES) )]
                games -= PARALLEL_TRAINING_GAMES
                
                for board in boards:
                    board_mines = (X * Y * random.randint(120, 160)) // 1000
                    board.start_game( X, Y, board_mines )

                with torch.no_grad():
                    states, masks, all_actions, old_log_probs, values, all_rewards = game_data(
                        model           = model, 
                        device          = device, 
                        MIN_SIZE        = MIN_TEST_SIZE,
                        MAX_SIZE        = MAX_TEST_SIZE,
                        random_moves    = 0,
                        passed_boards   = boards,
                        parallel_boards = games,
                        pad_boards      = False)


                for i, test_board in enumerate(boards):
                    rewards = all_rewards[i]
                    actions = all_actions[i]

                    rewards_per_game.append(rewards)

                    if test_board.has_won:
                        won[Y - MIN_TEST_SIZE][X - MIN_TEST_SIZE] += 1

                    lenghts[Y - MIN_TEST_SIZE][X - MIN_TEST_SIZE].append(len(rewards))


                    for j, action in enumerate(actions):
                        index, act = get_action(action, X, Y)
                        x = index.item() % X
                        y = index.item() // X
                        
                        if act.item() == 0:
                            if test_board.mines[y][x] == MINED:
                                mine_clicks += 1
                            else:
                                correct_clicks += 1

                        elif act.item() == 1:

                            try:
                                if test_board.mines[y][x] == MINED:
                                    correct_flags += 1
                                else:
                                    incorrect_flags += 1
                            except:
                                print(f"x = {x}, y = {y}, {test_board.mines}, {j}, {len(actions)}")
                                for row in test_board.get_board():
                                    print(row)
                                exit()

                        elif act.item() == 2:
                            flags_removed += 1

    total_games = GAMES_PER_TEST * (span**2)

    if correct_clicks + mine_clicks != 0:
        print( f"Average clicks: {(correct_clicks + mine_clicks) / total_games:.2f}")
        print( f"Correct clicks: {correct_clicks * 100 / (correct_clicks + mine_clicks):.2f}%" )
        print( f"Mine clicks: {mine_clicks * 100 / (correct_clicks + mine_clicks):.2f}%" )
    else:
        print("No clicks")

    if correct_flags + incorrect_flags != 0:
        print( f"Average flags placed: { (correct_flags + incorrect_flags)/total_games:.2f}")
        print( f"Average flags removed: {flags_removed / total_games:.2f}" )
        print( f"Correct flags: {correct_flags * 100 /  (correct_flags + incorrect_flags):.2f}%" )
        print( f"Incorrect flags: {incorrect_flags * 100 / (correct_flags + incorrect_flags):.2f}%" )
    else:
        print("No flags placed")

    lenghts = np.array(lenghts)


    if span > 1:
        print("Win rates:")

        print("Y \\ X |", "".join([f"{ str(i):<4}| " for i in iter_range]) )
        
        percent_sum = 0
        for Y in iter_range:
            print(f"  {Y:<3} |", end="")

            for X in iter_range:
                percentage = f"{won[Y - MIN_TEST_SIZE][X - MIN_TEST_SIZE] * 100 // GAMES_PER_TEST}%"
                print(f" { percentage:<4}|", end="")

                percent_sum += won[Y - MIN_TEST_SIZE][X - MIN_TEST_SIZE]
            print()

        print(f"Average win rate: { percent_sum * 100 / total_games:.2f}%")

        
        print("Y \\ X |", "".join([f"{ str(i):<11}| " for i in iter_range]) )
        for Y in iter_range:
            print(f"  {Y:<3} |", end="")

            for X in iter_range:
                average = f"{lenghts[Y - MIN_TEST_SIZE][X - MIN_TEST_SIZE].mean():.2f}"
                std = f"{lenghts[Y - MIN_TEST_SIZE][X - MIN_TEST_SIZE].std():.2f}"
                print(f" { average}/{std} ", end="")
            print()

    else:
        print(f"Win rate: {won[0][0] * 100 / GAMES_PER_TEST:.2f}%")        

    print(f"Average game length: {lenghts.mean():.2f}, Deviation: {lenghts.std():.2f}")

    print("\n")

    return won, lenghts, (correct_clicks, mine_clicks), (correct_flags, incorrect_flags, flags_removed), rewards_per_game
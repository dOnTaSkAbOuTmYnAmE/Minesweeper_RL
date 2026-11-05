from minesweeper_board import MinesweeperBoard, UNCOVERED_FIELD, COVERED_FIELD, MINED, FLAGGED
# from bit_minesweeper_board import MinesweeperBoard
from model import MinesweeperModel, get_action_distribution, get_action
from parameters import *

import traceback
import random
import torch

ACTION_CLICK = 0
ACTION_FLAG = 1
ACTION_UNFLAG = 2

def get_reward(board, x, y, action):
    reward = 0

    # if board.mines_spawned:
    if board.are_mines_spawned:
        # if board.discovered_fields[ y ][ x ] == UNCOVERED_FIELD:
        #     return -10


        if action == ACTION_FLAG:
            if board.mines[y][x] == MINED:
                reward += 0.3
            else:
                reward -= 0.3          # Flagging an incorrect spot

        if action == ACTION_UNFLAG:
            if board.mines[y][x] == MINED:
            # if board.mines[y] & (1 << x) == 1:
                reward -= 0.5         # Unflagging an incorrect spot

        # else: 
        #     if board.flags[y][x] == FLAGGED:
        #         if board.mines[y][x] == MINED:
        #     # if board.flags[y] & (1 << x) == 1:
        #     #     if board.mines[y] & (1 << x) == 1:
        #             reward -= 5          # Clicking on a correctly flagged spot
            
        #     if board.mines[y][x] != MINED:
        #     # if board.mines[y] & (1 << x) == 1:
        #         # has_neighbor = False
        #         # for pos_y in range( max(0, y-1), min(y + 2, board.size_y) ):
        #         #     for pos_x in range( max(0, x-1), min(x + 2, board.size_x) ):
        #         #         if board.discovered_fields[pos_y][pos_x] == UNCOVERED_FIELD:
        #         #             has_neighbor = True
        #         #             break
        #         #     if has_neighbor:
        #         #         break

        #         # if has_neighbor:
        #         #     reward += 5          # Clicking on a correct spot
        #         # else:
        #             reward += 2
        #     else:
        #         reward -= 10          # Clicking on a mine

    elif action != ACTION_CLICK:
        reward -= 0.5                 # Flagging or Unflagging before mines are spawned
    else:
        reward += 0.5                 # Clicking before mines are spawned

    return reward


# MIN_BOARD_SIZE = 3
# MAX_BOARD_SIZE = 4
# history = []


def game_data(model: MinesweeperModel, 
              device, 
              MIN_SIZE, MAX_SIZE, 
              random_moves: float = 1, 
              passed_boards: list[MinesweeperBoard] | None = None, 
              parallel_boards: int = 1,
              pad_boards: bool = True):
    # global history
    
    parallel_boards = max(1, parallel_boards)

    if passed_boards is None:
        boards = [ MinesweeperBoard() for _ in range(parallel_boards) ]

        for board in boards:
            board_x = random.randint(MIN_SIZE, MAX_SIZE)
            board_y = random.randint(MIN_SIZE, MAX_SIZE)
            board_mines = (board_x * board_y * random.randint(120, 160)) // 1000
            board.start_game(board_x, board_y, board_mines)
    else:
        boards = passed_boards
        parallel_boards = len(boards)


    max_moves = [ board.size_x * board.size_y for board in boards ]
    move_counts = [0 for _ in range(parallel_boards)]

    states = [[] for _ in range(parallel_boards)]
    masks = [[] for _ in range(parallel_boards)]
    actions = [[] for _ in range(parallel_boards)]
    probabilities = [[] for _ in range(parallel_boards)]
    values = [[] for _ in range(parallel_boards)]
    rewards = [[] for _ in range(parallel_boards)]

    board_size_x = MAX_SIZE if pad_boards else boards[0].size_x
    board_size_y = MAX_SIZE if pad_boards else boards[0].size_y


    encodes = torch.empty((parallel_boards, MODEL_CHANNELS, board_size_y, board_size_x), # type: ignore
                            dtype=torch.float32, 
                            device= device)
    temp_masks = torch.empty((parallel_boards, 3, board_size_y, board_size_x), # type: ignore
                            dtype=torch.float32,
                            device=device)


    while any( max_moves[i] > move_counts[i] and not boards[i].game_over for i in range(parallel_boards) ):
        for y, board in enumerate(boards):
            if not board.is_game_over():
                if pad_boards:
                    encodes[y] = board.padded_encode(USE_COMBINED_NUMBERS, MAX_SIZE)
                    temp_masks[y] = board.get_mask(MAX_SIZE)
                else:
                    encodes[y] = board.encode(USE_COMBINED_NUMBERS)
                    temp_masks[y] = board.get_mask()


        with torch.inference_mode():
            move, value = model( encodes )

            distribution = get_action_distribution(move, temp_masks)

            if parallel_boards != 1:
                sampled_actions = distribution.sample().squeeze(-1)
            else:
                sampled_actions = distribution.sample()
            
            rand = torch.rand(parallel_boards, device=device) >= random_moves

            best_moves = torch.argmax(distribution.probs, dim=1)
            chosen_actions = torch.where(
                rand, best_moves, sampled_actions
            )

            indexes = chosen_actions.cpu()
            log_prob = distribution.log_prob(chosen_actions)

        for i in range(parallel_boards):
            if boards[i].is_game_over() or move_counts[i] >= max_moves[i]:
                # history[i] += "Game is over, skipping \n"
                continue

            agent_move, agent_action = get_action(indexes[i], board_size_x, board_size_y)

            agent_x = int(agent_move % board_size_x)
            agent_y = int(agent_move // board_size_x)

            # CALCULATE INTERMEDIATE REWARDS
            action_reward = get_reward(boards[i], agent_x, agent_y, agent_action)
            # action_reward = 0

            # discovered = boards[i].discovered_fields_count

            try:
                if agent_action == 0:
                    boards[i].click_field(agent_x, agent_y)
                else:
                    boards[i].toggle_flag(agent_x, agent_y)

                move_counts[i] += 1
            
            except Exception as e:
                print("Error while gathering data at board",i)
                print(move_counts[i])
                print(f"{agent_y} | {boards[i].size_y}", f"{agent_x} | {boards[i].size_x}", f"{indexes[i]} ( {agent_action} | {agent_move} - {move} )", sep="\n")

                for row in boards[i].get_board():
                    print(row)

                traceback.print_exc()

                exit()


            # for row in boards[i].get_board():
            #     history[i] += " ".join(row) + '\n'
            # history[i] += '\n' 

            # acts = ["Click", "Flag", "Unflag"]
            # history[i] += f"{acts[agent_action]}, {agent_move} ({agent_x}, {agent_y})\n\n"

            if boards[i].is_game_over():
                if boards[i].has_won:
                    action_reward += 1             # Won
                else:
                    action_reward -= 1             # Lost
            elif move_counts[i] >= max_moves[i]:
                action_reward -= 1                 # Ran out of moves
            # else:
                # action_reward -= 1

            # else:
            #     action_reward += boards[i].discovered_fields_count - discovered # bonus for uncovering fields

            states[i].append( encodes[i].detach().clone() )
            masks[i].append( temp_masks[i].detach().clone() )
            actions[i].append( chosen_actions[i].detach().clone() )
            probabilities[i].append( log_prob[i].detach().clone() )
            values[i].append( value[i].detach().clone() )
            rewards[i].append( action_reward * REWARDS_SCALE )

        if all(board.is_game_over() for board in boards):
            break


    return states, masks, actions, probabilities, values, rewards

if __name__ == "__main__":
    random.seed(22187)
    game_data(MinesweeperModel(5, device), device, 8, 10, random_moves=1, parallel_boards = 4)

    # print("\n\n".join(history))
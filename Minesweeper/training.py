from minesweeper_board import MinesweeperBoard, MINED
from model import MinesweeperModel, get_action, get_action_distribution
from data_collection import game_data
from parameters import *
from testing import test_model

import torch
import time
import hickle as hkl
import sys
import os


if len(sys.argv) <= 1:
    print("No save path provided")
    exit()

dir_name = sys.argv[1]
abs_path = f"{os.path.dirname(os.path.abspath(__file__))}/{dir_name}"

if os.path.exists(abs_path):
    print("Path already exists!")
    exit()

board = MinesweeperBoard()
model = MinesweeperModel(MODEL_CHANNELS, device=device)
# model.load_state_dict( torch.load("./8_8_flags/model.pth") )


print(f"GAMMA {GAMMA}, ENTR_COEF {ENTROPY_COEFFICIENT}, VALUE_IMP {VALUE_IMPACT}, EPSILON {CLIP_EPSILON}")
print(f"LR: SHARED {SHARED_LEARNING_RATE}, ACTION {ACTION_LEARNING_RATE}, VALUE {VALUE_LEARNING_RATE}")
print(f"EPOCHS {EPOCHS}, GAMES PER ITERATION {GAMES}, ITERATIONS {ITERATIONS}, TEST EVERY {BATCHES_PER_TEST} BATCHES")
print(f"MIN TRAINING BOARD SIZE {MIN_TRAIN_SIZE}x{MIN_TRAIN_SIZE}, MAX BOARD SIZE {MAX_TRAIN_SIZE}x{MAX_TRAIN_SIZE}")
print(f"MIN TESTING BOARD SIZE {MIN_TEST_SIZE}x{MIN_TEST_SIZE}, MAX BOARD SIZE {MAX_TEST_SIZE}x{MAX_TEST_SIZE}")
print()

optimizer = torch.optim.AdamW([
    {
        "params": model.in_conv.parameters(),
        "lr": SHARED_LEARNING_RATE,
    },
    {
        "params": model.action_head.parameters(),
        "lr": ACTION_LEARNING_RATE,
    },
    {
        "params": model.value_head.parameters(),
        "lr": VALUE_LEARNING_RATE,
    },
])

test_points = []

# print("Before training test:")
# test_points.append(test_model(model))


losses = []
value_losses = []
entropies = []
policy_losses = []

training_start = time.perf_counter()

for game_index in range(1, ITERATIONS + 1):
    states  = []
    masks   = []
    actions = []
    old_log_probs = []
    values  = []
    advantages = []
    returns = []

    start = time.perf_counter()

    games = GAMES
    while games > 0:
        temp_states, temp_masks, temp_actions, temp_old_log_probs, temp_values, temp_rewards = game_data(
            model           = model, 
            device          = device, 
            MIN_SIZE        = MIN_TRAIN_SIZE, 
            MAX_SIZE        = MAX_TRAIN_SIZE, 
            random_moves    =1, 
            parallel_boards =min(games, PARALLEL_TRAINING_GAMES))
        
        games -= PARALLEL_TRAINING_GAMES

        for i in range(PARALLEL_TRAINING_GAMES):
            temp_returns = []

            if GAMMA == 0:
                temp_returns = temp_rewards
            else:
                G = 0

                for reward in reversed(temp_rewards[i]):
                    G = reward + GAMMA * G
                    temp_returns.insert(0, G)

            temp_returns = torch.tensor(temp_returns, dtype=torch.float32, device=device)
            local_values = torch.stack(temp_values[i]).detach().reshape(-1)
            temp_advantages = temp_returns - local_values

            states.extend(temp_states[i])
            masks.extend(temp_masks[i])
            actions.extend(temp_actions[i])
            old_log_probs.extend(temp_old_log_probs[i])
            values.extend(local_values.cpu())
            advantages.extend(temp_advantages.cpu())
            returns.extend(temp_returns.cpu())

    states = torch.stack(states).to(device)
    masks = torch.stack(masks).to(device)
    old_log_probs = torch.stack(old_log_probs).squeeze(-1).to(device)
    actions = torch.stack(actions).squeeze(-1).to(device)

    values = torch.stack(values).to(device)
    returns = torch.stack(returns).to(device)
    advantages = torch.stack(advantages).to(device)


    advantages = ( advantages - advantages.mean() ) / (advantages.std(unbiased=False) + 1e-8)
    print(f"\rBatch {game_index % BATCHES_PER_TEST}/{BATCHES_PER_TEST}, collection {(game_index // BATCHES_PER_TEST) + 1}/{ITERATIONS//BATCHES_PER_TEST}", end="")
    # print(f"allocated: {round(torch.cuda.memory_allocated() / 1024**2)} MB, reserved: {round(torch.cuda.memory_reserved() / 1024**2)}MB")

    if game_index % BATCHES_PER_TEST == 0:
        print("\033[2K\r", end="")

        # print("returns: ",
        #     f"MEAN {returns.mean().item():.6} ",
        #     f"STD {returns.std().item():.6} ",
        #     f"MIN {returns.min().item():.6} ",
        #     f"MAX {returns.max().item():.6} ",
        #     sep="\t")

        # print("values: ",
        #     f"MEAN {values.mean().item():.6}",
        #     f"STD {values.std().item():.6}",
        #     f"MIN {values.min().item():.6}",
        #     f"MAX {values.max().item():.6}",
        #     sep="\t")

        # print("advantages: ",
        #     f"MEAN {advantages.mean().item():.6}",
        #     f"STD {advantages.std().item():.6}",
        #     f"MIN {advantages.min().item():.6}",
        #     f"MAX {advantages.max().item():.6}",
        #     sep="\t")

        # value_mse = ((values - returns) ** 2).mean()

        # return_var = returns.var(unbiased=False)

        # explained_variance = 1 - value_mse / (return_var + 1e-8)

        # print(f"explained variance: {explained_variance.item():.6}")

    for epoch in range(1, EPOCHS + 1):
        logits, values = model(states)

        dist = get_action_distribution(logits, masks)
        entropy = dist.entropy().mean()

        new_log_probs = dist.log_prob(actions)

        ratios = torch.exp(
            new_log_probs - old_log_probs
        )

        unclipped = ratios * advantages
        clipped = torch.clamp(
            ratios,
            1.0 - CLIP_EPSILON,
            1.0 + CLIP_EPSILON,
        ) * advantages

        policy_loss = -torch.min(
            unclipped,
            clipped,
        ).mean()

        value_loss = torch.nn.functional.mse_loss(
            values.squeeze(-1),
            returns,
        )
        
        loss = (
            policy_loss + value_loss * VALUE_IMPACT - entropy * ENTROPY_COEFFICIENT
        )

        optimizer.zero_grad()
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)
        optimizer.step()

        losses.append(float(loss.detach()))
        policy_losses.append(float(policy_loss.detach()))
        value_losses.append(float(value_loss.detach()))
        entropies.append(float(entropy.detach()))

    if game_index % BATCHES_PER_TEST == 0:
        test_points.append(test_model(model))

training_time = time.perf_counter() - training_start

os.makedirs(abs_path)

torch.save(model.state_dict(), f"{abs_path}/model.pth")

hkl.dump([losses, policy_losses, value_losses, entropies], f"{abs_path}/losses.hkl", mode="w")
hkl.dump(test_points, f"{abs_path}/training_progress.hkl", mode="w")
with open(f"{abs_path}/model.txt", "w") as file:
    file.write( str(model) )
with open(f"{abs_path}/parameters.txt", "w") as file:
    file.write(
f"""Training board sizes: {MIN_TRAIN_SIZE}x{MIN_TRAIN_SIZE} -- {MAX_TRAIN_SIZE}x{MAX_TRAIN_SIZE}
Testing board sizes: {MIN_TEST_SIZE}x{MIN_TEST_SIZE} -- {MAX_TEST_SIZE}x{MAX_TEST_SIZE}
Combined numbers: {USE_COMBINED_NUMBERS}
Games per training batch: {GAMES}
Iterations: {ITERATIONS}
Gamma: {GAMMA}
Epsilon: {CLIP_EPSILON}
Value impact: {VALUE_IMPACT}
Entropy coefficient: {ENTROPY_COEFFICIENT}
Epochs: {EPOCHS}
Learning rates:
    Shared: {SHARED_LEARNING_RATE}
    Action: {ACTION_LEARNING_RATE}
    Value: {VALUE_LEARNING_RATE}
Batches between tests: {BATCHES_PER_TEST}
Games per test: {GAMES_PER_TEST}
""")

minutes = training_time // 60
hours = int(minutes // 60)
seconds = int(training_time // 60)
minutes = int(minutes % 60)

print(f"Training took {hours} hours {minutes} minutes {seconds} seconds")   

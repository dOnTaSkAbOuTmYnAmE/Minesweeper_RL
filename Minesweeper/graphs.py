import hickle as hkl
import matplotlib.pyplot as plt

import sys
import os
import numpy as np
from parameters import *

if len(sys.argv) <= 1:
    print("No load dir provided")
    exit()

dir_name = sys.argv[1]
path = os.path.dirname(os.path.abspath(__file__))
dir_path = f"{path}/{dir_name}"

datas = hkl.load(f"{dir_path}/losses.hkl")

r = range(len(datas[0]))

for data in datas[0:3]:
    plt.plot(r, data)

plt.savefig(f"{dir_path}/loss.png")

plt.clf()
plt.plot(r, datas[3])
plt.savefig(f"{dir_path}/entropy.png")

plt.clf()

datas = hkl.load(f"{dir_path}/training_progress.hkl")

# board_sizes = range(MIN_TEST_SIZE, MAX_TEST_SIZE + 1)
board_sizes = range(0, MAX_TEST_SIZE - MIN_TEST_SIZE + 1)

figures = [
    plt.figure(i) for i in range(3)
]

plots = [
    fig.add_subplot() for fig in figures
]


won_games = [[] for _ in board_sizes]
avg_correct_clicks = []

avg_lenghts = []
rewards = []

for point in datas:
    won, lenghts, (correct_clicks, mine_clicks), (correct_flags, incorrect_flags, flags_removed), rewards_per_game = point

    for size in board_sizes:
        won_games[size].append((won[size][size] / GAMES_PER_TEST) * 100)
        
    avg_correct_clicks.append((correct_clicks / (correct_clicks + mine_clicks)) * 100)

    avg_lenghts.append(np.array(lenghts).mean())

    rewards.append(np.array([sum(game) / REWARDS_SCALE for game in rewards_per_game]).mean())


for i, won in enumerate(won_games, MIN_TEST_SIZE):
    r = range(0, len(won) * BATCHES_PER_TEST, BATCHES_PER_TEST)
    plots[0].plot(r, won, label=f"Win rate {i}x{i}")
# plots[0].plot(r, avg_correct_clicks, label="Correct click rate")
plots[1].plot(r, avg_lenghts)
plots[2].plot(r, rewards)


for plot in plots:
    plot.set_xlabel("Iteration")

plots[0].set_ylabel("Percent")
plots[0].legend()

plots[1].set_ylabel("Average game length")
plots[2].set_ylabel("Average rewards gained")


for i, fig in enumerate(figures):
    fig.savefig(f"{dir_path}/fig_{i}.png")
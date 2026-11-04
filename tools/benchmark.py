"""Measure physics and software drawing; excludes GPU upload and the frame cap."""

import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import time

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame
from rendering import CircleRenderer, make_surface
from simulation import Simulation, candidate_pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=int, default=600)
    parser.add_argument('--count', type=int, default=100)
    args = parser.parse_args()
    if args.frames < 1:
        parser.error('--frames must be positive')
    simulation = Simulation((1920, 1080), args.count, seed=1)
    renderer = CircleRenderer(simulation.circles)
    surface = make_surface((1920, 1080))
    all_pairs = args.count * (args.count - 1) // 2
    nearby = len(list(candidate_pairs(simulation.circles)))
    physics, drawing = [], []
    for frame in range(args.frames + 30):
        start = time.perf_counter()
        simulation.update(mouse=(960, 540))
        middle = time.perf_counter()
        renderer.draw(surface)
        end = time.perf_counter()
        if frame >= 30:
            physics.append((middle - start) * 1000)
            drawing.append((end - middle) * 1000)
    print(json.dumps({'circles': args.count, 'frames': args.frames,
                      'initial_pairs': nearby, 'all_pairs': all_pairs,
                      'physics_median_ms': round(statistics.median(physics), 3),
                      'draw_median_ms': round(statistics.median(drawing), 3)}, indent=2))


if __name__ == '__main__':
    main()

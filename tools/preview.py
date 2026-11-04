"""Save a seeded frame through the actual postprocessing shader, without a window."""

import argparse
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import moderngl
import pygame
from rendering import CircleRenderer, PostProcessor, make_surface
from simulation import Simulation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, default=Path('docs/preview.png'))
    args = parser.parse_args()
    options = {'backend': 'egl'} if sys.platform == 'linux' else {}
    context = moderngl.create_standalone_context(require=330, **options)
    target = post = None
    try:
        size = (1280, 720)
        target = context.simple_framebuffer(size)
        target.use()
        simulation = Simulation(size, seed=1)
        for _ in range(120):
            simulation.update(mouse=(640, 360))
        surface = make_surface(size)
        CircleRenderer(simulation.circles).draw(surface)
        post = PostProcessor(context, size)
        post.draw(surface)
        image = pygame.image.frombytes(target.read(components=3, alignment=1), size, 'RGB')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(pygame.transform.flip(image, False, True), str(args.output))
        print(args.output)
    finally:
        if post is not None:
            post.close()
        if target is not None:
            target.release()
        context.release()


if __name__ == '__main__':
    main()

import argparse
import pygame

from rendering import CircleRenderer, PostProcessor, make_surface
from simulation import Simulation

FIXED_STEP = 1 / 60


class App:
    def __init__(self, size=None, count=100, seed=None, postprocessing=True):
        self.post = None
        self.context = None
        self.closed = False
        pygame.init()
        try:
            self.size = tuple(size or pygame.display.get_desktop_sizes()[0])
            self.simulation = Simulation(self.size, count, seed)
            if postprocessing:
                import moderngl
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK,
                                                pygame.GL_CONTEXT_PROFILE_CORE)
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_FLAGS,
                                                pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG)
                self.window = pygame.display.set_mode(self.size, pygame.OPENGL | pygame.DOUBLEBUF)
                try:
                    self.context = moderngl.create_context(require=330)
                    self.post = PostProcessor(self.context, self.size)
                except moderngl.Error as error:
                    raise RuntimeError(f"OpenGL initialization failed: {error}") from error
            else:
                self.window = pygame.display.set_mode(self.size)
            pygame.display.set_caption("Circle collisions")
            self.surface = make_surface(self.size)
            self.renderer = CircleRenderer(self.simulation.circles)
            self.clock = pygame.time.Clock()
            self.accumulator = 0.0
            self.running = True
            self.mouse = (-1000, -1000)
            self.pressed = False
        except Exception:
            self.close()
            raise

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN
                    and event.key in (pygame.K_ESCAPE, pygame.K_F1)):
                self.running = False
            elif event.type == pygame.MOUSEMOTION:
                self.mouse = event.pos
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                self.mouse = event.pos
                if event.button == 1:
                    self.pressed = event.type == pygame.MOUSEBUTTONDOWN
            elif event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWLEAVE):
                self.pressed = False
                self.mouse = (-1000, -1000)

    def frame(self, elapsed):
        self.events()
        if not self.running:
            return False
        self.accumulator += min(max(elapsed, 0), 0.25)
        stepped = False
        while self.accumulator + 1e-12 >= FIXED_STEP:
            self.simulation.update(FIXED_STEP, self.mouse, self.pressed)
            self.accumulator -= FIXED_STEP
            stepped = True
        # Update the cursor fade even on frames without a physics step.
        if not stepped:
            self.simulation.update(0, self.mouse)
        self.renderer.draw(self.surface)
        if self.post is not None:
            self.post.draw(self.surface)
        else:
            self.window.blit(self.surface, (0, 0))
        pygame.display.flip()
        return True

    def run(self):
        while self.frame(self.clock.tick(60) / 1000):
            pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.post is not None:
            self.post.close()
        if self.context is not None:
            self.context.release()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Moving circles with curved-screen postprocessing")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--size", type=int, nargs=2, metavar=("WIDTH", "HEIGHT"))
    parser.add_argument("--seed", type=int, help="repeat a starting arrangement")
    parser.add_argument("--no-postprocessing", action="store_true", help="use the software renderer")
    args = parser.parse_args()
    app = None
    try:
        app = App(args.size, args.count, args.seed, not args.no_postprocessing)
        app.run()
    except (pygame.error, RuntimeError, ImportError, ValueError) as error:
        parser.exit(1, f"Cannot start: {error}\nTry --no-postprocessing if OpenGL is unavailable.\n")
    finally:
        if app is not None:
            app.close()


if __name__ == "__main__":
    main()

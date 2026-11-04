import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

from dataclasses import replace
import tempfile
import unittest
from unittest.mock import patch
import pygame

from main import App
from rendering import CircleRenderer, make_surface
from simulation import Circle


class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = App((640, 360), count=10, seed=2, postprocessing=False)
        pygame.event.clear()

    def tearDown(self):
        self.app.close()

    def test_press_is_held_until_release(self):
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(200, 100)))
        self.app.frame(1 / 60)
        self.assertTrue(self.app.pressed)
        self.app.frame(1 / 60)
        self.assertTrue(self.app.pressed)
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(210, 110)))
        self.app.frame(1 / 60)
        self.assertFalse(self.app.pressed)
        self.assertEqual(self.app.mouse, (210, 110))

    def test_focus_loss_releases_mouse(self):
        self.app.pressed = True
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.app.frame(0)
        self.assertFalse(self.app.pressed)

    def test_quit_does_not_render_after_closing_display(self):
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        with patch.object(self.app.renderer, 'draw') as draw:
            self.assertFalse(self.app.frame(1 / 60))
            draw.assert_not_called()

    def test_both_exit_keys(self):
        for key in (pygame.K_ESCAPE, pygame.K_F1):
            self.app.running = True
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
            self.assertFalse(self.app.frame(0))

    def test_fixed_physics_is_independent_of_render_rate(self):
        initial = [replace(circle) for circle in self.app.simulation.circles]
        for _ in range(60):
            self.app.frame(1 / 60)
        expected = [replace(circle) for circle in self.app.simulation.circles]
        self.app.simulation.circles[:] = initial
        self.app.accumulator = 0
        for _ in range(30):
            self.app.frame(1 / 30)
        self.assertEqual(self.app.simulation.circles, expected)

    def test_zero_elapsed_does_not_move_circles(self):
        expected = [replace(circle) for circle in self.app.simulation.circles]
        self.app.frame(0)
        self.assertEqual(self.app.simulation.circles, expected)

    def test_drawing_allocates_no_circle_surfaces(self):
        with patch('pygame.Surface', side_effect=AssertionError('allocated during draw')):
            self.app.renderer.draw(self.app.surface)
            self.app.renderer.draw(self.app.surface)

    def test_odd_width_rgba_upload_is_contiguous(self):
        surface = make_surface((641, 123))
        surface.fill((12, 34, 56))
        view = memoryview(surface.get_view('1')).cast('B')
        self.assertEqual(len(view), 641 * 123 * 4)
        self.assertEqual(list(view[:3]), [12, 34, 56])

    def test_cached_draw_matches_original_for_fractional_positions(self):
        circles = [Circle(20, 45.8, 55.2, 0, 0, (125, 230, 45), alpha)
                   for alpha in (0, 1, 64, 128, 255)]
        circles.append(Circle(20, 45.8, 55.2, 0, 0, (0, 0, 0), 128))
        for circle in circles:
            current = make_surface((100, 100))
            expected = make_surface((100, 100))
            expected.fill((10, 10, 10))
            disk = pygame.Surface((40, 40))
            disk.set_colorkey((0, 0, 0))
            disk.set_alpha(circle.alpha)
            pygame.draw.circle(disk, circle.color, (20, 20), 20)
            expected.blit(disk, (circle.x - 20, circle.y - 20))
            pygame.draw.circle(expected, circle.color, (circle.x, circle.y), 20, width=3)
            CircleRenderer([circle]).draw(current)
            self.assertEqual(pygame.image.tobytes(current, 'RGB'),
                             pygame.image.tobytes(expected, 'RGB'))

    def test_software_mode_works_from_another_directory(self):
        previous = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as directory:
                os.chdir(directory)
                app = App((640, 360), 10, 2, postprocessing=False)
                self.assertTrue(app.frame(1 / 60))
                app.close()
        finally:
            os.chdir(previous)

import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import sys
import tempfile
import unittest
import pygame
from rendering import PostProcessor, make_surface


@unittest.skipUnless(os.environ.get('RUN_GL_TESTS') == '1', 'set RUN_GL_TESTS=1 for OpenGL tests')
class PostprocessingTests(unittest.TestCase):
    def setUp(self):
        import moderngl
        self.size = (321, 181)
        options = {'backend': 'egl'} if sys.platform == 'linux' else {}
        self.context = moderngl.create_standalone_context(require=330, **options)
        self.target = self.context.simple_framebuffer(self.size)
        self.target.use()
        self.post = PostProcessor(self.context, self.size)

    def tearDown(self):
        self.post.close()
        self.target.release()
        self.context.release()

    def output(self):
        image = pygame.image.frombytes(self.target.read(components=3, alignment=1), self.size, 'RGB')
        return pygame.transform.flip(image, False, True)

    def test_odd_width_upload_has_correct_colors_and_orientation(self):
        surface = make_surface(self.size)
        surface.fill((255, 0, 0))
        pygame.draw.rect(surface, (0, 255, 0), (160, 0, 161, 90))
        pygame.draw.rect(surface, (0, 0, 255), (0, 90, 160, 91))
        pygame.draw.rect(surface, (255, 255, 0), (160, 90, 161, 91))
        self.post.draw(surface)
        image = self.output()
        for point, channels in (((80, 45), (1, 0, 0)), ((240, 45), (0, 1, 0)),
                                ((80, 135), (0, 0, 1)), ((240, 135), (1, 1, 0))):
            color = image.get_at(point)
            for value, enabled in zip(color, channels):
                self.assertGreater(value, 190) if enabled else self.assertEqual(value, 0)

    def test_curved_corners_and_scanlines_are_preserved(self):
        surface = make_surface(self.size)
        surface.fill((255, 255, 255))
        self.post.draw(surface)
        image = self.output()
        self.assertEqual(tuple(image.get_at((0, 0)))[:3], (0, 0, 0))
        self.assertEqual(tuple(image.get_at((320, 180)))[:3], (0, 0, 0))
        self.assertTrue(all(190 < value <= 255 for value in image.get_at((160, 90))[:3]))
        scanline = [image.get_at((x, 45))[0] for x in range(40, 281)]
        self.assertGreaterEqual(min(scanline), 190)
        self.assertLess(min(scanline), 250)

    def test_shader_paths_work_from_another_directory(self):
        previous = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as directory:
                os.chdir(directory)
                post = PostProcessor(self.context, self.size)
                post.close()
                self.assertEqual(post.resources, [])
        finally:
            os.chdir(previous)

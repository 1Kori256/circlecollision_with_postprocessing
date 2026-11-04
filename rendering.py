"""Cached Pygame circles and the original curved-screen postprocessing."""

from pathlib import Path
import struct
import pygame

SHADER_DIR = Path(__file__).resolve().parent
BACKGROUND = (10, 10, 10)


def make_surface(size):
    # Packed RGBA gives a contiguous upload even when the width is odd.
    return pygame.Surface(size, depth=32, masks=(0xFF, 0xFF00, 0xFF0000, 0xFF000000))


class CircleRenderer:
    def __init__(self, circles):
        self.sprites = []
        for circle in circles:
            radius = circle.radius
            fill = pygame.Surface((2 * radius, 2 * radius))
            fill.set_colorkey((0, 0, 0))
            pygame.draw.circle(fill, circle.color, (radius, radius), radius)
            outline = pygame.Surface((2 * radius, 2 * radius))
            transparent = (255, 255, 255) if circle.color == (0, 0, 0) else (0, 0, 0)
            outline.fill(transparent)
            outline.set_colorkey(transparent)
            pygame.draw.circle(outline, circle.color, (radius, radius), radius, width=3)
            self.sprites.append((circle, fill, outline))

    def draw(self, surface):
        surface.fill(BACKGROUND)
        for circle, fill, outline in self.sprites:
            position = (int(circle.x) - circle.radius, int(circle.y) - circle.radius)
            if circle.alpha:
                fill.set_alpha(circle.alpha)
                surface.blit(fill, position)
            surface.blit(outline, position)


class PostProcessor:
    def __init__(self, context, size):
        import moderngl
        self.context = context
        self.resources = []
        try:
            self.program = context.program(
                vertex_shader=(SHADER_DIR / "vertex_shaders.glsl").read_text(),
                fragment_shader=(SHADER_DIR / "fragment_shaders.glsl").read_text())
            self.resources.append(self.program)
            self.vertices = context.buffer(struct.pack(
                "16f", -1, -1, 0, 1, 1, -1, 1, 1, -1, 1, 0, 0, 1, 1, 1, 0))
            self.resources.append(self.vertices)
            self.vao = context.vertex_array(self.program, [(self.vertices, "2f 2f", "vert", "in_text")])
            self.resources.append(self.vao)
            self.texture = context.texture(size, 4, alignment=1)
            self.resources.append(self.texture)
            self.texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self.texture.repeat_x = self.texture.repeat_y = False
            self.program["Texture"].value = 0
            self.mode = moderngl.TRIANGLE_STRIP
        except Exception:
            self.close()
            raise

    def draw(self, surface):
        self.texture.write(surface.get_view("1"), alignment=1)
        self.texture.use(location=0)
        self.vao.render(mode=self.mode)

    def close(self):
        for resource in reversed(self.resources):
            resource.release()
        self.resources.clear()

import struct
import pygame
import random
import math
from math import *
from pygame.locals import *

import moderngl

pygame.init()

FPS = 60
clock = pygame.time.Clock()

import tkinter as tk
root = tk.Tk()
WIDTH: int = int(root.winfo_screenwidth())
HEIGHT: int = int(root.winfo_screenheight())
print(int(root.winfo_screenwidth()))

VIRTUAL_RES = (WIDTH // 1, HEIGHT // 1)
REAL_RES = (WIDTH, HEIGHT)

WIDTH = VIRTUAL_RES[0]
HEIGHT = VIRTUAL_RES[1]

screen = pygame.Surface(VIRTUAL_RES).convert((255, 65280, 16711680, 0))
pygame.display.set_mode(REAL_RES, DOUBLEBUF | OPENGL)

ctx = moderngl.create_context()

texture_coordinates = [0, 1, 1, 1,
                       0, 0, 1, 0]

world_coordinates = [-1, -1, 1, -1,
                     -1, 1, 1, 1]

render_indices = [0, 1, 2,
                  1, 2, 3]

prog = ctx.program(
    vertex_shader=open("vertex_shaders.glsl").read(),
    fragment_shader=open("fragment_shaders.glsl").read()
)

screen_texture = ctx.texture(
    VIRTUAL_RES, 3,
    pygame.image.tostring(screen, "RGB", 1))

screen_texture.repeat_x = False
screen_texture.repeat_y = False

vbo = ctx.buffer(struct.pack('8f', *world_coordinates))
uvmap = ctx.buffer(struct.pack('8f', *texture_coordinates))
ibo = ctx.buffer(struct.pack('6I', *render_indices))

vao_content = [
    (vbo, '2f', 'vert'),
    (uvmap, '2f', 'in_text')
]

vao = ctx.vertex_array(prog, vao_content, ibo)


def rescale(img):
    current_size = img.get_rect().size
    transformed_size = (int((current_size[0] / 1920) * WIDTH), int((current_size[1] / 1080) * HEIGHT))
    transformed_img = pygame.transform.scale(img, transformed_size)
    return transformed_img


def _randomColor():
    red = random.randint(0, 255)
    green = random.randint(0, 255)
    blue = random.randint(0, 255)
    return (red, green, blue)


def distance(x1, y1, x2, y2):
    return sqrt(pow(x1 - x2, 2) + pow(y1 - y2, 2))


def rotate(velocity, angle):
    rotatedVel = {
        "x": velocity["x"] * cos(angle) - velocity["y"] * sin(angle),
        "y": velocity["x"] * sin(angle) + velocity["y"] * cos(angle)
    }
    return rotatedVel


def collide(particle1, particle2):
    xVelDiff = particle1.velocity["x"] - particle2.velocity["x"]
    yVelDiff = particle1.velocity["y"] - particle2.velocity["y"]
    xDiff = particle2.x - particle1.x
    yDiff = particle2.y - particle1.y

    if xVelDiff * xDiff + yVelDiff * yDiff >= 0:
        angle = -1 * atan2(yDiff, xDiff)
        m1 = particle1.mass
        m2 = particle2.mass
        vel1 = rotate(particle1.velocity, angle)
        vel2 = rotate(particle2.velocity, angle)
        updatedVel1 = {"x": vel1["x"] * (m1 - m2) / (m1 + m2) + 2 * vel2["x"] * m2 / (m1 + m2), "y": vel1["y"]}
        updatedVel2 = {"x": vel2["x"] * (m2 - m1) / (m1 + m2) + 2 * vel1["x"] * m1 / (m1 + m2), "y": vel2["y"]}
        finalVel1 = rotate(updatedVel1, -angle)
        finalVel2 = rotate(updatedVel2, -angle)
        particle1.velocity = finalVel1
        particle2.velocity = finalVel2

class Circle():
    def __init__(self, particles):
        _resConst = VIRTUAL_RES[0] / 1920
        self.radius = random.randint(int(20 * _resConst), int(50 * _resConst))
        self.x = self.radius + random.randint(0, WIDTH - 2 * self.radius)
        self.y = self.radius + random.randint(0, HEIGHT - 2 * self.radius)
        self.velocity = {"x": (random.random() - 0.5) * _resConst * 5, "y": (random.random() - 0.5) * _resConst * 5}
        self.color = _randomColor()
        self.mass = self.radius / 30
        self.alpha = 0

        if len(particles) != 0:
            i = 0
            while i < len(particles):
                if (distance(self.x, self.y, particles[i].x, particles[i].y) - (self.radius + particles[i].radius)) <= 0:
                    self.x = self.radius + random.randint(0, WIDTH - 2 * self.radius)
                    self.y = self.radius + random.randint(0, HEIGHT - 2 * self.radius)
                    i = -1
                i += 1

    def draw(self, surface) -> None:
        circle_surface = pygame.Surface((2 * self.radius, 2 * self.radius))
        circle_surface.set_colorkey((0, 0, 0))
        circle_surface.set_alpha(self.alpha)
        pygame.draw.circle(circle_surface, self.color, (self.radius, self.radius), self.radius)
        surface.blit(circle_surface, (self.x - self.radius, self.y - self.radius))
        pygame.draw.circle(surface, self.color, (self.x, self.y), self.radius, width=3)

    def update(self, particles, j, mouse_pos, mouse_pressed) -> None:

        for i in range(j + 1, len(particles)):
            if self == particles[i]: continue
            else:
                if (distance(self.x, self.y, particles[i].x, particles[i].y) - (self.radius + particles[i].radius)) < 0:
                    collide(self, particles[i])

        if self.x - self.radius <= 0 or self.x + self.radius >= WIDTH:
            self.velocity["x"] = -1 * self.velocity["x"]
        if self.y - self.radius <= 0 or self.y + self.radius >= HEIGHT:
            self.velocity["y"] = -1 * self.velocity["y"]

        self.x += self.velocity["x"]
        self.y += self.velocity["y"]

        mouse_dis = distance(mouse_pos[0], mouse_pos[1], self.x, self.y)
        _resConst = VIRTUAL_RES[0] / 1920
        if (mouse_dis) < 300 * _resConst:
            self.alpha = min(map_val(mouse_dis, 300 * _resConst, 100 * _resConst, 1, 255), 255)
            if mouse_pressed:
                self.velocity["x"] += 4 * (copysign(1, self.x - mouse_pos[0]) * (300 - abs(self.x - mouse_pos[0]))) / 300
                self.velocity["y"] += 4 * (copysign(1, self.y - mouse_pos[1]) * (300 - abs(self.y - mouse_pos[1]))) / 300
        else:
            self.alpha = 0


def map_val(x, a, b, c, d):

    val = (x-a)/((b-a)/(d-c))+c

    return val


def render():
    texture_data = screen.get_view("1")
    screen_texture.write(texture_data)
    ctx.clear(14 / 255, 40 / 255, 66 / 255)
    screen_texture.use()
    vao.render()
    pygame.display.flip()


def main(surface):
    particles = []
    for i in range(100):
        particle = Circle(particles)
        particles.append(particle)

    mouse_pos = (-100, -100)
    mouse_pressed = False

    run: bool = True
    while run:

        mouse_pressed = False
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                run = False
                pygame.display.quit()

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_F1:
                    run = False
                    pygame.display.quit()

            if event.type == pygame.MOUSEMOTION:
                mouse_pos: tuple[int] = pygame.mouse.get_pos()
                mouse_pos = (mouse_pos[0] / REAL_RES[0] * VIRTUAL_RES[0],
                             mouse_pos[1] / REAL_RES[1] * VIRTUAL_RES[1])

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos: tuple[int] = pygame.mouse.get_pos()
                mouse_pos = (mouse_pos[0] / REAL_RES[0] * VIRTUAL_RES[0],
                             mouse_pos[1] / REAL_RES[1] * VIRTUAL_RES[1])

                if event.button == 1:
                    mouse_pressed = True

            if event.type == pygame.MOUSEBUTTONUP:
                mouse_pos: tuple[int] = pygame.mouse.get_pos()
                mouse_pos = (mouse_pos[0] / REAL_RES[0] * VIRTUAL_RES[0],
                             mouse_pos[1] / REAL_RES[1] * VIRTUAL_RES[1])

                if event.button == 1:
                    mouse_pressed = False


        surface.fill((10, 10, 10))
        for particle in particles:
            particle.draw(surface)
        for i in range(len(particles)):
            particles[i].update(particles, i, mouse_pos, mouse_pressed)

        if mouse_pressed and False:
            particle = Circle(particles)
            particle.x, particle.y = mouse_pos
            particles.append(particle)

        #pygame.display.update()

        render()
        clock.tick(FPS)


if __name__ == "__main__":
    main(screen)
    pygame.quit()

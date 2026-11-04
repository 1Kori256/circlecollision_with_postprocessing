"""Circle physics without window or graphics dependencies."""

from dataclasses import dataclass
from itertools import combinations
import math
import random


@dataclass(slots=True)
class Circle:
    radius: int
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int] = (255, 255, 255)
    alpha: int = 0

    @property
    def mass(self):
        return self.radius / 30


def candidate_pairs(circles):
    """Visit each nearby pair once; distant grid cells cannot overlap."""
    if len(circles) < 2:
        return
    cell_size = 2 * max(circle.radius for circle in circles)
    cells = {}
    for i, circle in enumerate(circles):
        key = (math.floor(circle.x / cell_size), math.floor(circle.y / cell_size))
        cells.setdefault(key, []).append(i)
    for (x, y), indices in cells.items():
        yield from combinations(indices, 2)
        for dx, dy in ((1, 0), (-1, 1), (0, 1), (1, 1)):
            for other in cells.get((x + dx, y + dy), ()):
                for i in indices:
                    yield i, other


def collide(a, b):
    dx, dy = b.x - a.x, b.y - a.y
    distance_squared = dx * dx + dy * dy
    radius = a.radius + b.radius
    if distance_squared >= radius * radius:
        return False
    if distance_squared:
        distance = math.sqrt(distance_squared)
        nx, ny = dx / distance, dy / distance
    else:
        # Coincident centers still need a finite separation direction.
        speed = math.hypot(a.vx - b.vx, a.vy - b.vy)
        nx, ny = ((a.vx - b.vx) / speed, (a.vy - b.vy) / speed) if speed else (1, 0)
        distance = 0
    inverse_a, inverse_b = 1 / a.mass, 1 / b.mass
    inverse_sum = inverse_a + inverse_b
    penetration = radius - distance
    a.x -= nx * penetration * inverse_a / inverse_sum
    a.y -= ny * penetration * inverse_a / inverse_sum
    b.x += nx * penetration * inverse_b / inverse_sum
    b.y += ny * penetration * inverse_b / inverse_sum
    approach = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
    if approach < 0:
        impulse = -2 * approach / inverse_sum
        a.vx -= impulse * nx * inverse_a
        a.vy -= impulse * ny * inverse_a
        b.vx += impulse * nx * inverse_b
        b.vy += impulse * ny * inverse_b
    return True


def confine(circle, width, height):
    if circle.x < circle.radius:
        circle.x = circle.radius
        circle.vx = abs(circle.vx)
    elif circle.x > width - circle.radius:
        circle.x = width - circle.radius
        circle.vx = -abs(circle.vx)
    if circle.y < circle.radius:
        circle.y = circle.radius
        circle.vy = abs(circle.vy)
    elif circle.y > height - circle.radius:
        circle.y = height - circle.radius
        circle.vy = -abs(circle.vy)


class Simulation:
    def __init__(self, size, count=100, seed=None):
        self.width, self.height = size
        if min(size) < 64 or count < 1:
            raise ValueError("Use a window of at least 64×64 and at least one circle")
        self.scale = self.width / 1920
        self.influence = 300 * self.scale
        self.circles = self._populate(count, random.Random(seed))
        self.minimum_radius = min(circle.radius for circle in self.circles)

    def _populate(self, count, rng):
        low = max(1, int(20 * self.scale))
        high = min(max(low, int(50 * self.scale)), min(self.width, self.height) // 2 - 1)
        low = min(low, high)
        cell_size = 2 * high
        cells = {}
        circles = []
        for _ in range(count):
            radius = rng.randint(low, high)
            circle = Circle(radius, rng.randint(radius, self.width - radius),
                            rng.randint(radius, self.height - radius),
                            (rng.random() - 0.5) * self.scale * 5,
                            (rng.random() - 0.5) * self.scale * 5,
                            tuple(rng.randint(0, 255) for _ in range(3)))
            for attempt in range(5000):
                key = (math.floor(circle.x / cell_size), math.floor(circle.y / cell_size))
                neighbors = (other for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                             for other in cells.get((key[0] + dx, key[1] + dy), ()))
                if all((circle.x - other.x) ** 2 + (circle.y - other.y) ** 2
                       > (radius + other.radius) ** 2 for other in neighbors):
                    cells.setdefault(key, []).append(circle)
                    circles.append(circle)
                    break
                circle.x = rng.randint(radius, self.width - radius)
                circle.y = rng.randint(radius, self.height - radius)
            else:
                raise ValueError(f"Only {len(circles)} circles fit. Lower --count or use a taller --size")
        return circles

    def update(self, dt=1 / 60, mouse=(-1000, -1000), pressed=False):
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("dt must be finite and nonnegative")
        frame_scale = min(dt, 0.25) * 60
        if frame_scale:
            speed = max(math.hypot(circle.vx, circle.vy) for circle in self.circles)
            # Smaller steps keep ordinary mouse-driven collisions from tunneling.
            travel = (speed + 4 * self.scale * frame_scale) * frame_scale
            steps = min(64, max(1, math.ceil(travel / (self.minimum_radius * 0.5))))
            step = frame_scale / steps
            for _ in range(steps):
                for circle in self.circles:
                    dx, dy = circle.x - mouse[0], circle.y - mouse[1]
                    if pressed and dx * dx + dy * dy < self.influence ** 2:
                        force = 4 * self.scale * step / self.influence
                        circle.vx += force * math.copysign(self.influence - abs(dx), dx)
                        circle.vy += force * math.copysign(self.influence - abs(dy), dy)
                    circle.x += circle.vx * step
                    circle.y += circle.vy * step
                    confine(circle, self.width, self.height)
                for i, j in candidate_pairs(self.circles):
                    collide(self.circles[i], self.circles[j])
                for circle in self.circles:
                    confine(circle, self.width, self.height)
        for circle in self.circles:
            dx, dy = circle.x - mouse[0], circle.y - mouse[1]
            squared = dx * dx + dy * dy
            circle.alpha = (min(255, round(1 + (self.influence - math.sqrt(squared))
                                          * 254 / (200 * self.scale)))
                            if squared < self.influence ** 2 else 0)

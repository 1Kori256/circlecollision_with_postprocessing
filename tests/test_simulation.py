from dataclasses import replace
import math
import random
import unittest

from simulation import Circle, Simulation, candidate_pairs, collide, confine


class PhysicsTests(unittest.TestCase):
    def test_grid_contains_every_overlap_without_duplicates(self):
        rng = random.Random(1)
        for _ in range(20):
            circles = [Circle(rng.randint(1, 40), rng.uniform(-100, 800),
                              rng.uniform(-100, 500), 0, 0) for _ in range(100)]
            pairs = [tuple(sorted(pair)) for pair in candidate_pairs(circles)]
            self.assertEqual(len(pairs), len(set(pairs)))
            overlapping = {(i, j) for i, a in enumerate(circles)
                           for j, b in enumerate(circles) if i < j
                           and (a.x - b.x) ** 2 + (a.y - b.y) ** 2 < (a.radius + b.radius) ** 2}
            self.assertTrue(overlapping.issubset(set(pairs)))

    def test_distant_circles_are_skipped(self):
        circles = [Circle(10, 50 * i, 0, 0, 0) for i in range(100)]
        self.assertLess(len(list(candidate_pairs(circles))), 100)
        self.assertEqual(list(candidate_pairs([])), [])
        self.assertEqual(list(candidate_pairs(circles[:1])), [])

    def test_equal_masses_exchange_normal_velocity(self):
        a, b = Circle(10, 0, 0, 2, 1), Circle(10, 19, 0, -3, 4)
        self.assertTrue(collide(a, b))
        self.assertEqual((a.vx, a.vy), (-3, 1))
        self.assertEqual((b.vx, b.vy), (2, 4))
        self.assertAlmostEqual(math.hypot(a.x - b.x, a.y - b.y), 20)

    def test_unequal_mass_collision_conserves_momentum_and_energy(self):
        a, b = Circle(10, 0, 0, 4, 2), Circle(30, 25, 20, -2, -3)
        def totals():
            return (a.mass * a.vx + b.mass * b.vx,
                    a.mass * a.vy + b.mass * b.vy,
                    a.mass * (a.vx ** 2 + a.vy ** 2) + b.mass * (b.vx ** 2 + b.vy ** 2))
        before = totals()
        collide(a, b)
        for expected, actual in zip(before, totals()):
            self.assertAlmostEqual(actual, expected)

    def test_separating_overlap_only_corrects_positions(self):
        a, b = Circle(10, 0, 0, -2, 0), Circle(10, 19, 0, 3, 0)
        collide(a, b)
        self.assertEqual((a.vx, b.vx), (-2, 3))
        self.assertAlmostEqual(b.x - a.x, 20)

    def test_coincident_centers_remain_finite(self):
        for velocity in (0, 2):
            a, b = Circle(10, 20, 20, velocity, 0), Circle(10, 20, 20, -velocity, 0)
            collide(a, b)
            self.assertAlmostEqual(math.hypot(a.x - b.x, a.y - b.y), 20)
            self.assertTrue(all(math.isfinite(v) for c in (a, b) for v in (c.x, c.y, c.vx, c.vy)))

    def test_noncontact_does_not_change_particles(self):
        a, b = Circle(10, 0, 0, 1, 0), Circle(10, 20, 0, -1, 0)
        before = replace(a), replace(b)
        self.assertFalse(collide(a, b))
        self.assertEqual((a, b), before)

    def test_wall_correction_reflects_outward_velocity(self):
        circle = Circle(10, -20, 120, -5, 7)
        confine(circle, 100, 100)
        self.assertEqual((circle.x, circle.y, circle.vx, circle.vy), (10, 90, 5, -7))
        circle.vx, circle.vy = 5, -7
        circle.x, circle.y = 0, 100
        confine(circle, 100, 100)
        self.assertEqual((circle.vx, circle.vy), (5, -7))

    def test_seeded_population_is_repeatable_and_nonoverlapping(self):
        a = Simulation((1280, 720), seed=3)
        b = Simulation((1280, 720), seed=3)
        self.assertEqual(a.circles, b.circles)
        for i, j in candidate_pairs(a.circles):
            first, second = a.circles[i], a.circles[j]
            self.assertGreater(math.hypot(first.x - second.x, first.y - second.y),
                               first.radius + second.radius)

    def test_crowded_population_fails_instead_of_hanging(self):
        with self.assertRaisesRegex(ValueError, 'Only .* circles fit'):
            Simulation((1920, 64), count=100, seed=1)

    def test_invalid_simulation_parameters(self):
        for size, count in (((10, 10), 1), ((640, 480), 0), ((640, 480), -1)):
            with self.assertRaises(ValueError):
                Simulation(size, count)
        simulation = Simulation((640, 480), 1, seed=1)
        for dt in (-1, math.nan, math.inf):
            with self.assertRaises(ValueError):
                simulation.update(dt)

    def test_smaller_steps_prevent_fast_head_on_pass_through(self):
        simulation = Simulation((640, 480), 1)
        a, b = Circle(10, 150, 100, 100, 0), Circle(10, 250, 100, -100, 0)
        simulation.circles = [a, b]
        simulation.minimum_radius = 10
        simulation.update()
        self.assertLess(a.x, b.x)
        self.assertLess(a.vx, 0)
        self.assertGreater(b.vx, 0)

    def test_held_mouse_applies_force_on_subsequent_updates(self):
        simulation = Simulation((1920, 1080), 1)
        circle = Circle(20, 900, 500, 0, 0)
        simulation.circles = [circle]
        simulation.minimum_radius = 20
        simulation.update(mouse=(850, 500), pressed=True)
        first_speed = circle.vx
        simulation.update(mouse=(850, 500), pressed=True)
        self.assertGreater(circle.vx, first_speed)
        self.assertGreater(first_speed, 0)

    def test_fade_matches_original_curve(self):
        simulation = Simulation((1920, 1080), 1)
        circle = Circle(20, 1000, 500, 0, 0)
        simulation.circles = [circle]
        for distance, expected in ((0, 255), (100, 255), (200, 128), (300, 0), (400, 0)):
            simulation.update(0, mouse=(circle.x - distance, circle.y))
            self.assertEqual(circle.alpha, expected)

    def test_long_running_mouse_input_keeps_particles_on_board(self):
        simulation = Simulation((960, 540), 100, seed=4)
        for _ in range(300):
            simulation.update(mouse=(480, 270), pressed=True)
        for circle in simulation.circles:
            self.assertTrue(circle.radius <= circle.x <= simulation.width - circle.radius)
            self.assertTrue(circle.radius <= circle.y <= simulation.height - circle.radius)
            self.assertTrue(math.isfinite(circle.vx) and math.isfinite(circle.vy))

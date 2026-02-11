"""
Cube Game - A 3D rotating cube game built with Pygame.

Navigate a cube through obstacles, collect points, and survive as long as possible.
Controls:
    Arrow Keys / WASD - Move the cube
    Space - Jump
    ESC - Pause / Quit
"""

import pygame
import sys
import math
import random

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 50, 50)
GREEN = (50, 200, 80)
BLUE = (50, 100, 220)
YELLOW = (240, 220, 50)
CYAN = (50, 200, 220)
PURPLE = (150, 50, 200)
DARK_GRAY = (30, 30, 40)
LIGHT_GRAY = (180, 180, 190)
ORANGE = (240, 150, 30)

CUBE_COLORS = [RED, GREEN, BLUE, YELLOW, CYAN, PURPLE]

# Physics
GRAVITY = 0.6
JUMP_FORCE = -12
GROUND_Y = 420
MOVE_SPEED = 5

# Obstacle settings
OBSTACLE_SPEED_INITIAL = 3
OBSTACLE_SPEED_INCREMENT = 0.0005
OBSTACLE_SPAWN_INTERVAL = 90  # frames
MIN_OBSTACLE_GAP = 60

# Collectible settings
COLLECTIBLE_SPAWN_INTERVAL = 150


# ---------------------------------------------------------------------------
# 3D Cube projection helpers
# ---------------------------------------------------------------------------
def rotate_x(point, angle):
    """Rotate a 3D point around the X axis."""
    y = point[1] * math.cos(angle) - point[2] * math.sin(angle)
    z = point[1] * math.sin(angle) + point[2] * math.cos(angle)
    return (point[0], y, z)


def rotate_y(point, angle):
    """Rotate a 3D point around the Y axis."""
    x = point[0] * math.cos(angle) + point[2] * math.sin(angle)
    z = -point[0] * math.sin(angle) + point[2] * math.cos(angle)
    return (x, point[1], z)


def rotate_z(point, angle):
    """Rotate a 3D point around the Z axis."""
    x = point[0] * math.cos(angle) - point[1] * math.sin(angle)
    y = point[0] * math.sin(angle) + point[1] * math.cos(angle)
    return (x, y, point[2])


def project(point, cx, cy, fov=256, distance=4):
    """Project a 3D point onto 2D screen coordinates."""
    factor = fov / (distance + point[2])
    x = point[0] * factor + cx
    y = -point[1] * factor + cy
    return (x, y)


class Cube3D:
    """A 3D cube that can be rendered with rotation."""

    VERTICES = [
        (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
        (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
    ]

    FACES = [
        (0, 1, 2, 3),  # front
        (4, 5, 6, 7),  # back
        (0, 1, 5, 4),  # bottom
        (2, 3, 7, 6),  # top
        (0, 3, 7, 4),  # left
        (1, 2, 6, 5),  # right
    ]

    EDGES = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]

    def __init__(self, size=30):
        self.size = size
        self.angle_x = 0
        self.angle_y = 0
        self.angle_z = 0

    def get_transformed_vertices(self):
        transformed = []
        for v in self.VERTICES:
            p = (v[0] * self.size, v[1] * self.size, v[2] * self.size)
            p = rotate_x(p, self.angle_x)
            p = rotate_y(p, self.angle_y)
            p = rotate_z(p, self.angle_z)
            transformed.append(p)
        return transformed

    def draw(self, surface, cx, cy, color=BLUE):
        transformed = self.get_transformed_vertices()
        projected = [project(v, cx, cy) for v in transformed]

        # Sort faces by average z-depth for painter's algorithm
        face_depths = []
        for i, face in enumerate(self.FACES):
            avg_z = sum(transformed[v][2] for v in face) / 4
            face_depths.append((avg_z, i))
        face_depths.sort(reverse=True)

        for depth, i in face_depths:
            face = self.FACES[i]
            points = [projected[v] for v in face]
            # Shade based on depth
            shade = max(0.3, min(1.0, 0.6 + depth / (self.size * 4)))
            face_color = (
                int(color[0] * shade),
                int(color[1] * shade),
                int(color[2] * shade),
            )
            pygame.draw.polygon(surface, face_color, points)
            pygame.draw.polygon(surface, WHITE, points, 1)


# ---------------------------------------------------------------------------
# Game Objects
# ---------------------------------------------------------------------------
class Player:
    """The player-controlled cube."""

    def __init__(self):
        self.x = 150.0
        self.y = float(GROUND_Y)
        self.vel_y = 0.0
        self.on_ground = True
        self.cube = Cube3D(size=22)
        self.color = BLUE
        self.width = 40
        self.height = 40
        self.alive = True
        self.spin_speed = 0.03

    def update(self, keys):
        # Horizontal movement
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= MOVE_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += MOVE_SPEED

        # Clamp to screen
        self.x = max(self.width // 2, min(SCREEN_WIDTH - self.width // 2, self.x))

        # Jumping
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_FORCE
            self.on_ground = False

        # Gravity
        self.vel_y += GRAVITY
        self.y += self.vel_y

        if self.y >= GROUND_Y:
            self.y = GROUND_Y
            self.vel_y = 0
            self.on_ground = True

        # Rotate the cube visually
        self.cube.angle_y += self.spin_speed
        self.cube.angle_x += self.spin_speed * 0.7

    def get_rect(self):
        return pygame.Rect(
            int(self.x) - self.width // 2,
            int(self.y) - self.height,
            self.width,
            self.height,
        )

    def draw(self, surface):
        cx = int(self.x)
        cy = int(self.y) - self.height // 2
        self.cube.draw(surface, cx, cy, self.color)


class Obstacle:
    """An obstacle the player must avoid."""

    def __init__(self, x, speed):
        self.width = random.randint(30, 60)
        self.height = random.randint(30, 80)
        self.x = float(x)
        self.y = float(GROUND_Y - self.height)
        self.speed = speed
        self.color = random.choice([RED, ORANGE, PURPLE])
        self.cube = Cube3D(size=min(self.width, self.height) // 3)

    def update(self):
        self.x -= self.speed
        self.cube.angle_y += 0.02
        self.cube.angle_z += 0.015

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def draw(self, surface):
        cx = int(self.x) + self.width // 2
        cy = int(self.y) + self.height // 2
        self.cube.draw(surface, cx, cy, self.color)

    def is_off_screen(self):
        return self.x + self.width < 0


class Collectible:
    """A spinning collectible that gives points."""

    def __init__(self, x, speed):
        self.size = 20
        self.x = float(x)
        self.y = float(GROUND_Y - random.randint(40, 150))
        self.speed = speed
        self.color = YELLOW
        self.cube = Cube3D(size=10)
        self.collected = False

    def update(self):
        self.x -= self.speed
        self.cube.angle_y += 0.05
        self.cube.angle_x += 0.03

    def get_rect(self):
        return pygame.Rect(
            int(self.x) - self.size // 2,
            int(self.y) - self.size // 2,
            self.size,
            self.size,
        )

    def draw(self, surface):
        if not self.collected:
            self.cube.draw(surface, int(self.x), int(self.y), self.color)

    def is_off_screen(self):
        return self.x + self.size < 0


class Particle:
    """Simple particle for visual effects."""

    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 6)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 2
        self.life = random.randint(15, 35)
        self.max_life = self.life
        self.color = color
        self.size = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15
        self.life -= 1

    def draw(self, surface):
        alpha = self.life / self.max_life
        color = (
            int(self.color[0] * alpha),
            int(self.color[1] * alpha),
            int(self.color[2] * alpha),
        )
        pygame.draw.rect(
            surface, color,
            (int(self.x), int(self.y), self.size, self.size),
        )

    def is_dead(self):
        return self.life <= 0


# ---------------------------------------------------------------------------
# Star background
# ---------------------------------------------------------------------------
class Star:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.brightness = random.randint(80, 255)
        self.size = random.choice([1, 1, 1, 2])
        self.twinkle_speed = random.uniform(0.02, 0.06)
        self.twinkle_offset = random.uniform(0, math.pi * 2)

    def draw(self, surface, frame):
        b = self.brightness * (0.7 + 0.3 * math.sin(frame * self.twinkle_speed + self.twinkle_offset))
        b = int(max(0, min(255, b)))
        color = (b, b, b)
        if self.size == 1:
            surface.set_at((self.x, self.y), color)
        else:
            pygame.draw.rect(surface, color, (self.x, self.y, self.size, self.size))


# ---------------------------------------------------------------------------
# Main Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Cube Game")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont("monospace", 48, bold=True)
        self.font_medium = pygame.font.SysFont("monospace", 28)
        self.font_small = pygame.font.SysFont("monospace", 20)
        self.stars = [Star() for _ in range(120)]
        self.reset()

    def reset(self):
        self.player = Player()
        self.obstacles = []
        self.collectibles = []
        self.particles = []
        self.score = 0
        self.high_score = getattr(self, "high_score", 0)
        self.frame = 0
        self.obstacle_speed = OBSTACLE_SPEED_INITIAL
        self.game_over = False
        self.paused = False

    def spawn_obstacle(self):
        if self.frame % OBSTACLE_SPAWN_INTERVAL == 0 and self.frame > 60:
            # Don't spawn too close to existing obstacles
            if self.obstacles:
                last_x = max(o.x for o in self.obstacles)
                if last_x > SCREEN_WIDTH - MIN_OBSTACLE_GAP:
                    return
            self.obstacles.append(Obstacle(SCREEN_WIDTH + 20, self.obstacle_speed))

    def spawn_collectible(self):
        if self.frame % COLLECTIBLE_SPAWN_INTERVAL == 0 and self.frame > 30:
            self.collectibles.append(
                Collectible(SCREEN_WIDTH + 20, self.obstacle_speed)
            )

    def create_particles(self, x, y, color, count=12):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def check_collisions(self):
        player_rect = self.player.get_rect()

        for obs in self.obstacles:
            if player_rect.colliderect(obs.get_rect()):
                self.player.alive = False
                self.game_over = True
                self.create_particles(self.player.x, self.player.y - 20, RED, 25)
                if self.score > self.high_score:
                    self.high_score = self.score

        for col in self.collectibles:
            if not col.collected and player_rect.colliderect(col.get_rect()):
                col.collected = True
                self.score += 100
                self.create_particles(col.x, col.y, YELLOW, 15)

    def draw_ground(self):
        pygame.draw.line(self.screen, LIGHT_GRAY, (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 2)
        # Ground pattern
        for x in range(0, SCREEN_WIDTH, 40):
            offset = (self.frame * 2) % 40
            gx = x - offset
            pygame.draw.line(
                self.screen, (60, 60, 70),
                (gx, GROUND_Y + 1), (gx + 20, GROUND_Y + 15), 1,
            )

    def draw_hud(self):
        score_text = self.font_medium.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (20, 20))

        hi_text = self.font_small.render(f"Best: {self.high_score}", True, LIGHT_GRAY)
        self.screen.blit(hi_text, (20, 55))

        speed_text = self.font_small.render(
            f"Speed: {self.obstacle_speed:.1f}", True, CYAN
        )
        self.screen.blit(speed_text, (SCREEN_WIDTH - 160, 20))

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        go_text = self.font_large.render("GAME OVER", True, RED)
        rect = go_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40))
        self.screen.blit(go_text, rect)

        score_text = self.font_medium.render(f"Score: {self.score}", True, WHITE)
        rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        self.screen.blit(score_text, rect)

        restart_text = self.font_small.render("Press R to restart or ESC to quit", True, LIGHT_GRAY)
        rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 65))
        self.screen.blit(restart_text, rect)

    def draw_start_screen(self):
        self.screen.fill(DARK_GRAY)
        for star in self.stars:
            star.draw(self.screen, self.frame)

        title_cube = Cube3D(size=50)
        title_cube.angle_x = self.frame * 0.02
        title_cube.angle_y = self.frame * 0.03
        title_cube.draw(self.screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80, CYAN)

        title = self.font_large.render("CUBE GAME", True, WHITE)
        rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        self.screen.blit(title, rect)

        instructions = [
            "Arrow Keys / WASD - Move",
            "Space / Up - Jump",
            "Avoid red obstacles, collect yellow cubes",
            "",
            "Press SPACE to start",
        ]
        for i, line in enumerate(instructions):
            color = YELLOW if i == len(instructions) - 1 else LIGHT_GRAY
            text = self.font_small.render(line, True, color)
            rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70 + i * 28))
            self.screen.blit(text, rect)

    def run(self):
        # Start screen
        on_start_screen = True
        while on_start_screen:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        on_start_screen = False
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

            self.draw_start_screen()
            self.frame += 1
            pygame.display.flip()
            self.clock.tick(FPS)

        self.frame = 0

        # Main game loop
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_over:
                            running = False
                        else:
                            self.paused = not self.paused
                    if event.key == pygame.K_r and self.game_over:
                        self.reset()

            if not self.paused and not self.game_over:
                keys = pygame.key.get_pressed()
                self.player.update(keys)

                self.obstacle_speed = OBSTACLE_SPEED_INITIAL + self.frame * OBSTACLE_SPEED_INCREMENT
                self.spawn_obstacle()
                self.spawn_collectible()

                for obs in self.obstacles:
                    obs.update()
                for col in self.collectibles:
                    col.update()
                for p in self.particles:
                    p.update()

                self.obstacles = [o for o in self.obstacles if not o.is_off_screen()]
                self.collectibles = [
                    c for c in self.collectibles if not c.is_off_screen() and not c.collected
                ]
                self.particles = [p for p in self.particles if not p.is_dead()]

                self.check_collisions()

                # Score increases over time
                if self.frame % 10 == 0:
                    self.score += 1

                self.frame += 1

            # ---- Draw ----
            self.screen.fill(DARK_GRAY)

            for star in self.stars:
                star.draw(self.screen, self.frame)

            self.draw_ground()

            for obs in self.obstacles:
                obs.draw(self.screen)
            for col in self.collectibles:
                col.draw(self.screen)

            self.player.draw(self.screen)

            for p in self.particles:
                p.draw(self.screen)

            self.draw_hud()

            if self.game_over:
                self.draw_game_over()

            if self.paused and not self.game_over:
                pause_text = self.font_large.render("PAUSED", True, WHITE)
                rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                self.screen.blit(pause_text, rect)

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()

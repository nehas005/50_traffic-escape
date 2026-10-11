import pygame
import random

LANE_W = 80
CAR_W, CAR_H = 60, 80
COLORS = [(220, 60, 60), (220, 140, 40), (140, 60, 180), (60, 180, 80), (180, 180, 40), (60, 80, 200)]


class Car:
    def __init__(self, lane_x, y, direction, speed, lane=0):
        self.rect = pygame.Rect(lane_x + (LANE_W - CAR_W) // 2, y, CAR_W, CAR_H)
        self.y = float(y)            # float position: Rect truncates fractions (BUG-05)
        self.direction = direction   # 1 = down, -1 = up
        self.speed = speed
        self.lane = lane
        self.color = random.choice(COLORS)

    def update(self):
        self.y += self.direction * self.speed
        self.rect.y = round(self.y)

    def off_screen(self, road_top, road_bottom):
        if self.direction == 1:
            return self.rect.top > road_bottom
        return self.rect.bottom < road_top

    # ---- headlights -----------------------------------------------------
    @property
    def front_y(self):
        return self.rect.bottom if self.direction == 1 else self.rect.top

    def beam_polygon(self, length):
        """Trapezoid light cone in front of the car (longer at night)."""
        cx, fy, d = self.rect.centerx, self.front_y, self.direction
        near, far = 22, 22 + length * 0.4
        return [(cx - near, fy), (cx + near, fy),
                (cx + far, fy + d * length), (cx - far, fy + d * length)]

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (180, 220, 240),
                         pygame.Rect(self.rect.x + 8, self.rect.y + 10, 44, 22), border_radius=4)
        for wx in [self.rect.x + 6, self.rect.right - 16]:
            for wy in [self.rect.y + 4, self.rect.bottom - 16]:
                pygame.draw.rect(screen, (30, 30, 30), pygame.Rect(wx, wy, 10, 12), border_radius=3)
        # headlamps on the front bumper
        ly = self.rect.bottom - 7 if self.direction == 1 else self.rect.top + 1
        for lx in (self.rect.x + 6, self.rect.right - 16):
            pygame.draw.rect(screen, (255, 245, 170), pygame.Rect(lx, ly, 10, 6), border_radius=2)


def make_car(lane_idx, speed, road_top, road_bottom):
    x = lane_idx * LANE_W
    direction = 1 if lane_idx % 2 == 0 else -1
    y = road_top - CAR_H if direction == 1 else road_bottom
    return Car(x, y, direction, speed, lane_idx)

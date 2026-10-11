import pygame

LOG_W = 130


class Log:
    def __init__(self, x, top, height, speed):
        self.rect = pygame.Rect(x, top, LOG_W, height)
        self.speed = speed  # px per frame, +right / -left

    def update(self, width):
        self.rect.x += self.speed
        if self.speed > 0 and self.rect.left > width:
            self.rect.right = 0
        elif self.speed < 0 and self.rect.right < 0:
            self.rect.left = width

    def draw(self, screen):
        pygame.draw.rect(screen, (120, 80, 40), self.rect, border_radius=14)
        pygame.draw.rect(screen, (150, 105, 55), self.rect.inflate(-10, -16), border_radius=10)
        for i in range(1, 4):  # wood rings
            cx = self.rect.x + i * LOG_W // 4
            pygame.draw.ellipse(screen, (100, 65, 30), pygame.Rect(cx - 6, self.rect.centery - 8, 12, 16), 2)


class River:
    """A horizontal water band. Standing on water without a log = drowning."""

    def __init__(self, top, bottom, width, speed=2, n_logs=3):
        self.top, self.bottom, self.width = top, bottom, width
        self.tick = 0
        spacing = width // n_logs
        self.logs = [Log(i * spacing, top + 8, bottom - top - 16, speed) for i in range(n_logs)]

    def contains(self, rect):
        return self.top <= rect.centery < self.bottom

    def log_under(self, rect):
        for log in self.logs:
            if log.rect.left <= rect.centerx <= log.rect.right:
                return log
        return None

    def update(self):
        self.tick += 1
        for log in self.logs:
            log.update(self.width)

    def draw(self, screen):
        band = pygame.Rect(0, self.top, self.width, self.bottom - self.top)
        pygame.draw.rect(screen, (40, 100, 180), band)
        for row in range(3):  # drifting ripples
            y = self.top + 14 + row * 22
            off = (self.tick * (row + 1)) % 40
            for x in range(-40 + off, self.width, 40):
                pygame.draw.line(screen, (90, 150, 220), (x, y), (x + 14, y), 2)
        for log in self.logs:
            log.draw(screen)

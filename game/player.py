import pygame

SPEED = 4          # vertical speed, px per frame (was declared but never used - see BUG-02)
LANE_W = 80
HOP_COOLDOWN = 12  # frames between sideways lane hops
PLAYER_W, PLAYER_H = 40, 60


class Player:
    def __init__(self, x, y):
        """(x, y) is the CENTRE of the player."""
        self.rect = pygame.Rect(0, 0, PLAYER_W, PLAYER_H)
        self.rect.center = (x, y)
        self.color = (60, 160, 220)
        self.hop_cooldown = 0
        self.invulnerable = 0  # frames of post-hit protection

    # ---- lane helpers -------------------------------------------------
    def snap_to_lane(self, max_x):
        """Centre the player exactly in the lane it is mostly in (BUG-01)."""
        lanes = max(1, max_x // LANE_W)
        lane = max(0, min(lanes - 1, self.rect.centerx // LANE_W))
        self.rect.centerx = lane * LANE_W + LANE_W // 2

    def place_in_lane(self, lane, centery):
        self.rect.center = (lane * LANE_W + LANE_W // 2, centery)

    # ---- movement -----------------------------------------------------
    def move(self, keys, min_x, max_x, min_y=0, max_y=None):
        # sideways hops have their own cooldown; it no longer blocks W/S (BUG-03)
        if self.hop_cooldown > 0:
            self.hop_cooldown -= 1

        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        up = keys[pygame.K_UP] or keys[pygame.K_w]
        down = keys[pygame.K_DOWN] or keys[pygame.K_s]

        if (left != right) and self.hop_cooldown == 0:
            nx = self.rect.x + (-LANE_W if left else LANE_W)
            # a hop that would leave the road is ignored, so we never end up
            # half-way between lanes at the edge (BUG-01)
            if nx >= min_x and nx + self.rect.width <= max_x:
                self.rect.x = nx
                self.hop_cooldown = HOP_COOLDOWN

        if up != down:
            ny = self.rect.y + (-SPEED if up else SPEED)
            ny = max(min_y, ny)
            if max_y is not None:                      # BUG-04: stay on screen
                ny = min(max_y - self.rect.height, ny)
            self.rect.y = ny

    # ---- drawing ------------------------------------------------------
    def draw(self, screen):
        if self.invulnerable > 0 and (self.invulnerable // 6) % 2 == 1:
            return  # blink while protected
        pygame.draw.rect(screen, self.color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (180, 220, 240),
                         pygame.Rect(self.rect.x + 6, self.rect.y + 8, 28, 18), border_radius=4)
        for wx in [self.rect.x + 4, self.rect.right - 12]:
            for wy in [self.rect.y + 4, self.rect.bottom - 14]:
                pygame.draw.rect(screen, (30, 30, 30), pygame.Rect(wx, wy, 8, 10), border_radius=3)

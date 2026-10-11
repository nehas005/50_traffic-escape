import pygame
import random
from game.player import Player, LANE_W
from game.traffic import make_car, CAR_H
from game.river import River
from game.daynight import DayNight
from game.highscores import HighScores

LANES = 8
WIDTH = LANES * LANE_W
HEIGHT = 600
FPS = 60
BG = (60, 60, 60)

# vertical layout (top -> bottom)
HUD_H = 30
RIVER_TOP, RIVER_BOTTOM = 70, 140      # goal sidewalk is HUD_H..RIVER_TOP
ROAD_TOP, ROAD_BOTTOM = 170, 530       # grass bank is RIVER_BOTTOM..ROAD_TOP
ROAD_RECT = pygame.Rect(0, ROAD_TOP, WIDTH, ROAD_BOTTOM - ROAD_TOP)

START_LIVES = 3
INVULN_FRAMES = 120   # 2 s of protection after a respawn
MIN_CAR_GAP = 70      # px between cars in the same lane
WIN_BONUS, LIFE_BONUS = 500, 100
SIDEWALK = (150, 130, 110)
GRASS = (70, 140, 70)


class GameEngine:
    def __init__(self, highscore_path=None):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Traffic Escape")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 24, bold=True)
        self.hud_font = pygame.font.SysFont("monospace", 20, bold=True)
        self.big_font = pygame.font.SysFont("monospace", 44, bold=True)
        self.small_font = pygame.font.SysFont("monospace", 18, bold=True)
        self.highscores = HighScores(highscore_path) if highscore_path else HighScores()
        self.reset()

    # ------------------------------------------------------------------ setup
    def reset(self):
        self.player = Player(0, 0)
        self._respawn(invulnerable=False)
        self.cars = []
        self.river = River(RIVER_TOP, RIVER_BOTTOM, WIDTH)
        self.daynight = DayNight()
        self.lane_factor = [random.uniform(0.8, 1.2) for _ in range(LANES)]
        self.timer = 0
        self.spawn_interval = 50
        self.speed = 3
        self.frames = 0
        self.score = 0
        self.best_y = self.player.rect.y   # furthest point reached (for progress score)
        self.lives = START_LIVES
        self.game_over = False
        self.won = False
        self.rank = None                   # position in high-score table, if any

    def _respawn(self, invulnerable=True):
        self.player.place_in_lane(LANES // 2, HEIGHT - 10 - self.player.rect.height // 2)
        self.player.hop_cooldown = 0
        self.player.invulnerable = INVULN_FRAMES if invulnerable else 0

    # ----------------------------------------------------------------- events
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
                elif event.key == pygame.K_ESCAPE:
                    return False
        return True

    # ----------------------------------------------------------------- update
    def _lane_clear(self, lane, spawn_y):
        return all(abs(c.y - spawn_y) >= CAR_H + MIN_CAR_GAP for c in self.cars if c.lane == lane)

    def _spawn_car(self):
        lanes = list(range(LANES))
        random.shuffle(lanes)
        for lane in lanes:
            car = make_car(lane, self.speed, ROAD_TOP, ROAD_BOTTOM)
            if self._lane_clear(lane, car.y):   # BUG-06: no stacked cars
                self.cars.append(car)
                return True
        return False

    def _lose_life(self):
        self.lives -= 1
        if self.lives <= 0:
            self._finish(won=False)
        else:
            self._respawn()

    def _finish(self, won):
        if won:
            self.won = True
            self.score += WIN_BONUS + LIFE_BONUS * self.lives
        else:
            self.game_over = True
        self.rank = self.highscores.add(self.score, "WIN" if won else "LOSS")

    def update(self, keys=None):
        if self.game_over or self.won:
            return
        if keys is None:
            keys = pygame.key.get_pressed()
        self.frames += 1
        p = self.player

        self.daynight.update()
        p.move(keys, 0, WIDTH, HUD_H, HEIGHT)
        if p.invulnerable > 0:
            p.invulnerable -= 1

        # --- river: must stand on a log, which carries you sideways --------
        self.river.update()
        if self.river.contains(p.rect):
            log = self.river.log_under(p.rect)
            if log is None:
                self._lose_life()                      # fell in the water
                return
            p.rect.x += log.speed
            if p.rect.centerx < 0 or p.rect.centerx > WIDTH:
                self._lose_life()                      # carried off-screen
                return
        else:
            p.snap_to_lane(WIDTH)                      # BUG-01: always lane-aligned off the river

        # --- traffic ---------------------------------------------------------
        self.timer += 1
        if self.timer >= self.spawn_interval:
            self._spawn_car()
            self.timer = 0
            self.spawn_interval = max(22, self.spawn_interval - 0.2)
        for c in self.cars:
            c.speed = self.speed * self.lane_factor[c.lane]
            c.update()
            # only the visible part of a car on the road can hurt (BUG-07)
            if p.invulnerable == 0 and p.rect.colliderect(c.rect.clip(ROAD_RECT)):
                self._lose_life()
                break
        self.cars = [c for c in self.cars if not c.off_screen(ROAD_TOP, ROAD_BOTTOM)]
        if self.game_over:
            return

        # --- difficulty ramp + progress score -------------------------------
        if self.frames % 300 == 0:
            self.speed = min(10, self.speed + 0.5)
        if p.rect.y < self.best_y:
            self.score += (self.best_y - p.rect.y) // 2
            self.best_y = p.rect.y

        # --- goal -------------------------------------------------------------
        if p.rect.centery < RIVER_TOP:
            self._finish(won=True)

    # ------------------------------------------------------------------- draw
    def _draw_world(self):
        s = self.screen
        s.fill(BG)
        # road lane lines + dashes (road only)
        for i in range(LANES + 1):
            pygame.draw.line(s, (100, 100, 100), (i * LANE_W, ROAD_TOP), (i * LANE_W, ROAD_BOTTOM), 2)
        for y in range(ROAD_TOP, ROAD_BOTTOM, 60):
            for i in range(LANES):
                pygame.draw.rect(s, (200, 200, 100),
                                 pygame.Rect(i * LANE_W + LANE_W // 2 - 3, y, 6, min(30, ROAD_BOTTOM - y)))
        pygame.draw.rect(s, SIDEWALK, pygame.Rect(0, ROAD_BOTTOM, WIDTH, HEIGHT - ROAD_BOTTOM))
        pygame.draw.rect(s, GRASS, pygame.Rect(0, RIVER_BOTTOM, WIDTH, ROAD_TOP - RIVER_BOTTOM))
        pygame.draw.rect(s, SIDEWALK, pygame.Rect(0, HUD_H, WIDTH, RIVER_TOP - HUD_H))
        for x in range(0, WIDTH, 40):  # finish-line checker strip
            for r in range(2):
                if (x // 40 + r) % 2 == 0:
                    pygame.draw.rect(s, (240, 240, 240), pygame.Rect(x, HUD_H + r * 8, 40, 8))
        self.river.draw(s)
        s.set_clip(ROAD_RECT)               # cars never paint over river/grass
        for c in self.cars:
            c.draw(s)
        s.set_clip(None)
        self.player.draw(s)

    def _draw_night(self):
        lvl = self.daynight.level
        if lvl <= 0:
            return
        length = self.daynight.beam_length
        alpha = self.daynight.darkness
        dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dark.fill((5, 5, 30, alpha))
        glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for c in self.cars:
            poly = c.beam_polygon(length)
            pygame.draw.polygon(dark, (5, 5, 30, int(alpha * 0.2)), poly)     # punch light into darkness
            pygame.draw.polygon(glow, (255, 235, 140, int(55 * lvl)), poly)   # warm tint
        pygame.draw.circle(dark, (5, 5, 30, int(alpha * 0.35)), self.player.rect.center, 70)
        self.screen.blit(dark, (0, 0))
        self.screen.blit(glow, (0, 0))

    @staticmethod
    def _heart(surface, x, y, color):
        pygame.draw.circle(surface, color, (x + 4, y + 4), 4)
        pygame.draw.circle(surface, color, (x + 11, y + 4), 4)
        pygame.draw.polygon(surface, color, [(x, y + 6), (x + 15, y + 6), (x + 7, y + 15)])

    def _draw_hud(self):
        pygame.draw.rect(self.screen, (20, 20, 20), pygame.Rect(0, 0, WIDTH, HUD_H))
        txt = self.hud_font.render(f"Score:{self.score}", True, (220, 220, 220))
        self.screen.blit(txt, (6, 5))
        label = self.hud_font.render("Lives", True, (220, 220, 220))
        x0 = WIDTH // 2 - 70
        self.screen.blit(label, (x0, 5))
        for i in range(START_LIVES):
            self._heart(self.screen, x0 + 68 + i * 22, 7, (230, 60, 70) if i < self.lives else (70, 70, 70))
        night = self.daynight.night
        mode = self.hud_font.render(f"{'NIGHT' if night else 'DAY'} {self.daynight.seconds_left:>2}s",
                                    True, (150, 170, 255) if night else (255, 220, 100))
        self.screen.blit(mode, (WIDTH - mode.get_width() - 8, 5))

    def draw(self):
        self._draw_world()
        self._draw_night()
        self._draw_hud()
        if self.game_over:
            self._end_screen("GAME OVER", (220, 60, 60))
        if self.won:
            self._end_screen("YOU MADE IT!", (80, 220, 80))
        pygame.display.flip()

    def _end_screen(self, text, color):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 190))
        self.screen.blit(ov, (0, 0))
        cx = WIDTH // 2
        m = self.big_font.render(text, True, color)
        self.screen.blit(m, (cx - m.get_width() // 2, 120))
        sc = self.font.render(f"Your score: {self.score}", True, (240, 240, 240))
        self.screen.blit(sc, (cx - sc.get_width() // 2, 180))
        head = self.font.render("-- TOP 5 --", True, (255, 220, 100))
        self.screen.blit(head, (cx - head.get_width() // 2, 235))
        entries = self.highscores.entries
        for i in range(5):
            if i < len(entries):
                e = entries[i]
                row = f"{i + 1}. {e['score']:>5}  {e.get('result', ''):<4} {e.get('date', '')[5:]}"
            else:
                row = f"{i + 1}.   ---"
            col = (255, 255, 120) if i == self.rank else (200, 200, 200)
            t = self.small_font.render(row, True, col)
            self.screen.blit(t, (cx - 150, 275 + i * 28))
        if self.rank is not None:
            n = self.small_font.render("New high score!", True, (255, 255, 120))
            self.screen.blit(n, (cx - n.get_width() // 2, 425))
        sub = self.font.render("Press R to Restart", True, (200, 200, 200))
        self.screen.blit(sub, (cx - sub.get_width() // 2, 480))

    # -------------------------------------------------------------------- run
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

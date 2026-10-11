"""Headless tests. Run:  python -m pytest -q"""
import json
import random
import pygame
import pytest

from game import game_engine as ge
from game.game_engine import GameEngine, WIDTH, LANES, ROAD_TOP, ROAD_BOTTOM, RIVER_TOP, RIVER_BOTTOM
from game.player import Player, LANE_W, SPEED
from game.traffic import Car, make_car
from game.daynight import DayNight, CYCLE_SECONDS, FPS
from game.highscores import HighScores


class Keys(dict):
    """Fake pygame.key.get_pressed() result."""
    def __getitem__(self, k):
        return self.get(k, False)


def pressed(*ks):
    return Keys({k: True for k in ks})


NONE = Keys()


@pytest.fixture
def eng(tmp_path):
    random.seed(7)
    return GameEngine(str(tmp_path / "hs.json"))


def clear_traffic(e):
    e.cars = []
    e.timer = -10**6   # stop spawning


# ---------------------------------------------------------------- BUG fixes
def test_bug01_player_always_centred_in_lane(eng):
    p = eng.player
    assert p.rect.centerx % LANE_W == LANE_W // 2
    for _ in range(10):
        p.hop_cooldown = 0
        p.move(pressed(pygame.K_RIGHT), 0, WIDTH, 30, 600)
        assert p.rect.centerx % LANE_W == LANE_W // 2
        assert 0 <= p.rect.left and p.rect.right <= WIDTH


def test_bug02_forward_speed_uses_SPEED_constant(eng):
    p = eng.player
    y = p.rect.y
    p.move(pressed(pygame.K_UP), 0, WIDTH, 30, 600)
    assert y - p.rect.y == SPEED


def test_bug03_lane_hop_does_not_block_forward(eng):
    p = eng.player
    p.move(pressed(pygame.K_RIGHT), 0, WIDTH, 30, 600)
    y = p.rect.y
    p.move(pressed(pygame.K_UP), 0, WIDTH, 30, 600)
    assert p.rect.y < y


def test_bug04_cannot_leave_screen_vertically(eng):
    p = eng.player
    for _ in range(300):
        p.move(pressed(pygame.K_DOWN), 0, WIDTH, 30, 600)
    assert p.rect.bottom <= 600
    for _ in range(600):
        p.move(pressed(pygame.K_UP), 0, WIDTH, 30, 600)
    assert p.rect.top >= 30


@pytest.mark.parametrize("direction", [1, -1])
def test_bug05_both_directions_same_real_speed(direction):
    c = Car(0, 200, direction, 3.5)
    y0 = c.rect.y
    for _ in range(10):
        c.update()
    assert abs(c.rect.y - y0) == 35


def test_bug06_cars_in_same_lane_never_overlap(eng):
    eng.spawn_interval = 22
    for _ in range(3000):
        eng.player.invulnerable = 10**6
        eng.update(NONE)
        by_lane = {}
        for c in eng.cars:
            by_lane.setdefault(c.lane, []).append(c.rect)
        for rects in by_lane.values():
            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    assert not rects[i].colliderect(rects[j])


def test_bug07_offroad_car_part_is_harmless(eng):
    clear_traffic(eng)
    p = eng.player
    p.invulnerable = 0
    p.rect.centerx = 4 * LANE_W + 40
    p.rect.centery = RIVER_BOTTOM            # on the grass bank, just below the river
    car = Car(4 * LANE_W, ROAD_TOP - 60, 1, 0, lane=4)   # car still hidden above the road
    assert p.rect.colliderect(car.rect)       # raw rects overlap...
    eng.cars = [car]
    eng.update(NONE)
    assert eng.lives == ge.START_LIVES        # ...but it must not count as a hit


# ------------------------------------------------------------------- Task 1
def test_task1_three_lives_then_game_over(eng):
    assert eng.lives == 3
    for expected in (2, 1):
        clear_traffic(eng)
        eng.player.invulnerable = 0
        eng.player.rect.center = (4 * LANE_W + 40, 300)
        c = Car(4 * LANE_W, 280, 1, 0, lane=4)
        eng.cars = [c]
        eng.update(NONE)
        assert eng.lives == expected and not eng.game_over
        # respawned at the bottom, protected
        assert eng.player.rect.top >= ROAD_BOTTOM and eng.player.invulnerable > 0
    clear_traffic(eng)
    eng.player.invulnerable = 0
    eng.player.rect.center = (4 * LANE_W + 40, 300)
    eng.cars = [Car(4 * LANE_W, 280, 1, 0, lane=4)]
    eng.update(NONE)
    assert eng.lives == 0 and eng.game_over


def test_task1_invulnerability_prevents_instant_double_hit(eng):
    clear_traffic(eng)
    eng.player.invulnerable = 60
    eng.player.rect.center = (4 * LANE_W + 40, 300)
    eng.cars = [Car(4 * LANE_W, 280, 1, 0, lane=4)]
    eng.update(NONE)
    assert eng.lives == 3


def test_restart_resets_everything(eng):
    eng.lives = 0
    eng.game_over = True
    eng.reset()
    assert eng.lives == 3 and not eng.game_over and eng.score == 0


# ------------------------------------------------------------------- Task 2
def put_on_river(eng, x):
    clear_traffic(eng)
    eng.player.invulnerable = 0
    eng.player.rect.centerx = x
    eng.player.rect.centery = RIVER_BOTTOM - 5


def test_task2_water_without_log_costs_a_life(eng):
    put_on_river(eng, 0)
    gap_x = (eng.river.logs[0].rect.right + eng.river.logs[1].rect.left) // 2   # middle of a gap
    eng.player.rect.centerx = gap_x
    eng.update(NONE)
    assert eng.lives == 2


def test_task2_log_carries_player_sideways(eng):
    log = eng.river.logs[0]
    put_on_river(eng, log.rect.centerx)
    x0 = eng.player.rect.centerx
    eng.update(NONE)
    assert eng.lives == 3
    assert eng.player.rect.centerx - x0 == log.speed


def test_task2_carried_offscreen_drowns(eng):
    log = eng.river.logs[2]
    log.rect.right = WIDTH + 100
    put_on_river(eng, WIDTH - 3)
    for _ in range(10):
        if eng.lives < 3:
            break
        eng.river.logs[2].rect.right = WIDTH + 100
        eng.update(NONE)
    assert eng.lives == 2


def test_task2_crossing_the_river_wins(eng):
    log = eng.river.logs[1]
    put_on_river(eng, log.rect.centerx)
    for _ in range(200):
        log = eng.river.log_under(eng.player.rect) or log
        eng.update(pressed(pygame.K_UP))
        if eng.won:
            break
    assert eng.won and eng.lives == 3
    assert eng.score >= ge.WIN_BONUS


# ------------------------------------------------------------------- Task 3
def test_task3_top5_sorted_trimmed_and_persisted(tmp_path):
    path = tmp_path / "hs.json"
    hs = HighScores(str(path))
    for s in (50, 400, 120, 900, 10, 700, 300):
        hs.add(s, "WIN")
    assert [e["score"] for e in hs.entries] == [900, 700, 400, 300, 120]
    # persisted -> new session sees the same table
    assert [e["score"] for e in HighScores(str(path)).entries] == [900, 700, 400, 300, 120]
    assert hs.add(5, "LOSS") is None            # too low
    assert hs.add(800, "WIN") == 1              # rank 2


def test_task3_corrupt_or_missing_file_is_safe(tmp_path):
    p = tmp_path / "hs.json"
    assert HighScores(str(p)).entries == []
    p.write_text("{not json")
    assert HighScores(str(p)).entries == []
    p.write_text(json.dumps([{"score": "x"}, {"score": 5, "result": "WIN"}, 7]))
    assert [e["score"] for e in HighScores(str(p)).entries] == [5]


def test_task3_score_saved_when_game_ends(eng):
    eng.score = 250
    eng.lives = 1
    clear_traffic(eng)
    eng.player.invulnerable = 0
    eng.player.rect.center = (4 * LANE_W + 40, 300)
    eng.cars = [Car(4 * LANE_W, 280, 1, 0, lane=4)]
    eng.update(NONE)
    assert eng.game_over and eng.rank == 0
    assert HighScores(eng.highscores.path).entries[0]["score"] == 250
    eng.draw()  # end screen renders without error


# ------------------------------------------------------------------- Task 4
def test_task4_switches_every_30_seconds():
    dn = DayNight()
    assert not dn.night
    for _ in range(CYCLE_SECONDS * FPS - 1):
        dn.update()
    assert not dn.night
    dn.update()
    assert dn.night
    for _ in range(CYCLE_SECONDS * FPS):
        dn.update()
    assert not dn.night


def test_task4_night_beams_reach_further():
    dn = DayNight()
    day_len = dn.beam_length
    dn.night = True
    for _ in range(FPS + 1):
        dn.update()
    assert dn.level == 1.0
    assert dn.beam_length > 4 * day_len
    assert dn.darkness > 0


def test_task4_beam_points_in_driving_direction():
    down = Car(0, 100, 1, 3)
    up = Car(0, 100, -1, 3)
    assert max(y for _, y in down.beam_polygon(200)) > down.rect.bottom
    assert min(y for _, y in up.beam_polygon(200)) < up.rect.top


def test_task4_engine_draws_night_frame(eng):
    eng.daynight.timer = eng.daynight.period - 1
    for _ in range(120):
        eng.player.invulnerable = 10**6
        eng.update(NONE)
        eng.draw()
    assert eng.daynight.night and eng.daynight.level == 1.0

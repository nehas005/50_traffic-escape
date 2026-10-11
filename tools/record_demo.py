"""
Headless demo recorder: a scripted bot plays the game and every frame is piped to ffmpeg.

  python tools/record_demo.py --game <dir with main.py> --mode before|after --seed N --out clip.mp4

The game code is the *real* game (same engine/draw code) - only the keyboard is replaced by a bot.
"""
import argparse, os, random, subprocess, sys, tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

SECONDS, SIM_FPS, VID_FPS = 10, 60, 30


class Keys(dict):
    def __getitem__(self, k):
        return self.get(k, False)


def make_bots(pygame):
    K = pygame

    # ---------------------------------------------------------------- BEFORE
    def before_bot(e, f, st):
        keys = set()
        if f in (40,):                       # one hop right: still straddling a lane line
            keys.add(K.K_RIGHT)
        if f in (100,):
            keys.add(K.K_LEFT)
        return keys

    def before_caption(e, f, st):
        r = e.player.rect
        if e.game_over:
            return "BUG: one hit = instant game over (no lives)"
        if f < 80:
            return f"BUG: car is on a lane LINE (x={r.x}-{r.right}) - hit by 2 lanes"
        return "BUG: lane hops keep it between lanes, hitbox spans 2 lanes"

    # ----------------------------------------------------------------- AFTER
    def after_bot(e, f, st):
        from game.game_engine import ROAD_TOP, RIVER_BOTTOM, RIVER_TOP
        keys = set()
        p = e.player
        cx, cy = p.rect.center
        careless = e.lives == 3 and f < st.get("careless_until", 0)
        if cy >= RIVER_BOTTOM + 1 and cy > ROAD_TOP - 30:             # road / start / bank
            if p.rect.bottom <= ROAD_TOP + 8 and cy < ROAD_TOP:       # on the bank: wait for a log
                log = None
                for l in e.river.logs:
                    if l.rect.left + 25 < cx < l.rect.right - 25 and cx < 400:
                        log = l
                if log is not None:
                    keys.add(K.K_UP)
                return keys
            lane = cx // 80
            zone = K.Rect(p.rect.x, p.rect.y - 80, 40, 150)
            danger = False
            if not careless:
                for c in e.cars:
                    if c.lane == lane:
                        ahead = c.rect.move(0, c.direction * c.speed * 14)
                        if zone.colliderect(c.rect) or zone.colliderect(ahead):
                            danger = True
            if p.invulnerable == 0 or True:
                if not danger:
                    keys.add(K.K_UP)
        else:                                  # in the river / past it
            if RIVER_TOP <= cy < RIVER_BOTTOM - 25 and st.setdefault("ride", 0) < 80:
                st["ride"] += 1                # sit on the log and let it carry us
            else:
                keys.add(K.K_UP)
        return keys

    def after_caption(e, f, st):
        from game.game_engine import RIVER_TOP, RIVER_BOTTOM
        if e.won:
            return "Crossed! Score saved to the TOP-5 table (highscores.json)"
        if e.game_over:
            return "3 hits = GAME OVER, score saved to TOP-5"
        if e.player.invulnerable > 0 and e.lives < 3:
            return f"Task 1: hit! lives {e.lives}/3 - respawn + 2s protection"
        if RIVER_TOP <= e.player.rect.centery < RIVER_BOTTOM:
            return "Task 2: standing on a moving log (water = lose a life)"
        if e.daynight.level > 0.5:
            return "Task 4: NIGHT - headlight beams reach much further"
        return "Task 4: day/night toggles every 30 s (demo: timer pre-set to show night)"

    return before_bot, before_caption, after_bot, after_caption


def run(game_dir, mode, seed, out, hs_path=None, night_at=None, careless_until=0, frames_only=False):
    sys.path.insert(0, os.path.abspath(game_dir))
    import pygame
    from game.game_engine import GameEngine
    random.seed(seed)
    cur = {"keys": Keys()}
    pygame.key.get_pressed = lambda: cur["keys"]
    engine = GameEngine(hs_path) if (mode == "after" and hs_path) else GameEngine()
    if night_at is not None:
        engine.daynight.timer = engine.daynight.period - int(night_at * SIM_FPS)
    bb, bc, ab, ac = make_bots(pygame)
    bot, cap = (bb, bc) if mode == "before" else (ab, ac)
    st = {"careless_until": careless_until}
    font = pygame.font.SysFont("monospace", 17, bold=True)
    W, H = engine.screen.get_size()
    canvas = pygame.Surface((W, H + 40))
    ff = None
    if out:
        ff = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H+40}",
             "-r", str(VID_FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", out],
            stdin=subprocess.PIPE)
    log = {"lost": 0, "log_frames": 0, "night": False, "won": False, "over_at": None, "prev_lives": getattr(engine, "lives", 1)}
    for f in range(SECONDS * SIM_FPS):
        cur["keys"] = Keys({k: True for k in bot(engine, f, st)})
        engine.update()
        engine.draw()
        if mode == "after":
            if engine.lives < log["prev_lives"]:
                log["lost"] += 1
            log["prev_lives"] = engine.lives
            from game.game_engine import RIVER_TOP, RIVER_BOTTOM
            if RIVER_TOP <= engine.player.rect.centery < RIVER_BOTTOM:
                log["log_frames"] += 1
            log["night"] |= engine.daynight.level > 0.9
            if engine.won and not log["won"]:
                log["won_at"] = f
            log["won"] = engine.won
        if engine.game_over and log["over_at"] is None:
            log["over_at"] = f
        if ff and f % (SIM_FPS // VID_FPS) == 0:
            canvas.fill((15, 15, 15))
            canvas.blit(engine.screen, (0, 0))
            t = font.render(cap(engine, f, st), True, (255, 230, 120))
            canvas.blit(t, (8, H + 10))
            ff.stdin.write(pygame.image.tostring(canvas, "RGB"))
        if (engine.game_over or engine.won) and f - (log["over_at"] or f) > 0 and False:
            break
    if ff:
        ff.stdin.close(); ff.wait()
    return log


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=".")
    ap.add_argument("--mode", choices=["before", "after"], required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="demo.mp4")
    ap.add_argument("--night-at", type=float, default=None, help="seconds into the clip when night starts (demo only)")
    ap.add_argument("--careless", type=int, default=0, help="frames the bot ignores traffic")
    ap.add_argument("--hs", default=None)
    a = ap.parse_args()
    print(run(a.game, a.mode, a.seed, a.out, a.hs, a.night_at, a.careless))

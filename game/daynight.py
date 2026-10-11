FPS = 60
CYCLE_SECONDS = 30
DAY_BEAM = 40       # px: little glow in daylight
NIGHT_BEAM = 240    # px: long beams at night
MAX_DARKNESS = 170  # alpha 0-255


class DayNight:
    """Toggles day <-> night every CYCLE_SECONDS, with a 1-second fade."""

    def __init__(self, period_frames=CYCLE_SECONDS * FPS):
        self.period = period_frames
        self.timer = 0
        self.night = False
        self.level = 0.0  # 0 = full day, 1 = full night

    def update(self):
        self.timer += 1
        if self.timer >= self.period:
            self.timer = 0
            self.night = not self.night
        target = 1.0 if self.night else 0.0
        step = 1.0 / FPS
        if self.level < target:
            self.level = min(target, self.level + step)
        elif self.level > target:
            self.level = max(target, self.level - step)

    @property
    def seconds_left(self):
        return max(0, (self.period - self.timer + FPS - 1) // FPS)

    @property
    def beam_length(self):
        return DAY_BEAM + (NIGHT_BEAM - DAY_BEAM) * self.level

    @property
    def darkness(self):
        return int(MAX_DARKNESS * self.level)

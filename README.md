# Traffic Escape

Cross 8 lanes of oncoming traffic to reach the other side (Frogger-style).

## Setup

```bash
pip install -r requirements.txt
python main.py
```

## Controls

| Key | Action |
|-----|--------|
| A/D or Left/Right | Change lane |
| W / UP | Move forward |
| S / DOWN | Move back |
| R | Restart |

## Tasks to Complete  (all done)

### Task 1: Lives System - DONE
> Give the player 3 lives. Getting hit loses one; game over at 0.

Three hearts in the HUD. A hit respawns you on the start sidewalk with 2 s of protection (car blinks). Third hit = GAME OVER.

### Task 2: Moving Log/Raft Lane - DONE
> Add a safe lane where the player must hop on a moving log to cross.

A river sits between the road and the finish line. Water is deadly: you must stand on a log, which carries you sideways.
Falling in the water, or being carried off-screen, costs a life.

### Task 3: High Score Table - DONE
> Track and display the top 5 scores across sessions (save to JSON).

Scores are saved to `highscores.json` (created next to `main.py`, git-ignored) and the TOP 5 is shown on the end screen.
Score = 1 point per 2 px of new forward progress, +500 for finishing, +100 per life left.

### Task 4: Day/Night Cycle - DONE
> Every 30 seconds switch between day and night. At night, cars have headlights visible further ahead.

HUD shows `DAY`/`NIGHT` with a countdown. Night fades in over 1 s; headlight beams grow from 40 px (day) to 240 px (night).

## Bugs fixed in the starter code
See `Lab-4/bug_testing/BUG_REPORT.md` (BUG-01 .. BUG-09): player sat on a lane line, unused `SPEED`, hop cooldown blocking W/S,
no bottom clamp, float-speed truncation, overlapping cars, cars driving over sidewalks, invisible finish line.

## Tests
```bash
pip install -r requirements-dev.txt
python -m pytest -q          # 22 headless tests
```

## Demo recorder (how the before/after clips were made)
```bash
python tools/record_demo.py --game . --mode after --seed 3 --night-at 2.5 --out after.mp4
```
A scripted bot presses the keys; `--night-at` pre-advances the 30 s day/night timer so night shows up inside a 10 s clip.

## Folder Structure

```
traffic-escape/
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── game/
│   ├── __init__.py
│   ├── game_engine.py   # loop, lives, scoring, drawing, night overlay
│   ├── player.py        # lane-aligned movement
│   ├── traffic.py       # cars + headlight beams
│   ├── river.py         # water band + logs        (Task 2)
│   ├── daynight.py      # 30 s cycle               (Task 4)
│   └── highscores.py    # top-5 JSON table         (Task 3)
├── tests/
├── tools/record_demo.py
└── README.md
```

## Submission Checklist

Submission is only the following three things:

- [] A 10-second video of gameplay **before** your changes, showing the bug/broken behavior
- [] A 10-second video of gameplay **after** your changes, showing the bug fixed and the new features working
- [] The Chat/LLM used page link, with the complete chat history


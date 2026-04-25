# Rescue Mission: Shadow Kingdom

Python/Pygame top-down rescue shooter prototype.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

```powershell
.\.venv\Scripts\python.exe game_cuu_con_tin.py
```

Controls:

- `WASD` or arrow keys: move
- Mouse / left click: aim and shoot
- `Space`: shoot
- `Esc`: pause
- `R`: retry from pause/game over
- `M`: return to menu from pause/game over
- `F11` or `Alt+Enter`: toggle fullscreen

## Test

```powershell
python -m unittest discover -v
```

The first run may generate processed image cache files under `assets/.processed_cache/`.
They are ignored by git and make later startups faster.

## Runtime Notes

- Main entrypoint: `game_cuu_con_tin.py`
- Current runtime package: `rescue_mission/`
- `nhap.py` is a legacy single-file prototype kept for reference.

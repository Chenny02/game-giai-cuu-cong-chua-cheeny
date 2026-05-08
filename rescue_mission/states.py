from enum import Enum, auto


class GameState(Enum):
    MENU = auto()
    DIALOGUE = auto()
    PLAYING = auto()
    PAUSED = auto()
    LEVEL_COMPLETE = auto()
    UPGRADE_PICK = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    PROFILE = auto()
    LEVEL_PICK = auto()

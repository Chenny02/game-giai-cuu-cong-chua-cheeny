from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCREEN_WIDTH = 1180
SCREEN_HEIGHT = 760
FPS = 60
LEVEL_TIME_LIMIT_SECONDS = 180

WORLD_LEFT = 28
WORLD_TOP = 108
WORLD_WIDTH = 1124
WORLD_HEIGHT = 620

GAME_TITLE_MAIN = "Rescue Mission"
GAME_TITLE_SUBTITLE = "Shadow Kingdom"
TITLE = f"{GAME_TITLE_MAIN}: {GAME_TITLE_SUBTITLE}"

PLAYER_NAME = "Aris"
HOSTAGE_NAME = "Lina"
BOSS_NAME = "ORION"
LEVEL_COMPLETE_DELAY = 1800

PLAYER_BASE_HEALTH = 110
PLAYER_BASE_SPEED = 4.0
PLAYER_BASE_FIRE_INTERVAL = 13
PLAYER_BASE_BULLET_SPEED = 12.5
PLAYER_BASE_BULLET_DAMAGE = 18
PLAYER_IFRAMES = 18

PLAYER_SKILL_NAME = "Energy Shot"
PLAYER_SKILL_KEY_LABEL = "Q"
PLAYER_SKILL_DAMAGE = 52
PLAYER_SKILL_SPEED = 10.8
PLAYER_SKILL_LIFETIME = 1.15
PLAYER_SKILL_COOLDOWN = 1.2
PLAYER_SKILL_ENERGY_MAX = 100
PLAYER_SKILL_ENERGY_COST = 35
PLAYER_SKILL_ENERGY_REGEN = 17
PLAYER_SKILL_KNOCKBACK = 18

TILE_SIZE = 24
MAZE_WIDTH = 45
MAZE_HEIGHT = 25

BOSS_HEALTH = 420

CHARACTER_SHEET_COLUMNS = 1
CHARACTER_SHEET_ROWS = 1
BOSS_SHEET_COLUMNS = 1
BOSS_SHEET_ROWS = 1

PLAYER_RENDER_SIZE = (72, 72)
BOSS_RENDER_SIZE = (156, 156)
HOSTAGE_RENDER_SIZE = (72, 72)
EFFECT_RENDER_SIZE = (48, 48)

AnimationSpec = Dict[str, object]

PLAYER_ANIMATIONS: Dict[str, AnimationSpec] = {
    "idle": {
        "sections": [(470, 72, 660, 236, 4)],
        "fps": 7,
        "loop": True,
        "size": PLAYER_RENDER_SIZE,
        "pad": 6,
    },
    "run": {
        "sections": [(470, 545, 675, 245, 4)],
        "fps": 12,
        "loop": True,
        "size": PLAYER_RENDER_SIZE,
        "pad": 6,
    },
    "shoot": {
        "sections": [(20, 780, 450, 190, 3)],
        "fps": 18,
        "loop": False,
        "size": PLAYER_RENDER_SIZE,
        "pad": 6,
    },
}

BOSS_ANIMATIONS: Dict[str, AnimationSpec] = {
    "idle": {
        "sections": [(430, 30, 390, 145, 3)],
        "fps": 6,
        "loop": True,
        "size": BOSS_RENDER_SIZE,
        "pad": 8,
    },
    "move": {
        "sections": [(850, 30, 465, 145, 4)],
        "fps": 9,
        "loop": True,
        "size": BOSS_RENDER_SIZE,
        "pad": 8,
    },
    "attack1": {
        "sections": [
            (430, 176, 390, 144, 4),
            (845, 176, 470, 144, 4),
        ],
        "fps": 14,
        "loop": False,
        "size": BOSS_RENDER_SIZE,
        "pad": 8,
    },
    "attack2": {
        "sections": [(430, 300, 400, 125, 4)],
        "fps": 12,
        "loop": False,
        "size": BOSS_RENDER_SIZE,
        "pad": 8,
    },
    "attack3": {
        "sections": [(860, 295, 150, 130, 1)],
        "fps": 10,
        "loop": False,
        "size": BOSS_RENDER_SIZE,
        "pad": 8,
    },
    "death": {
        "sections": [(590, 430, 725, 150, 5)],
        "fps": 8,
        "loop": False,
        "size": (190, 160),
        "pad": 10,
    },
}

HOSTAGE_ANIMATIONS: Dict[str, AnimationSpec] = {
    "idle": {
        "sections": [(320, 615, 515, 120, 6)],
        "fps": 6,
        "loop": True,
        "size": HOSTAGE_RENDER_SIZE,
        "pad": 4,
    },
    "walk": {
        "sections": [(320, 735, 515, 125, 6)],
        "fps": 8,
        "loop": True,
        "size": HOSTAGE_RENDER_SIZE,
        "pad": 4,
    },
    "captured": {
        "sections": [(320, 1000, 515, 175, 4)],
        "fps": 5,
        "loop": True,
        "size": HOSTAGE_RENDER_SIZE,
        "pad": 4,
    },
    "rescued": {
        "sections": [(320, 865, 515, 130, 4)],
        "fps": 7,
        "loop": True,
        "size": HOSTAGE_RENDER_SIZE,
        "pad": 4,
    },
}

EFFECT_ANIMATIONS: Dict[str, AnimationSpec] = {
    "bullet": {
        "rects": [(910, 610, 90, 80)],
        "fps": 18,
        "loop": False,
        "size": (28, 28),
        "pad": 2,
    },
    "hit": {
        "rects": [(1200, 610, 95, 80)],
        "fps": 18,
        "loop": False,
        "size": EFFECT_RENDER_SIZE,
        "pad": 2,
    },
    "explosion": {
        "rects": [(1100, 605, 95, 88)],
        "fps": 16,
        "loop": False,
        "size": (72, 72),
        "pad": 2,
    },
}

COLOR_BG = (8, 14, 28)
COLOR_PANEL = (14, 24, 42)
COLOR_PANEL_ALT = (21, 34, 58)
COLOR_BORDER = (83, 161, 255)
COLOR_ACCENT = (69, 221, 191)
COLOR_ACCENT_DIM = (30, 132, 120)
COLOR_WARNING = (255, 174, 43)
COLOR_DANGER = (255, 82, 108)
COLOR_TEXT = (237, 244, 255)
COLOR_SUBTEXT = (164, 184, 214)
COLOR_GRID = (22, 40, 72)
COLOR_SHADOW = (2, 6, 14)
COLOR_MAZE_WALL = (46, 72, 108)
COLOR_MAZE_WALL_ALT = (28, 43, 68)
COLOR_SKILL = (86, 226, 255)
COLOR_SKILL_DIM = (40, 108, 148)


@dataclass(frozen=True)
class PlayerStats:
    move_speed: float
    fire_interval: int
    bullet_speed: float
    bullet_damage: int
    max_health: int


@dataclass(frozen=True)
class UpgradeInfo:
    title: str
    description: str


@dataclass(frozen=True)
class BossProfile:
    key: str
    display_name: str
    max_health: int
    move_speed: float
    desired_range: float
    primary_damage: int
    primary_speed: float
    secondary_damage: int
    secondary_speed: float
    phase_count: int
    summon_enabled: bool
    summon_cooldown: float
    contact_damage: int
    primary_color: Tuple[int, int, int]
    secondary_color: Tuple[int, int, int]


BOSS_PROFILES = {
    "aegis_prime": BossProfile(
        key="aegis_prime",
        display_name="AEGIS PRIME",
        max_health=320,
        move_speed=2.05,
        desired_range=155,
        primary_damage=17,
        primary_speed=10.2,
        secondary_damage=14,
        secondary_speed=7.0,
        phase_count=2,
        summon_enabled=False,
        summon_cooldown=999.0,
        contact_damage=22,
        primary_color=(255, 150, 96),
        secondary_color=(255, 204, 110),
    ),
    "orion_prime": BossProfile(
        key="orion_prime",
        display_name=BOSS_NAME,
        max_health=560,
        move_speed=2.2,
        desired_range=190,
        primary_damage=20,
        primary_speed=11.0,
        secondary_damage=16,
        secondary_speed=7.8,
        phase_count=3,
        summon_enabled=True,
        summon_cooldown=3.8,
        contact_damage=28,
        primary_color=(255, 154, 91),
        secondary_color=(219, 132, 255),
    ),
}


def player_stats_for_level(level_number: int) -> PlayerStats:
    return PlayerStats(
        move_speed=PLAYER_BASE_SPEED + 0.22 * (level_number - 1),
        fire_interval=max(6, PLAYER_BASE_FIRE_INTERVAL - (level_number - 1)),
        bullet_speed=PLAYER_BASE_BULLET_SPEED + 0.55 * (level_number - 1),
        bullet_damage=PLAYER_BASE_BULLET_DAMAGE + 3 * (level_number - 1),
        max_health=PLAYER_BASE_HEALTH + 10 * (level_number - 1),
    )


def upgrade_for_level(level_number: int) -> UpgradeInfo:
    upgrades = {
        1: UpgradeInfo("Trang bị I", "Di chuyển cơ bản, súng ổn định."),
        2: UpgradeInfo("Nhịp chiến đấu", "Bắn nhanh hơn, sát thương cao hơn."),
        3: UpgradeInfo("Dấu dẫn đường", "Mê cung lộ tuyến chính rõ hơn."),
        4: UpgradeInfo("Energy Shot", "Mở kỹ năng bắn chưởng bằng phím Q."),
        5: UpgradeInfo("Áp lực tổng hợp", "Địch đông hơn, xuất hiện miniboss."),
        6: UpgradeInfo("Giao tranh cuối", "Đấu trường boss hoàn chỉnh."),
    }
    return upgrades[level_number]

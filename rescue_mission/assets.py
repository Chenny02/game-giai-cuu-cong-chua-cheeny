from collections import Counter, deque
import hashlib
import math
from pathlib import Path

import pygame

from . import config
from .core.sprite_sheet import SpriteSheet


DIRECTION_TOKENS = ("e", "se", "s", "sw", "w", "nw", "n", "ne")


def _clamp_color(color):
    return tuple(max(0, min(255, int(value))) for value in color)


def tint_surface(surface, color, alpha=90):
    tinted = surface.copy()
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((*_clamp_color(color), alpha))
    tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return tinted


def make_vertical_gradient(size, top_color, bottom_color):
    surface = pygame.Surface(size)
    width, height = size
    for y in range(height):
        blend = y / max(1, height - 1)
        color = (
            top_color[0] + (bottom_color[0] - top_color[0]) * blend,
            top_color[1] + (bottom_color[1] - top_color[1]) * blend,
            top_color[2] + (bottom_color[2] - top_color[2]) * blend,
        )
        pygame.draw.line(surface, _clamp_color(color), (0, y), (width, y))
    return surface.convert()


def make_grid_surface(size, cell_size, color, accent):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    width, height = size
    for x in range(0, width, cell_size):
        pygame.draw.line(surface, (*color, 120), (x, 0), (x, height))
    for y in range(0, height, cell_size):
        pygame.draw.line(surface, (*color, 120), (0, y), (width, y))
    for x in range(0, width, cell_size * 4):
        pygame.draw.line(surface, (*accent, 60), (x, 0), (x, height), 2)
    for y in range(0, height, cell_size * 4):
        pygame.draw.line(surface, (*accent, 60), (0, y), (width, y), 2)
    return surface


def make_player_surface(size):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    rect = surface.get_rect()
    pygame.draw.circle(surface, (57, 161, 255), rect.center, rect.width // 2 - 2)
    pygame.draw.circle(surface, (203, 236, 255), rect.center, rect.width // 4)
    pygame.draw.circle(surface, (255, 255, 255), (rect.centerx + 5, rect.centery - 5), 3)
    return surface


def make_enemy_surface(size, primary, secondary):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    rect = surface.get_rect()
    points = [
        (rect.centerx, rect.top + 2),
        (rect.right - 3, rect.centery + 2),
        (rect.centerx + 4, rect.bottom - 3),
        (rect.centerx, rect.bottom - 8),
        (rect.centerx - 4, rect.bottom - 3),
        (rect.left + 3, rect.centery + 2),
    ]
    pygame.draw.polygon(surface, (8, 12, 24, 150), [(x + 2, y + 2) for x, y in points])
    pygame.draw.polygon(surface, primary, points)
    pygame.draw.polygon(surface, secondary, [rect.center, (rect.centerx + 8, rect.centery + 2), (rect.centerx, rect.centery + 10), (rect.centerx - 8, rect.centery + 2)])
    pygame.draw.circle(surface, (255, 255, 255), (rect.centerx - 5, rect.centery - 5), 2)
    pygame.draw.circle(surface, (255, 255, 255), (rect.centerx + 5, rect.centery - 5), 2)
    return surface


def make_radial_glow(size, color, alpha_scale=1.0):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    width, height = size
    if width <= 0 or height <= 0:
        return surface

    center = (width / 2, height / 2)
    rings = 18
    for ring in range(rings, 0, -1):
        blend = ring / rings
        glow_w = max(8, int(width * blend))
        glow_h = max(8, int(height * blend))
        alpha = int(22 * blend * alpha_scale)
        rect = pygame.Rect(0, 0, glow_w, glow_h)
        rect.center = (int(center[0]), int(center[1]))
        pygame.draw.ellipse(surface, (*_clamp_color(color), alpha), rect)
    return surface


def make_hostage_surface(size):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    rect = surface.get_rect()
    pygame.draw.rect(surface, (255, 214, 85), (rect.centerx - 8, 12, 16, rect.height - 20), border_radius=8)
    pygame.draw.circle(surface, (255, 236, 175), (rect.centerx, 9), 8)
    pygame.draw.rect(surface, (53, 37, 18), (rect.centerx - 6, 18, 12, 4), border_radius=2)
    return surface


def make_boss_surface(size):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    rect = surface.get_rect()
    pygame.draw.circle(surface, (194, 63, 255), rect.center, rect.width // 2 - 2)
    pygame.draw.circle(surface, (255, 130, 85), rect.center, rect.width // 4 + 4)
    pygame.draw.circle(surface, (255, 255, 255), (rect.centerx - 10, rect.centery - 10), 4)
    pygame.draw.circle(surface, (255, 255, 255), (rect.centerx + 10, rect.centery - 10), 4)
    return surface


def _border_points(width, height):
    for x in range(width):
        yield x, 0
        if height > 1:
            yield x, height - 1
    for y in range(1, height - 1):
        yield 0, y
        if width > 1:
            yield width - 1, y


def cleanup_loose_frame_background(surface):
    """Loại nền sáng/checkerboard dính trong PNG frame rời.

    Nhiều asset export từ tool ảnh giữ nguyên nền preview trắng/xám thay vì alpha thật.
    Ta chỉ xóa vùng nền nối từ mép ảnh để không ăn mất chi tiết sáng bên trong nhân vật.
    """

    width, height = surface.get_size()
    if width <= 2 or height <= 2:
        return surface

    border_samples = [surface.get_at(point) for point in _border_points(width, height)]
    if not border_samples or any(sample.a < 250 for sample in border_samples):
        return surface

    def quantize(color, step=16):
        return tuple((channel // step) * step for channel in color[:3])

    palette_counts = Counter(quantize(sample) for sample in border_samples)
    palette = [color for color, _ in palette_counts.most_common(4)]
    if not palette:
        return surface

    average_brightness = sum(max(sample.r, sample.g, sample.b) for sample in border_samples) / len(border_samples)
    if average_brightness < 150:
        return surface

    def near_border_color(color):
        rgb = color[:3]
        return any(sum(abs(rgb[index] - bg[index]) for index in range(3)) <= 42 for bg in palette)

    cleaned = surface.copy()
    queue = deque()
    visited = set()

    for point in _border_points(width, height):
        pixel = cleaned.get_at(point)
        if pixel.a >= 250 and near_border_color(pixel):
            queue.append(point)
            visited.add(point)

    removed = 0
    while queue:
        x, y = queue.popleft()
        pixel = cleaned.get_at((x, y))
        if pixel.a == 0 or not near_border_color(pixel):
            continue

        cleaned.set_at((x, y), (0, 0, 0, 0))
        removed += 1

        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                visited.add((nx, ny))
                neighbor = cleaned.get_at((nx, ny))
                if neighbor.a >= 250 and near_border_color(neighbor):
                    queue.append((nx, ny))

    # Một số ảnh export để lại vài pixel trắng lẻ ở đúng mép ảnh.
    # Xoá nốt những điểm này để bounding box không bị kéo full canvas.
    changed = True
    while changed:
        changed = False
        for point in list(_border_points(width, height)):
            pixel = cleaned.get_at(point)
            if pixel.a >= 250 and near_border_color(pixel):
                cleaned.set_at(point, (0, 0, 0, 0))
                changed = True

    if removed == 0 and not changed:
        return surface

    bounds = cleaned.get_bounding_rect(min_alpha=1)
    if bounds.width <= 0 or bounds.height <= 0:
        return surface
    return cleaned.subsurface(bounds).copy()


def trim_frame_surface(surface, pad=6):
    """Trim alpha thật để sprite không bị bé do viền trống quá lớn."""

    bounds = surface.get_bounding_rect(min_alpha=1)
    if bounds.width <= 0 or bounds.height <= 0:
        return surface

    width, height = surface.get_size()
    has_transparent_corners = any(
        surface.get_at(point).a == 0
        for point in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1))
    )

    # Một số PNG có alpha đúng ở viền ngoài nhưng vẫn còn bóng đen rất lớn bên trong.
    # Khi đó bounding rect theo alpha sẽ giữ gần như cả canvas và làm sprite bị bé.
    if has_transparent_corners and (bounds.width >= width * 0.9 or bounds.height >= height * 0.9):
        visible = _find_visible_bounds(surface, min_alpha=16, min_brightness=28)
        if visible is not None:
            bounds = visible

    if pad:
        bounds.inflate_ip(pad * 2, pad * 2)
        bounds = bounds.clip(surface.get_rect())
    return surface.subsurface(bounds).copy()


def _find_visible_bounds(surface, min_alpha=16, min_brightness=28):
    """Tìm bounds của phần sprite thực sự nhìn thấy được.

    Bỏ qua bóng rất tối hoặc rác alpha yếu để khung cắt sát nhân vật hơn.
    """

    width, height = surface.get_size()
    min_x, min_y = width, height
    max_x, max_y = -1, -1

    for y in range(height):
        for x in range(width):
            r, g, b, a = surface.get_at((x, y))
            if a < min_alpha or max(r, g, b) < min_brightness:
                continue
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
            if x > max_x:
                max_x = x
            if y > max_y:
                max_y = y

    if max_x < min_x or max_y < min_y:
        return None
    return pygame.Rect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)


def fit_surface_to_canvas(surface, canvas_size):
    """Scale giữ nguyên tỉ lệ rồi đặt vào canvas trong suốt.

    Tránh kéo méo ảnh khi nguồn có tỉ lệ khác canvas đích.
    """

    target_w, target_h = canvas_size
    if target_w <= 0 or target_h <= 0:
        return surface.copy()

    source_w, source_h = surface.get_size()
    if source_w <= 0 or source_h <= 0:
        return pygame.Surface(canvas_size, pygame.SRCALPHA)

    scale = min(target_w / source_w, target_h / source_h)
    scaled_size = (
        max(1, round(source_w * scale)),
        max(1, round(source_h * scale)),
    )
    scaled = pygame.transform.smoothscale(surface, scaled_size)

    canvas = pygame.Surface(canvas_size, pygame.SRCALPHA)
    rect = scaled.get_rect(center=(target_w // 2, target_h // 2))
    canvas.blit(scaled, rect)
    return canvas


def make_motion_variants(frame, count, mode):
    if count <= 1:
        return [frame]

    variants = []
    width, height = frame.get_size()
    for index in range(count):
        phase = (index / count) * math.tau
        canvas = pygame.Surface((width, height), pygame.SRCALPHA)

        if mode == "shoot":
            scale = 1.0 + (0.08 if index == 0 else -0.03 if index == 1 else 0.0)
            offset_x = -4 if index == 0 else 3 if index == 1 else 0
            offset_y = 0
        elif mode == "death":
            scale = 1.0 + index * 0.045
            offset_x = 0
            offset_y = index * 2
        elif mode.startswith("attack"):
            scale = 1.0 + math.sin(phase) * 0.05
            offset_x = -2 if index % 2 == 0 else 2
            offset_y = -2
        else:
            scale = 1.0 + math.sin(phase) * 0.025
            offset_x = int(math.sin(phase) * 2)
            offset_y = int(math.cos(phase) * 3)

        scaled_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        scaled = pygame.transform.smoothscale(frame, scaled_size)
        if mode == "death":
            scaled.set_alpha(max(45, 255 - index * (190 // max(1, count - 1))))
        rect = scaled.get_rect(center=(width // 2 + offset_x, height // 2 + offset_y))
        canvas.blit(scaled, rect)

        if mode in ("shoot", "attack1", "attack2", "attack3") and index == 0:
            glow_color = (255, 238, 170, 95) if mode == "shoot" else (255, 110, 170, 80)
            pygame.draw.circle(canvas, glow_color, (width // 2 + width // 4, height // 2), max(7, width // 10))
        variants.append(canvas)
    return variants


def prepare_alpha_surface(surface, target_size, cleanup_scale=4):
    """Chuẩn hóa sprite alpha theo kích thước đích với chi phí thấp hơn.

    Các frame nguồn hiện rất lớn so với kích thước render cuối cùng.
    Nếu cleanup trực tiếp trên ảnh gốc, startup sẽ bị treo hàng chục giây.
    Vì sprite cuối chỉ hiển thị rất nhỏ, ta thu ảnh về cỡ làm việc gần target trước,
    rồi mới cleanup/trim/final-fit.
    """

    target_w, target_h = target_size
    if target_w <= 0 or target_h <= 0:
        return surface.copy()

    working_max_w = max(target_w * cleanup_scale, target_w)
    working_max_h = max(target_h * cleanup_scale, target_h)
    source_w, source_h = surface.get_size()

    scale = min(1.0, working_max_w / max(1, source_w), working_max_h / max(1, source_h))
    if scale < 1.0:
        surface = pygame.transform.smoothscale(
            surface,
            (
                max(1, round(source_w * scale)),
                max(1, round(source_h * scale)),
            ),
        )

    surface = cleanup_loose_frame_background(surface)
    surface = trim_frame_surface(surface)
    return fit_surface_to_canvas(surface, target_size)


class AssetManager:
    """Quản lý asset của game.

    Thứ tự ưu tiên:
    1. `assets/animations/<entity>/<state>/*.png`
    2. atlas cũ `character.png`, `boss.png`
    3. sprite đơn lẻ / fallback vẽ bằng code

    Mục tiêu là để pipeline làm ảnh đơn giản hơn: chỉ cần thả frame PNG vào đúng thư mục.
    """

    def __init__(self):
        self.project_root = Path(config.PROJECT_ROOT)
        self.animation_root = self.project_root / "assets" / "animations"
        self.cache_root = self.project_root / "assets" / ".processed_cache"

        self.font_title = pygame.font.SysFont("bahnschrift", 64, bold=True)
        self.font_menu_hero = pygame.font.SysFont("bahnschrift", 78, bold=True)
        self.font_menu_title = pygame.font.SysFont("bahnschrift", 58, bold=True)
        self.font_menu_panel = pygame.font.SysFont("bahnschrift", 22, bold=True)
        self.font_h1 = pygame.font.SysFont("segoeui", 36, bold=True)
        self.font_h2 = pygame.font.SysFont("segoeui", 24, bold=True)
        self.font_body = pygame.font.SysFont("segoeui", 20)
        self.font_small = pygame.font.SysFont("consolas", 16)

        self.menu_background = self.build_menu_background()
        self.menu_frame_overlay = self.build_menu_frame_overlay()
        self.world_background = make_vertical_gradient(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            (8, 16, 31),
            (4, 8, 14),
        )
        self.grid_overlay = make_grid_surface(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            24,
            config.COLOR_GRID,
            config.COLOR_BORDER,
        )

        self.animation_frames = {
            "player": self.load_animation_folders(
                "player",
                {
                    "idle": config.PLAYER_RENDER_SIZE,
                    "run": config.PLAYER_RENDER_SIZE,
                    "shoot": config.PLAYER_RENDER_SIZE,
                },
            ),
            "boss": self.load_animation_folders(
                "boss",
                {
                    "idle": config.BOSS_RENDER_SIZE,
                    "move": config.BOSS_RENDER_SIZE,
                    "attack1": config.BOSS_RENDER_SIZE,
                    "attack2": config.BOSS_RENDER_SIZE,
                    "attack3": config.BOSS_RENDER_SIZE,
                    "death": (190, 160),
                },
            ),
            "hostage": self.load_animation_folders(
                "hostage",
                {
                    "idle": config.HOSTAGE_RENDER_SIZE,
                    "walk": config.HOSTAGE_RENDER_SIZE,
                    "rescued": config.HOSTAGE_RENDER_SIZE,
                    "captured": config.HOSTAGE_RENDER_SIZE,
                },
            ),
            "effects": self.load_animation_folders(
                "effects",
                {
                    "bullet": (28, 28),
                    "hit": config.EFFECT_RENDER_SIZE,
                    "explosion": (72, 72),
                    "rescue": (84, 84),
                },
            ),
        }
        self.directional_animation_frames = {
            "player": self.load_directional_animation_folders(
                "player",
                {
                    "idle": config.PLAYER_RENDER_SIZE,
                    "run": config.PLAYER_RENDER_SIZE,
                    "shoot": config.PLAYER_RENDER_SIZE,
                },
            ),
            "boss": self.load_directional_animation_folders(
                "boss",
                {
                    "idle": config.BOSS_RENDER_SIZE,
                    "move": config.BOSS_RENDER_SIZE,
                    "attack1": config.BOSS_RENDER_SIZE,
                    "attack2": config.BOSS_RENDER_SIZE,
                    "attack3": config.BOSS_RENDER_SIZE,
                    "death": (190, 160),
                },
            ),
            "hostage": self.load_directional_animation_folders(
                "hostage",
                {
                    "idle": config.HOSTAGE_RENDER_SIZE,
                    "walk": config.HOSTAGE_RENDER_SIZE,
                    "rescued": config.HOSTAGE_RENDER_SIZE,
                    "captured": config.HOSTAGE_RENDER_SIZE,
                },
            ),
        }

        self.sprite_sheets = {
            "character": self.load_sprite_sheet("character.png", config.CHARACTER_SHEET_COLUMNS, config.CHARACTER_SHEET_ROWS),
            "boss": self.load_sprite_sheet("boss.png", config.BOSS_SHEET_COLUMNS, config.BOSS_SHEET_ROWS),
        }

        self.images = {
            "player": self.load_first_available_image(("image.png", "player.png"), (34, 34), alpha=True) or make_player_surface((34, 34)),
            "hostage": self.load_optional_image("hostage.png", (26, 42), alpha=True) or make_hostage_surface((26, 42)),
            "enemy_grunt": self.load_optional_image("enemy.png", (30, 30), alpha=True) or make_enemy_surface((30, 30), (246, 87, 110), (255, 205, 214)),
            "enemy_runner": make_enemy_surface((26, 26), (255, 169, 55), (255, 228, 175)),
            "enemy_shooter": make_enemy_surface((32, 32), (134, 94, 255), (219, 208, 255)),
            "boss": make_boss_surface((96, 96)),
            "world_bg": self.load_optional_image("bg.png", (config.SCREEN_WIDTH, config.SCREEN_HEIGHT), alpha=False),
        }
        self.menu_glow_blue = make_radial_glow((250, 320), (72, 208, 255), alpha_scale=0.72)
        self.menu_glow_purple = make_radial_glow((360, 430), (182, 74, 255), alpha_scale=0.82)
        self.menu_glow_gold = make_radial_glow((250, 330), (255, 194, 76), alpha_scale=0.72)
        self.menu_player_portrait = self.load_menu_portrait("player", "idle", (210, 250), self.images["player"])
        self.menu_boss_portrait = self.load_menu_portrait("boss", "idle", (350, 400), self.images["boss"])
        self.menu_hostage_portrait = self.load_menu_portrait("hostage", "idle", (220, 340), self.images["hostage"])

    def load_optional_image(self, filename, size, alpha=True):
        path = self.project_root / filename
        if not path.exists():
            return None

        if alpha:
            return self.load_prepared_alpha_image(path, size)

        image = pygame.image.load(str(path)).convert()
        return pygame.transform.smoothscale(image, size)

    def load_prepared_alpha_image(self, path, size):
        cached = self.load_cached_prepared_image(path, size)
        if cached is not None:
            return cached

        image = pygame.image.load(str(path)).convert_alpha()
        prepared = prepare_alpha_surface(image, size)
        self.save_cached_prepared_image(path, size, prepared)
        return prepared

    def cache_path_for(self, path, size):
        try:
            stat = path.stat()
        except OSError:
            return None

        source_id = f"{path.relative_to(self.project_root)}|{stat.st_mtime_ns}|{stat.st_size}|{size[0]}x{size[1]}"
        digest = hashlib.sha1(source_id.encode("utf-8")).hexdigest()
        return self.cache_root / f"{digest}.png"

    def load_cached_prepared_image(self, path, size):
        cache_path = self.cache_path_for(path, size)
        if cache_path is None or not cache_path.exists():
            return None
        try:
            image = pygame.image.load(str(cache_path)).convert_alpha()
        except (pygame.error, FileNotFoundError):
            return None
        if image.get_size() != tuple(size):
            return None
        return image

    def save_cached_prepared_image(self, path, size, surface):
        cache_path = self.cache_path_for(path, size)
        if cache_path is None:
            return
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(surface, str(cache_path))
        except (OSError, pygame.error):
            return

    def load_sprite_sheet(self, filename, columns, rows):
        path = self.project_root / filename
        if not path.exists():
            return None
        return SpriteSheet(path, columns, rows)

    def load_first_available_image(self, filenames, size, alpha=True):
        for filename in filenames:
            image = self.load_optional_image(filename, size, alpha=alpha)
            if image is not None:
                return image
        return None

    def load_menu_portrait(self, entity_name, state_name, size, fallback_surface):
        fit_overrides = {
            "player": "tmp_player_idle_clean.png",
            "boss": "tmp_boss_idle_clean.png",
            "hostage": "tmp_hostage_idle_clean.png",
        }
        override_name = fit_overrides.get(entity_name)
        if override_name:
            override_path = self.project_root / override_name
            if override_path.exists():
                return self.load_prepared_alpha_image(override_path, size)

        state_dir = self.animation_root / entity_name / state_name
        if state_dir.exists():
            for image_path in sorted(state_dir.glob("*.png")):
                return self.load_prepared_alpha_image(image_path, size)
        return fit_surface_to_canvas(fallback_surface, size)

    def build_menu_background(self):
        surface = make_vertical_gradient(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            (18, 14, 42),
            (5, 8, 18),
        )
        surface.blit(make_radial_glow((760, 520), (140, 66, 255), alpha_scale=1.5), (210, 18), special_flags=pygame.BLEND_RGBA_ADD)
        surface.blit(make_radial_glow((360, 280), (74, 214, 255), alpha_scale=1.2), (-40, 190), special_flags=pygame.BLEND_RGBA_ADD)
        surface.blit(make_radial_glow((360, 280), (255, 181, 82), alpha_scale=0.9), (850, 230), special_flags=pygame.BLEND_RGBA_ADD)

        for x in range(0, config.SCREEN_WIDTH, 48):
            top = 24 + int(14 * math.sin(x / 120))
            pygame.draw.line(surface, (22, 34, 72), (x, 0), (x + 22, top), 1)
        for idx in range(28):
            px = 40 + idx * 40
            py = 36 + (idx * 29) % 160
            color = (255, 205, 96) if idx % 5 == 0 else (164, 184, 214)
            surface.fill(color, ((px, py), (2, 2)))

        horizon = config.SCREEN_HEIGHT - 176
        ridge_points = [
            (0, horizon + 54),
            (92, horizon + 34),
            (176, horizon + 60),
            (264, horizon + 22),
            (356, horizon + 72),
            (446, horizon + 28),
            (548, horizon + 56),
            (658, horizon + 12),
            (778, horizon + 58),
            (898, horizon + 22),
            (1020, horizon + 72),
            (1116, horizon + 36),
            (config.SCREEN_WIDTH, horizon + 58),
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            (0, config.SCREEN_HEIGHT),
        ]
        pygame.draw.polygon(surface, (20, 16, 44), ridge_points)

        castle_color = (12, 16, 34)
        accent_color = (56, 34, 94)
        towers = [
            pygame.Rect(486, horizon - 48, 42, 128),
            pygame.Rect(558, horizon - 98, 54, 178),
            pygame.Rect(646, horizon - 64, 46, 144),
        ]
        for tower in towers:
            pygame.draw.rect(surface, castle_color, tower)
            pygame.draw.rect(surface, accent_color, tower.inflate(-24, -34), border_radius=6)
            roof = [(tower.x - 8, tower.y + 10), (tower.centerx, tower.y - 34), (tower.right + 8, tower.y + 10)]
            pygame.draw.polygon(surface, (30, 24, 62), roof)

        for chain_x in (268, 886):
            for segment in range(10):
                y = 18 + segment * 34
                link = pygame.Rect(chain_x + (segment % 2) * 8, y, 22, 12)
                pygame.draw.ellipse(surface, (28, 32, 60), link, 3)

        fog = pygame.Surface((config.SCREEN_WIDTH, 220), pygame.SRCALPHA)
        for row in range(12):
            alpha = 18 + row * 6
            pygame.draw.ellipse(
                fog,
                (120, 54, 192, alpha),
                pygame.Rect(-90 + row * 18, 26 + row * 8, config.SCREEN_WIDTH - row * 12, 140),
            )
        surface.blit(fog, (0, config.SCREEN_HEIGHT - 220))
        return surface.convert()

    def build_menu_frame_overlay(self):
        surface = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        outer = pygame.Rect(16, 16, config.SCREEN_WIDTH - 32, config.SCREEN_HEIGHT - 32)
        inner = outer.inflate(-20, -20)
        pygame.draw.rect(surface, (62, 112, 210, 92), outer, width=2, border_radius=18)
        pygame.draw.rect(surface, (28, 46, 88, 180), inner, width=1, border_radius=16)

        corners = [
            ((outer.left, outer.top + 36), (outer.left, outer.top), (outer.left + 36, outer.top)),
            ((outer.right - 36, outer.top), (outer.right, outer.top), (outer.right, outer.top + 36)),
            ((outer.left, outer.bottom - 36), (outer.left, outer.bottom), (outer.left + 36, outer.bottom)),
            ((outer.right - 36, outer.bottom), (outer.right, outer.bottom), (outer.right, outer.bottom - 36)),
        ]
        for points in corners:
            pygame.draw.lines(surface, (114, 196, 255, 155), False, points, 3)
        return surface

    def load_animation_folders(self, entity_name, state_sizes):
        """Load frame rời từ thư mục.

        Cấu trúc:
        `assets/animations/<entity>/<state>/*.png`

        Ví dụ:
        `assets/animations/player/idle/idle_01.png`
        """

        entity_root = self.animation_root / entity_name
        loaded = {}
        if not entity_root.exists():
            return loaded

        for state_name, size in state_sizes.items():
            state_dir = entity_root / state_name
            if not state_dir.exists():
                continue

            frames = []
            for image_path in sorted(state_dir.glob("*.png")):
                frames.append(self.load_prepared_alpha_image(image_path, size))

            if frames:
                loaded[state_name] = self.expand_loose_frames(entity_name, state_name, frames)

        return loaded

    def load_directional_animation_folders(self, entity_name, state_sizes):
        entity_root = self.animation_root / entity_name
        loaded = {}
        if not entity_root.exists():
            return loaded

        for state_name, size in state_sizes.items():
            state_dir = entity_root / f"{state_name}_8dir"
            if not state_dir.exists():
                continue

            state_bank = {}
            for token in DIRECTION_TOKENS:
                frames = []
                exact = state_dir / f"{token}.png"
                if exact.exists():
                    frames.append(self.load_prepared_alpha_image(exact, size))
                for image_path in sorted(state_dir.glob(f"{token}_*.png")):
                    frames.append(self.load_prepared_alpha_image(image_path, size))
                if len(frames) == 1:
                    frames = self.expand_directional_frames(state_name, frames[0])
                if frames:
                    state_bank[token] = frames

            if state_bank:
                loaded[state_name] = state_bank

        idle_bank = loaded.get("idle")
        if idle_bank:
            synthesized_by_entity = {
                "player": {
                    "run": ("run", 4),
                    "shoot": ("shoot", 3),
                },
                "boss": {
                    "move": ("run", 4),
                    "attack1": ("attack1", 4),
                    "attack2": ("attack2", 4),
                    "attack3": ("attack3", 3),
                    "death": ("death", 5),
                },
                "hostage": {
                    "walk": ("run", 4),
                    "rescued": ("idle", 3),
                    "captured": ("idle", 3),
                },
            }
            synthesized = synthesized_by_entity.get(entity_name, {})
            for state_name, (mode, count) in synthesized.items():
                if state_name in loaded:
                    continue
                loaded[state_name] = {
                    token: make_motion_variants(frames[0], count, mode)
                    for token, frames in idle_bank.items()
                    if frames
                }

        return loaded

    def expand_loose_frames(self, entity_name, state_name, frames):
        """Give single-frame placeholder states enough motion for playtests."""

        if len(frames) != 1:
            return frames

        desired_counts = {
            "player": {"run": 4, "shoot": 3},
            "boss": {"move": 4, "attack1": 4, "attack2": 4, "attack3": 3, "death": 5},
            "hostage": {"walk": 4, "rescued": 3, "captured": 3},
        }
        count = desired_counts.get(entity_name, {}).get(state_name, 1)
        return make_motion_variants(frames[0], count, state_name)

    def expand_directional_frames(self, state_name, frame):
        desired_counts = {
            "run": 4,
            "shoot": 3,
        }
        count = desired_counts.get(state_name, 1)
        return make_motion_variants(frame, count, state_name) if count > 1 else [frame]

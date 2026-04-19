from collections import Counter, deque
from pathlib import Path

import pygame

from . import config
from .core.sprite_sheet import SpriteSheet


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
    pygame.draw.circle(surface, primary, rect.center, rect.width // 2 - 2)
    pygame.draw.circle(surface, secondary, rect.center, rect.width // 4)
    pygame.draw.circle(surface, (255, 255, 255), (rect.centerx - 5, rect.centery - 4), 2)
    pygame.draw.circle(surface, (255, 255, 255), (rect.centerx + 5, rect.centery - 4), 2)
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

        self.font_title = pygame.font.SysFont("bahnschrift", 64, bold=True)
        self.font_h1 = pygame.font.SysFont("segoeui", 36, bold=True)
        self.font_h2 = pygame.font.SysFont("segoeui", 24, bold=True)
        self.font_body = pygame.font.SysFont("segoeui", 20)
        self.font_small = pygame.font.SysFont("consolas", 16)

        self.menu_background = make_vertical_gradient(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            (10, 16, 34),
            (4, 8, 16),
        )
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

    def load_optional_image(self, filename, size, alpha=True):
        path = self.project_root / filename
        if not path.exists():
            return None

        image = pygame.image.load(str(path))
        image = image.convert_alpha() if alpha else image.convert()
        if alpha:
            return prepare_alpha_surface(image, size)
        return pygame.transform.smoothscale(image, size)

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
                image = pygame.image.load(str(image_path)).convert_alpha()
                image = prepare_alpha_surface(image, size)
                frames.append(image)

            if frames:
                loaded[state_name] = frames

        return loaded

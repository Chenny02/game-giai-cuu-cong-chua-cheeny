"""He thong man choi va mission runtime.

Y tuong:
- `LevelSpec` chua du lieu tinh cua tung man.
- `Maze` chiu trach nhiem sinh me cung, va cham grid, minimap va pathfinding.
- `LevelScene` la noi ghep tat ca thanh 1 man choi hoan chinh.

Tach rieng module nay giup `Game` khong phai biet combat loop, spawn hay objective.
"""

import random
from collections import deque
from dataclasses import dataclass
from typing import Dict, Tuple

import pygame

from . import config
from .entities import Bullet, ENEMY_TYPES, Enemy
from .pathfinding import AStarPathfinder
from .sprites.boss import Boss
from .sprites.effects import Effect, build_effect_animations
from .sprites.hostage import Hostage
from .sprites.player import Player


@dataclass(frozen=True)
class LevelSpec:
    """Du lieu cau hinh cho tung man."""

    number: int
    title: str
    description: str
    use_maze: bool
    has_boss: bool
    hostage_required: bool
    time_limit: int
    enemy_weights: Dict[str, int]
    spawn_range: Tuple[int, int]
    max_enemies: int


def build_level_specs():
    """Tao danh sach man.

    Man 1-2 de day nguoi choi nhip combat.
    Man 3 dua maze vao de thay doi khong gian choi.
    Man 4 chot campaign bang boss fight.
    """

    return [
        LevelSpec(
            number=1,
            title="Tiến vào lâu đài",
            description=f"{config.PLAYER_NAME} xâm nhập Shadow Kingdom để tìm {config.HOSTAGE_NAME}.",
            use_maze=False,
            has_boss=False,
            hostage_required=True,
            time_limit=config.LEVEL_TIME_LIMIT_SECONDS,
            enemy_weights={"grunt": 85, "runner": 15},
            spawn_range=(70, 110),
            max_enemies=5,
        ),
        LevelSpec(
            number=2,
            title="Cuộc săn đuổi",
            description=f"Quân của {config.BOSS_NAME} truy đuổi {config.PLAYER_NAME} khắp lâu đài.",
            use_maze=False,
            has_boss=False,
            hostage_required=True,
            time_limit=config.LEVEL_TIME_LIMIT_SECONDS,
            enemy_weights={"grunt": 50, "runner": 20, "shooter": 30},
            spawn_range=(58, 92),
            max_enemies=7,
        ),
        LevelSpec(
            number=3,
            title="Mê cung bóng tối",
            description=f"{config.PLAYER_NAME} lần theo dấu vết của {config.HOSTAGE_NAME} trong mê cung DFS.",
            use_maze=True,
            has_boss=False,
            hostage_required=True,
            time_limit=config.LEVEL_TIME_LIMIT_SECONDS,
            enemy_weights={"grunt": 50, "runner": 30, "shooter": 20},
            spawn_range=(65, 95),
            max_enemies=8,
        ),
        LevelSpec(
            number=4,
            title="Trận chiến cuối",
            description=f"Đối đầu {config.BOSS_NAME}, cứu {config.HOSTAGE_NAME} và kết thúc bóng tối.",
            use_maze=False,
            has_boss=True,
            hostage_required=True,
            time_limit=config.LEVEL_TIME_LIMIT_SECONDS,
            enemy_weights={"grunt": 35, "runner": 30, "shooter": 35},
            spawn_range=(72, 108),
            max_enemies=9,
        ),
    ]


class Maze:
    """Maze được pre-render sẵn để giảm chi phí vẽ mỗi frame."""

    def __init__(self, world_rect):
        self.tile_size = config.TILE_SIZE
        self.width = config.MAZE_WIDTH
        self.height = config.MAZE_HEIGHT
        self.grid = [[1] * self.width for _ in range(self.height)]
        self.origin = pygame.Vector2(
            world_rect.left + (world_rect.width - self.width * self.tile_size) // 2,
            world_rect.top + (world_rect.height - self.height * self.tile_size) // 2,
        )

        self.generate_dfs(1, 1)
        self.player_start = (1, 1)
        self.hostage_cell = self.find_farthest_cell(self.player_start)
        self.pathfinder = AStarPathfinder(self.grid)
        self.wall_surface = self.build_wall_surface()
        self.minimap_surface = self.build_minimap_surface()

    def generate_dfs(self, start_x, start_y):
        """Sinh me cung bang DFS de tao hanh lang co tinh chat me cung kinh dien."""

        stack = [(start_x, start_y)]
        self.grid[start_y][start_x] = 0
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]

        while stack:
            x, y = stack[-1]
            candidates = []
            for dx, dy in directions:
                nx, ny = x + dx * 2, y + dy * 2
                if 0 < nx < self.width - 1 and 0 < ny < self.height - 1 and self.grid[ny][nx] == 1:
                    candidates.append((nx, ny))

            if not candidates:
                stack.pop()
                continue

            nx, ny = random.choice(candidates)
            wx, wy = (x + nx) // 2, (y + ny) // 2
            self.grid[wy][wx] = 0
            self.grid[ny][nx] = 0
            stack.append((nx, ny))

    def build_wall_surface(self):
        """Pre-render toan bo tuong maze de khong phai ve lai tung o moi frame."""

        size = (self.width * self.tile_size, self.height * self.tile_size)
        surface = pygame.Surface(size, pygame.SRCALPHA)
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == 1:
                    rect = pygame.Rect(x * self.tile_size, y * self.tile_size, self.tile_size, self.tile_size)
                    pygame.draw.rect(surface, config.COLOR_MAZE_WALL, rect, border_radius=4)
                    inner = rect.inflate(-6, -6)
                    pygame.draw.rect(surface, config.COLOR_MAZE_WALL_ALT, inner, border_radius=3)
        return surface

    def build_minimap_surface(self):
        """Pre-render minimap de Scene chi can scale lai theo khung nho."""

        surface = pygame.Surface((self.width * 3, self.height * 3), pygame.SRCALPHA)
        for y in range(self.height):
            for x in range(self.width):
                color = (50, 70, 110, 200) if self.grid[y][x] == 1 else (18, 34, 56, 180)
                pygame.draw.rect(surface, color, (x * 3, y * 3, 3, 3))
        return surface

    def draw(self, surface):
        surface.blit(self.wall_surface, self.origin)

    def world_to_cell(self, pos):
        local_x = int((pos[0] - self.origin.x) // self.tile_size)
        local_y = int((pos[1] - self.origin.y) // self.tile_size)
        return local_x, local_y

    def cell_to_world(self, cell):
        return (
            self.origin.x + cell[0] * self.tile_size + self.tile_size / 2,
            self.origin.y + cell[1] * self.tile_size + self.tile_size / 2,
        )

    def is_walkable_cell(self, cell):
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height and self.grid[y][x] == 0

    def is_point_walkable(self, pos):
        return self.is_walkable_cell(self.world_to_cell(pos))

    def is_rect_walkable(self, rect):
        """Kiem tra 4 goc hitbox de giu movement don gian ma van dung duoc."""

        corners = [
            (rect.left, rect.top),
            (rect.right - 1, rect.top),
            (rect.left, rect.bottom - 1),
            (rect.right - 1, rect.bottom - 1),
        ]
        return all(self.is_point_walkable(point) for point in corners)

    def find_farthest_cell(self, start_cell):
        """Tim o xa nhat de dat hostage, tao muc tieu co y nghia trong maze."""

        queue = deque([start_cell])
        visited = {start_cell}
        farthest = start_cell

        while queue:
            current = queue.popleft()
            farthest = current
            x, y = current
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nxt = (x + dx, y + dy)
                if nxt not in visited and self.is_walkable_cell(nxt):
                    visited.add(nxt)
                    queue.append(nxt)

        return farthest

    def random_far_cell(self, origin, min_distance):
        """Chon o spawn xa player de tranh spawn sat mat qua bat cong."""

        cells = []
        origin = pygame.Vector2(origin)
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == 0:
                    world_pos = pygame.Vector2(self.cell_to_world((x, y)))
                    if world_pos.distance_to(origin) >= min_distance:
                        cells.append((x, y))
        return random.choice(cells) if cells else self.player_start


class LevelScene:
    """Quản lý toàn bộ logic của một mission; Game chỉ cần điều khiển state."""

    def __init__(self, assets, level_spec):
        self.assets = assets
        self.level_spec = level_spec
        self.frame_count = 0
        self.world_rect = pygame.Rect(
            config.WORLD_LEFT,
            config.WORLD_TOP,
            config.WORLD_WIDTH,
            config.WORLD_HEIGHT,
        )

        self.score = 0
        self.result = None
        self.result_reason = ""
        self.screen_shake = 0
        self.hit_effects = []
        self.path_cache = {}
        self.cached_goal = None
        self.effect_animations = build_effect_animations(assets)

        self.maze = Maze(self.world_rect) if level_spec.use_maze else None
        player_stats = config.player_stats_for_level(level_spec.number)

        if self.maze:
            player_pos = self.maze.cell_to_world(self.maze.player_start)
            hostage_pos = self.maze.cell_to_world(self.maze.hostage_cell)
        else:
            player_pos = (self.world_rect.left + 90, self.world_rect.centery)
            hostage_pos = (self.world_rect.right - 110, self.world_rect.centery + 80)

        self.player = Player(player_pos, assets, player_stats)
        self.hostage = Hostage(hostage_pos, assets)
        self.enemies = pygame.sprite.Group()
        self.player_bullets = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.effects = pygame.sprite.Group()
        self.boss = Boss((self.world_rect.centerx, self.world_rect.top + 120), assets) if level_spec.has_boss else None
        self.spawn_timer = random.randint(*level_spec.spawn_range)
        self.time_left = level_spec.time_limit * config.FPS
        self.objective_flash = 0

    def update(self, delta_time):
        """Một frame gameplay.

        Trật tự ở đây quan trọng:
        1. Update entity
        2. Spawn
        3. Collision
        4. Check objective

        Giữ thứ tự ổn định sẽ giúp game dễ debug hơn khi mở rộng.
        """

        if self.result:
            return

        self.frame_count += 1
        self.time_left -= 1
        self.objective_flash = (self.objective_flash + 1) % 120
        self.screen_shake = max(0, self.screen_shake - 1)
        self.update_effects()

        self.player.update(self, delta_time)
        self.hostage.update(self, delta_time)
        self.player_bullets.update(self)
        self.enemy_bullets.update(self)
        self.effects.update(delta_time)

        for enemy in list(self.enemies):
            enemy.update(self)
        if self.boss:
            self.boss.update(self, delta_time)

        self.handle_spawning()
        self.handle_collisions()
        self.check_objectives()

        if self.time_left <= 0:
            self.fail_level("Hết thời gian.")
        elif self.player.health <= 0:
            self.fail_level("Bạn đã bị hạ gục.")

    def update_effects(self):
        """Hiệu ứng trúng đạn được giữ ngắn và rẻ để vẽ."""

        updated = []
        for effect in self.hit_effects:
            effect["life"] -= 1
            effect["radius"] += 1.25
            if effect["life"] > 0:
                updated.append(effect)
        self.hit_effects = updated

    def handle_spawning(self):
        """Giữ áp lực giao tranh bằng timer spawn và giới hạn số enemy sống."""

        self.spawn_timer -= 1
        if self.spawn_timer > 0:
            return

        if len(self.enemies) < self.level_spec.max_enemies:
            self.spawn_enemy()
        self.spawn_timer = random.randint(*self.level_spec.spawn_range)

    def spawn_enemy(self, forced_type=None):
        """Sinh enemy theo trọng số hoặc theo yêu cầu cưỡng bức từ boss."""

        enemy_key = forced_type or random.choices(
            population=list(self.level_spec.enemy_weights.keys()),
            weights=list(self.level_spec.enemy_weights.values()),
            k=1,
        )[0]
        enemy_type = ENEMY_TYPES[enemy_key]

        if self.maze:
            spawn_cell = self.maze.random_far_cell(self.player.pos, min_distance=190)
            spawn_pos = self.maze.cell_to_world(spawn_cell)
        else:
            edge = random.choice(["left", "right", "top", "bottom"])
            if edge == "left":
                spawn_pos = (self.world_rect.left + 10, random.randint(self.world_rect.top + 30, self.world_rect.bottom - 30))
            elif edge == "right":
                spawn_pos = (self.world_rect.right - 10, random.randint(self.world_rect.top + 30, self.world_rect.bottom - 30))
            elif edge == "top":
                spawn_pos = (random.randint(self.world_rect.left + 30, self.world_rect.right - 30), self.world_rect.top + 10)
            else:
                spawn_pos = (random.randint(self.world_rect.left + 30, self.world_rect.right - 30), self.world_rect.bottom - 10)

        self.enemies.add(Enemy(spawn_pos, self.assets, enemy_type, self.level_spec.number))

    def handle_collisions(self):
        """Tách collision theo nhóm để sau này dễ mở rộng hệ thống damage."""

        player_hitbox = self.player.collision_rect()
        hostage_hitbox = self.hostage.collision_rect()
        boss_hitbox = self.boss.collision_rect() if self.boss and self.boss.health > 0 else None

        for bullet in list(self.player_bullets):
            enemy = next(
                (candidate for candidate in self.enemies if candidate.collision_rect().colliderect(bullet.rect)),
                None,
            )
            if enemy:
                bullet.kill()
                self.add_effect("hit", bullet.pos)
                if enemy.take_damage(bullet.damage):
                    self.score += enemy.score_value
                    self.add_effect("explosion", enemy.pos)
                    enemy.kill()
                continue

            if boss_hitbox and boss_hitbox.colliderect(bullet.rect):
                bullet.kill()
                self.add_effect("hit", bullet.pos)
                if self.boss.take_damage(bullet.damage):
                    self.add_effect("explosion", self.boss.pos)
                    boss_hitbox = None

        for bullet in list(self.enemy_bullets):
            if player_hitbox.colliderect(bullet.rect):
                bullet.kill()
                if self.player.take_damage(bullet.damage):
                    self.add_effect("hit", self.player.pos)
                    self.screen_shake = 7

        for enemy in list(self.enemies):
            if player_hitbox.colliderect(enemy.collision_rect()):
                if self.player.take_damage(enemy.contact_damage):
                    self.add_effect("hit", self.player.pos)
                    self.screen_shake = 10
                enemy.kill()

        if boss_hitbox and player_hitbox.colliderect(boss_hitbox):
            if self.player.take_damage(22):
                self.add_effect("hit", self.player.pos)
                self.screen_shake = 12

        if self.level_spec.hostage_required and not self.hostage.rescued and player_hitbox.colliderect(hostage_hitbox):
            self.hostage.rescued = True
            self.score += 200
            self.add_effect("explosion", self.hostage.pos)

    def check_objectives(self):
        """Dieu kien thang duoc gom vao 1 cho de de doc va de doi luat choi."""

        boss_dead = not self.boss or self.boss.health <= 0
        hostage_ready = self.hostage.rescued if self.level_spec.hostage_required else True

        if self.level_spec.has_boss:
            if boss_dead and hostage_ready:
                self.result = "win"
                self.result_reason = f"{config.BOSS_NAME} đã bị tiêu diệt và {config.HOSTAGE_NAME} đã an toàn."
        elif hostage_ready:
            self.result = "win"
            self.result_reason = f"{config.HOSTAGE_NAME} đã được {config.PLAYER_NAME} giải cứu."

    def fail_level(self, reason):
        self.result = "lose"
        self.result_reason = reason

    def get_path(self, start_cell, goal_cell):
        """Cache theo ô đích để nhiều enemy dùng lại kết quả A* trong cùng nhịp."""

        if not self.maze:
            return []

        if self.cached_goal != goal_cell:
            self.path_cache.clear()
            self.cached_goal = goal_cell

        key = (start_cell, goal_cell)
        if key not in self.path_cache:
            self.path_cache[key] = self.maze.pathfinder.find_path(start_cell, goal_cell)
        return list(self.path_cache[key])

    def has_clear_line(self, start, end):
        """Shooter và boss dùng ray đơn giản để biết có bắn xuyên tường hay không."""

        if not self.maze:
            return True

        start = pygame.Vector2(start)
        end = pygame.Vector2(end)
        delta = end - start
        steps = max(1, int(delta.length() // 8))
        for index in range(1, steps + 1):
            point = start.lerp(end, index / steps)
            if not self.maze.is_point_walkable(point):
                return False
        return True

    def spawn_bullet(self, origin, direction, speed, damage, friendly, color):
        """Ham chung de boss va cac he thong khac co the tao dan dung nhom."""

        bullet = Bullet(origin, direction, speed, damage, friendly, color, lifetime=130)
        if friendly:
            self.player_bullets.add(bullet)
        else:
            self.enemy_bullets.add(bullet)
        self.add_effect("bullet", origin, angle=-pygame.Vector2(direction).angle_to(pygame.Vector2(1, 0)))

    def add_burst(self, position, color, radius):
        """Luu hieu ung hit feedback o dang du lieu nhe thay vi sprite rieng."""

        self.hit_effects.append(
            {
                "pos": pygame.Vector2(position),
                "color": color,
                "radius": radius,
                "life": 10,
            }
        )

    def add_effect(self, name, position, angle=0.0):
        """Thêm effect animation, tự fallback nếu sheet chưa đúng layout."""

        if name not in self.effect_animations:
            return
        effect = Effect(position, self.effect_animations, name, angle=angle)
        self.effects.add(effect)

    def draw(self, surface):
        """Vẽ scene.

        Scene được vẽ lên world layer trước, sau đó mới đổ lên screen.
        Cách này giúp screen shake đơn giản: chỉ cần xê dịch cả layer.
        """

        offset = pygame.Vector2(0, 0)
        if self.screen_shake:
            offset.x = random.randint(-self.screen_shake, self.screen_shake)
            offset.y = random.randint(-self.screen_shake, self.screen_shake)

        surface.blit(self.assets.world_background, (0, 0))
        if self.assets.images["world_bg"]:
            surface.blit(self.assets.images["world_bg"], (0, 0))
        surface.blit(self.assets.grid_overlay, (0, 0))

        world_layer = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(world_layer, (7, 12, 26), self.world_rect, border_radius=18)
        pygame.draw.rect(world_layer, config.COLOR_BORDER, self.world_rect, width=2, border_radius=18)

        if self.maze:
            self.maze.draw(world_layer)

        self.draw_objective_line(world_layer)
        world_layer.blit(self.hostage.image, self.hostage.rect)
        self.draw_entity_label(
            world_layer,
            self.hostage.rect,
            config.HOSTAGE_NAME,
            config.COLOR_WARNING if not self.hostage.rescued else config.COLOR_ACCENT,
        )
        for bullet in self.player_bullets:
            world_layer.blit(bullet.image, bullet.rect)
        for bullet in self.enemy_bullets:
            world_layer.blit(bullet.image, bullet.rect)
        for effect in self.effects:
            world_layer.blit(effect.image, effect.rect)
        for enemy in self.enemies:
            world_layer.blit(enemy.image, enemy.rect)
        if self.boss:
            world_layer.blit(self.boss.image, self.boss.rect)
            if self.boss.health > 0:
                self.draw_entity_label(world_layer, self.boss.rect, config.BOSS_NAME, (194, 63, 255))
        world_layer.blit(self.player.image, self.player.rect)
        self.draw_entity_label(world_layer, self.player.rect, config.PLAYER_NAME, (88, 197, 255))
        self.draw_effects(world_layer)
        self.draw_muzzle_flash(world_layer)

        surface.blit(world_layer, (int(offset.x), int(offset.y)))

    def draw_entity_label(self, surface, rect, name, color):
        """Vẽ tên nhân vật ngay trên sprite để người chơi nhận ra nhanh."""

        label = self.assets.font_small.render(name, True, config.COLOR_TEXT)
        padding_x = 10
        panel = pygame.Rect(
            rect.centerx - (label.get_width() + padding_x * 2) // 2,
            rect.y - 24,
            label.get_width() + padding_x * 2,
            18,
        )
        pygame.draw.rect(surface, (5, 10, 20, 190), panel, border_radius=9)
        pygame.draw.rect(surface, color, panel, width=1, border_radius=9)
        surface.blit(label, (panel.x + padding_x, panel.y + 1))

    def draw_effects(self, surface):
        for effect in self.hit_effects:
            alpha = int(255 * (effect["life"] / 10))
            color = (*effect["color"], alpha)
            pygame.draw.circle(surface, color, effect["pos"], int(effect["radius"]), width=2)

    def draw_muzzle_flash(self, surface):
        """Muzzle flash nhỏ để súng có cảm giác bắn mà không làm UI ồn ào."""

        if self.player.muzzle_timer <= 0:
            return
        center = self.player.pos + self.player.aim_direction * 24
        radius = 8 + self.player.muzzle_timer * 3
        pygame.draw.circle(surface, (255, 245, 194, 180), center, radius)

    def draw_objective_line(self, surface):
        """Đường nối mờ giúp người chơi mới biết hướng con tin mà không cần text dài."""

        if self.hostage.rescued:
            return
        if self.objective_flash < 60:
            pygame.draw.line(surface, (255, 221, 122, 70), self.player.pos, self.hostage.pos, width=1)

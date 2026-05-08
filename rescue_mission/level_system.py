"""Level data and mission runtime."""

import math
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import pygame

from . import config
from .entities import Bullet, ENEMY_TYPES, Enemy, FloatingText, HealthPack, ExitGate
from .pathfinding import AStarPathfinder
from .projectiles import EnergyProjectile
from .sprites.boss import Boss
from .sprites.effects import Effect, build_effect_animations
from .sprites.hostage import Hostage
from .sprites.player import Player
from .sprites.rabbit import LoveRabbitCompanion


@dataclass(frozen=True)
class LevelSpec:
    number: int
    title: str
    description: str
    use_maze: bool
    time_limit: int
    enemy_weights: Dict[str, int]
    spawn_range: Tuple[int, int]
    max_enemies: int
    objective_mode: str = "rescue"
    hostage_required: bool = True
    kill_target: int = 0
    guidance_enabled: bool = False
    boss_profile_key: Optional[str] = None
    hazard_layout: Tuple[str, ...] = ()

    @property
    def has_boss(self):
        return self.boss_profile_key is not None


@dataclass
class HazardZone:
    center: pygame.Vector2
    radius: float
    damage: int
    interval: float
    label: str = ""
    pulse: float = 0.0
    cooldown_left: float = field(default_factory=lambda: 0.0)


def build_level_specs():
    return [
        LevelSpec(
            number=1,
            title="Tiến vào lâu đài",
            description=f"{config.PLAYER_NAME} đột nhập vào Shadow Kingdom để tìm {config.HOSTAGE_NAME}.",
            use_maze=False,
            time_limit=config.LEVEL_TIME_LIMIT_SECONDS,
            enemy_weights={"grunt": 82, "runner": 18},
            spawn_range=(70, 108),
            max_enemies=5,
            objective_mode="rescue",
        ),
        LevelSpec(
            number=2,
            title="Cuộc săn đuổi",
            description=f"Đội truy kích của {config.BOSS_NAME} ép {config.PLAYER_NAME} phải vừa chạy vừa giao tranh.",
            use_maze=False,
            time_limit=config.LEVEL_TIME_LIMIT_SECONDS,
            enemy_weights={"grunt": 45, "runner": 22, "shooter": 33},
            spawn_range=(58, 90),
            max_enemies=7,
            objective_mode="rescue",
        ),
        LevelSpec(
            number=3,
            title="Mê cung bóng tối",
            description=f"Lần theo dấu dẫn chính để tìm đúng nhánh có {config.HOSTAGE_NAME}.",
            use_maze=True,
            time_limit=config.LEVEL_TIME_LIMIT_SECONDS,
            enemy_weights={"grunt": 48, "runner": 30, "shooter": 22},
            spawn_range=(64, 92),
            max_enemies=8,
            objective_mode="rescue",
            guidance_enabled=True,
        ),
        LevelSpec(
            number=4,
            title="Áp lực giao tranh",
            description="Dọn sạch tuyến canh gác, tránh bẫy nền và chỉ cứu Lina khi khu vực đã hở lối.",
            use_maze=False,
            time_limit=195,
            enemy_weights={"grunt": 34, "runner": 26, "shooter": 24, "brute": 16},
            spawn_range=(36, 62),
            max_enemies=9,
            objective_mode="purge_then_rescue",
            kill_target=14,
            hazard_layout=("mid_left", "mid_right", "center"),
        ),
        LevelSpec(
            number=5,
            title="Thử thách hỗn hợp",
            description="Vượt qua vùng phản ứng năng lượng, hạ AEGIS PRIME rồi mở đường tới Lina.",
            use_maze=False,
            time_limit=210,
            enemy_weights={"runner": 22, "shooter": 36, "brute": 24, "grunt": 18},
            spawn_range=(38, 66),
            max_enemies=9,
            objective_mode="boss_and_rescue",
            boss_profile_key="aegis_prime",
            hazard_layout=("north_left", "north_right", "center"),
        ),
        LevelSpec(
            number=6,
            title="Đấu trường cuối",
            description=f"Đấu trường cuối cùng. Hạ {config.BOSS_NAME} và đưa {config.HOSTAGE_NAME} rời khỏi ngai bóng tối.",
            use_maze=False,
            time_limit=225,
            enemy_weights={"runner": 28, "shooter": 34, "brute": 38},
            spawn_range=(34, 58),
            max_enemies=10,
            objective_mode="boss_and_rescue",
            boss_profile_key="orion_prime",
            hazard_layout=("arena_left", "arena_right", "center"),
        ),
    ]


class Maze:
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
        corners = [
            (rect.left, rect.top),
            (rect.right - 1, rect.top),
            (rect.left, rect.bottom - 1),
            (rect.right - 1, rect.bottom - 1),
        ]
        return all(self.is_point_walkable(point) for point in corners)

    def find_farthest_cell(self, start_cell):
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
        cells = []
        origin = pygame.Vector2(origin)
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == 0:
                    world_pos = pygame.Vector2(self.cell_to_world((x, y)))
                    if world_pos.distance_to(origin) >= min_distance:
                        cells.append((x, y))
        return random.choice(cells) if cells else self.player_start

    def find_nearest_walkable_cell(self, origin_cell, max_radius=8):
        if self.is_walkable_cell(origin_cell):
            return origin_cell

        ox, oy = origin_cell
        best_cell = None
        best_distance = None
        for radius in range(1, max_radius + 1):
            for y in range(max(0, oy - radius), min(self.height, oy + radius + 1)):
                for x in range(max(0, ox - radius), min(self.width, ox + radius + 1)):
                    cell = (x, y)
                    if not self.is_walkable_cell(cell):
                        continue
                    distance = abs(x - ox) + abs(y - oy)
                    if best_distance is None or distance < best_distance:
                        best_cell = cell
                        best_distance = distance
            if best_cell is not None:
                return best_cell
        return None


class LevelScene:
    def __init__(self, assets, level_spec, player_stats_override=None):
        self.assets = assets
        self.level_spec = level_spec
        self.frame_count = 0
        self.world_rect = pygame.Rect(config.WORLD_LEFT, config.WORLD_TOP, config.WORLD_WIDTH, config.WORLD_HEIGHT)

        self.score = 0
        self.result = None
        self.result_reason = ""
        self.screen_shake = 0.0
        self.hit_effects = []
        self.path_cache = {}
        self.cached_goal = None
        self.effect_animations = build_effect_animations(assets)
        self.player_invincible = False
        self.audio = None
        self.tutorial_timer = 10.0
        self.banner_timer = 2.6
        self.status_message = ""
        self.status_timer = 0.0
        self.defeated_enemies = 0
        self.objective_flash = 0.0
        self.dash_afterimages = []   # [{"image", "pos", "alpha"}]

        # --- Combo Kill Streak ---
        self.combo_count = 0
        self.combo_timer = 0.0
        self.combo_max_gap = 2.5   # giây tối đa giữa 2 kill
        self.floating_texts = []   # [FloatingText]

        # --- Health Packs ---
        self.health_packs = pygame.sprite.Group()

        self.maze = Maze(self.world_rect) if level_spec.use_maze else None
        player_pos, hostage_pos, boss_pos = self.resolve_anchor_positions()
        player_stats = player_stats_override if player_stats_override else config.player_stats_for_level(level_spec.number)

        self.player = Player(player_pos, assets, player_stats)
        self.hostage = Hostage(hostage_pos, assets)
        self.enemies = pygame.sprite.Group()
        self.player_bullets = pygame.sprite.Group()
        self.skill_projectiles = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.effects = pygame.sprite.Group()
        self.boss = None
        self.love_rabbit = None
        if level_spec.has_boss:
            profile = config.BOSS_PROFILES[level_spec.boss_profile_key]
            self.boss = Boss(boss_pos, assets, profile)
        self.spawn_timer = random.randint(*level_spec.spawn_range) / config.FPS
        self.time_left = float(level_spec.time_limit)
        
        # Tạo cửa thoát hiểm
        exit_gate_pos = self.resolve_exit_position(player_pos, hostage_pos)
        self.exit_gate = ExitGate(exit_gate_pos, assets)
        
        self.hazards = self.build_hazards()

    def resolve_anchor_positions(self):
        if self.maze:
            player_pos = self.maze.cell_to_world(self.maze.player_start)
            hostage_pos = self.maze.cell_to_world(self.maze.hostage_cell)
            boss_pos = (self.world_rect.centerx, self.world_rect.top + 140)
            return player_pos, hostage_pos, boss_pos

        anchors = {
            1: ((self.world_rect.left + 90, self.world_rect.centery), (self.world_rect.right - 110, self.world_rect.centery + 80), (self.world_rect.centerx, self.world_rect.top + 120)),
            2: ((self.world_rect.left + 110, self.world_rect.centery + 120), (self.world_rect.right - 100, self.world_rect.top + 120), (self.world_rect.centerx, self.world_rect.top + 120)),
            4: ((self.world_rect.left + 120, self.world_rect.bottom - 110), (self.world_rect.right - 120, self.world_rect.top + 120), (self.world_rect.centerx, self.world_rect.top + 120)),
            5: ((self.world_rect.left + 120, self.world_rect.bottom - 110), (self.world_rect.right - 120, self.world_rect.bottom - 110), (self.world_rect.centerx, self.world_rect.centery - 30)),
            6: ((self.world_rect.left + 140, self.world_rect.bottom - 130), (self.world_rect.centerx, self.world_rect.top + 130), (self.world_rect.centerx, self.world_rect.centery - 40)),
        }
        default = ((self.world_rect.left + 90, self.world_rect.centery), (self.world_rect.right - 110, self.world_rect.centery + 80), (self.world_rect.centerx, self.world_rect.top + 120))
        return anchors.get(self.level_spec.number, default)

    def resolve_exit_position(self, player_pos, hostage_pos):
        """Xác định vị trí cửa thoát hiểm khác nhau cho mỗi màn."""
        if self.maze:
            if self.level_spec.number == 3:
                # Riêng màn 3, đặt cửa cạnh Luna theo yêu cầu
                h_cell = self.maze.world_to_cell(hostage_pos)
                # Tìm ô trống cạnh Lina
                exit_cell = self.maze.find_nearest_walkable_cell((h_cell[0] + 1, h_cell[1]), max_radius=3)
                return self.maze.cell_to_world(exit_cell or h_cell)
            else:
                # Các màn maze khác (nếu có), cửa nằm tại điểm bắt đầu
                return player_pos
        
        # Các màn thường, cửa nằm ở các góc nhưng TRÁNH vùng phía trên (nơi có thanh UI)
        # Ta ưu tiên các góc ở nửa dưới màn hình
        corners = [
            (self.world_rect.left + 80, self.world_rect.bottom - 100),
            (self.world_rect.right - 80, self.world_rect.bottom - 100),
            (self.world_rect.left + 80, self.world_rect.centery + 40),
            (self.world_rect.right - 80, self.world_rect.centery + 40),
        ]
        # Tìm góc xa Lina nhất trong số các góc an toàn
        h_pos = pygame.Vector2(hostage_pos)
        return max(corners, key=lambda p: h_pos.distance_to(p))

    def build_hazards(self):
        if self.maze:
            return []

        placements = {
            "mid_left": (0.34, 0.48, 52, 5, "Bẫy"),
            "mid_right": (0.66, 0.48, 52, 5, "Bẫy"),
            "center": (0.5, 0.56, 60, 10, "Lõi nóng"),
            "north_left": (0.32, 0.34, 50, 5, "Bẫy"),
            "north_right": (0.68, 0.34, 50, 5, "Bẫy"),
            "arena_left": (0.32, 0.42, 56, 5, "Bẫy"),
            "arena_right": (0.68, 0.42, 56, 5, "Bẫy"),
        }
        hazards = []
        for token in self.level_spec.hazard_layout:
            rx, ry, radius, damage, label = placements[token]
            hazards.append(
                HazardZone(
                    center=pygame.Vector2(
                        self.world_rect.left + self.world_rect.width * rx,
                        self.world_rect.top + self.world_rect.height * ry,
                    ),
                    radius=radius,
                    damage=damage,
                    interval=0.85,
                    label=label,
                    cooldown_left=random.random() * 0.35,
                )
            )
        return hazards

    def update(self, delta_time):
        if self.result:
            return

        self.frame_count += 1
        frame_scale = delta_time * config.FPS
        self.time_left -= delta_time
        self.tutorial_timer = max(0.0, self.tutorial_timer - delta_time)
        self.banner_timer = max(0.0, self.banner_timer - delta_time)
        self.status_timer = max(0.0, self.status_timer - delta_time)
        if self.status_timer <= 0:
            self.status_message = ""
        self.objective_flash = (self.objective_flash + frame_scale) % 120
        self.screen_shake = max(0.0, self.screen_shake - frame_scale)
        self.update_effects(delta_time)

        self.player.update(self, delta_time)
        self.update_hazards(delta_time)
        self.hostage.update(self, delta_time)
        if self.love_rabbit:
            self.love_rabbit.update(self, delta_time)
        self.exit_gate.update(self, delta_time)
        self.player_bullets.update(self, delta_time)
        self.skill_projectiles.update(self, delta_time)
        self.enemy_bullets.update(self, delta_time)
        self.effects.update(delta_time)

        for enemy in list(self.enemies):
            enemy.update(self, delta_time)
        if self.boss:
            self.boss.update(self, delta_time)

        self.handle_spawning(delta_time)
        self.handle_collisions()
        self.check_objectives()

        if self.time_left <= 0:
            self.fail_level("Hết thời gian.")
        elif self.player.health <= 0:
            self.fail_level("Bạn đã bị hạ gục.")

    def update_effects(self, delta_time):
        frame_scale = delta_time * config.FPS
        updated = []
        for effect in self.hit_effects:
            effect["life"] -= frame_scale
            effect["radius"] += 1.25 * frame_scale
            if effect["life"] > 0:
                updated.append(effect)
        self.hit_effects = updated

        # Fade afterimage trail
        updated_ai = []
        for af in self.dash_afterimages:
            af["alpha"] -= 280 * delta_time
            if af["alpha"] > 0:
                updated_ai.append(af)
        self.dash_afterimages = updated_ai

        # Combo timer — reset nếu quá lâu không kill
        if self.combo_count > 0:
            self.combo_timer -= delta_time
            if self.combo_timer <= 0:
                self.combo_count = 0

        # Floating texts
        self.floating_texts = [ft for ft in self.floating_texts if ft.alive]
        for ft in self.floating_texts:
            ft.update(delta_time)

        # Health packs
        for pack in list(self.health_packs):
            pack.update(delta_time)
            if pack.try_pickup(self.player):
                self.add_burst(pack.pos, (255, 120, 140), 10)
                self.push_status_message(f"Hồi {pack.heal_amount} máu!", 0.8)
                if self.audio:
                    self.audio.play("rescue", volume=0.5)

    def update_hazards(self, delta_time):
        for hazard in self.hazards:
            hazard.pulse = (hazard.pulse + delta_time * 2.5) % 1000
            hazard.cooldown_left = max(0.0, hazard.cooldown_left - delta_time)
            if pygame.Vector2(self.player.pos).distance_to(hazard.center) <= hazard.radius and hazard.cooldown_left <= 0.0:
                damaged = self.player.take_damage(hazard.damage, scene=self)
                if damaged:
                    if hazard.label == "Lõi nóng":
                        # Hiệu ứng đốm lửa cam đỏ
                        self.add_burst(self.player.pos, (255, 120, 0), 22)
                        self.add_burst(self.player.pos, (255, 55, 0), 14)
                        self.add_burst(self.player.pos + pygame.Vector2(0, -10), (255, 200, 50), 8)
                        self.add_effect("explosion", self.player.pos)
                        # Hiển thị số trừ máu màu cam đỏ trên đầu player
                        self.floating_texts.append(FloatingText(
                            pos=self.player.pos + pygame.Vector2(0, -40),
                            text=f"-{hazard.damage}",
                            color=(255, 90, 0),
                            font=self.assets.font_small,
                            duration=1.2,
                            rise_speed=42,
                        ))
                    else:
                        self.add_burst(self.player.pos, config.COLOR_DANGER, 14)
                        self.add_effect("hit", self.player.pos)
                        # Hiển thị số trừ máu màu đỏ trên đầu player
                        self.floating_texts.append(FloatingText(
                            pos=self.player.pos + pygame.Vector2(0, -40),
                            text=f"-{hazard.damage}",
                            color=(255, 60, 60),
                            font=self.assets.font_small,
                            duration=1.0,
                            rise_speed=40,
                        ))
                    self.screen_shake = max(self.screen_shake, 8)
                    if self.audio:
                        self.audio.play("hurt", volume=0.75)
                hazard.cooldown_left = hazard.interval



    def handle_spawning(self, delta_time):
        if self.level_spec.objective_mode == "purge_then_rescue" and self.defeated_enemies >= self.level_spec.kill_target:
            return

        self.spawn_timer -= delta_time
        if self.spawn_timer > 0:
            return

        if len(self.enemies) < self.level_spec.max_enemies:
            self.spawn_enemy()
        self.spawn_timer = random.randint(*self.level_spec.spawn_range) / config.FPS

    def spawn_enemy(self, forced_type=None):
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
            margin = 18
            if edge == "left":
                spawn_pos = (self.world_rect.left + margin, random.randint(self.world_rect.top + 30, self.world_rect.bottom - 30))
            elif edge == "right":
                spawn_pos = (self.world_rect.right - margin, random.randint(self.world_rect.top + 30, self.world_rect.bottom - 30))
            elif edge == "top":
                spawn_pos = (random.randint(self.world_rect.left + 30, self.world_rect.right - 30), self.world_rect.top + margin)
            else:
                spawn_pos = (random.randint(self.world_rect.left + 30, self.world_rect.right - 30), self.world_rect.bottom - margin)

        self.enemies.add(Enemy(spawn_pos, self.assets, enemy_type, self.level_spec.number))

    def handle_collisions(self):
        player_hitbox = self.player.collision_rect()
        hostage_hitbox = self.hostage.collision_rect()
        boss_hitbox = self.boss.collision_rect() if self.boss and self.boss.health > 0 else None

        for bullet in list(self.player_bullets):
            if self.resolve_friendly_projectile_hit(bullet, boss_hitbox):
                if self.boss and self.boss.health <= 0:
                    boss_hitbox = None

        for projectile in list(self.skill_projectiles):
            if self.resolve_friendly_projectile_hit(projectile, boss_hitbox, is_skill=True):
                if self.boss and self.boss.health <= 0:
                    boss_hitbox = None

        for bullet in list(self.enemy_bullets):
            if player_hitbox.colliderect(bullet.rect):
                bullet.kill()
                if self.player.take_damage(bullet.damage, scene=self):
                    self.add_effect("hit", self.player.pos)
                    if self.audio:
                        self.audio.play("hurt")
                    self.screen_shake = 7

        for enemy in list(self.enemies):
            if player_hitbox.colliderect(enemy.collision_rect()):
                if self.player.take_damage(enemy.contact_damage, scene=self):
                    self.add_effect("hit", self.player.pos)
                    if self.audio:
                        self.audio.play("hurt")
                    self.screen_shake = 10
                enemy.kill()

        if boss_hitbox and player_hitbox.colliderect(boss_hitbox):
            if self.player.take_damage(self.boss.profile.contact_damage, scene=self):
                self.add_effect("hit", self.player.pos)
                if self.audio:
                    self.audio.play("hurt")
                self.screen_shake = 12

        if self.level_spec.hostage_required and not self.hostage.rescued and player_hitbox.colliderect(hostage_hitbox):
            if self.can_rescue_hostage():
                self.hostage.rescued = True
                self.score += 200
                self.add_effect("rescue", self.hostage.pos)
                self.add_burst(self.hostage.pos, config.COLOR_WARNING, 14)
                if self.audio:
                    self.audio.play("rescue")
            else:
                if self.level_spec.objective_mode == "purge_then_rescue":
                    remaining = max(0, self.level_spec.kill_target - self.defeated_enemies)
                    self.push_status_message(f"Dọn sạch khu canh gác trước: còn {remaining} địch.", 1.2)
                elif self.level_spec.objective_mode == "boss_and_rescue" and self.boss and self.boss.health > 0:
                    self.push_status_message(f"Hạ {self.boss.display_name} trước khi giải cứu.", 1.2)

    def resolve_friendly_projectile_hit(self, projectile, boss_hitbox, is_skill=False):
        enemy = next((candidate for candidate in self.enemies if candidate.collision_rect().colliderect(projectile.rect)), None)
        if enemy:
            projectile.kill()
            self.add_effect("hit", projectile.pos)
            self.add_burst(projectile.pos, config.COLOR_SKILL if is_skill else config.COLOR_ACCENT, 10 if is_skill else 6)
            if self.audio:
                self.audio.play("hit", volume=0.85 if is_skill else 0.75)
            if is_skill and isinstance(projectile, EnergyProjectile):
                push = (enemy.pos - projectile.pos)
                if push.length_squared() > 0:
                    enemy.pos += push.normalize() * projectile.knockback
            if enemy.take_damage(projectile.damage):
                self.score += enemy.score_value
                self.defeated_enemies += 1
                self.add_effect("explosion", enemy.pos)
                if self.audio:
                    self.audio.play("enemy_down", volume=0.75)
                # --- Combo ---
                self.combo_count += 1
                self.combo_timer = self.combo_max_gap
                multiplier = self._combo_multiplier()
                bonus = int(enemy.score_value * (multiplier - 1))
                if bonus > 0:
                    self.score += bonus
                label = f"+{enemy.score_value + bonus}"
                if multiplier > 1:
                    label += f" x{multiplier:.1f}"
                self.floating_texts.append(FloatingText(
                    pos=enemy.pos + pygame.Vector2(0, -28),
                    text=label,
                    color=(255, 220, 80) if multiplier > 1 else (200, 240, 200),
                    font=self.assets.font_small,
                    duration=1.0,
                ))
                # --- Health Drop ---
                drop_chance = 0.40 if enemy.enemy_type.key == "brute" else 0.20
                heal_amt = 40 if enemy.enemy_type.key == "brute" else 25
                if random.random() < drop_chance:
                    pack = HealthPack(enemy.pos, heal_amt)
                    self.health_packs.add(pack)
                enemy.kill()
            return True

        if boss_hitbox and boss_hitbox.colliderect(projectile.rect):
            projectile.kill()
            self.add_effect("hit", projectile.pos)
            self.add_burst(projectile.pos, config.COLOR_SKILL if is_skill else config.COLOR_ACCENT, 12 if is_skill else 7)
            if self.audio:
                self.audio.play("hit", volume=0.88)
            if self.boss.take_damage(projectile.damage):
                self.add_effect("explosion", self.boss.pos)
                self.add_burst(self.boss.pos, config.COLOR_WARNING, 24)
                self.push_status_message(f"{self.boss.display_name} đã gục ngã.", 1.0)
                if self.audio:
                    self.audio.play("enemy_down")
            return True

        return False

    def _combo_multiplier(self):
        """Nhân điểm theo combo count: 1→x1, 3→x1.5, 5→x2, 8→x2.5, 12→x3."""
        if self.combo_count >= 12:
            return 3.0
        if self.combo_count >= 8:
            return 2.5
        if self.combo_count >= 5:
            return 2.0
        if self.combo_count >= 3:
            return 1.5
        return 1.0

    def can_rescue_hostage(self):
        if self.level_spec.objective_mode == "purge_then_rescue":
            return self.defeated_enemies >= self.level_spec.kill_target
        if self.level_spec.objective_mode == "boss_and_rescue":
            return not self.boss or self.boss.health <= 0
        return True

    def current_objective_text(self):
        if self.level_spec.objective_mode == "purge_then_rescue":
            remaining = max(0, self.level_spec.kill_target - self.defeated_enemies)
            if remaining > 0:
                return f"Hạ {self.level_spec.kill_target} địch ({remaining} còn lại)"
            if not self.hostage.rescued:
                return f"Tiếp cận {config.HOSTAGE_NAME}"
            return f"{config.HOSTAGE_NAME} đã được giải cứu"

        if self.level_spec.objective_mode == "boss_and_rescue" and self.boss and self.boss.health > 0:
            return f"Hạ {self.boss.display_name}"

        if not self.hostage.rescued:
            return f"Cứu {config.HOSTAGE_NAME}"
        return f"{config.HOSTAGE_NAME} an toàn"

    def check_objectives(self):
        # Kiểm tra điều kiện tiên quyết (Boss, số lượng địch, cứu Lina)
        ready_to_exit = False
        
        if self.level_spec.objective_mode == "boss_and_rescue":
            if (not self.boss or self.boss.health <= 0) and self.hostage.rescued:
                ready_to_exit = True
        elif self.level_spec.objective_mode == "purge_then_rescue":
            if self.defeated_enemies >= self.level_spec.kill_target and self.hostage.rescued:
                ready_to_exit = True
        else:
            if self.hostage.rescued:
                ready_to_exit = True

        # Nếu đã xong hết mục tiêu chính, yêu cầu đi tới cửa thoát hiểm
        if ready_to_exit:
            if self.player.collision_rect().colliderect(self.exit_gate.collision_rect()):
                self.result = "win"
                self.result_reason = f"Tuyệt vời! Aris đã bảo vệ Lina thành công qua cửa thoát hiểm."
            elif self.frame_count % 60 == 0:
                self.push_status_message("Dẫn Lina tới Cửa thoát hiểm!", 1.5)

    def fail_level(self, reason):
        self.result = "lose"
        self.result_reason = reason

    def get_path(self, start_cell, goal_cell, heuristic_type="manhattan", use_safety=False):
        if not self.maze:
            return []

        # Cache key includes heuristic and safety flag
        key = (start_cell, goal_cell, heuristic_type, use_safety)
        
        if self.cached_goal != goal_cell:
            self.path_cache.clear()
            self.cached_goal = goal_cell

        key = (start_cell, goal_cell)
        if key not in self.path_cache:
            enemy_cells = None
            if use_safety:
                enemy_cells = [self.maze.world_to_cell(e.pos) for e in self.enemies]
            
            self.path_cache[key] = self.maze.pathfinder.find_path(
                start_cell, 
                goal_cell, 
                heuristic_type=heuristic_type,
                enemy_positions=enemy_cells
            )
        return list(self.path_cache[key])

    def has_clear_line(self, start, end):
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
        bullet = Bullet(origin, direction, speed, damage, friendly, color, lifetime=130)
        if friendly:
            self.player_bullets.add(bullet)
        else:
            self.enemy_bullets.add(bullet)
        self.add_effect("bullet", origin, angle=-pygame.Vector2(direction).angle_to(pygame.Vector2(1, 0)))

    def add_burst(self, position, color, radius):
        self.hit_effects.append({"pos": pygame.Vector2(position), "color": color, "radius": radius, "life": 10})

    def add_effect(self, name, position, angle=0.0):
        if name not in self.effect_animations:
            return
        self.effects.add(Effect(position, self.effect_animations, name, angle=angle))

    def push_status_message(self, text, duration):
        self.status_message = text
        self.status_timer = duration

    def enable_love_rabbit(self):
        if self.love_rabbit is None:
            self.love_rabbit = LoveRabbitCompanion(self.player.pos + pygame.Vector2(52, -18), self.assets)

    def draw(self, surface):
        offset = pygame.Vector2(0, 0)
        if self.screen_shake:
            shake_amount = max(1, int(round(self.screen_shake)))
            offset.x = random.randint(-shake_amount, shake_amount)
            offset.y = random.randint(-shake_amount, shake_amount)

        # Draw a level-specific background if available, otherwise fall back
        bg = None
        try:
            bg = self.assets.level_background_for(self.level_spec)
        except Exception:
            bg = None

        if bg:
            surface.blit(bg, (0, 0))
        else:
            surface.blit(self.assets.world_background, (0, 0))
            if self.assets.images["world_bg"]:
                surface.blit(self.assets.images["world_bg"], (0, 0))

        surface.blit(self.assets.grid_overlay, (0, 0))

        world_layer = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        # Draw level background into the world layer so it appears inside the play area.
        try:
            bg = self.assets.level_background_for(self.level_spec)
        except Exception:
            bg = None

        if bg:
            world_layer.blit(bg, (0, 0))

        # Draw a semi-transparent dark panel over the play area to keep UI readable
        overlay_color = (7, 12, 26, 220)
        pygame.draw.rect(world_layer, overlay_color, self.world_rect, border_radius=18)
        pygame.draw.rect(world_layer, config.COLOR_BORDER, self.world_rect, width=2, border_radius=18)

        if self.maze:
            self.maze.draw(world_layer)

        self.draw_hazards(world_layer)
        # Vẽ cửa thoát hiểm
        world_layer.blit(self.exit_gate.image, self.exit_gate.rect)
        self.draw_entity_label(world_layer, self.exit_gate.rect, "Lối thoát", (100, 255, 150) if self.hostage.rescued else (150, 150, 150))
        
        self.draw_guidance(world_layer)
        self.draw_objective_line(world_layer)
        world_layer.blit(self.hostage.image, self.hostage.rect)
        self.draw_entity_label(world_layer, self.hostage.rect, config.HOSTAGE_NAME, config.COLOR_WARNING if not self.hostage.rescued else config.COLOR_ACCENT)
        # Ve afterimage trail truoc khi ve player
        self.draw_dash_afterimages(world_layer)
        for bullet in self.player_bullets:
            world_layer.blit(bullet.image, bullet.rect)
        for projectile in self.skill_projectiles:
            world_layer.blit(projectile.image, projectile.rect)
        for bullet in self.enemy_bullets:
            world_layer.blit(bullet.image, bullet.rect)
        for effect in self.effects:
            world_layer.blit(effect.image, effect.rect)
        for enemy in self.enemies:
            world_layer.blit(enemy.image, enemy.rect)
        if self.boss:
            world_layer.blit(self.boss.image, self.boss.rect)
            if self.boss.health > 0:
                self.draw_entity_label(world_layer, self.boss.rect, self.boss.display_name, self.boss.profile.secondary_color)
        if self.love_rabbit:
            world_layer.blit(self.love_rabbit.image, self.love_rabbit.rect)
            self.draw_entity_label(world_layer, self.love_rabbit.rect, "Thỏ tai đỏ", (255, 196, 212))
        world_layer.blit(self.player.image, self.player.rect)
        self.draw_entity_label(world_layer, self.player.rect, config.PLAYER_NAME, (88, 197, 255))
        self.draw_effects(world_layer)
        self.draw_muzzle_flash(world_layer)
        # Vẽ health packs
        for pack in self.health_packs:
            world_layer.blit(pack.image, pack.rect)
        # Vẽ floating texts (điểm kill + combo)
        for ft in self.floating_texts:
            ft.draw(world_layer)
        self.draw_tutorial_prompt(world_layer)
        self.draw_level_banner(world_layer)
        self.draw_status_message(world_layer)
        # Enemy off-screen indicators
        self.draw_enemy_indicators(world_layer)
        # Combo counter góc phải màn hình chơi
        self.draw_combo_hud(world_layer)

        surface.blit(world_layer, (int(offset.x), int(offset.y)))

    def draw_entity_label(self, surface, rect, name, color):
        label = self.assets.font_small.render(name, True, config.COLOR_TEXT)
        padding_x = 10
        panel = pygame.Rect(rect.centerx - (label.get_width() + padding_x * 2) // 2, rect.y - 24, label.get_width() + padding_x * 2, 18)
        pygame.draw.rect(surface, (5, 10, 20, 190), panel, border_radius=9)
        pygame.draw.rect(surface, color, panel, width=1, border_radius=9)
        surface.blit(label, (panel.x + padding_x, panel.y + 1))

    def draw_effects(self, surface):
        for effect in self.hit_effects:
            alpha = int(255 * (effect["life"] / 10))
            color = (*effect["color"], alpha)
            pygame.draw.circle(surface, color, effect["pos"], int(effect["radius"]), width=2)

    def draw_muzzle_flash(self, surface):
        if self.player.muzzle_timer <= 0:
            return
        center = self.player.pos + self.player.aim_direction * 24
        flash_ratio = self.player.muzzle_timer / max(self.player.muzzle_flash_duration, 0.001)
        radius = 8 + flash_ratio * 9
        pygame.draw.circle(surface, (255, 245, 194, 180), center, radius)

    def draw_objective_line(self, surface):
        if self.hostage.rescued or self.maze:
            return
        if self.objective_flash < 60:
            pygame.draw.line(surface, (255, 221, 122, 70), self.player.pos, self.hostage.pos, width=1)

    def draw_guidance(self, surface):
        if not self.level_spec.guidance_enabled or not self.maze or self.hostage.rescued:
            return

        # Màn 3 sử dụng heuristic "Euclidean" và né tránh kẻ địch để dẫn đường
        h_type = "euclidean" if self.level_spec.number == 3 else "manhattan"
        use_safety = (self.level_spec.number == 3)

        path = self.get_path(
            self.maze.world_to_cell(self.player.pos), 
            self.maze.hostage_cell,
            heuristic_type=h_type,
            use_safety=use_safety
        )
        if not path:
            return

        sampled = path[1:24:2]
        for index, cell in enumerate(sampled):
            pos = pygame.Vector2(self.maze.cell_to_world(cell))
            pulse = 0.65 + 0.35 * ((self.frame_count / 18.0 + index) % 2)
            enemy_near = any(pygame.Vector2(enemy.pos).distance_to(pos) < 72 for enemy in self.enemies)
            color = config.COLOR_DANGER if enemy_near else config.COLOR_WARNING
            radius = 5 if index else 7
            pygame.draw.circle(surface, (*color, int(160 * pulse)), pos, radius)
            pygame.draw.circle(surface, (*config.COLOR_TEXT, int(120 * pulse)), pos, max(2, radius - 3), width=1)

        destination = pygame.Vector2(self.hostage.pos)
        pygame.draw.circle(surface, (*config.COLOR_WARNING, 35), destination, 28)
        pygame.draw.circle(surface, config.COLOR_WARNING, destination, 14, width=2)
        
        # Label cho màn 3 đặc biệt hơn
        label_text = "Lối an toàn" if self.level_spec.number == 3 else "Lối chính"
        label = self.assets.font_small.render(label_text, True, config.COLOR_WARNING)
        surface.blit(label, (destination.x - label.get_width() // 2, destination.y - 34))

    def draw_hazards(self, surface):
        for hazard in self.hazards:
            pulse = 0.75 + 0.25 * (1 + pygame.math.Vector2(1, 0).rotate(hazard.pulse * 90).x) * 0.5
            base_alpha = int(42 + 30 * pulse)
            pygame.draw.circle(surface, (255, 68, 92, base_alpha), hazard.center, hazard.radius)
            pygame.draw.circle(surface, (255, 118, 132), hazard.center, int(hazard.radius * (0.72 + pulse * 0.16)), width=2)
            if hazard.label:
                label = self.assets.font_small.render(hazard.label, True, config.COLOR_DANGER)
                surface.blit(label, (hazard.center.x - label.get_width() // 2, hazard.center.y - hazard.radius - 22))

    def draw_tutorial_prompt(self, surface):
        if self.tutorial_timer <= 0:
            return

        if self.level_spec.number == 1:
            text_value = "WASD di chuyển | Chuột/Space bắn | Shift né đạn | Chạm Lina để cứu | ESC tạm dừng"
        elif self.level_spec.number == 3:
            text_value = "Lần theo các điểm sáng 'Lối an toàn' (Heuristic) để tránh địch và tìm Lina."
        elif self.level_spec.number >= 4:
            text_value = f"Nhấn {config.PLAYER_SKILL_KEY_LABEL} để bắn {config.PLAYER_SKILL_NAME} | Né vùng đỏ trên nền"
        else:
            return

        alpha = min(220, int(70 + self.tutorial_timer * 18))
        panel = pygame.Surface((660, 42), pygame.SRCALPHA)
        pygame.draw.rect(panel, (5, 10, 20, alpha), panel.get_rect(), border_radius=14)
        pygame.draw.rect(panel, (*config.COLOR_ACCENT, min(220, alpha)), panel.get_rect(), width=1, border_radius=14)
        text = self.assets.font_small.render(text_value, True, config.COLOR_TEXT)
        panel.blit(text, (20, 12))
        target_y = self.world_rect.top + 18 if self.level_spec.number == 1 else self.world_rect.bottom - 58
        surface.blit(panel, (self.world_rect.centerx - panel.get_width() // 2, target_y))

    def draw_level_banner(self, surface):
        if self.banner_timer <= 0:
            return
        alpha = min(255, int(255 * min(1.0, self.banner_timer / 2.6)))
        panel = pygame.Surface((520, 72), pygame.SRCALPHA)
        pygame.draw.rect(panel, (4, 10, 22, int(alpha * 0.82)), panel.get_rect(), border_radius=16)
        pygame.draw.rect(panel, (*config.COLOR_BORDER, min(255, alpha)), panel.get_rect(), width=2, border_radius=16)
        title = self.assets.font_h2.render(f"Màn {self.level_spec.number} - {self.level_spec.title}", True, config.COLOR_TEXT)
        desc = self.assets.font_small.render(self.current_objective_text(), True, config.COLOR_SUBTEXT)
        panel.blit(title, (panel.get_width() // 2 - title.get_width() // 2, 14))
        panel.blit(desc, (panel.get_width() // 2 - desc.get_width() // 2, 42))
        surface.blit(panel, (self.world_rect.centerx - panel.get_width() // 2, self.world_rect.top + 10))

    def draw_status_message(self, surface):
        if not self.status_message:
            return
        panel = pygame.Surface((420, 38), pygame.SRCALPHA)
        pygame.draw.rect(panel, (5, 10, 22, 190), panel.get_rect(), border_radius=12)
        pygame.draw.rect(panel, config.COLOR_WARNING, panel.get_rect(), width=1, border_radius=12)
        text = self.assets.font_small.render(self.status_message, True, config.COLOR_TEXT)
        panel.blit(text, (panel.get_width() // 2 - text.get_width() // 2, 10))
        surface.blit(panel, (self.world_rect.centerx - panel.get_width() // 2, self.world_rect.bottom - 54))

    def draw_dash_afterimages(self, surface):
        """Vẽ các bóng afterimage khi player đang dash.

        Mỗi afterimage là snapshot sprite của player lúc spawn,
        được tint màu xanh cyan và fade dần để tạo hiệu ứng tốc độ.
        """
        for af in self.dash_afterimages:
            alpha = max(0, int(af["alpha"]))
            img = af["image"].copy()
            # Tint xanh cyan lên afterimage
            tint = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            tint.fill((80, 200, 255, min(alpha, 120)))
            img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            img.set_alpha(alpha)
            rect = img.get_rect(center=(int(af["pos"].x), int(af["pos"].y)))
            surface.blit(img, rect)

    def draw_enemy_indicators(self, surface):
        """Vẽ mũi tên tam giác ở rìa world_rect khi địch ngoài màn hình.

        Màu đỏ = enemy thường, tím = boss. Giúp player nhận biết mối nguy
        đến từ hướng nào mà không cần nhìn minimap.
        """
        margin = 14
        rect = self.world_rect
        targets = []
        for enemy in self.enemies:
            targets.append((enemy.pos, config.COLOR_DANGER))
        if self.boss and self.boss.health > 0:
            targets.append((self.boss.pos, (200, 80, 255)))

        for pos, color in targets:
            # Chỉ vẽ nếu ngoài world_rect (mở rộng thêm 12px để tránh flicker)
            if rect.inflate(24, 24).collidepoint(pos):
                continue

            # Tính góc từ tâm world_rect → vị trí địch
            center = pygame.Vector2(rect.centerx, rect.centery)
            to_enemy = pos - center
            angle = math.atan2(to_enemy.y, to_enemy.x)

            # Tìm điểm giao của tia với cạnh world_rect
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            half_w, half_h = rect.width / 2 - margin, rect.height / 2 - margin
            if cos_a != 0 and sin_a != 0:
                t_x = half_w / abs(cos_a)
                t_y = half_h / abs(sin_a)
                t = min(t_x, t_y)
            elif cos_a == 0:
                t = half_h / abs(sin_a) if sin_a != 0 else half_w
            else:
                t = half_w / abs(cos_a)

            arrow_center = center + pygame.Vector2(cos_a * t, sin_a * t)
            arrow_center.x = max(rect.left + margin, min(rect.right - margin, arrow_center.x))
            arrow_center.y = max(rect.top + margin, min(rect.bottom - margin, arrow_center.y))

            # Vẽ tam giác mũi tên nhỏ hướng vào địch
            size = 9
            tip = arrow_center + pygame.Vector2(cos_a, sin_a) * size
            perp = pygame.Vector2(-sin_a, cos_a)
            base1 = arrow_center - pygame.Vector2(cos_a, sin_a) * 4 + perp * size * 0.6
            base2 = arrow_center - pygame.Vector2(cos_a, sin_a) * 4 - perp * size * 0.6

            # Nhấp nháy nhẹ
            pulse_alpha = 160 + int(60 * math.sin(self.frame_count * 0.12))
            arrow_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.polygon(arrow_surf, (*color, pulse_alpha),
                                [(tip - pygame.Vector2(rect.left, rect.top)),
                                 (base1 - pygame.Vector2(rect.left, rect.top)),
                                 (base2 - pygame.Vector2(rect.left, rect.top))])
            surface.blit(arrow_surf, (rect.left, rect.top))

    def draw_combo_hud(self, surface):
        """Vẽ combo counter góc phải dưới world_rect khi combo >= 2."""
        if self.combo_count < 2:
            return
        multiplier = self._combo_multiplier()
        pulse = 0.85 + 0.15 * math.sin(self.frame_count * 0.2)
        # Màu đổi theo multiplier
        if multiplier >= 3.0:
            color = (255, 80, 80)
        elif multiplier >= 2.0:
            color = (255, 180, 40)
        elif multiplier >= 1.5:
            color = (255, 220, 80)
        else:
            color = (180, 255, 180)

        label = f"COMBO x{self.combo_count}"
        mult_label = f"x{multiplier:.1f} điểm"
        w = 160
        panel = pygame.Surface((w, 46), pygame.SRCALPHA)
        pygame.draw.rect(panel, (5, 10, 22, int(200 * pulse)), panel.get_rect(), border_radius=12)
        pygame.draw.rect(panel, (*color, int(220 * pulse)), panel.get_rect(), width=2, border_radius=12)
        combo_text = self.assets.font_h2.render(label, True, color)
        mult_text = self.assets.font_small.render(mult_label, True, config.COLOR_TEXT)
        panel.blit(combo_text, (w // 2 - combo_text.get_width() // 2, 4))
        panel.blit(mult_text, (w // 2 - mult_text.get_width() // 2, 26))
        x = self.world_rect.right - w - 12
        y = self.world_rect.top + 12
        surface.blit(panel, (x, y))

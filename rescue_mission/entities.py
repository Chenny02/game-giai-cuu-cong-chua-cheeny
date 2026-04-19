"""Các entity và hành vi combat có thể tái sử dụng.

Ý tưởng:
- Mỗi thực thể trong game là một sprite riêng.
- `Actor` gom những thứ chung nhất: vị trí, sprite, hit flash.
- `Player`, `Enemy`, `Boss` chỉ ghi đè những hành vi đặc thù.

Khi cần thêm enemy mới, ta ưu tiên thêm vào `EnemyType` và nới rộng AI trong `Enemy`
thay vì viết lại hệ thống collision hay bullet.
"""

import math
import random
from dataclasses import dataclass
from typing import Tuple

import pygame

from . import config
from .assets import tint_surface


def make_vector_from_angle(angle_degrees):
    """Tiện ích cho boss pattern quay tròn."""

    radians = math.radians(angle_degrees)
    return pygame.Vector2(math.cos(radians), math.sin(radians))


def safe_normalize(vector, fallback=(1, 0)):
    """Tránh lỗi chia cho 0 khi vector quá ngắn hoặc bằng 0."""

    if vector.length_squared() == 0:
        return pygame.Vector2(fallback)
    return vector.normalize()


@dataclass(frozen=True)
class EnemyType:
    key: str
    label: str
    speed: float
    max_health: int
    score_value: int
    contact_damage: int
    fire_interval: int
    bullet_speed: float
    preferred_range: float
    sprite_key: str
    bullet_color: Tuple[int, int, int]


ENEMY_TYPES = {
    "grunt": EnemyType(
        key="grunt",
        label="Assaulter",
        speed=2.2,
        max_health=42,
        score_value=20,
        contact_damage=14,
        fire_interval=0,
        bullet_speed=0,
        preferred_range=0,
        sprite_key="enemy_grunt",
        bullet_color=(255, 120, 120),
    ),
    "runner": EnemyType(
        key="runner",
        label="Runner",
        speed=3.4,
        max_health=28,
        score_value=28,
        contact_damage=18,
        fire_interval=0,
        bullet_speed=0,
        preferred_range=0,
        sprite_key="enemy_runner",
        bullet_color=(255, 196, 72),
    ),
    "shooter": EnemyType(
        key="shooter",
        label="Marksman",
        speed=1.9,
        max_health=36,
        score_value=36,
        contact_damage=10,
        fire_interval=95,
        bullet_speed=8.5,
        preferred_range=240,
        sprite_key="enemy_shooter",
        bullet_color=(204, 168, 255),
    ),
}


class Actor(pygame.sprite.Sprite):
    """Base sprite cho các thực thể có sprite sống và hit flash.

    Actor không biết gì về gameplay.
    Nó chỉ biết cách giữ vị trí và đổi sprite tạm thời khi bị trúng đạn.
    Cách tách này giúp combat logic nằm ở class con, còn Actor giữ code vẽ gọn.
    """

    def __init__(self, pos):
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.base_image = pygame.Surface((8, 8), pygame.SRCALPHA)
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))
        self.hitbox_size = pygame.Vector2(16, 16)
        self.flash_timer = 0
        self.flash_color = (255, 255, 255)

    def set_base_image(self, surface):
        center = getattr(self, "rect", surface.get_rect()).center
        self.base_image = surface
        self.image = surface.copy()
        self.rect = self.image.get_rect(center=center)

    def update_visual(self):
        """Cập nhật sprite hiện tại sau mỗi frame.

        Nếu đang có flash, ta tint tạm lên base_image.
        Nếu không, sprite quay lại base_image.
        """

        if self.flash_timer > 0:
            alpha = 60 + self.flash_timer * 18
            self.image = tint_surface(self.base_image, self.flash_color, alpha=min(160, alpha))
            self.flash_timer -= 1
        else:
            self.image = self.base_image
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def flash(self, frames=5, color=(255, 255, 255)):
        self.flash_timer = max(self.flash_timer, frames)
        self.flash_color = color

    def set_hitbox(self, width, height=None):
        height = width if height is None else height
        self.hitbox_size = pygame.Vector2(width, height)

    def collision_rect(self, position=None):
        pos = pygame.Vector2(position) if position is not None else self.pos
        width = max(1, int(round(self.hitbox_size.x)))
        height = max(1, int(round(self.hitbox_size.y)))
        return pygame.Rect(
            round(pos.x - width / 2),
            round(pos.y - height / 2),
            width,
            height,
        )


class Bullet(pygame.sprite.Sprite):
    """Đạn dùng chung cho player, enemy và boss.

    Đạn không tự xử lý va chạm với mục tiêu.
    Nó chỉ bay, chạm tường nếu có maze, và tự hủy khi hết thời gian.
    Collision với enemy/player được để ở LevelScene để dễ quản lý luật chơi.
    """

    def __init__(self, origin, direction, speed, damage, friendly, color, lifetime=120):
        super().__init__()
        self.pos = pygame.Vector2(origin)
        self.velocity = safe_normalize(direction) * speed
        self.damage = damage
        self.friendly = friendly
        self.lifetime = lifetime
        self.radius = 5 if friendly else 6
        self.color = color

        size = self.radius * 2 + 6
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        pygame.draw.circle(self.image, (*color, 90), (center, center), self.radius + 2)
        pygame.draw.circle(self.image, color, (center, center), self.radius)
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def update(self, scene):
        self.pos += self.velocity
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        self.lifetime -= 1

        if self.lifetime <= 0 or not scene.world_rect.inflate(40, 40).collidepoint(self.pos):
            self.kill()
            return

        if scene.maze and not scene.maze.is_point_walkable(self.pos):
            scene.add_burst(self.pos, self.color, 4)
            self.kill()


class Player(Actor):
    """Nhân vật người chơi.

    Player chỉ phụ trách:
    - đọc input
    - di chuyển
    - bắn đạn
    - quản lý invulnerability sau khi trúng đạn

    Mọi kết quả ngoài việc đó, ví dụ thắng/thua màn, đều do LevelScene quyết định.
    """

    def __init__(self, pos, assets, stats):
        super().__init__(pos)
        self.stats = stats
        self.max_health = stats.max_health
        self.health = stats.max_health
        self.radius = 16
        self.fire_interval = stats.fire_interval
        self.fire_timer = 0
        self.invulnerable_timer = 0
        self.muzzle_timer = 0
        self.aim_direction = pygame.Vector2(1, 0)
        self.set_base_image(assets.images["player"])

    def update(self, scene):
        # Input vector được normalize để đi chéo không nhanh hơn đi thẳng.
        keys = pygame.key.get_pressed()
        input_vector = pygame.Vector2(
            (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
            (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        if input_vector.length_squared() > 0:
            input_vector = input_vector.normalize()

        self.move(input_vector * self.stats.move_speed, scene)
        self.fire_timer = max(0, self.fire_timer - 1)
        self.invulnerable_timer = max(0, self.invulnerable_timer - 1)
        self.muzzle_timer = max(0, self.muzzle_timer - 1)

        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        self.aim_direction = safe_normalize(mouse_pos - self.pos)

        mouse_pressed = pygame.mouse.get_pressed()[0]
        if (mouse_pressed or keys[pygame.K_SPACE]) and self.fire_timer == 0:
            self.fire(scene)
            self.fire_timer = self.fire_interval

        if self.invulnerable_timer > 0 and self.invulnerable_timer % 4 < 2:
            self.flash(3, (155, 228, 255))

        self.update_visual()

    def move(self, velocity, scene):
        # Xử lý va chạm theo từng trục để đi mê cung mượt và không xuyên tường.
        self.pos.x += velocity.x
        if scene.maze and not scene.maze.is_rect_walkable(self.rect_for_position(self.pos)):
            self.pos.x -= velocity.x
        self.clamp_to_world(scene.world_rect)

        self.pos.y += velocity.y
        if scene.maze and not scene.maze.is_rect_walkable(self.rect_for_position(self.pos)):
            self.pos.y -= velocity.y
        self.clamp_to_world(scene.world_rect)

    def clamp_to_world(self, world_rect):
        radius = self.radius + 2
        self.pos.x = max(world_rect.left + radius, min(world_rect.right - radius, self.pos.x))
        self.pos.y = max(world_rect.top + radius, min(world_rect.bottom - radius, self.pos.y))

    def rect_for_position(self, position):
        # Hitbox nhỏ hơn sprite để player luôn đi được trong hành lang maze.
        return pygame.Rect(0, 0, 16, 16).move(round(position.x) - 8, round(position.y) - 8)

    def fire(self, scene):
        # Player không tạo hiệu ứng tại chỗ; nó thông báo scene để scene thêm feedback chung.
        muzzle_pos = self.pos + self.aim_direction * 22
        bullet = Bullet(
            origin=muzzle_pos,
            direction=self.aim_direction,
            speed=self.stats.bullet_speed,
            damage=self.stats.bullet_damage,
            friendly=True,
            color=(244, 248, 255),
            lifetime=90,
        )
        self.muzzle_timer = 3
        scene.player_bullets.add(bullet)
        scene.add_burst(muzzle_pos, (190, 225, 255), 6)

    def take_damage(self, amount):
        if self.invulnerable_timer > 0:
            return False

        self.health = max(0, self.health - amount)
        self.invulnerable_timer = config.PLAYER_IFRAMES
        self.flash(6, config.COLOR_DANGER)
        return True


class Hostage(Actor):
    """Con tin có 2 trạng thái: đứng yên hoặc đi theo player sau khi được cứu."""

    def __init__(self, pos, assets):
        super().__init__(pos)
        self.set_base_image(assets.images["hostage"])
        self.rescued = False
        self.follow_offset = pygame.Vector2(-32, 26)
        self.pulse = 0

    def update(self, scene):
        self.pulse = (self.pulse + 1) % 120
        if self.rescued:
            desired = scene.player.pos + self.follow_offset.rotate(math.sin(self.pulse / 18) * 6)
            self.pos += (desired - self.pos) * 0.18
        self.update_visual()


class Enemy(Actor):
    """Enemy dùng chung cho nhiều archetype.

    Khác biệt giữa grunt / runner / shooter không nằm ở class con,
    mà nằm ở data `EnemyType`. Cách này để scale số lượng loại địch nhanh hơn.
    """

    def __init__(self, pos, assets, enemy_type, level_number):
        super().__init__(pos)
        self.enemy_type = enemy_type
        self.level_number = level_number
        self.max_health = enemy_type.max_health + (level_number - 1) * 3
        self.health = self.max_health
        self.speed = enemy_type.speed + (level_number - 1) * 0.07
        self.contact_damage = enemy_type.contact_damage + (1 if level_number >= 3 else 0)
        self.score_value = enemy_type.score_value + (level_number - 1) * 2
        self.fire_timer = random.randint(18, max(20, enemy_type.fire_interval)) if enemy_type.fire_interval else 0
        self.path_timer = random.randint(8, 18)
        self.path = []
        self.strafe_dir = random.choice([-1, 1])
        self.set_hitbox(16 if enemy_type.key != "shooter" else 18)
        self.set_base_image(assets.images[enemy_type.sprite_key])

    def update(self, scene):
        # Enemy maze ưu tiên pathfinding, enemy màn thường ưu tiên AI theo range.
        self.path_timer = max(0, self.path_timer - 1)
        target_pos = pygame.Vector2(scene.player.pos)
        to_player = target_pos - self.pos
        distance = to_player.length() if to_player.length_squared() > 0 else 0.0
        direction = safe_normalize(to_player, fallback=(1, 0))

        if scene.maze:
            if self.path_timer == 0 or not self.path:
                self.path = scene.get_path(scene.maze.world_to_cell(self.pos), scene.maze.world_to_cell(target_pos))
                self.path_timer = random.randint(15, 28)
            if self.path:
                waypoint = pygame.Vector2(scene.maze.cell_to_world(self.path[0]))
                if waypoint.distance_to(self.pos) < 10:
                    self.path.pop(0)
                move_dir = safe_normalize(waypoint - self.pos, fallback=direction)
                self.try_move(move_dir * self.speed, scene)
            else:
                self.try_move(direction * self.speed, scene)
        else:
            if self.enemy_type.key == "shooter":
                self.update_shooter_ai(scene, direction, distance)
            elif self.enemy_type.key == "runner":
                self.try_move(direction * (self.speed * 1.15), scene)
            else:
                self.try_move(direction * self.speed, scene)

        if self.enemy_type.fire_interval:
            self.fire_timer = max(0, self.fire_timer - 1)
            if self.fire_timer == 0 and scene.has_clear_line(self.pos, scene.player.pos):
                self.fire(scene)
                self.fire_timer = max(36, self.enemy_type.fire_interval - self.level_number * 4)

        self.update_visual()

    def update_shooter_ai(self, scene, direction, distance):
        """Shooter có xu hướng giữ tầm, lùa góc và strafe ngang."""

        preferred = self.enemy_type.preferred_range
        tangent = pygame.Vector2(-direction.y, direction.x) * self.strafe_dir
        if distance > preferred + 30:
            move = direction * self.speed
        elif distance < preferred * 0.65:
            move = -direction * self.speed
        else:
            move = tangent * (self.speed * 0.9)
        self.try_move(move, scene)

        if random.random() < 0.01:
            self.strafe_dir *= -1

    def try_move(self, velocity, scene):
        """Di chuyển có kiểm tra tường nếu đang ở maze."""

        self.pos.x += velocity.x
        if scene.maze and not scene.maze.is_rect_walkable(self.collision_rect()):
            self.pos.x -= velocity.x
        self.pos.y += velocity.y
        if scene.maze and not scene.maze.is_rect_walkable(self.collision_rect()):
            self.pos.y -= velocity.y

        radius = max(self.rect.width, self.rect.height) // 2
        self.pos.x = max(scene.world_rect.left + radius, min(scene.world_rect.right - radius, self.pos.x))
        self.pos.y = max(scene.world_rect.top + radius, min(scene.world_rect.bottom - radius, self.pos.y))

    def collision_rect(self):
        return super().collision_rect()

    def fire(self, scene):
        """Shooter bắn thông qua scene để đạn vào đúng nhóm enemy_bullets."""

        direction = safe_normalize(scene.player.pos - self.pos)
        bullet = Bullet(
            origin=self.pos + direction * 16,
            direction=direction,
            speed=self.enemy_type.bullet_speed,
            damage=9 + self.level_number,
            friendly=False,
            color=self.enemy_type.bullet_color,
            lifetime=120,
        )
        scene.enemy_bullets.add(bullet)
        scene.add_burst(self.pos + direction * 16, self.enemy_type.bullet_color, 5)

    def take_damage(self, amount):
        self.health -= amount
        self.flash(4, (255, 255, 255))
        return self.health <= 0


class Boss(Actor):
    """Boss level 4.

    Boss được thiết kế theo phase:
    - Phase 1: ban thang vao player
    - Phase 2: them spread va vong dan
    - Phase 3: ap luc manh hon va goi them enemy

    Các pattern được giữ trong class này vì đây là hành vi rất đặc thù.
    """

    def __init__(self, pos, assets):
        super().__init__(pos)
        self.set_base_image(assets.images["boss"])
        self.max_health = config.BOSS_HEALTH
        self.health = self.max_health
        self.primary_timer = 35
        self.secondary_timer = 110
        self.summon_timer = 360
        self.phase = 1

    def update(self, scene):
        # Boss luôn tự xác định phase dựa trên phần trăm HP hiện tại.
        self.phase = self.get_phase()
        self.primary_timer = max(0, self.primary_timer - 1)
        self.secondary_timer = max(0, self.secondary_timer - 1)
        self.summon_timer = max(0, self.summon_timer - 1)

        to_player = scene.player.pos - self.pos
        distance = to_player.length() if to_player.length_squared() > 0 else 0
        direction = safe_normalize(to_player)
        desired_range = 220 if self.phase == 1 else 170
        move_speed = 1.6 + self.phase * 0.35

        if distance > desired_range:
            self.pos += direction * move_speed
        elif distance < desired_range - 70:
            self.pos -= direction * (move_speed * 0.7)
        else:
            self.pos += pygame.Vector2(-direction.y, direction.x) * (0.65 * random.choice([-1, 1]))

        radius = 44
        self.pos.x = max(scene.world_rect.left + radius, min(scene.world_rect.right - radius, self.pos.x))
        self.pos.y = max(scene.world_rect.top + radius, min(scene.world_rect.bottom - radius, self.pos.y))

        if self.primary_timer == 0:
            self.fire_primary(scene)
            self.primary_timer = max(18, 44 - self.phase * 7)

        if self.phase >= 2 and self.secondary_timer == 0:
            self.fire_secondary(scene)
            self.secondary_timer = max(60, 150 - self.phase * 25)

        if self.phase >= 2 and self.summon_timer == 0 and len(scene.enemies) < scene.level_spec.max_enemies:
            scene.spawn_enemy(forced_type="runner" if self.phase == 3 else "grunt")
            self.summon_timer = max(180, 320 - self.phase * 40)

        self.update_visual()

    def get_phase(self):
        ratio = self.health / self.max_health
        if ratio <= 0.33:
            return 3
        if ratio <= 0.66:
            return 2
        return 1

    def fire_primary(self, scene):
        """Pattern cơ bản: bắn thẳng / spread tùy phase."""

        direction = safe_normalize(scene.player.pos - self.pos)
        if self.phase == 1:
            scene.spawn_bullet(self.pos, direction, 8.6, 14, False, (255, 154, 91))
        elif self.phase == 2:
            for angle in [-16, -8, 0, 8, 16]:
                scene.spawn_bullet(self.pos, direction.rotate(angle), 9.2, 15, False, (255, 154, 91))
        else:
            for angle in [-20, -10, 0, 10, 20]:
                scene.spawn_bullet(self.pos, direction.rotate(angle), 10.4, 17, False, (255, 188, 122))

    def fire_secondary(self, scene):
        """Pattern phụ: vòng đạn, xoay đạn và kết hợp line pressure."""

        if self.phase == 2:
            for index in range(10):
                scene.spawn_bullet(self.pos, make_vector_from_angle(index * 36), 6.4, 12, False, (206, 120, 255))
        else:
            for index in range(14):
                direction = make_vector_from_angle(index * (360 / 14) + scene.frame_count * 0.7)
                scene.spawn_bullet(self.pos, direction, 7.2, 13, False, (219, 132, 255))
            direction = safe_normalize(scene.player.pos - self.pos)
            for angle in [-12, 0, 12]:
                scene.spawn_bullet(self.pos, direction.rotate(angle), 11.2, 17, False, (255, 108, 162))

    def take_damage(self, amount):
        self.health = max(0, self.health - amount)
        self.flash(5, (255, 255, 255))
        return self.health <= 0

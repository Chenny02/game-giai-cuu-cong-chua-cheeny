"""Player animated bằng sprite sheet."""

import math

import pygame

from .. import config
from ..core.animation import Animation, AnimationManager, build_animations_from_frames, build_animations_from_sheet
from ..entities import Actor, Bullet, safe_normalize


def _fallback_player_animations(assets):
    frame = pygame.transform.smoothscale(assets.images["player"], config.PLAYER_RENDER_SIZE)
    return {
        "idle": Animation([frame], fps=6, loop=True),
        "run": Animation([frame], fps=6, loop=True),
        "shoot": Animation([frame], fps=6, loop=False),
    }


class Player(Actor):
    """Player có state animation: idle, run, shoot và xoay theo chuột."""

    def __init__(self, pos, assets, stats):
        super().__init__(pos)
        self.stats = stats
        self.max_health = stats.max_health
        self.health = stats.max_health
        self.radius = 16
        self.set_hitbox(16, 16)
        self.fire_interval = stats.fire_interval
        self.fire_timer = 0
        self.invulnerable_timer = 0
        self.shoot_anim_timer = 0.0
        self.muzzle_timer = 0.0
        self.aim_direction = pygame.Vector2(1, 0)
        self.flip_x = False

        folder_frames = assets.animation_frames.get("player", {})
        character_sheet = assets.sprite_sheets.get("character")
        if character_sheet:
            animations = build_animations_from_sheet(character_sheet, config.PLAYER_ANIMATIONS)
        else:
            animations = _fallback_player_animations(assets)

        # State nào đã có frame rời trong thư mục sẽ ghi đè lên fallback.
        if folder_frames:
            animations.update(build_animations_from_frames(folder_frames, config.PLAYER_ANIMATIONS))
        self.animation_manager = AnimationManager(animations, initial_state="idle", angle_step=10)
        self.set_base_image(self.animation_manager.get_image())

    def update(self, scene, delta_time):
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
        self.shoot_anim_timer = max(0.0, self.shoot_anim_timer - delta_time)
        self.muzzle_timer = max(0.0, self.muzzle_timer - delta_time)

        mouse_pos = pygame.Vector2(getattr(scene, "mouse_pos", pygame.mouse.get_pos()))
        aim_vector = mouse_pos - self.pos
        self.aim_direction = safe_normalize(aim_vector)
        angle = -self.aim_direction.angle_to(pygame.Vector2(1, 0))
        self.flip_x = self.aim_direction.x < -0.2

        mouse_pressed = pygame.mouse.get_pressed()[0]
        if (mouse_pressed or keys[pygame.K_SPACE]) and self.fire_timer == 0:
            self.fire(scene)
            self.fire_timer = self.fire_interval
            self.shoot_anim_timer = 0.12
            self.muzzle_timer = 0.08

        if self.shoot_anim_timer > 0:
            self.animation_manager.switch("shoot")
        elif input_vector.length_squared() > 0:
            self.animation_manager.switch("run")
        else:
            self.animation_manager.switch("idle")

        self.animation_manager.update(delta_time)
        self.set_base_image(self.animation_manager.get_image(angle=angle, flip_x=self.flip_x))

        if self.invulnerable_timer > 0 and self.invulnerable_timer % 4 < 2:
            self.flash(3, (155, 228, 255))

        self.update_visual()

    def move(self, velocity, scene):
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
        return self.collision_rect(position)

    def fire(self, scene):
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
        scene.player_bullets.add(bullet)
        scene.add_effect("bullet", muzzle_pos, angle=-self.aim_direction.angle_to(pygame.Vector2(1, 0)))

    def take_damage(self, amount):
        if self.invulnerable_timer > 0:
            return False

        self.health = max(0, self.health - amount)
        self.invulnerable_timer = config.PLAYER_IFRAMES
        self.flash(6, config.COLOR_DANGER)
        return True

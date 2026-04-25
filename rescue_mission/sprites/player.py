"""Player sprite and gameplay control."""

import math

import pygame

from .. import config
from ..core.animation import (
    Animation,
    AnimationManager,
    build_animations_from_frames,
    build_animations_from_sheet,
    build_directional_animations_from_frames,
)
from ..entities import Actor, Bullet, safe_normalize
from ..player_skill import PlayerSkillController


def _fallback_player_animations(assets):
    frame = pygame.transform.smoothscale(assets.images["player"], config.PLAYER_RENDER_SIZE)
    return {
        "idle": Animation([frame], fps=6, loop=True),
        "run": Animation([frame], fps=6, loop=True),
        "shoot": Animation([frame], fps=6, loop=False),
    }


def _direction_token_from_vector(vector):
    if vector.length_squared() <= 0:
        return "e"

    angle = math.degrees(math.atan2(vector.y, vector.x))
    sectors = [
        (22.5, "e"),
        (67.5, "se"),
        (112.5, "s"),
        (157.5, "sw"),
        (202.5, "w"),
        (247.5, "nw"),
        (292.5, "n"),
        (337.5, "ne"),
        (360.0, "e"),
    ]
    normalized = (angle + 360.0) % 360.0
    for threshold, token in sectors:
        if normalized < threshold:
            return token
    return "e"


class Player(Actor):
    def __init__(self, pos, assets, stats):
        super().__init__(pos)
        self.stats = stats
        self.max_health = stats.max_health
        self.health = stats.max_health
        self.radius = 16
        self.set_hitbox(16, 16)
        self.fire_interval = stats.fire_interval / config.FPS
        self.fire_timer = 0.0
        self.invulnerable_duration = config.PLAYER_IFRAMES / config.FPS
        self.invulnerable_timer = 0.0
        self.shoot_anim_timer = 0.0
        self.cast_anim_timer = 0.0
        self.muzzle_flash_duration = 0.08
        self.muzzle_timer = 0.0
        self.aim_direction = pygame.Vector2(1, 0)
        self.last_move_direction = pygame.Vector2(1, 0)
        self.flip_x = False
        self.direction_token = "e"
        self.last_direction_token = "e"
        self.directional_state = None
        self.skill = PlayerSkillController()
        self.skill_pressed_last_frame = False

        folder_frames = assets.animation_frames.get("player", {})
        directional_frames = assets.directional_animation_frames.get("player", {})
        character_sheet = assets.sprite_sheets.get("character")
        if character_sheet:
            animations = build_animations_from_sheet(character_sheet, config.PLAYER_ANIMATIONS)
        else:
            animations = _fallback_player_animations(assets)

        if folder_frames:
            animations.update(build_animations_from_frames(folder_frames, config.PLAYER_ANIMATIONS))
        self.animation_manager = AnimationManager(animations, initial_state="idle", angle_step=10)
        self.directional_animations = build_directional_animations_from_frames(directional_frames, config.PLAYER_ANIMATIONS)
        self.set_base_image(self.animation_manager.get_image())

    def update(self, scene, delta_time):
        keys = pygame.key.get_pressed()
        input_vector = pygame.Vector2(
            (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
            (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        if input_vector.length_squared() > 0:
            input_vector = input_vector.normalize()
            self.last_move_direction = pygame.Vector2(input_vector)

        self.move(input_vector * self.stats.move_speed * delta_time * config.FPS, scene)
        self.fire_timer = max(0.0, self.fire_timer - delta_time)
        self.invulnerable_timer = max(0.0, self.invulnerable_timer - delta_time)
        self.shoot_anim_timer = max(0.0, self.shoot_anim_timer - delta_time)
        self.cast_anim_timer = max(0.0, self.cast_anim_timer - delta_time)
        self.muzzle_timer = max(0.0, self.muzzle_timer - delta_time)
        self.skill.update(delta_time)

        mouse_pos = pygame.Vector2(getattr(scene, "mouse_pos", pygame.mouse.get_pos()))
        aim_vector = mouse_pos - self.pos
        if aim_vector.length_squared() > 0:
            self.aim_direction = safe_normalize(aim_vector)
        else:
            self.aim_direction = safe_normalize(self.last_move_direction)

        self.direction_token = _direction_token_from_vector(self.aim_direction)
        angle = -self.aim_direction.angle_to(pygame.Vector2(1, 0))
        self.flip_x = self.aim_direction.x < -0.2

        mouse_pressed = pygame.mouse.get_pressed()[0]
        if (mouse_pressed or keys[pygame.K_SPACE]) and self.fire_timer <= 0:
            self.fire(scene)
            self.fire_timer = self.fire_interval
            self.shoot_anim_timer = 0.12
            self.muzzle_timer = self.muzzle_flash_duration

        skill_pressed = bool(keys[pygame.K_q])
        if skill_pressed and not self.skill_pressed_last_frame:
            if self.skill.try_cast(self, scene, self.aim_direction):
                self.cast_anim_timer = 0.18
        self.skill_pressed_last_frame = skill_pressed

        if self.cast_anim_timer > 0 or self.shoot_anim_timer > 0:
            current_state = "shoot"
        elif input_vector.length_squared() > 0:
            current_state = "run"
        else:
            current_state = "idle"

        directional_bank = self.directional_animations.get(current_state)
        directional_anim = directional_bank.get(self.direction_token) if directional_bank else None
        if directional_anim is not None:
            if self.directional_state != current_state or self.last_direction_token != self.direction_token:
                directional_anim.reset()
                self.directional_state = current_state
                self.last_direction_token = self.direction_token
            directional_anim.update(delta_time)
            self.set_base_image(directional_anim.current_frame)
        else:
            self.directional_state = None
            self.last_direction_token = self.direction_token
            self.animation_manager.switch(current_state)
            self.animation_manager.update(delta_time)
            self.set_base_image(self.animation_manager.get_image(angle=angle, flip_x=self.flip_x))

        if self.invulnerable_timer > 0 and int(self.invulnerable_timer * config.FPS) % 4 < 2:
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
        if getattr(scene, "audio", None):
            scene.audio.play("shoot", volume=0.75)

    def take_damage(self, amount, scene=None):
        if scene is not None and getattr(scene, "player_invincible", False):
            return False
        if self.invulnerable_timer > 0:
            return False

        self.health = max(0, self.health - amount)
        self.invulnerable_timer = self.invulnerable_duration
        self.flash(6, config.COLOR_DANGER)
        return True

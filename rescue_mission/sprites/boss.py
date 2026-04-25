"""Boss sprite and combat logic."""

import math
import random

import pygame

from .. import config
from ..core.animation import (
    Animation,
    AnimationManager,
    build_animations_from_frames,
    build_animations_from_sheet,
    build_directional_animations_from_frames,
)
from ..entities import Actor, make_vector_from_angle, safe_normalize


def _fallback_boss_animations(assets):
    frame = pygame.transform.smoothscale(assets.images["boss"], config.BOSS_RENDER_SIZE)
    return {
        "idle": Animation([frame], fps=5, loop=True),
        "move": Animation([frame], fps=6, loop=True),
        "attack1": Animation([frame], fps=8, loop=False),
        "attack2": Animation([frame], fps=8, loop=False),
        "attack3": Animation([frame], fps=8, loop=False),
        "death": Animation([frame], fps=6, loop=False),
    }


def _direction_token_from_vector(vector):
    if vector.length_squared() <= 0:
        return "s"

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
    return "s"


class Boss(Actor):
    def __init__(self, pos, assets, profile):
        super().__init__(pos)
        self.profile = profile
        self.display_name = profile.display_name
        self.max_health = profile.max_health
        self.health = self.max_health
        self.phase = 1
        self.set_hitbox(76, 76)

        self.primary_timer = 0.75
        self.secondary_timer = 2.25
        self.summon_timer = profile.summon_cooldown
        self.action_timer = 0.0
        self.attack_windup = 0.0
        self.pending_attack = None
        self.dead = False
        self.direction_token = "s"
        self.last_direction_token = "s"
        self.directional_state = None

        folder_frames = assets.animation_frames.get("boss", {})
        directional_frames = assets.directional_animation_frames.get("boss", {})
        boss_sheet = assets.sprite_sheets.get("boss")
        if boss_sheet:
            animations = build_animations_from_sheet(boss_sheet, config.BOSS_ANIMATIONS)
        else:
            animations = _fallback_boss_animations(assets)

        if folder_frames:
            animations.update(build_animations_from_frames(folder_frames, config.BOSS_ANIMATIONS))
        self.animation_manager = AnimationManager(animations, initial_state="idle", angle_step=12)
        self.directional_animations = build_directional_animations_from_frames(directional_frames, config.BOSS_ANIMATIONS)
        self.set_base_image(self.animation_manager.get_image())

    def update(self, scene, delta_time):
        self.phase = self.get_phase()
        if self.health <= 0:
            self.dead = True
            self.render_state(delta_time, "death", pygame.Vector2(0, 1))
            self.update_visual()
            return

        self.primary_timer = max(0.0, self.primary_timer - delta_time)
        self.secondary_timer = max(0.0, self.secondary_timer - delta_time)
        self.summon_timer = max(0.0, self.summon_timer - delta_time)
        self.action_timer = max(0.0, self.action_timer - delta_time)
        if self.pending_attack:
            self.attack_windup = max(0.0, self.attack_windup - delta_time)

        to_player = scene.player.pos - self.pos
        direction = safe_normalize(to_player)
        distance = to_player.length() if to_player.length_squared() > 0 else 0.0
        desired_range = self.profile.desired_range - (18 * (self.phase - 1))
        move_speed = (self.profile.move_speed + self.phase * 0.18) * config.FPS
        angle = -direction.angle_to(pygame.Vector2(1, 0))
        self.direction_token = _direction_token_from_vector(direction)

        moved = False
        if distance > desired_range:
            self.pos += direction * move_speed * delta_time
            moved = True
        elif distance < desired_range - 65:
            self.pos -= direction * (move_speed * 0.72) * delta_time
            moved = True
        else:
            strafe_speed = 0.72 * config.FPS
            self.pos += pygame.Vector2(-direction.y, direction.x) * (strafe_speed * random.choice([-1, 1]) * delta_time)
            moved = True

        radius = 44
        self.pos.x = max(scene.world_rect.left + radius, min(scene.world_rect.right - radius, self.pos.x))
        self.pos.y = max(scene.world_rect.top + radius, min(scene.world_rect.bottom - radius, self.pos.y))

        attack_state = None
        phase_pressure = 0.1 if self.profile.key == "orion_prime" and self.phase >= 3 else 0.0

        if self.pending_attack and self.attack_windup <= 0.0:
            if self.pending_attack == "primary":
                self.fire_primary(scene)
                self.primary_timer = max(0.22, 0.82 - self.phase * 0.12 - phase_pressure)
                attack_state = "attack1"
            else:
                self.fire_secondary(scene)
                self.secondary_timer = max(0.7, 2.35 - self.phase * 0.3 - phase_pressure)
                attack_state = "attack2" if self.phase < 3 else "attack3"
            self.pending_attack = None
            self.action_timer = 0.22 if attack_state == "attack1" else 0.36
        elif not self.pending_attack and self.primary_timer <= 0.0:
            self.pending_attack = "primary"
            self.attack_windup = 0.22 if self.profile.key == "orion_prime" and self.phase >= 3 else 0.24
            self.action_timer = self.attack_windup
            attack_state = "attack1"
            scene.add_burst(self.pos, self.profile.primary_color, 24)
            if getattr(scene, "audio", None):
                scene.audio.play("boss_attack", volume=0.56)
        elif not self.pending_attack and self.phase >= 2 and self.secondary_timer <= 0.0:
            self.pending_attack = "secondary"
            self.attack_windup = 0.28 if self.profile.key == "orion_prime" and self.phase >= 3 else 0.34
            self.action_timer = self.attack_windup
            attack_state = "attack2" if self.phase < 3 else "attack3"
            scene.add_burst(self.pos, self.profile.secondary_color, 30)
            if getattr(scene, "audio", None):
                scene.audio.play("boss_attack", volume=0.72)
        elif (
            not self.pending_attack
            and self.profile.summon_enabled
            and self.phase >= 2
            and self.summon_timer <= 0.0
            and len(scene.enemies) < scene.level_spec.max_enemies
        ):
            forced_type = "runner" if self.phase == 2 else "brute"
            scene.spawn_enemy(forced_type=forced_type)
            if self.profile.key == "orion_prime" and self.phase >= 3 and len(scene.enemies) < scene.level_spec.max_enemies:
                scene.spawn_enemy(forced_type="runner")
            self.summon_timer = max(2.3, self.profile.summon_cooldown - self.phase * 0.6)

        current_state = "idle"
        if self.action_timer > 0 and attack_state is not None:
            current_state = attack_state
        elif self.action_timer > 0:
            current_state = self.directional_state or self.animation_manager.state
        elif moved:
            current_state = "move"

        self.render_state(delta_time, current_state, direction, angle)
        self.update_visual()

    def render_state(self, delta_time, state, direction, angle=0.0):
        directional_bank = self.directional_animations.get(state)
        directional_anim = directional_bank.get(self.direction_token) if directional_bank else None
        if directional_anim is not None:
            if self.directional_state != state or self.last_direction_token != self.direction_token:
                directional_anim.reset()
                self.directional_state = state
                self.last_direction_token = self.direction_token
            directional_anim.update(delta_time)
            self.set_base_image(directional_anim.current_frame)
            return

        self.directional_state = None
        self.last_direction_token = self.direction_token
        self.animation_manager.switch(state, restart=False)
        self.animation_manager.update(delta_time)
        self.set_base_image(self.animation_manager.get_image(angle=angle))

    def get_phase(self):
        ratio = self.health / max(1, self.max_health)
        if self.profile.phase_count >= 3:
            if ratio <= 0.33:
                return 3
            if ratio <= 0.66:
                return 2
            return 1
        return 2 if ratio <= 0.5 else 1

    def fire_primary(self, scene):
        direction = safe_normalize(scene.player.pos - self.pos)
        if self.profile.key == "aegis_prime":
            spread_angles = [-16, -6, 6, 16] if self.phase == 1 else [-24, -12, 0, 12, 24, 36]
            for angle in spread_angles:
                scene.spawn_bullet(
                    self.pos,
                    direction.rotate(angle),
                    self.profile.primary_speed,
                    self.profile.primary_damage,
                    False,
                    self.profile.primary_color,
                )
            return

        if self.phase == 1:
            scene.spawn_bullet(self.pos, direction, self.profile.primary_speed - 1.0, self.profile.primary_damage - 3, False, self.profile.primary_color)
        elif self.phase == 2:
            for angle in [-16, -8, 0, 8, 16]:
                scene.spawn_bullet(self.pos, direction.rotate(angle), self.profile.primary_speed - 0.4, self.profile.primary_damage - 2, False, self.profile.primary_color)
        else:
            for angle in [-30, -20, -10, 0, 10, 20, 30]:
                scene.spawn_bullet(self.pos, direction.rotate(angle), self.profile.primary_speed, self.profile.primary_damage, False, self.profile.primary_color)

    def fire_secondary(self, scene):
        if self.profile.key == "aegis_prime":
            projectile_count = 10 + self.phase * 2
            for index in range(projectile_count):
                direction = make_vector_from_angle(index * (360 / projectile_count))
                scene.spawn_bullet(self.pos, direction, self.profile.secondary_speed, self.profile.secondary_damage, False, self.profile.secondary_color)
            scene.add_effect("explosion", self.pos)
            return

        if self.phase == 2:
            for index in range(10):
                scene.spawn_bullet(self.pos, make_vector_from_angle(index * 36), self.profile.secondary_speed - 0.8, self.profile.secondary_damage - 2, False, self.profile.secondary_color)
            scene.add_effect("explosion", self.pos)
        else:
            for index in range(18):
                direction = make_vector_from_angle(index * (360 / 18) + scene.frame_count * 0.7)
                scene.spawn_bullet(self.pos, direction, self.profile.secondary_speed, self.profile.secondary_damage, False, self.profile.secondary_color)
            direction = safe_normalize(scene.player.pos - self.pos)
            for angle in [-18, -9, 0, 9, 18]:
                scene.spawn_bullet(self.pos, direction.rotate(angle), self.profile.primary_speed + 1.0, self.profile.primary_damage + 1, False, (255, 108, 162))
            scene.add_effect("explosion", self.pos)

    def take_damage(self, amount):
        self.health = max(0, self.health - amount)
        self.flash(5, (255, 255, 255))
        return self.health <= 0

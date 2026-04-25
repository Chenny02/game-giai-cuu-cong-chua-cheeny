"""Hostage / princess animation handling."""

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
from ..entities import Actor


def _fallback_hostage_animations(assets):
    frame = pygame.transform.smoothscale(assets.images["hostage"], config.HOSTAGE_RENDER_SIZE)
    return {
        "idle": Animation([frame], fps=5, loop=True),
        "walk": Animation([frame], fps=6, loop=True),
        "rescued": Animation([frame], fps=6, loop=True),
        "captured": Animation([frame], fps=5, loop=True),
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


class Hostage(Actor):
    """Hostage with directional idle / walk / rescued / captured states."""

    def __init__(self, pos, assets):
        super().__init__(pos)
        self.rescued = False
        self.set_hitbox(18, 22)
        self.follow_offset = pygame.Vector2(-32, 26)
        self.pulse = 0.0
        self.direction_token = "s"
        self.last_direction_token = "s"
        self.directional_state = None

        folder_frames = assets.animation_frames.get("hostage", {})
        directional_frames = assets.directional_animation_frames.get("hostage", {})
        boss_sheet = assets.sprite_sheets.get("boss")
        if boss_sheet:
            animations = build_animations_from_sheet(boss_sheet, config.HOSTAGE_ANIMATIONS)
        else:
            animations = _fallback_hostage_animations(assets)

        if folder_frames:
            animations.update(build_animations_from_frames(folder_frames, config.HOSTAGE_ANIMATIONS))
        self.animation_manager = AnimationManager(animations, initial_state="captured", angle_step=15)
        self.directional_animations = build_directional_animations_from_frames(directional_frames, config.HOSTAGE_ANIMATIONS)
        self.set_base_image(self.animation_manager.get_image())

    def update(self, scene, delta_time):
        self.pulse = (self.pulse + delta_time * 10) % 1000
        move_amount = 0.0

        if self.rescued:
            desired = scene.player.pos + self.follow_offset.rotate(math.sin(self.pulse) * 6)
            previous_pos = pygame.Vector2(self.pos)
            delta = desired - self.pos
            follow_alpha = min(1.0, 0.18 * delta_time * config.FPS)
            candidate = self.pos + delta * follow_alpha
            self.pos = self.resolve_follow_position(scene, candidate)
            move_vector = self.pos - previous_pos
            move_amount = move_vector.length()
            if move_amount > 0.6:
                self.direction_token = _direction_token_from_vector(move_vector)
            else:
                self.direction_token = _direction_token_from_vector(scene.player.pos - self.pos)
        else:
            self.direction_token = "s"

        if self.rescued:
            state = "walk" if move_amount > 1.2 else "rescued"
        else:
            state = "captured"

        directional_bank = self.directional_animations.get(state)
        directional_anim = directional_bank.get(self.direction_token) if directional_bank else None
        if directional_anim is not None:
            if self.directional_state != state or self.last_direction_token != self.direction_token:
                directional_anim.reset()
                self.directional_state = state
                self.last_direction_token = self.direction_token
            directional_anim.update(delta_time)
            self.set_base_image(directional_anim.current_frame)
        else:
            self.directional_state = None
            self.last_direction_token = self.direction_token
            self.animation_manager.switch(state)
            self.animation_manager.update(delta_time)
            self.set_base_image(self.animation_manager.get_image())
        self.update_visual()

    def resolve_follow_position(self, scene, candidate):
        half_width = self.hitbox_size.x / 2
        half_height = self.hitbox_size.y / 2
        clamped = pygame.Vector2(
            max(scene.world_rect.left + half_width, min(scene.world_rect.right - half_width, candidate.x)),
            max(scene.world_rect.top + half_height, min(scene.world_rect.bottom - half_height, candidate.y)),
        )
        if not scene.maze:
            return clamped

        if scene.maze.is_rect_walkable(self.collision_rect(clamped)):
            return clamped

        axis_candidate = pygame.Vector2(self.pos)
        axis_candidate.x = clamped.x
        if scene.maze.is_rect_walkable(self.collision_rect(axis_candidate)):
            fallback = pygame.Vector2(axis_candidate)
        else:
            fallback = pygame.Vector2(self.pos)

        axis_candidate = pygame.Vector2(fallback)
        axis_candidate.y = clamped.y
        if scene.maze.is_rect_walkable(self.collision_rect(axis_candidate)):
            return axis_candidate

        if scene.maze.is_rect_walkable(self.collision_rect(fallback)):
            return fallback

        nearest_cell = scene.maze.find_nearest_walkable_cell(scene.maze.world_to_cell(clamped))
        if nearest_cell is not None:
            return pygame.Vector2(scene.maze.cell_to_world(nearest_cell))
        return pygame.Vector2(self.pos)

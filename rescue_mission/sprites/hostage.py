"""Hostage / princess animated bằng boss sprite sheet."""

import math

import pygame

from .. import config
from ..core.animation import Animation, AnimationManager, build_animations_from_frames, build_animations_from_sheet
from ..entities import Actor


def _fallback_hostage_animations(assets):
    frame = pygame.transform.smoothscale(assets.images["hostage"], config.HOSTAGE_RENDER_SIZE)
    return {
        "idle": Animation([frame], fps=5, loop=True),
        "walk": Animation([frame], fps=6, loop=True),
        "rescued": Animation([frame], fps=6, loop=True),
        "captured": Animation([frame], fps=5, loop=True),
    }


class Hostage(Actor):
    """Hostage có các trạng thái idle, walk, rescued, captured."""

    def __init__(self, pos, assets):
        super().__init__(pos)
        self.rescued = False
        self.set_hitbox(18, 22)
        self.follow_offset = pygame.Vector2(-32, 26)
        self.pulse = 0.0

        folder_frames = assets.animation_frames.get("hostage", {})
        boss_sheet = assets.sprite_sheets.get("boss")
        if boss_sheet:
            animations = build_animations_from_sheet(boss_sheet, config.HOSTAGE_ANIMATIONS)
        else:
            animations = _fallback_hostage_animations(assets)

        if folder_frames:
            animations.update(build_animations_from_frames(folder_frames, config.HOSTAGE_ANIMATIONS))
        self.animation_manager = AnimationManager(animations, initial_state="captured", angle_step=15)
        self.set_base_image(self.animation_manager.get_image())

    def update(self, scene, delta_time):
        self.pulse = (self.pulse + delta_time * 10) % 1000
        move_amount = 0.0

        if self.rescued:
            desired = scene.player.pos + self.follow_offset.rotate(math.sin(self.pulse) * 6)
            delta = desired - self.pos
            move_amount = delta.length()
            self.pos += delta * 0.18

        if self.rescued:
            state = "walk" if move_amount > 1.2 else "rescued"
        else:
            state = "captured"

        self.animation_manager.switch(state)
        self.animation_manager.update(delta_time)
        self.set_base_image(self.animation_manager.get_image())
        self.update_visual()

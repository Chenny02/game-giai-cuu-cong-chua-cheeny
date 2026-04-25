"""Cute rabbit companion used by the emyeutho easter egg."""

import math

import pygame

from ..entities import Actor


class LoveRabbitCompanion(Actor):
    def __init__(self, pos, assets):
        super().__init__(pos)
        self.set_hitbox(18, 24)
        self.set_base_image(assets.images["rabbit_companion"])
        self.phase = 0.0
        self.anchor_offset = pygame.Vector2(64, -30)

    def update(self, scene, delta_time):
        self.phase = (self.phase + delta_time * 5.0) % 1000
        bob = math.sin(self.phase * 1.4) * 8
        sway = math.cos(self.phase * 0.7) * 6
        target = scene.player.pos + self.anchor_offset + pygame.Vector2(sway, bob)
        lerp = min(1.0, 0.14 * delta_time * 60)
        self.pos += (target - self.pos) * lerp
        self.update_visual()

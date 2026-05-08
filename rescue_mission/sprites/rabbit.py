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
        self.fire_timer = 2.0
        self.fire_interval = 2.2

    def update(self, scene, delta_time):
        self.phase = (self.phase + delta_time * 5.0) % 1000
        bob = math.sin(self.phase * 1.4) * 8
        sway = math.cos(self.phase * 0.7) * 6
        target = scene.player.pos + self.anchor_offset + pygame.Vector2(sway, bob)
        lerp = min(1.0, 0.14 * delta_time * 60)
        self.pos += (target - self.pos) * lerp
        
        # Tính năng mới: Tự động bắn tim vào kẻ địch gần nhất
        self.fire_timer -= delta_time
        if self.fire_timer <= 0:
            nearest_enemy = None
            min_dist = 400
            for enemy in scene.enemies:
                dist = self.pos.distance_to(enemy.pos)
                if dist < min_dist:
                    min_dist = dist
                    nearest_enemy = enemy
            
            if nearest_enemy:
                direction = (nearest_enemy.pos - self.pos).normalize()
                # Bắn đạn hình trái tim (màu hồng)
                scene.spawn_bullet(
                    origin=self.pos,
                    direction=direction,
                    speed=7.5,
                    damage=15,
                    friendly=True,
                    color=(255, 100, 180) # Màu hồng của thỏ
                )
                self.fire_timer = self.fire_interval

        self.update_visual()

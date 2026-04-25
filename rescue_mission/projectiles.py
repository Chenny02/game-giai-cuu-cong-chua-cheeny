import pygame

from . import config
from .entities import Bullet, safe_normalize


class EnergyProjectile(Bullet):
    """Heavy player skill projectile with larger hit area and impact burst."""

    def __init__(self, origin, direction):
        super().__init__(
            origin=origin,
            direction=safe_normalize(direction),
            speed=config.PLAYER_SKILL_SPEED,
            damage=config.PLAYER_SKILL_DAMAGE,
            friendly=True,
            color=config.COLOR_SKILL,
            lifetime=int(config.PLAYER_SKILL_LIFETIME * config.FPS),
        )
        self.radius = 10
        self.knockback = config.PLAYER_SKILL_KNOCKBACK
        self.image = self._build_image()
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def _build_image(self):
        size = self.radius * 2 + 14
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        for halo_radius, alpha in ((self.radius + 8, 55), (self.radius + 4, 110)):
            pygame.draw.circle(surface, (*config.COLOR_SKILL, alpha), (center, center), halo_radius)
        pygame.draw.circle(surface, (214, 250, 255), (center, center), self.radius + 1)
        pygame.draw.circle(surface, config.COLOR_SKILL, (center, center), self.radius - 2)
        return surface

    def update(self, scene, delta_time):
        previous_pos = pygame.Vector2(self.pos)
        super().update(scene, delta_time)
        if not self.alive():
            return

        direction = self.pos - previous_pos
        if direction.length_squared() > 0:
            trail_pos = self.pos - direction * 0.35
            scene.add_burst(trail_pos, config.COLOR_SKILL, 4)

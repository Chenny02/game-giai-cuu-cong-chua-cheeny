from dataclasses import dataclass

import pygame

from . import config
from .projectiles import EnergyProjectile


@dataclass(frozen=True)
class SkillSnapshot:
    energy: float
    max_energy: float
    cooldown_left: float
    cooldown_total: float

    @property
    def ready(self):
        return self.cooldown_left <= 0.0 and self.energy >= config.PLAYER_SKILL_ENERGY_COST

    @property
    def energy_ratio(self):
        if self.max_energy <= 0:
            return 0.0
        return max(0.0, min(1.0, self.energy / self.max_energy))

    @property
    def cooldown_ratio(self):
        if self.cooldown_total <= 0:
            return 1.0
        return 1.0 - max(0.0, min(1.0, self.cooldown_left / self.cooldown_total))


class PlayerSkillController:
    """Minimal skill controller: energy, cooldown, and projectile spawn."""

    def __init__(self):
        self.energy = float(config.PLAYER_SKILL_ENERGY_MAX)
        self.cooldown_left = 0.0

    def update(self, delta_time):
        self.cooldown_left = max(0.0, self.cooldown_left - delta_time)
        self.energy = min(
            float(config.PLAYER_SKILL_ENERGY_MAX),
            self.energy + config.PLAYER_SKILL_ENERGY_REGEN * delta_time,
        )

    def snapshot(self):
        return SkillSnapshot(
            energy=self.energy,
            max_energy=float(config.PLAYER_SKILL_ENERGY_MAX),
            cooldown_left=self.cooldown_left,
            cooldown_total=float(config.PLAYER_SKILL_COOLDOWN),
        )

    def can_cast(self):
        return self.cooldown_left <= 0.0 and self.energy >= config.PLAYER_SKILL_ENERGY_COST

    def try_cast(self, player, scene, direction):
        direction = pygame.Vector2(direction)
        if direction.length_squared() <= 0:
            direction = pygame.Vector2(1, 0)
        if not self.can_cast():
            return False

        self.energy -= config.PLAYER_SKILL_ENERGY_COST
        self.cooldown_left = float(config.PLAYER_SKILL_COOLDOWN)
        projectile = EnergyProjectile(player.pos + direction.normalize() * 26, direction)
        scene.skill_projectiles.add(projectile)
        scene.add_burst(projectile.pos, config.COLOR_SKILL, 16)
        scene.add_effect("explosion", projectile.pos)
        scene.push_status_message("Energy Shot đã kích hoạt", 0.55)
        if getattr(scene, "audio", None):
            scene.audio.play("skill_cast", volume=0.78)
        return True

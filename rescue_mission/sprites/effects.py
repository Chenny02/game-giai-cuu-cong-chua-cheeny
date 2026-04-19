"""Effect animation chạy 1 lần rồi tự huỷ."""

import pygame

from .. import config
from ..core.animation import Animation, AnimationManager, build_animations_from_frames, build_animations_from_sheet


def _fallback_effect_frames(color, size, count):
    frames = []
    for index in range(count):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        radius = max(4, int((index + 1) / count * min(size) * 0.45))
        pygame.draw.circle(surface, (*color, 180), (size[0] // 2, size[1] // 2), radius, width=2)
        frames.append(surface)
    return frames


class Effect(pygame.sprite.Sprite):
    """Hiệu ứng frame-based như hit, nổ, đầu đạn."""

    def __init__(self, pos, animations, state, angle=0.0):
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.angle = angle

        # Mỗi effect giữ bản Animation riêng để không dùng chung index với effect khác.
        animation_copies = {
            name: Animation(animation.frames, fps=animation.fps, loop=animation.loop)
            for name, animation in animations.items()
        }
        self.animations = AnimationManager(animation_copies, initial_state=state, angle_step=12)
        self.image = self.animations.get_image(angle=self.angle)
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def update(self, delta_time):
        self.animations.update(delta_time)
        self.image = self.animations.get_image(angle=self.angle)
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))
        if self.animations.current.finished and not self.animations.current.loop:
            self.kill()


def build_effect_animations(assets):
    """Tạo bank animation cho effect.

    Ưu tiên frame rời trong thư mục trước, sau đó mới đến atlas cũ.
    """

    sheet = assets.sprite_sheets.get("boss")
    if sheet:
        animations = build_animations_from_sheet(sheet, config.EFFECT_ANIMATIONS)
    else:
        animations = {
        "bullet": Animation(_fallback_effect_frames((255, 235, 170), (28, 28), 4), fps=18, loop=False),
        "hit": Animation(_fallback_effect_frames((255, 110, 140), config.EFFECT_RENDER_SIZE, 4), fps=20, loop=False),
        "explosion": Animation(_fallback_effect_frames((255, 196, 120), (72, 72), 6), fps=16, loop=False),
        }

    folder_frames = assets.animation_frames.get("effects", {})
    if folder_frames:
        animations.update(build_animations_from_frames(folder_frames, config.EFFECT_ANIMATIONS))
    return animations

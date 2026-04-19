"""UI tối giản cho game.

Ý tưởng giao diện:
- Giữ phần chơi là trung tâm, UI chỉ đóng vai trò hỗ trợ.
- Bỏ bớt mô tả dài dòng; thông tin quan trọng phải đọc được trong 1-2 giây.
- Cùng một ngôn ngữ tạo hình được dùng lại cho menu, HUD và overlay để game đồng bộ hơn.
"""

import math
from dataclasses import dataclass

import pygame

from . import config


@dataclass
class Button:
    """Button đơn giản cho menu chính."""

    rect: pygame.Rect
    label: str
    subtitle: str

    def hovered(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


def draw_glass_panel(surface, rect):
    """Panel nền mờ để nổi thông tin lên mà vẫn giữ được background."""

    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (*config.COLOR_PANEL, 215), panel.get_rect(), border_radius=18)
    pygame.draw.rect(panel, (*config.COLOR_BORDER, 160), panel.get_rect(), width=2, border_radius=18)
    surface.blit(panel, rect.topleft)


def draw_menu(surface, assets, buttons, mouse_pos, total_score, pulse):
    """Menu tối giản: tiêu đề, thông tin ngắn, 2 nút rõ ràng."""

    surface.blit(assets.menu_background, (0, 0))

    title_y = 108 + int(math.sin(pulse / 18) * 4)
    shadow = assets.font_title.render(config.GAME_TITLE_MAIN, True, config.COLOR_SHADOW)
    title = assets.font_title.render(config.GAME_TITLE_MAIN, True, config.COLOR_TEXT)
    subtitle = assets.font_body.render(config.GAME_TITLE_SUBTITLE, True, config.COLOR_SUBTEXT)
    story_1 = assets.font_body.render(
        f"{config.PLAYER_NAME} tiến vào lâu đài để giải cứu công chúa {config.HOSTAGE_NAME}.",
        True,
        config.COLOR_SUBTEXT,
    )
    story_2 = assets.font_body.render(
        f"{config.BOSS_NAME} đang điều khiển bóng tối và toàn bộ quái vật.",
        True,
        config.COLOR_SUBTEXT,
    )
    hint = assets.font_body.render("WASD di chuyển, chuột để bắn, F11 phóng to", True, config.COLOR_SUBTEXT)
    score_text = assets.font_small.render(f"Điểm cao: {total_score}", True, config.COLOR_ACCENT)

    surface.blit(shadow, (58, title_y + 6))
    surface.blit(title, (52, title_y))
    surface.blit(subtitle, (56, title_y + 74))
    surface.blit(story_1, (56, title_y + 112))
    surface.blit(story_2, (56, title_y + 140))
    surface.blit(hint, (56, title_y + 168))
    surface.blit(score_text, (56, title_y + 198))

    for button in buttons:
        draw_button(surface, assets, button, button.hovered(mouse_pos))

    tip = assets.font_small.render("Nhấn chuột để chọn.", True, config.COLOR_SUBTEXT)
    surface.blit(tip, (72, config.SCREEN_HEIGHT - 42))


def draw_button(surface, assets, button, hovered):
    """Nút menu được vẽ rõ, gọn và có hover nhẹ để tránh rối mắt."""

    panel = pygame.Surface(button.rect.size, pygame.SRCALPHA)
    base = config.COLOR_PANEL_ALT if hovered else config.COLOR_PANEL
    border = config.COLOR_ACCENT if hovered else config.COLOR_BORDER
    pygame.draw.rect(panel, (*base, 235), panel.get_rect(), border_radius=18)
    pygame.draw.rect(panel, (*border, 255), panel.get_rect(), width=2, border_radius=18)
    if hovered:
        pygame.draw.rect(panel, (*config.COLOR_ACCENT, 30), panel.get_rect().inflate(-6, -6), border_radius=14)
    surface.blit(panel, button.rect.topleft)

    label = assets.font_h1.render(button.label, True, config.COLOR_TEXT)
    subtitle = assets.font_small.render(button.subtitle, True, config.COLOR_SUBTEXT)
    surface.blit(label, (button.rect.x + 22, button.rect.y + 14))
    surface.blit(subtitle, (button.rect.x + 24, button.rect.y + 54))


def draw_hud(surface, assets, scene, next_upgrade_text, mouse_pos):
    """HUD tối giản.

    Chỉ giữ 4 nhóm thông tin:
    - Màn đang chơi
    - Máu và thời gian
    - Mục tiêu hiện tại
    - Điểm và minimap

    Chuỗi `next_upgrade_text` vẫn được truyền vào để giữ giao diện hàm ổn định,
    nhưng bản HUD tối giản không còn hiển thị nó để màn hình sạch hơn.
    """

    del next_upgrade_text

    header = pygame.Rect(18, 14, 760, 82)
    draw_glass_panel(surface, header)

    stage_text = assets.font_h2.render(f"Màn {scene.level_spec.number}", True, config.COLOR_TEXT)
    stage_name = assets.font_small.render(scene.level_spec.title, True, config.COLOR_SUBTEXT)
    briefing = assets.font_small.render(scene.level_spec.description, True, config.COLOR_SUBTEXT)
    surface.blit(stage_text, (32, 18))
    surface.blit(stage_name, (118, 24))
    surface.blit(briefing, (32, 50))

    draw_health_bar(surface, assets, scene.player.health, scene.player.max_health, pygame.Rect(248, 22, 170, 14), config.PLAYER_NAME)
    draw_timer_bar(
        surface,
        assets,
        scene.time_left / (scene.level_spec.time_limit * config.FPS),
        pygame.Rect(248, 43, 170, 8),
        max(0, scene.time_left // config.FPS),
    )

    if scene.boss and scene.boss.health > 0 and not scene.hostage.rescued:
        objective = f"Cứu {config.HOSTAGE_NAME} + hạ {config.BOSS_NAME}"
        objective_color = config.COLOR_WARNING
    elif scene.boss and scene.boss.health > 0:
        objective = f"Hạ {config.BOSS_NAME}"
        objective_color = config.COLOR_DANGER
    elif not scene.hostage.rescued:
        objective = f"Cứu {config.HOSTAGE_NAME}"
        objective_color = config.COLOR_WARNING
    else:
        objective = f"{config.HOSTAGE_NAME} an toàn"
        objective_color = config.COLOR_ACCENT
    objective_text = assets.font_small.render(objective, True, objective_color)
    surface.blit(objective_text, (452, 24))

    if scene.boss and scene.boss.health > 0:
        draw_health_bar(surface, assets, scene.boss.health, scene.boss.max_health, pygame.Rect(540, 24, 150, 12), config.BOSS_NAME)

    score = assets.font_h2.render(f"Điểm {scene.score}", True, config.COLOR_TEXT)
    surface.blit(score, (708, 18))

    draw_minimap(surface, assets, scene, pygame.Rect(config.SCREEN_WIDTH - 136, 14, 118, 118))
    draw_crosshair(surface, mouse_pos, scene.player.fire_timer == 0)


def draw_health_bar(surface, assets, value, maximum, rect, label):
    """Thanh máu chung cho player và boss để UI nhất quán và dễ mở rộng."""

    pygame.draw.rect(surface, (*config.COLOR_PANEL_ALT, 255), rect, border_radius=10)
    pygame.draw.rect(surface, (*config.COLOR_BORDER, 180), rect, width=2, border_radius=10)
    ratio = 0 if maximum <= 0 else max(0.0, min(1.0, value / maximum))
    fill_rect = rect.copy()
    fill_rect.width = max(8, int(rect.width * ratio))
    fill_color = config.COLOR_ACCENT if ratio > 0.45 else config.COLOR_WARNING if ratio > 0.2 else config.COLOR_DANGER
    pygame.draw.rect(surface, fill_color, fill_rect, border_radius=10)

    label_surf = assets.font_small.render(label, True, config.COLOR_TEXT)
    value_surf = assets.font_small.render(f"{int(value)}/{int(maximum)}", True, config.COLOR_TEXT)
    surface.blit(label_surf, (rect.x, rect.y - 18))
    surface.blit(value_surf, (rect.right - value_surf.get_width(), rect.y - 18))


def draw_timer_bar(surface, assets, ratio, rect, seconds_left):
    """Dòng thời gian được nén thành 1 thanh ngắn để tiết kiệm diện tích."""

    pygame.draw.rect(surface, (*config.COLOR_PANEL_ALT, 255), rect, border_radius=8)
    pygame.draw.rect(surface, (*config.COLOR_BORDER, 180), rect, width=1, border_radius=8)
    fill = rect.copy()
    fill.width = max(6, int(rect.width * max(0.0, min(1.0, ratio))))
    pygame.draw.rect(surface, config.COLOR_WARNING, fill, border_radius=8)

    minutes = seconds_left // 60
    seconds = seconds_left % 60
    timer_label = assets.font_small.render(f"{minutes:02d}:{seconds:02d}", True, config.COLOR_TEXT)
    surface.blit(timer_label, (rect.right + 8, rect.y - 8))


def draw_minimap(surface, assets, scene, rect):
    """Minimap nhỏ chỉ để định hướng, không có tham vọng thay thế world view."""

    draw_glass_panel(surface, rect)
    inner = rect.inflate(-10, -10)
    pygame.draw.rect(surface, (6, 12, 22), inner, border_radius=12)

    if scene.maze:
        mini = pygame.transform.smoothscale(scene.maze.minimap_surface, inner.size)
        surface.blit(mini, inner.topleft)
        draw_minimap_point(surface, inner, scene.maze.width, scene.maze.height, scene.maze.world_to_cell(scene.player.pos), (88, 197, 255))
        if not scene.hostage.rescued:
            draw_minimap_point(surface, inner, scene.maze.width, scene.maze.height, scene.maze.world_to_cell(scene.hostage.pos), config.COLOR_WARNING)
        for enemy in list(scene.enemies)[:10]:
            draw_minimap_point(surface, inner, scene.maze.width, scene.maze.height, scene.maze.world_to_cell(enemy.pos), config.COLOR_DANGER)
    else:
        pygame.draw.rect(surface, (18, 34, 56), inner, border_radius=12)
        pygame.draw.rect(surface, (*config.COLOR_BORDER, 100), inner, width=1, border_radius=12)
        draw_world_point(surface, inner, scene.world_rect, scene.player.pos, (88, 197, 255))
        if not scene.hostage.rescued:
            draw_world_point(surface, inner, scene.world_rect, scene.hostage.pos, config.COLOR_WARNING)
        for enemy in list(scene.enemies)[:12]:
            draw_world_point(surface, inner, scene.world_rect, enemy.pos, config.COLOR_DANGER)
        if scene.boss and scene.boss.health > 0:
            draw_world_point(surface, inner, scene.world_rect, scene.boss.pos, (194, 63, 255), radius=5)

    label = assets.font_small.render("Bản đồ", True, config.COLOR_TEXT)
    surface.blit(label, (rect.x + 10, rect.y - 18))


def draw_world_point(surface, rect, world_rect, position, color, radius=4):
    """Chuyển tọa độ world sang minimap cho các màn không dùng maze."""

    px = rect.x + (position.x - world_rect.left) / world_rect.width * rect.width
    py = rect.y + (position.y - world_rect.top) / world_rect.height * rect.height
    pygame.draw.circle(surface, color, (int(px), int(py)), radius)


def draw_minimap_point(surface, rect, maze_width, maze_height, cell, color):
    """Chuyển tọa độ ô grid sang minimap cho màn mê cung."""

    px = rect.x + (cell[0] / max(1, maze_width - 1)) * rect.width
    py = rect.y + (cell[1] / max(1, maze_height - 1)) * rect.height
    pygame.draw.circle(surface, color, (int(px), int(py)), 3)


def draw_crosshair(surface, mouse_pos, ready):
    """Crosshair đổi màu theo cooldown để thấy nhịp bắn mà không cần text."""

    color = config.COLOR_ACCENT if ready else config.COLOR_WARNING
    x, y = mouse_pos
    pygame.draw.circle(surface, color, (x, y), 10, width=1)
    pygame.draw.line(surface, color, (x - 16, y), (x - 4, y), 1)
    pygame.draw.line(surface, color, (x + 4, y), (x + 16, y), 1)
    pygame.draw.line(surface, color, (x, y - 16), (x, y - 4), 1)
    pygame.draw.line(surface, color, (x, y + 4), (x, y + 16), 1)


def draw_overlay(surface, assets, title, subtitle, footer, accent_color):
    """Overlay kết thúc màn/thất bại theo hướng ngắn gọn, đọc nhanh."""

    veil = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
    veil.fill((4, 8, 18, 180))
    surface.blit(veil, (0, 0))

    card = pygame.Rect(config.SCREEN_WIDTH // 2 - 210, config.SCREEN_HEIGHT // 2 - 96, 420, 192)
    draw_glass_panel(surface, card)
    pygame.draw.rect(surface, accent_color, card.inflate(-18, -18), width=2, border_radius=18)

    title_surf = assets.font_title.render(title, True, config.COLOR_TEXT)
    subtitle_surf = assets.font_h2.render(subtitle, True, config.COLOR_SUBTEXT)
    footer_surf = assets.font_body.render(footer, True, accent_color)

    surface.blit(title_surf, (card.centerx - title_surf.get_width() // 2, card.y + 24))
    surface.blit(subtitle_surf, (card.centerx - subtitle_surf.get_width() // 2, card.y + 92))
    surface.blit(footer_surf, (card.centerx - footer_surf.get_width() // 2, card.y + 132))


def wrap_text(font, text, max_width):
    """Tách text dài thành nhiều dòng để card hội thoại không bị tràn ngang."""

    lines = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue

        current_line = words[0]
        for word in words[1:]:
            candidate = f"{current_line} {word}"
            if font.size(candidate)[0] <= max_width:
                current_line = candidate
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
    return lines


def draw_dialogue(surface, assets, title, speaker, text, accent_color, page_index, page_total, footer, subtitle=""):
    """Card hội thoại nhiều trang cho intro, giữa màn và kết thúc."""

    veil = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
    veil.fill((4, 8, 18, 192))
    surface.blit(veil, (0, 0))

    card = pygame.Rect(config.SCREEN_WIDTH // 2 - 430, config.SCREEN_HEIGHT // 2 - 146, 860, 292)
    draw_glass_panel(surface, card)
    pygame.draw.rect(surface, accent_color, card.inflate(-16, -16), width=2, border_radius=20)

    title_surf = assets.font_h1.render(title, True, config.COLOR_TEXT)
    surface.blit(title_surf, (card.x + 28, card.y + 24))

    if subtitle:
        subtitle_surf = assets.font_small.render(subtitle, True, config.COLOR_SUBTEXT)
        surface.blit(subtitle_surf, (card.x + 30, card.y + 66))

    page_surf = assets.font_small.render(f"{page_index}/{page_total}", True, config.COLOR_SUBTEXT)
    surface.blit(page_surf, (card.right - page_surf.get_width() - 28, card.y + 28))

    speaker_tag = pygame.Rect(card.x + 30, card.y + 104, 180, 34)
    pygame.draw.rect(surface, (*accent_color, 55), speaker_tag, border_radius=16)
    pygame.draw.rect(surface, accent_color, speaker_tag, width=1, border_radius=16)
    speaker_surf = assets.font_h2.render(speaker, True, config.COLOR_TEXT)
    surface.blit(
        speaker_surf,
        (
            speaker_tag.centerx - speaker_surf.get_width() // 2,
            speaker_tag.centery - speaker_surf.get_height() // 2 - 1,
        ),
    )

    text_lines = wrap_text(assets.font_body, text, card.width - 60)
    text_y = card.y + 154
    for line in text_lines:
        line_surf = assets.font_body.render(line, True, config.COLOR_TEXT)
        surface.blit(line_surf, (card.x + 30, text_y))
        text_y += 28

    footer_surf = assets.font_small.render(footer, True, accent_color)
    surface.blit(footer_surf, (card.x + 30, card.bottom - 34))

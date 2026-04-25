"""UI helpers for menu, HUD, and overlays."""

import math
from dataclasses import dataclass

import pygame

from . import config


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    subtitle: str = ""
    enabled: bool = True
    variant: str = "default"
    icon: str = ""

    def hovered(self, mouse_pos):
        return self.enabled and self.rect.collidepoint(mouse_pos)


def draw_glass_panel(surface, rect):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (*config.COLOR_PANEL, 215), panel.get_rect(), border_radius=18)
    pygame.draw.rect(panel, (*config.COLOR_BORDER, 160), panel.get_rect(), width=2, border_radius=18)
    surface.blit(panel, rect.topleft)


def pick_font_that_fits(text, fonts, max_width):
    for font in fonts:
        if font.size(text)[0] <= max_width:
            return font
    return fonts[-1]


def draw_cut_panel(surface, rect, fill, border, alpha=220, width=2, cut=18, glow=None):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    local = panel.get_rect()
    points = [
        (cut, 0),
        (local.width - cut, 0),
        (local.width, cut),
        (local.width, local.height - cut),
        (local.width - cut, local.height),
        (cut, local.height),
        (0, local.height - cut),
        (0, cut),
    ]
    pygame.draw.polygon(panel, (*fill, alpha), points)
    pygame.draw.polygon(panel, border, points, width)
    if glow is not None:
        inner = [
            (cut + 8, 8),
            (local.width - cut - 8, 8),
            (local.width - 8, cut + 8),
            (local.width - 8, local.height - cut - 8),
            (local.width - cut - 8, local.height - 8),
            (cut + 8, local.height - 8),
            (8, local.height - cut - 8),
            (8, cut + 8),
        ]
        pygame.draw.polygon(panel, (*glow, 28), inner)
    surface.blit(panel, rect.topleft)


def draw_menu_icon(surface, icon_name, rect, color):
    cx, cy = rect.center
    if icon_name == "diamond":
        points = [(cx, rect.top + 2), (rect.right - 2, cy), (cx, rect.bottom - 2), (rect.left + 2, cy)]
        pygame.draw.polygon(surface, color, points, 2)
        pygame.draw.line(surface, color, (cx, rect.top + 2), (cx, rect.bottom - 2), 1)
    elif icon_name == "gear":
        pygame.draw.circle(surface, color, (cx, cy), min(rect.width, rect.height) // 3, 2)
        for angle in range(0, 360, 45):
            vx = math.cos(math.radians(angle))
            vy = math.sin(math.radians(angle))
            pygame.draw.line(surface, color, (cx + vx * 10, cy + vy * 10), (cx + vx * 16, cy + vy * 16), 2)
    elif icon_name == "trophy":
        cup = pygame.Rect(0, 0, 18, 16)
        cup.center = (cx, cy - 2)
        pygame.draw.rect(surface, color, cup, 2, border_radius=4)
        pygame.draw.arc(surface, color, cup.inflate(10, 2), math.pi / 2, math.pi * 1.5, 2)
        pygame.draw.arc(surface, color, cup.inflate(10, 2), -math.pi / 2, math.pi / 2, 2)
        pygame.draw.line(surface, color, (cx, cup.bottom), (cx, cup.bottom + 8), 2)
        pygame.draw.line(surface, color, (cx - 8, cup.bottom + 8), (cx + 8, cup.bottom + 8), 2)
    elif icon_name == "start":
        pygame.draw.circle(surface, color, (cx, cy), 16, 2)
        pygame.draw.circle(surface, color, (cx, cy), 3)
        pygame.draw.line(surface, color, (cx - 22, cy), (cx - 8, cy), 2)
        pygame.draw.line(surface, color, (cx + 8, cy), (cx + 22, cy), 2)
    elif icon_name == "play":
        points = [(rect.left + 8, rect.top + 5), (rect.right - 6, cy), (rect.left + 8, rect.bottom - 5)]
        pygame.draw.polygon(surface, color, points, 2)
    elif icon_name == "grid":
        for row in range(2):
            for col in range(2):
                cell = pygame.Rect(rect.x + col * 11 + 3, rect.y + row * 11 + 3, 8, 8)
                pygame.draw.rect(surface, color, cell, 2)
    elif icon_name == "exit":
        door = pygame.Rect(rect.x + 4, rect.y + 3, 15, 22)
        pygame.draw.rect(surface, color, door, 2)
        pygame.draw.line(surface, color, (rect.centerx - 2, cy), (rect.right + 2, cy), 2)
        pygame.draw.line(surface, color, (rect.right - 6, cy - 5), (rect.right + 2, cy), 2)
        pygame.draw.line(surface, color, (rect.right - 6, cy + 5), (rect.right + 2, cy), 2)


def draw_menu_button(surface, assets, button, hovered):
    colors = {
        "primary": ((24, 112, 178), (104, 239, 255), (214, 249, 255), (120, 238, 255)),
        "danger": ((74, 22, 38), (255, 108, 132), config.COLOR_TEXT, (255, 108, 132)),
        "default": ((10, 20, 40), (80, 135, 224), config.COLOR_TEXT, (70, 165, 255)),
    }
    fill, border, text_color, glow = colors.get(button.variant, colors["default"])
    if not button.enabled:
        fill = (20, 26, 38)
        border = (76, 86, 110)
        text_color = (122, 132, 150)
        glow = None
    elif hovered:
        fill = tuple(min(255, channel + 16) for channel in fill)

    draw_cut_panel(surface, button.rect, fill, border, alpha=238 if button.enabled else 188, glow=glow)

    icon_rect = pygame.Rect(button.rect.x + 18, button.rect.centery - 16, 32, 32)
    if button.icon:
        draw_menu_icon(surface, button.icon, icon_rect, text_color)

    label_fonts = [assets.font_h1, assets.font_h2] if button.rect.height >= 70 else [assets.font_h2, assets.font_body]
    label_font = pick_font_that_fits(button.label, label_fonts, button.rect.width - 96)
    label = label_font.render(button.label, True, text_color)
    label_x = button.rect.x + 62 if button.icon else button.rect.x + 22
    label_y = button.rect.y + (10 if button.subtitle else button.rect.height // 2 - label.get_height() // 2)
    surface.blit(label, (label_x, label_y))

    if button.subtitle:
        subtitle_color = config.COLOR_SUBTEXT if button.enabled else (102, 110, 126)
        subtitle = assets.font_small.render(button.subtitle, True, subtitle_color)
        surface.blit(subtitle, (label_x + 2, button.rect.bottom - 24))


def draw_character_plate(surface, assets, rect, accent, name, subtitle, portrait, glow_surface, pulse, align="center"):
    wobble = int(math.sin(pulse / 22) * 4)
    glow_rect = glow_surface.get_rect(midbottom=(rect.centerx, rect.bottom - 8 + wobble))
    if align == "left":
        glow_rect.midbottom = (rect.left + rect.width // 2, rect.bottom - 8 + wobble)
    elif align == "right":
        glow_rect.midbottom = (rect.right - rect.width // 2, rect.bottom - 8 + wobble)
    surface.blit(glow_surface, glow_rect)

    portrait_rect = portrait.get_rect(midbottom=(rect.centerx, rect.bottom + wobble))
    if align == "left":
        portrait_rect.midbottom = (rect.left + rect.width // 2 - 4, rect.bottom + wobble)
    elif align == "right":
        portrait_rect.midbottom = (rect.right - rect.width // 2 + 4, rect.bottom + wobble)
    surface.blit(portrait, portrait_rect)

    tag = pygame.Rect(rect.x + 18, rect.bottom - 78, rect.width - 36, 72)
    draw_cut_panel(surface, tag, (10, 18, 34), accent, alpha=230, cut=14, glow=accent)
    name_font = pick_font_that_fits(name, [assets.font_menu_title, assets.font_h1, assets.font_h2], tag.width - 18)
    name_surf = name_font.render(name, True, accent)
    subtitle_surf = assets.font_small.render(subtitle, True, config.COLOR_TEXT)
    name_y = tag.y + 8 if name_font != assets.font_h2 else tag.y + 14
    subtitle_y = tag.bottom - 24
    surface.blit(name_surf, (tag.centerx - name_surf.get_width() // 2, name_y))
    surface.blit(subtitle_surf, (tag.centerx - subtitle_surf.get_width() // 2, subtitle_y))


def draw_menu(surface, assets, buttons, mouse_pos, total_score, pulse):
    surface.blit(assets.menu_background, (0, 0))
    surface.blit(assets.menu_frame_overlay, (0, 0))

    score_rect = pygame.Rect(38, 34, 226, 86)
    draw_cut_panel(surface, score_rect, (10, 18, 38), config.COLOR_BORDER, alpha=228, glow=config.COLOR_BORDER)
    draw_menu_icon(surface, "diamond", pygame.Rect(score_rect.x + 16, score_rect.y + 24, 32, 32), config.COLOR_ACCENT)
    score_title = assets.font_menu_panel.render("ĐIỂM CAO", True, config.COLOR_TEXT)
    score_value = assets.font_h1.render(str(total_score), True, config.COLOR_WARNING)
    surface.blit(score_title, (score_rect.x + 54, score_rect.y + 16))
    surface.blit(score_value, (score_rect.x + 124, score_rect.y + 40))

    utility_specs = [
        (pygame.Rect(config.SCREEN_WIDTH - 180, 34, 62, 62), "gear", ""),
        (pygame.Rect(config.SCREEN_WIDTH - 104, 34, 62, 62), "trophy", ""),
    ]
    for rect, icon, label in utility_specs:
        draw_cut_panel(surface, rect, (10, 18, 38), config.COLOR_BORDER, alpha=220)
        draw_menu_icon(surface, icon, rect.inflate(-18, -18), config.COLOR_TEXT)
        if label:
            text = assets.font_small.render(label, True, config.COLOR_SUBTEXT)
            surface.blit(text, (rect.centerx - text.get_width() // 2, rect.bottom + 4))

    title_y = 72 + int(math.sin(pulse / 18) * 5)
    crown = [(592, title_y - 14), (604, title_y - 34), (620, title_y - 18), (636, title_y - 42), (652, title_y - 18), (666, title_y - 34), (680, title_y - 14)]
    pygame.draw.polygon(surface, config.COLOR_WARNING, crown)
    pygame.draw.polygon(surface, (90, 58, 18), crown, 2)

    rescue_shadow = assets.font_menu_hero.render("GIẢI CỨU", True, config.COLOR_SHADOW)
    rescue_title = assets.font_menu_hero.render("GIẢI CỨU", True, config.COLOR_TEXT)
    mission_shadow = assets.font_menu_hero.render("CÔNG CHÚA", True, config.COLOR_SHADOW)
    mission_title = assets.font_menu_hero.render("CÔNG CHÚA", True, config.COLOR_WARNING)
    surface.blit(rescue_shadow, (362, title_y + 6))
    surface.blit(rescue_title, (356, title_y))
    surface.blit(mission_shadow, (304, title_y + 70))
    surface.blit(mission_title, (298, title_y + 64))

    subtitle_rect = pygame.Rect(398, title_y + 154, 386, 42)
    draw_cut_panel(surface, subtitle_rect, (8, 24, 52), config.COLOR_BORDER, alpha=214)
    subtitle = assets.font_menu_panel.render("Giải cứu Lina - phá lõi Orion", True, config.COLOR_ACCENT)
    surface.blit(subtitle, (subtitle_rect.centerx - subtitle.get_width() // 2, subtitle_rect.y + 10))

    draw_character_plate(
        surface,
        assets,
        pygame.Rect(18, 334, 178, 320),
        (72, 208, 255),
        config.PLAYER_NAME.upper(),
        "ĐẶC VỤ TIÊN PHONG",
        assets.menu_player_portrait,
        assets.menu_glow_blue,
        pulse,
        align="left",
    )
    draw_character_plate(
        surface,
        assets,
        pygame.Rect(168, 196, 274, 454),
        (174, 88, 255),
        config.BOSS_NAME,
        "LÃNH CHÚA BÓNG TỐI",
        assets.menu_boss_portrait,
        assets.menu_glow_purple,
        pulse,
    )
    draw_character_plate(
        surface,
        assets,
        pygame.Rect(932, 286, 188, 368),
        config.COLOR_WARNING,
        config.HOSTAGE_NAME.upper(),
        "CÔNG CHÚA",
        assets.menu_hostage_portrait,
        assets.menu_glow_gold,
        pulse,
        align="right",
    )

    for button in buttons:
        draw_menu_button(surface, assets, button, button.hovered(mouse_pos))

    footer_rect = pygame.Rect(394, config.SCREEN_HEIGHT - 76, 408, 40)
    draw_cut_panel(surface, footer_rect, (10, 18, 38), config.COLOR_BORDER, alpha=210)
    footer = assets.font_small.render("WASD di chuyển  |  Chuột ngắm bắn  |  ESC tạm dừng", True, config.COLOR_TEXT)
    surface.blit(footer, (footer_rect.centerx - footer.get_width() // 2, footer_rect.y + 12))
    draw_crosshair(surface, mouse_pos, True)


def draw_button(surface, assets, button, hovered):
    panel = pygame.Surface(button.rect.size, pygame.SRCALPHA)
    base = config.COLOR_PANEL_ALT if hovered and button.enabled else config.COLOR_PANEL
    border = config.COLOR_ACCENT if hovered and button.enabled else config.COLOR_BORDER
    pygame.draw.rect(panel, (*base, 235 if button.enabled else 180), panel.get_rect(), border_radius=18)
    pygame.draw.rect(panel, (*border, 255 if button.enabled else 140), panel.get_rect(), width=2, border_radius=18)
    if hovered and button.enabled:
        pygame.draw.rect(panel, (*config.COLOR_ACCENT, 30), panel.get_rect().inflate(-6, -6), border_radius=14)
    surface.blit(panel, button.rect.topleft)

    label_font = assets.font_h2 if button.rect.height < 64 else assets.font_h1
    text_color = config.COLOR_TEXT if button.enabled else (126, 136, 152)
    label = label_font.render(button.label, True, text_color)
    if button.subtitle:
        subtitle_color = config.COLOR_SUBTEXT if button.enabled else (96, 104, 120)
        subtitle = assets.font_small.render(button.subtitle, True, subtitle_color)
        surface.blit(label, (button.rect.x + 22, button.rect.y + 10))
        surface.blit(subtitle, (button.rect.x + 24, button.rect.y + button.rect.height - 26))
    else:
        surface.blit(
            label,
            (
                button.rect.centerx - label.get_width() // 2,
                button.rect.centery - label.get_height() // 2,
            ),
        )


def draw_hud(surface, assets, scene, next_upgrade_text, mouse_pos):
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
        scene.time_left / scene.level_spec.time_limit,
        pygame.Rect(248, 43, 170, 8),
        max(0, math.ceil(scene.time_left)),
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
    draw_crosshair(surface, mouse_pos, scene.player.fire_timer <= 0)


def draw_health_bar(surface, assets, value, maximum, rect, label):
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
    px = rect.x + (position.x - world_rect.left) / world_rect.width * rect.width
    py = rect.y + (position.y - world_rect.top) / world_rect.height * rect.height
    pygame.draw.circle(surface, color, (int(px), int(py)), radius)


def draw_minimap_point(surface, rect, maze_width, maze_height, cell, color):
    px = rect.x + (cell[0] / max(1, maze_width - 1)) * rect.width
    py = rect.y + (cell[1] / max(1, maze_height - 1)) * rect.height
    pygame.draw.circle(surface, color, (int(px), int(py)), 3)


def draw_crosshair(surface, mouse_pos, ready):
    color = config.COLOR_ACCENT if ready else config.COLOR_WARNING
    x, y = mouse_pos
    pygame.draw.circle(surface, color, (x, y), 10, width=1)
    pygame.draw.line(surface, color, (x - 16, y), (x - 4, y), 1)
    pygame.draw.line(surface, color, (x + 4, y), (x + 16, y), 1)
    pygame.draw.line(surface, color, (x, y - 16), (x, y - 4), 1)
    pygame.draw.line(surface, color, (x, y + 4), (x, y + 16), 1)


def draw_pause_menu(surface, assets, pause_buttons, settings_buttons, mouse_pos, audio, fullscreen):
    veil = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
    veil.fill((4, 8, 18, 172))
    surface.blit(veil, (0, 0))

    card = pygame.Rect(config.SCREEN_WIDTH // 2 - 320, 190, 640, 430)
    draw_glass_panel(surface, card)
    pygame.draw.rect(surface, config.COLOR_ACCENT, card.inflate(-16, -16), width=2, border_radius=18)

    title = assets.font_title.render("TẠM DỪNG", True, config.COLOR_TEXT)
    hint = assets.font_small.render("ESC tiếp tục | R chơi lại | M về menu | F11 toàn màn hình", True, config.COLOR_SUBTEXT)
    surface.blit(title, (card.centerx - title.get_width() // 2, card.y + 22))
    surface.blit(hint, (card.centerx - hint.get_width() // 2, card.y + 92))

    for button in pause_buttons:
        draw_button(surface, assets, button, button.hovered(mouse_pos))

    settings_title = assets.font_h2.render("Âm lượng và hiển thị", True, config.COLOR_TEXT)
    surface.blit(settings_title, (card.x + 32, card.y + 306))
    sfx = assets.font_small.render(f"SFX {round(audio.sfx_volume * 100):3d}%", True, config.COLOR_SUBTEXT)
    music = assets.font_small.render(f"Music {round(audio.music_volume * 100):3d}%", True, config.COLOR_SUBTEXT)
    mode = assets.font_small.render("Toàn màn hình" if fullscreen else "Cửa sổ", True, config.COLOR_SUBTEXT)
    surface.blit(sfx, (card.x + 32, card.y + 340))
    surface.blit(music, (card.x + 150, card.y + 340))
    surface.blit(mode, (card.x + 288, card.y + 340))

    for button in settings_buttons:
        draw_button(surface, assets, button, button.hovered(mouse_pos))


def draw_game_over(surface, assets, reason, score, buttons, mouse_pos):
    veil = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
    veil.fill((18, 4, 10, 182))
    surface.blit(veil, (0, 0))

    card = pygame.Rect(config.SCREEN_WIDTH // 2 - 270, 190, 540, 430)
    draw_glass_panel(surface, card)
    pygame.draw.rect(surface, config.COLOR_DANGER, card.inflate(-16, -16), width=2, border_radius=18)

    title = assets.font_title.render("THẤT BẠI", True, config.COLOR_TEXT)
    reason_lines = wrap_text(assets.font_h2, reason, card.width - 64)
    score_text = assets.font_h2.render(f"Điểm màn: {score}", True, config.COLOR_WARNING)
    hint = assets.font_small.render("Enter/R thử lại | ESC/M về menu", True, config.COLOR_SUBTEXT)

    surface.blit(title, (card.centerx - title.get_width() // 2, card.y + 28))
    y = card.y + 112
    for line in reason_lines[:2]:
        line_surf = assets.font_h2.render(line, True, config.COLOR_SUBTEXT)
        surface.blit(line_surf, (card.centerx - line_surf.get_width() // 2, y))
        y += 32
    surface.blit(score_text, (card.centerx - score_text.get_width() // 2, card.y + 196))
    surface.blit(hint, (card.centerx - hint.get_width() // 2, card.y + 246))

    for button in buttons:
        draw_button(surface, assets, button, button.hovered(mouse_pos))


def draw_overlay(surface, assets, title, subtitle, footer, accent_color):
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


def draw_gameplay_hud(surface, assets, scene, next_upgrade_text, mouse_pos):
    header = pygame.Rect(18, 14, 860, 96)
    draw_glass_panel(surface, header)

    stage_text = assets.font_h2.render(f"Màn {scene.level_spec.number}", True, config.COLOR_TEXT)
    stage_name = assets.font_small.render(scene.level_spec.title, True, config.COLOR_SUBTEXT)
    briefing = assets.font_small.render(scene.level_spec.description, True, config.COLOR_SUBTEXT)
    surface.blit(stage_text, (32, 18))
    surface.blit(stage_name, (118, 24))
    surface.blit(briefing, (32, 50))

    draw_health_bar(surface, assets, scene.player.health, scene.player.max_health, pygame.Rect(276, 18, 170, 14), config.PLAYER_NAME)
    draw_timer_bar(
        surface,
        assets,
        scene.time_left / scene.level_spec.time_limit,
        pygame.Rect(276, 40, 170, 8),
        max(0, math.ceil(scene.time_left)),
    )

    objective = scene.current_objective_text()
    objective_color = config.COLOR_WARNING if not scene.hostage.rescued else config.COLOR_ACCENT
    if scene.boss and scene.boss.health > 0 and scene.level_spec.objective_mode == "boss_and_rescue":
        objective_color = config.COLOR_DANGER
    objective_text = assets.font_small.render(objective, True, objective_color)
    surface.blit(objective_text, (470, 20))

    if scene.boss and scene.boss.health > 0:
        draw_health_bar(surface, assets, scene.boss.health, scene.boss.max_health, pygame.Rect(610, 42, 180, 12), scene.boss.display_name)

    score = assets.font_h2.render(f"Điểm {scene.score}", True, config.COLOR_TEXT)
    surface.blit(score, (804, 18))

    upgrade = assets.font_small.render(next_upgrade_text, True, config.COLOR_SUBTEXT)
    surface.blit(upgrade, (470, 64))

    skill_rect = pygame.Rect(18, 102, 280, 54)
    draw_glass_panel(surface, skill_rect)
    snapshot = scene.player.skill.snapshot()
    title = assets.font_small.render(f"{config.PLAYER_SKILL_KEY_LABEL}  {config.PLAYER_SKILL_NAME}", True, config.COLOR_TEXT)
    state_text = "Sẵn sàng" if snapshot.ready else f"Hồi {snapshot.cooldown_left:.1f}s"
    status = assets.font_small.render(state_text, True, config.COLOR_SKILL if snapshot.ready else config.COLOR_WARNING)
    surface.blit(title, (skill_rect.x + 14, skill_rect.y + 8))
    surface.blit(status, (skill_rect.right - 14 - status.get_width(), skill_rect.y + 8))

    energy_rect = pygame.Rect(skill_rect.x + 14, skill_rect.y + 28, skill_rect.width - 28, 10)
    pygame.draw.rect(surface, (*config.COLOR_PANEL_ALT, 255), energy_rect, border_radius=8)
    pygame.draw.rect(surface, (*config.COLOR_SKILL_DIM, 220), energy_rect, width=1, border_radius=8)
    fill = energy_rect.copy()
    fill.width = max(6, int(energy_rect.width * snapshot.energy_ratio))
    pygame.draw.rect(surface, config.COLOR_SKILL, fill, border_radius=8)
    info = assets.font_small.render(
        f"Năng lượng {int(snapshot.energy)}/{int(snapshot.max_energy)} | Tốn {config.PLAYER_SKILL_ENERGY_COST}",
        True,
        config.COLOR_SUBTEXT,
    )
    surface.blit(info, (skill_rect.x + 14, skill_rect.bottom - 16))

    draw_minimap(surface, assets, scene, pygame.Rect(config.SCREEN_WIDTH - 136, 14, 118, 118))
    draw_crosshair(surface, mouse_pos, scene.player.fire_timer <= 0)


def draw_cheat_prompt(surface, assets, cheat_input):
    card = pygame.Rect(config.SCREEN_WIDTH - 344, 142, 326, 108)
    draw_glass_panel(surface, card)

    title = assets.font_h2.render("Hack Console", True, config.COLOR_TEXT)
    subtitle = assets.font_small.render("Nhap lenh va nhan Enter de kich hoat", True, config.COLOR_SUBTEXT)
    surface.blit(title, (card.x + 18, card.y + 14))
    surface.blit(subtitle, (card.x + 18, card.y + 42))

    input_rect = pygame.Rect(card.x + 18, card.y + 68, card.width - 36, 24)
    pygame.draw.rect(surface, (*config.COLOR_PANEL_ALT, 255), input_rect, border_radius=8)
    pygame.draw.rect(surface, config.COLOR_ACCENT, input_rect, width=1, border_radius=8)
    value = cheat_input if cheat_input else "_"
    text = assets.font_small.render(f"> {value}", True, config.COLOR_TEXT)
    surface.blit(text, (input_rect.x + 10, input_rect.y + 4))

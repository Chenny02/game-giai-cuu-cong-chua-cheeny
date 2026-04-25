"""Game bootstrap vĂ  state machine tá»•ng.

Ă tÆ°á»Ÿng kiáº¿n trĂºc:
- `Game` chá»‰ Ä‘iá»u phá»‘i tráº¡ng thĂ¡i lá»›n cá»§a á»©ng dá»¥ng.
- ToĂ n bá»™ logic chiáº¿n Ä‘áº¥u cá»§a 1 mĂ n Ä‘Æ°á»£c giao cho `LevelScene`.
- UI Ä‘Æ°á»£c gá»i tá»« Ä‘Ă¢y, nhÆ°ng `Game` khĂ´ng tá»± váº½ chi tiáº¿t tá»«ng entity.

Nhá» cĂ¡ch tĂ¡ch nĂ y, ta cĂ³ thá»ƒ thay Ä‘á»•i gameplay tá»«ng mĂ n mĂ  khĂ´ng pháº£i sá»­a menu,
vĂ  cÅ©ng cĂ³ thá»ƒ Ä‘á»•i giao diá»‡n mĂ  khĂ´ng lĂ m vá»¡ combat loop.
"""

import sys
from dataclasses import dataclass

import pygame

from . import config, ui
from .audio import AudioManager
from .assets import AssetManager
from .level_system import LevelScene, build_level_specs
from .states import GameState


@dataclass(frozen=True)
class DialogueBeat:
    title: str
    speaker: str
    text: str
    accent_color: tuple


def build_dialogue_scripts():
    """Tập thoại campaign, tách khỏi flow update để dễ chỉnh nội dung."""

    aris = (88, 197, 255)
    lina = config.COLOR_WARNING
    orion = (194, 63, 255)

    return {
        "intro": [
            DialogueBeat(
                "MỞ ĐẦU",
                config.HOSTAGE_NAME,
                f"{config.PLAYER_NAME}... nếu anh nghe thấy... hãy đến cứu em. Bóng tối đang nuốt chửng nơi này...",
                lina,
            ),
            DialogueBeat(
                "MỞ ĐẦU",
                config.BOSS_NAME,
                "Mọi hy vọng đều vô ích. Vương quốc này đã thuộc về ta.",
                orion,
            ),
            DialogueBeat(
                "MỞ ĐẦU",
                config.PLAYER_NAME,
                f"Ta sẽ không để điều đó xảy ra. {config.HOSTAGE_NAME}, hãy chờ ta.",
                aris,
            ),
        ],
        "level_1_clear": [
            DialogueBeat(
                "SAU MÀN 1 - THÂM NHẬP",
                config.PLAYER_NAME,
                "Mình đã vào được lâu đài, nhưng nơi này đầy cạm bẫy.",
                aris,
            ),
            DialogueBeat(
                "SAU MÀN 1 - THÂM NHẬP",
                config.HOSTAGE_NAME,
                f"{config.PLAYER_NAME}... hãy cẩn thận. Chúng đang canh giữ mọi lối đi...",
                lina,
            ),
            DialogueBeat(
                "SAU MÀN 1 - THÂM NHẬP",
                config.BOSS_NAME,
                "Ngươi chỉ vừa bước vào mà đã nghĩ mình có cơ hội sao?",
                orion,
            ),
        ],
        "level_2_clear": [
            DialogueBeat(
                "SAU MÀN 2 - TRUY ĐUỔI",
                config.PLAYER_NAME,
                "Những sinh vật này không di chuyển ngẫu nhiên. Chúng đang săn mình.",
                aris,
            ),
            DialogueBeat(
                "SAU MÀN 2 - TRUY ĐUỔI",
                config.HOSTAGE_NAME,
                f"Đó là {config.BOSS_NAME}... hắn điều khiển tất cả... hắn đang đọc từng bước đi của anh...",
                lina,
            ),
            DialogueBeat(
                "SAU MÀN 2 - TRUY ĐUỔI",
                config.BOSS_NAME,
                "Ta biết ngươi sẽ đi đâu trước cả khi ngươi quyết định.",
                orion,
            ),
        ],
        "level_3_clear": [
            DialogueBeat(
                "SAU MÀN 3 - MÊ CUNG",
                config.PLAYER_NAME,
                "Mê cung này thay đổi liên tục, như thể nó có ý thức vậy.",
                aris,
            ),
            DialogueBeat(
                "SAU MÀN 3 - MÊ CUNG",
                config.HOSTAGE_NAME,
                f"{config.BOSS_NAME} đang thử thách anh. Hắn muốn khiến anh lạc lối...",
                lina,
            ),
            DialogueBeat(
                "SAU MÀN 3 - MÊ CUNG",
                config.PLAYER_NAME,
                "Dù mê cung có phức tạp đến đâu, luôn có đường ra.",
                aris,
            ),
            DialogueBeat(
                "TRƯỚC MÀN 4 - ĐỐI ĐẦU",
                config.BOSS_NAME,
                f"Ngươi đã đi quá xa rồi, {config.PLAYER_NAME}. Đây sẽ là nơi ngươi kết thúc.",
                orion,
            ),
            DialogueBeat(
                "TRƯỚC MÀN 4 - ĐỐI ĐẦU",
                config.PLAYER_NAME,
                "Không. Đây là nơi ngươi thất bại.",
                aris,
            ),
            DialogueBeat(
                "TRƯỚC MÀN 4 - ĐỐI ĐẦU",
                config.HOSTAGE_NAME,
                f"{config.PLAYER_NAME}... em tin anh.",
                lina,
            ),
        ],
        "victory": [
            DialogueBeat(
                "KẾT THÚC",
                config.BOSS_NAME,
                "Không thể nào... một con người... lại đánh bại ta...",
                orion,
            ),
            DialogueBeat(
                "KẾT THÚC",
                config.PLAYER_NAME,
                "Sức mạnh thật sự không nằm ở tính toán.",
                aris,
            ),
            DialogueBeat(
                "KẾT THÚC",
                config.HOSTAGE_NAME,
                f"Anh đã làm được rồi, {config.PLAYER_NAME}.",
                lina,
            ),
            DialogueBeat(
                "KẾT THÚC",
                config.PLAYER_NAME,
                "Chúng ta về thôi. Vương quốc đang chờ.",
                aris,
            ),
        ],
        "game_over": [
            DialogueBeat(
                "THẤT BẠI",
                config.BOSS_NAME,
                "Kết thúc rồi. Con người luôn thất bại trước trí tuệ hoàn hảo.",
                orion,
            ),
            DialogueBeat(
                "THẤT BẠI",
                config.HOSTAGE_NAME,
                f"{config.PLAYER_NAME}... xin đừng bỏ cuộc...",
                lina,
            ),
        ],
    }


class Game:
    """State machine tá»•ng cho menu, chÆ¡i game, qua mĂ n, thua vĂ  chiáº¿n tháº¯ng."""

    CHEAT_CODES = {
        "chenny": "toggle_invincibility",
        "rabbit": "force_level_win",
    }

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        self.base_size = (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        self.fullscreen = False
        self.windowed_size = self.base_size
        self.window_surface = None
        self.present_rect = pygame.Rect(0, 0, *self.base_size)
        self.configure_display()
        self.screen = pygame.Surface(self.base_size).convert()
        self.clock = pygame.time.Clock()

        self.audio = AudioManager()
        self.assets = AssetManager()
        self.level_specs = build_level_specs()
        self.dialogue_scripts = build_dialogue_scripts()
        self.buttons = [
            ui.Button(pygame.Rect(430, 340, 360, 86), "BẮT ĐẦU", "Chiến dịch 1-4", True, "primary", "start"),
            ui.Button(pygame.Rect(452, 442, 316, 62), "TIẾP TỤC", "Chưa có lượt lưu", False, "default", "play"),
            ui.Button(pygame.Rect(452, 518, 316, 62), "CHỌN MÀN", "Sẽ mở sau", False, "default", "grid"),
            ui.Button(pygame.Rect(452, 594, 316, 62), "THOÁT", "Rời trò chơi", True, "danger", "exit"),
        ]
        self.pause_buttons = [
            ui.Button(pygame.Rect(438, 270, 304, 58), "Tiếp tục", "Quay lại màn chơi"),
            ui.Button(pygame.Rect(438, 342, 304, 58), "Chơi lại", "Bắt đầu lại màn này"),
            ui.Button(pygame.Rect(438, 414, 304, 58), "Về menu", "Kết thúc lượt chơi"),
        ]
        self.settings_buttons = [
            ui.Button(pygame.Rect(410, 540, 80, 44), "SFX -", ""),
            ui.Button(pygame.Rect(500, 540, 80, 44), "SFX +", ""),
            ui.Button(pygame.Rect(600, 540, 90, 44), "Music -", ""),
            ui.Button(pygame.Rect(700, 540, 90, 44), "Music +", ""),
            ui.Button(pygame.Rect(785, 540, 115, 44), "Fullscreen", ""),
        ]
        self.game_over_buttons = [
            ui.Button(pygame.Rect(438, 448, 304, 58), "Thử lại", "Chơi lại màn này"),
            ui.Button(pygame.Rect(438, 520, 304, 58), "Về menu", "Rời lượt chơi"),
        ]

        pygame.mouse.set_visible(False)

        self.running = True
        self.state = GameState.MENU
        self.level_index = 0
        self.scene = None
        self.total_score = 0
        self.best_score = 0
        self.overlay_timer = 0
        self.menu_pulse = 0
        self.dialogue_beats = []
        self.dialogue_index = 0
        self.dialogue_footer = ""
        self.dialogue_subtitle = ""
        self.dialogue_next_action = ""
        self.mouse_pos = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
        self.cheat_buffer = ""
        self.invincible_enabled = False

    def run(self):
        """VĂ²ng láº·p chĂ­nh cá»§a game.

        Má»—i frame chá»‰ lĂ m 3 viá»‡c:
        1. Äá»c input
        2. Update state hiá»‡n táº¡i
        3. Váº½ state hiá»‡n táº¡i
        """

        while self.running:
            self.clock.tick(config.FPS)
            self.menu_pulse += 1
            self.mouse_pos = self.get_logical_mouse_position()
            self.handle_events()
            self.update()
            self.draw()

        pygame.mouse.set_visible(True)
        pygame.quit()

    def handle_events(self):
        """PhĂ¢n input theo state Ä‘á»ƒ trĂ¡nh if/else lá»›n trong má»—i scene."""

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
                self.mouse_pos = self.get_logical_mouse_position()
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT):
                self.toggle_fullscreen()
                self.mouse_pos = self.get_logical_mouse_position()
                continue

            if event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.windowed_size = (
                    max(960, event.w),
                    max(640, event.h),
                )
                self.configure_display()
                self.mouse_pos = self.get_logical_mouse_position()
                continue

            if self.state == GameState.MENU:
                self.handle_menu_event(event)
            elif self.state == GameState.DIALOGUE:
                self.handle_dialogue_event(event)
            elif self.state == GameState.PLAYING:
                self.handle_playing_event(event)
            elif self.state == GameState.PAUSED:
                self.handle_pause_event(event)
            elif self.state == GameState.GAME_OVER:
                self.handle_game_over_event(event)
            else:
                self.handle_overlay_event(event)

    def handle_menu_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        mouse_pos = self.mouse_pos
        if self.buttons[0].hovered(mouse_pos):
            self.audio.play("ui_click")
            self.start_new_campaign()
        elif len(self.buttons) > 3 and self.buttons[3].hovered(mouse_pos):
            self.audio.play("ui_click")
            self.running = False

    def handle_playing_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pause_game()
            return

        self.process_cheat_input(event)

    def handle_pause_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.resume_game()
            elif event.key == pygame.K_r:
                self.restart_current_level()
            elif event.key == pygame.K_m:
                self.return_to_menu()
            return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        mouse_pos = self.mouse_pos
        if self.pause_buttons[0].hovered(mouse_pos):
            self.audio.play("ui_click")
            self.resume_game()
        elif self.pause_buttons[1].hovered(mouse_pos):
            self.audio.play("ui_click")
            self.restart_current_level()
        elif self.pause_buttons[2].hovered(mouse_pos):
            self.audio.play("ui_click")
            self.return_to_menu()
        elif self.settings_buttons[0].hovered(mouse_pos):
            self.audio.change_sfx_volume(-0.1)
            self.audio.play("ui_click")
        elif self.settings_buttons[1].hovered(mouse_pos):
            self.audio.change_sfx_volume(0.1)
            self.audio.play("ui_click")
        elif self.settings_buttons[2].hovered(mouse_pos):
            self.audio.change_music_volume(-0.1)
            self.audio.play("ui_click")
        elif self.settings_buttons[3].hovered(mouse_pos):
            self.audio.change_music_volume(0.1)
            self.audio.play("ui_click")
        elif self.settings_buttons[4].hovered(mouse_pos):
            self.audio.play("ui_click")
            self.toggle_fullscreen()
            self.mouse_pos = self.get_logical_mouse_position()

    def handle_game_over_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                self.restart_current_level()
            elif event.key in (pygame.K_ESCAPE, pygame.K_m):
                self.return_to_menu()
            return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        mouse_pos = self.mouse_pos
        if self.game_over_buttons[0].hovered(mouse_pos):
            self.audio.play("ui_click")
            self.restart_current_level()
        elif self.game_over_buttons[1].hovered(mouse_pos):
            self.audio.play("ui_click")
            self.return_to_menu()

    def handle_dialogue_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.audio.play("ui_click")
                self.return_to_menu()
                return
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.audio.play("ui_click", volume=0.5)
                self.advance_dialogue()
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.audio.play("ui_click", volume=0.5)
            self.advance_dialogue()

    def handle_overlay_event(self, event):
        # Sau mĂ n hoáº·c khi thua, báº¥t ká»³ phĂ­m/chuá»™t Ä‘á»u lĂ  má»™t xĂ¡c nháº­n há»£p lĂ½.
        if event.type not in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            return

        if self.state == GameState.LEVEL_COMPLETE:
            self.begin_next_level()
        else:
            self.return_to_menu()

    def update(self):
        """Chá»‰ cáº­p nháº­t state hiá»‡n táº¡i; Game khĂ´ng chen vĂ o ná»™i bá»™ combat."""

        if self.state == GameState.PLAYING:
            delta_time = self.clock.get_time() / 1000.0
            self.scene.mouse_pos = pygame.Vector2(self.mouse_pos)
            self.scene.update(delta_time)

            if self.scene.result == "win":
                self.total_score += self.scene.score
                self.best_score = max(self.best_score, self.total_score)
                if self.level_index == len(self.level_specs) - 1:
                    self.audio.play("win")
                    self.open_dialogue(
                        "victory",
                        "return_to_menu",
                        subtitle=f"Tổng điểm: {self.total_score}",
                        footer="Nhấn Enter, Space hoặc chuột trái để về menu.",
                    )
                else:
                    self.audio.play("rescue")
                    self.open_dialogue(
                        f"level_{self.level_index + 1}_clear",
                        "next_level",
                        subtitle=self.scene.result_reason,
                        footer="Nhấn Enter, Space hoặc chuột trái để tiếp tục.",
                    )

            elif self.scene.result == "lose":
                self.total_score += self.scene.score
                self.best_score = max(self.best_score, self.total_score)
                self.audio.play("lose")
                self.state = GameState.GAME_OVER

    def draw(self):
        """Má»—i state cĂ³ cĂ¡ch váº½ riĂªng, nhÆ°ng Ä‘á»u Ä‘i qua má»™t Ä‘iá»ƒm trung tĂ¢m."""

        if self.state == GameState.MENU:
            ui.draw_menu(
                self.screen,
                self.assets,
                self.buttons,
                self.mouse_pos,
                self.best_score,
                self.menu_pulse,
            )

        elif self.state == GameState.DIALOGUE:
            if self.scene:
                self.scene.draw(self.screen)
            else:
                self.screen.blit(self.assets.menu_background, (0, 0))

            current_dialogue = self.current_dialogue()
            if current_dialogue:
                ui.draw_dialogue(
                    self.screen,
                    self.assets,
                    current_dialogue.title,
                    current_dialogue.speaker,
                    current_dialogue.text,
                    current_dialogue.accent_color,
                    self.dialogue_index + 1,
                    len(self.dialogue_beats),
                    self.dialogue_footer,
                    subtitle=self.dialogue_subtitle,
                )

        elif self.state == GameState.PLAYING:
            if self.scene:
                self.scene.mouse_pos = pygame.Vector2(self.mouse_pos)
            self.scene.draw(self.screen)
            ui.draw_hud(self.screen, self.assets, self.scene, self.describe_next_upgrade(), self.mouse_pos)

        elif self.state == GameState.PAUSED:
            if self.scene:
                self.scene.mouse_pos = pygame.Vector2(self.mouse_pos)
                self.scene.draw(self.screen)
                ui.draw_hud(self.screen, self.assets, self.scene, self.describe_next_upgrade(), self.mouse_pos)
            ui.draw_pause_menu(
                self.screen,
                self.assets,
                self.pause_buttons,
                self.settings_buttons,
                self.mouse_pos,
                self.audio,
                self.fullscreen,
            )

        elif self.state == GameState.LEVEL_COMPLETE:
            if self.scene:
                self.scene.mouse_pos = pygame.Vector2(self.mouse_pos)
            self.scene.draw(self.screen)
            ui.draw_hud(self.screen, self.assets, self.scene, self.describe_next_upgrade(), self.mouse_pos)
            ui.draw_overlay(
                self.screen,
                self.assets,
                "HOĂ€N THĂ€NH",
                self.scene.result_reason,
                "Nhấn phím bất kỳ để qua màn.",
                config.COLOR_ACCENT,
            )

        elif self.state == GameState.GAME_OVER:
            if self.scene:
                self.scene.mouse_pos = pygame.Vector2(self.mouse_pos)
            self.scene.draw(self.screen)
            ui.draw_hud(self.screen, self.assets, self.scene, self.describe_next_upgrade(), self.mouse_pos)
            ui.draw_game_over(
                self.screen,
                self.assets,
                self.scene.result_reason,
                self.scene.score,
                self.game_over_buttons,
                self.mouse_pos,
            )

        elif self.state == GameState.VICTORY:
            if self.scene:
                self.scene.mouse_pos = pygame.Vector2(self.mouse_pos)
            self.scene.draw(self.screen)
            ui.draw_hud(self.screen, self.assets, self.scene, "Chiến dịch đã hoàn tất.", self.mouse_pos)
            ui.draw_overlay(
                self.screen,
                self.assets,
                "CHIáº¾N THáº®NG",
                f"{config.BOSS_NAME} đã bị hạ. {config.HOSTAGE_NAME} đã an toàn.",
                f"{config.PLAYER_NAME} hoàn thành sứ mệnh | Tổng điểm: {self.total_score}",
                config.COLOR_WARNING,
            )

        self.present_screen()

    def start_new_campaign(self):
        """Reset campaign vĂ  táº¡o scene cho mĂ n Ä‘áº§u tiĂªn."""

        self.total_score = 0
        self.level_index = 0
        self.reset_cheat_state()
        self.scene = self.create_level_scene(self.level_index)
        self.open_dialogue(
            "intro",
            "resume_current_level",
            subtitle="Lâu đài bóng tối vừa khép cổng.",
            footer="Nhấn Enter, Space hoặc chuột trái để tiếp.",
        )

    def begin_next_level(self):
        """Chuyá»ƒn sang mĂ n tiáº¿p theo, náº¿u háº¿t mĂ n thĂ¬ vĂ o state chiáº¿n tháº¯ng."""

        self.level_index += 1
        if self.level_index >= len(self.level_specs):
            self.return_to_menu()
            return

        self.scene = self.create_level_scene(self.level_index)
        self.state = GameState.PLAYING

    def restart_current_level(self):
        self.scene = self.create_level_scene(self.level_index)
        self.state = GameState.PLAYING

    def pause_game(self):
        if self.state == GameState.PLAYING:
            self.audio.play("ui_click", volume=0.6)
            self.state = GameState.PAUSED

    def resume_game(self):
        if self.state == GameState.PAUSED:
            self.state = GameState.PLAYING

    def return_to_menu(self):
        """XĂ³a scene hiá»‡n táº¡i Ä‘á»ƒ quay láº¡i menu sáº¡ch sáº½."""

        self.state = GameState.MENU
        self.scene = None
        self.dialogue_beats = []
        self.dialogue_index = 0
        self.dialogue_footer = ""
        self.dialogue_subtitle = ""
        self.dialogue_next_action = ""
        self.reset_cheat_state()

    def configure_display(self):
        """Táº¡o cá»­a sá»• tháº­t; pháº§n render logic váº«n giá»¯ á»Ÿ Ä‘á»™ phĂ¢n giáº£i cá»‘ Ä‘á»‹nh."""

        if self.fullscreen:
            self.window_surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window_surface = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.present_rect = self.calculate_present_rect(self.window_surface.get_size())

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.configure_display()

    def calculate_present_rect(self, window_size):
        window_w, window_h = window_size
        base_w, base_h = self.base_size
        scale = min(window_w / base_w, window_h / base_h)
        draw_w = max(1, int(base_w * scale))
        draw_h = max(1, int(base_h * scale))
        return pygame.Rect((window_w - draw_w) // 2, (window_h - draw_h) // 2, draw_w, draw_h)

    def get_logical_mouse_position(self):
        raw_x, raw_y = pygame.mouse.get_pos()
        rect = self.present_rect
        if rect.width <= 0 or rect.height <= 0:
            return raw_x, raw_y

        local_x = (raw_x - rect.x) / rect.width * self.base_size[0]
        local_y = (raw_y - rect.y) / rect.height * self.base_size[1]
        clamped_x = max(0, min(self.base_size[0] - 1, int(local_x)))
        clamped_y = max(0, min(self.base_size[1] - 1, int(local_y)))
        return clamped_x, clamped_y

    def present_screen(self):
        self.present_rect = self.calculate_present_rect(self.window_surface.get_size())
        self.window_surface.fill((0, 0, 0))
        scaled = pygame.transform.smoothscale(self.screen, self.present_rect.size)
        self.window_surface.blit(scaled, self.present_rect.topleft)
        pygame.display.flip()

    def open_dialogue(self, script_key, next_action, subtitle="", footer="Nhấn Enter để tiếp."):
        """Má»Ÿ há»™i thoáº¡i nhiá»u trang vĂ  ghi nhá»› hĂ nh Ä‘á»™ng sau khi Ä‘á»c xong."""

        self.dialogue_beats = list(self.dialogue_scripts.get(script_key, []))
        self.dialogue_index = 0
        self.dialogue_subtitle = subtitle
        self.dialogue_footer = footer
        self.dialogue_next_action = next_action
        if not self.dialogue_beats:
            self.finish_dialogue()
            return
        self.state = GameState.DIALOGUE

    def current_dialogue(self):
        if not self.dialogue_beats:
            return None
        return self.dialogue_beats[self.dialogue_index]

    def advance_dialogue(self):
        if not self.dialogue_beats:
            self.finish_dialogue()
            return

        if self.dialogue_index < len(self.dialogue_beats) - 1:
            self.dialogue_index += 1
            return

        self.finish_dialogue()

    def finish_dialogue(self):
        action = self.dialogue_next_action
        self.dialogue_beats = []
        self.dialogue_index = 0
        self.dialogue_footer = ""
        self.dialogue_subtitle = ""
        self.dialogue_next_action = ""

        if action == "resume_current_level":
            self.state = GameState.PLAYING
        elif action == "next_level":
            self.begin_next_level()
        else:
            self.return_to_menu()

    def create_level_scene(self, level_index):
        scene = LevelScene(self.assets, self.level_specs[level_index])
        scene.audio = self.audio
        self.apply_cheat_state_to_scene(scene)
        return scene

    def apply_cheat_state_to_scene(self, scene):
        scene.player_invincible = self.invincible_enabled

    def reset_cheat_state(self):
        self.cheat_buffer = ""
        self.invincible_enabled = False

    def process_cheat_input(self, event):
        if self.state != GameState.PLAYING or event.type != pygame.KEYDOWN:
            return

        typed_char = (event.unicode or "").lower()
        if not typed_char.isalpha():
            return

        max_length = max(len(code) for code in self.CHEAT_CODES)
        self.cheat_buffer = (self.cheat_buffer + typed_char)[-max_length:]
        for code, action_name in self.CHEAT_CODES.items():
            if self.cheat_buffer.endswith(code):
                getattr(self, action_name)()
                self.cheat_buffer = ""
                return

    def toggle_invincibility(self):
        self.invincible_enabled = not self.invincible_enabled
        if self.scene:
            self.apply_cheat_state_to_scene(self.scene)

    def force_level_win(self):
        if not self.scene or self.state != GameState.PLAYING:
            return

        if self.scene.level_spec.has_boss:
            self.scene.hostage.rescued = True
            if self.scene.boss:
                self.scene.boss.health = 0
                self.scene.boss.dead = True
            self.scene.result_reason = f"{config.BOSS_NAME} đã bị tiêu diệt và {config.HOSTAGE_NAME} đã an toàn."
        else:
            self.scene.hostage.rescued = True
            self.scene.result_reason = f"{config.HOSTAGE_NAME} đã được {config.PLAYER_NAME} giải cứu."
        self.scene.result = "win"

    def describe_next_upgrade(self):
        """Giá»¯ láº¡i thĂ´ng tin progression Ä‘á»ƒ cĂ³ thá»ƒ dĂ¹ng láº¡i náº¿u UI cáº§n."""

        current_level = min(self.level_index + 1, len(self.level_specs))
        if self.state == GameState.VICTORY:
            return "Chiến dịch đã hoàn tất."

        next_level = min(len(self.level_specs), current_level + 1)
        if next_level == current_level:
            return "Không còn nâng cấp."

        upgrade = config.upgrade_for_level(next_level)
        return f"Má»Ÿ khĂ³a: {upgrade.title}"


def main():
    """Entrypoint chung cho file launcher."""

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    Game().run()

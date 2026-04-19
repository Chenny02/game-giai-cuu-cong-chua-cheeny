"""Game bootstrap và state machine tổng.

Ý tưởng kiến trúc:
- `Game` chỉ điều phối trạng thái lớn của ứng dụng.
- Toàn bộ logic chiến đấu của 1 màn được giao cho `LevelScene`.
- UI được gọi từ đây, nhưng `Game` không tự vẽ chi tiết từng entity.

Nhờ cách tách này, ta có thể thay đổi gameplay từng màn mà không phải sửa menu,
và cũng có thể đổi giao diện mà không làm vỡ combat loop.
"""

import sys
from dataclasses import dataclass

import pygame

from . import config, ui
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
                "MỞ ĐẦU GAME",
                config.HOSTAGE_NAME,
                f"{config.PLAYER_NAME}... nếu anh nghe thấy... hãy đến cứu em... bóng tối đang nuốt chửng nơi này...",
                lina,
            ),
            DialogueBeat(
                "MỞ ĐẦU GAME",
                config.BOSS_NAME,
                "Mọi hy vọng đều vô ích. Vương quốc này... đã thuộc về ta.",
                orion,
            ),
            DialogueBeat(
                "MỞ ĐẦU GAME",
                config.PLAYER_NAME,
                f"Ta sẽ không để điều đó xảy ra. {config.HOSTAGE_NAME}, hãy chờ ta!",
                aris,
            ),
        ],
        "level_1_clear": [
            DialogueBeat(
                "SAU MÀN 1 – THÂM NHẬP",
                config.PLAYER_NAME,
                "Mình đã vào được lâu đài... nhưng nơi này đầy cạm bẫy.",
                aris,
            ),
            DialogueBeat(
                "SAU MÀN 1 – THÂM NHẬP",
                config.HOSTAGE_NAME,
                f"{config.PLAYER_NAME}... hãy cẩn thận... chúng đang canh giữ mọi lối đi...",
                lina,
            ),
            DialogueBeat(
                "SAU MÀN 1 – THÂM NHẬP",
                config.BOSS_NAME,
                "Ngươi chỉ vừa bước vào... và đã nghĩ mình có cơ hội sao?",
                orion,
            ),
        ],
        "level_2_clear": [
            DialogueBeat(
                "SAU MÀN 2 – TRUY ĐUỔI",
                config.PLAYER_NAME,
                "Những sinh vật này... chúng không di chuyển ngẫu nhiên... chúng đang săn mình!",
                aris,
            ),
            DialogueBeat(
                "SAU MÀN 2 – TRUY ĐUỔI",
                config.HOSTAGE_NAME,
                f"Đó là {config.BOSS_NAME}... nó điều khiển tất cả... nó học từ từng bước đi của anh...",
                lina,
            ),
            DialogueBeat(
                "SAU MÀN 2 – TRUY ĐUỔI",
                config.BOSS_NAME,
                "Ta biết ngươi sẽ đi đâu... trước cả khi ngươi quyết định.",
                orion,
            ),
        ],
        "level_3_clear": [
            DialogueBeat(
                "SAU MÀN 3 – MÊ CUNG",
                config.PLAYER_NAME,
                "Mê cung này... thay đổi liên tục... như có ý thức vậy...",
                aris,
            ),
            DialogueBeat(
                "SAU MÀN 3 – MÊ CUNG",
                config.HOSTAGE_NAME,
                f"{config.BOSS_NAME} đang thử thách anh... nó muốn khiến anh lạc lối...",
                lina,
            ),
            DialogueBeat(
                "SAU MÀN 3 – MÊ CUNG",
                config.PLAYER_NAME,
                "Dù mê cung có phức tạp đến đâu... luôn có đường ra!",
                aris,
            ),
            DialogueBeat(
                "TRƯỚC MÀN 4 – ĐỐI ĐẦU BOSS",
                config.BOSS_NAME,
                f"Ngươi đã đi quá xa rồi, {config.PLAYER_NAME}. Đây sẽ là nơi ngươi kết thúc.",
                orion,
            ),
            DialogueBeat(
                "TRƯỚC MÀN 4 – ĐỐI ĐẦU BOSS",
                config.PLAYER_NAME,
                "Không... đây là nơi ngươi thất bại.",
                aris,
            ),
            DialogueBeat(
                "TRƯỚC MÀN 4 – ĐỐI ĐẦU BOSS",
                config.HOSTAGE_NAME,
                f"{config.PLAYER_NAME}... em tin anh!",
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
                "Sức mạnh thật sự... không nằm ở tính toán.",
                aris,
            ),
            DialogueBeat(
                "KẾT THÚC",
                config.HOSTAGE_NAME,
                f"Anh đã làm được rồi, {config.PLAYER_NAME}!",
                lina,
            ),
            DialogueBeat(
                "KẾT THÚC",
                config.PLAYER_NAME,
                "Chúng ta về thôi... vương quốc đang chờ.",
                aris,
            ),
        ],
        "game_over": [
            DialogueBeat(
                "GAME OVER",
                config.BOSS_NAME,
                "Kết thúc rồi... con người luôn thất bại trước trí tuệ hoàn hảo.",
                orion,
            ),
            DialogueBeat(
                "GAME OVER",
                config.HOSTAGE_NAME,
                f"{config.PLAYER_NAME}... xin đừng bỏ cuộc...",
                lina,
            ),
        ],
    }


class Game:
    """State machine tổng cho menu, chơi game, qua màn, thua và chiến thắng."""

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

        self.assets = AssetManager()
        self.level_specs = build_level_specs()
        self.dialogue_scripts = build_dialogue_scripts()
        self.buttons = [
            ui.Button(pygame.Rect(70, 420, 300, 82), "Bắt đầu", "Chơi ngay"),
            ui.Button(pygame.Rect(70, 520, 300, 82), "Thoát", "Rời game"),
        ]

        pygame.mouse.set_visible(False)

        self.running = True
        self.state = GameState.MENU
        self.level_index = 0
        self.scene = None
        self.total_score = 0
        self.overlay_timer = 0
        self.menu_pulse = 0
        self.dialogue_beats = []
        self.dialogue_index = 0
        self.dialogue_footer = ""
        self.dialogue_subtitle = ""
        self.dialogue_next_action = ""
        self.mouse_pos = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)

    def run(self):
        """Vòng lặp chính của game.

        Mỗi frame chỉ làm 3 việc:
        1. Đọc input
        2. Update state hiện tại
        3. Vẽ state hiện tại
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
        """Phân input theo state để tránh if/else lớn trong mỗi scene."""

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
            else:
                self.handle_overlay_event(event)

    def handle_menu_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        mouse_pos = self.mouse_pos
        if self.buttons[0].hovered(mouse_pos):
            self.start_new_campaign()
        elif self.buttons[1].hovered(mouse_pos):
            self.running = False

    def handle_playing_event(self, event):
        # ESC được giữ lại như một nút thoát nhanh về menu.
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.return_to_menu()

    def handle_dialogue_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_to_menu()
                return
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.advance_dialogue()
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.advance_dialogue()

    def handle_overlay_event(self, event):
        # Sau màn hoặc khi thua, bất kỳ phím/chuột đều là một xác nhận hợp lý.
        if event.type not in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            return

        if self.state == GameState.LEVEL_COMPLETE:
            self.begin_next_level()
        else:
            self.return_to_menu()

    def update(self):
        """Chỉ cập nhật state hiện tại; Game không chen vào nội bộ combat."""

        if self.state == GameState.PLAYING:
            delta_time = self.clock.get_time() / 1000.0
            self.scene.update(delta_time)

            if self.scene.result == "win":
                self.total_score += self.scene.score
                if self.level_index == len(self.level_specs) - 1:
                    self.open_dialogue(
                        "victory",
                        "return_to_menu",
                        subtitle=f"Tổng điểm: {self.total_score}",
                        footer="Nhấn Enter, Space hoặc chuột trái để về menu.",
                    )
                else:
                    self.open_dialogue(
                        f"level_{self.level_index + 1}_clear",
                        "next_level",
                        subtitle=self.scene.result_reason,
                        footer="Nhấn Enter, Space hoặc chuột trái để tiếp tục.",
                    )

            elif self.scene.result == "lose":
                self.total_score += self.scene.score
                self.open_dialogue(
                    "game_over",
                    "return_to_menu",
                    subtitle=self.scene.result_reason,
                    footer="Nhấn Enter, Space hoặc chuột trái để về menu.",
                )

    def draw(self):
        """Mỗi state có cách vẽ riêng, nhưng đều đi qua một điểm trung tâm."""

        if self.state == GameState.MENU:
            ui.draw_menu(
                self.screen,
                self.assets,
                self.buttons,
                self.mouse_pos,
                self.total_score,
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

        elif self.state == GameState.LEVEL_COMPLETE:
            if self.scene:
                self.scene.mouse_pos = pygame.Vector2(self.mouse_pos)
            self.scene.draw(self.screen)
            ui.draw_hud(self.screen, self.assets, self.scene, self.describe_next_upgrade(), self.mouse_pos)
            ui.draw_overlay(
                self.screen,
                self.assets,
                "HOÀN THÀNH",
                self.scene.result_reason,
                "Nhấn phím bất kỳ để qua màn.",
                config.COLOR_ACCENT,
            )

        elif self.state == GameState.GAME_OVER:
            if self.scene:
                self.scene.mouse_pos = pygame.Vector2(self.mouse_pos)
            self.scene.draw(self.screen)
            ui.draw_hud(self.screen, self.assets, self.scene, self.describe_next_upgrade(), self.mouse_pos)
            ui.draw_overlay(
                self.screen,
                self.assets,
                "THẤT BẠI",
                self.scene.result_reason,
                "Nhấn phím bất kỳ để về menu.",
                config.COLOR_DANGER,
            )

        elif self.state == GameState.VICTORY:
            if self.scene:
                self.scene.mouse_pos = pygame.Vector2(self.mouse_pos)
            self.scene.draw(self.screen)
            ui.draw_hud(self.screen, self.assets, self.scene, "Chiến dịch đã hoàn tất.", self.mouse_pos)
            ui.draw_overlay(
                self.screen,
                self.assets,
                "CHIẾN THẮNG",
                f"{config.BOSS_NAME} đã bị hạ. {config.HOSTAGE_NAME} đã an toàn.",
                f"{config.PLAYER_NAME} hoàn thành sứ mệnh | Tổng điểm: {self.total_score}",
                config.COLOR_WARNING,
            )

        self.present_screen()

    def start_new_campaign(self):
        """Reset campaign và tạo scene cho màn đầu tiên."""

        self.total_score = 0
        self.level_index = 0
        self.scene = LevelScene(self.assets, self.level_specs[self.level_index])
        self.open_dialogue(
            "intro",
            "resume_current_level",
            subtitle="Lâu đài bóng tối vừa khép cổng.",
            footer="Nhấn Enter, Space hoặc chuột trái để tiếp.",
        )

    def begin_next_level(self):
        """Chuyển sang màn tiếp theo, nếu hết màn thì vào state chiến thắng."""

        self.level_index += 1
        if self.level_index >= len(self.level_specs):
            self.return_to_menu()
            return

        self.scene = LevelScene(self.assets, self.level_specs[self.level_index])
        self.state = GameState.PLAYING

    def return_to_menu(self):
        """Xóa scene hiện tại để quay lại menu sạch sẽ."""

        self.state = GameState.MENU
        self.scene = None
        self.dialogue_beats = []
        self.dialogue_index = 0
        self.dialogue_footer = ""
        self.dialogue_subtitle = ""
        self.dialogue_next_action = ""

    def configure_display(self):
        """Tạo cửa sổ thật; phần render logic vẫn giữ ở độ phân giải cố định."""

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
        """Mở hội thoại nhiều trang và ghi nhớ hành động sau khi đọc xong."""

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

    def describe_next_upgrade(self):
        """Giữ lại thông tin progression để có thể dùng lại nếu UI cần."""

        current_level = min(self.level_index + 1, len(self.level_specs))
        if self.state == GameState.VICTORY:
            return "Chiến dịch đã hoàn tất."

        next_level = min(len(self.level_specs), current_level + 1)
        if next_level == current_level:
            return "Không còn nâng cấp."

        upgrade = config.upgrade_for_level(next_level)
        return f"Mở khóa: {upgrade.title}"


def main():
    """Entrypoint chung cho file launcher."""

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    Game().run()

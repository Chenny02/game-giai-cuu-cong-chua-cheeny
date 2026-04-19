"""Tiện ích đọc atlas / sprite sheet cho game."""

from __future__ import annotations

import pygame


class SpriteSheet:
    """Đọc sprite sheet theo 2 kiểu:

    1. Grid đều: giữ tương thích với code cũ.
    2. Atlas thủ công: cắt theo từng vùng thật của file PNG.

    Hai sheet `character.png` và `boss.png` trong project không phải sheet dạng lưới
    chuẩn. Chúng là atlas trình bày có chữ, divider và ảnh minh họa lớn. Vì vậy lớp
    này bổ sung cơ chế:
    - cắt theo `rect` thủ công
    - cắt một dải thành N frame đều nhau
    - trim nền tối bằng phân tích màu, không phụ thuộc alpha trong suốt
    """

    def __init__(self, image_path, columns=1, rows=1):
        self.image_path = image_path
        self.sheet = pygame.image.load(str(image_path)).convert_alpha()
        self.columns = max(1, columns or 1)
        self.rows = max(1, rows or 1)
        self.sheet_width, self.sheet_height = self.sheet.get_size()
        self.cell_width = self.sheet_width / self.columns
        self.cell_height = self.sheet_height / self.rows

    def get_frame(self, x, y, w, h, trim=False, size=None, pad=0):
        """Lấy frame theo toạ độ pixel tuyệt đối."""

        rect = pygame.Rect(round(x), round(y), max(1, round(w)), max(1, round(h)))
        rect.clamp_ip(self.sheet.get_rect())
        frame = pygame.Surface(rect.size, pygame.SRCALPHA)
        frame.blit(self.sheet, (0, 0), rect)

        if trim:
            frame = self._trim_dark_background(frame, pad=pad)

        if size is not None:
            frame = pygame.transform.smoothscale(frame, size)

        return frame

    def get_grid_frame(self, col, row, trim=True, size=None, pad=0):
        """Giữ lại API cũ cho sheet grid đều."""

        x0 = round(col * self.cell_width)
        y0 = round(row * self.cell_height)
        x1 = round((col + 1) * self.cell_width)
        y1 = round((row + 1) * self.cell_height)
        return self.get_frame(x0, y0, max(1, x1 - x0), max(1, y1 - y0), trim=trim, size=size, pad=pad)

    def get_row(self, row_index, frame_count, start_col=0, trim=True, size=None, pad=0):
        """Giữ lại API cũ cho animation theo hàng."""

        frames = []
        row_index = max(0, min(self.rows - 1, row_index))
        max_cols = min(self.columns, start_col + frame_count)
        for col in range(start_col, max_cols):
            frames.append(self.get_grid_frame(col, row_index, trim=trim, size=size, pad=pad))

        if not frames:
            frames.append(self.get_grid_frame(0, row_index, trim=trim, size=size, pad=pad))
        return frames

    def get_strip(self, x, y, w, h, frame_count, trim=True, size=None, pad=0):
        """Cắt một dải ngang thành nhiều frame đều nhau.

        Đây là kiểu phù hợp nhất với 2 atlas hiện tại:
        - mỗi animation nằm trong một vùng riêng
        - các frame sắp theo chiều ngang
        - nền tối cần trim lại sau khi cắt
        """

        frames = []
        frame_width = w / max(1, frame_count)
        for index in range(frame_count):
            x0 = x + index * frame_width
            x1 = x + (index + 1) * frame_width
            frames.append(
                self.get_frame(x0, y, max(1, x1 - x0), h, trim=trim, size=size, pad=pad)
            )
        return frames

    def get_frames(self, rects, trim=True, size=None, pad=0):
        """Lấy danh sách frame từ danh sách rect thủ công."""

        return [self.get_frame(x, y, w, h, trim=trim, size=size, pad=pad) for x, y, w, h in rects]

    def get_animation(self, name, row, frames, start_col=0, trim=True, size=None, pad=0):
        """Giữ API cũ để builder không bị gãy khi gặp spec cũ."""

        return name, self.get_row(row, frames, start_col=start_col, trim=trim, size=size, pad=pad)

    def _trim_dark_background(self, frame, pad=0):
        """Cắt bớt nền tối của atlas.

        Ý tưởng:
        - sample màu nền từ viền ngoài của cell
        - pixel được xem là foreground nếu đủ sáng hoặc lệch đủ xa màu nền
        - sau đó nới biên thêm vài pixel để không cắt mất viền phát sáng
        """

        width, height = frame.get_size()
        if width <= 2 or height <= 2:
            return frame

        bg_r, bg_g, bg_b = self._sample_border_color(frame)
        cleaned = pygame.Surface((width, height), pygame.SRCALPHA)

        # Chuyển nền atlas thành alpha thật để xoay/scale không kéo theo ô vuông đen.
        for y in range(height):
            for x in range(width):
                r, g, b, a = frame.get_at((x, y))
                if a == 0:
                    continue

                brightness = max(r, g, b)
                color_distance = abs(r - bg_r) + abs(g - bg_g) + abs(b - bg_b)
                is_foreground = (
                    brightness >= 70
                    or color_distance >= 52
                    or (brightness >= 38 and color_distance >= 34)
                )

                if is_foreground:
                    cleaned.set_at((x, y), (r, g, b, a))

        bounds = cleaned.get_bounding_rect(min_alpha=1)
        if bounds.width <= 0 or bounds.height <= 0:
            return frame

        if pad:
            bounds.inflate_ip(pad * 2, pad * 2)
            bounds = bounds.clip(cleaned.get_rect())

        return cleaned.subsurface(bounds).copy()

    def _sample_border_color(self, frame):
        """Lấy màu nền đại diện từ viền ngoài của cell."""

        width, height = frame.get_size()
        samples = []

        for x in range(width):
            samples.append(frame.get_at((x, 0))[:3])
            samples.append(frame.get_at((x, height - 1))[:3])
        for y in range(1, height - 1):
            samples.append(frame.get_at((0, y))[:3])
            samples.append(frame.get_at((width - 1, y))[:3])

        # Dùng median để ít bị ảnh hưởng bởi vài pixel sáng ở sát mép.
        reds = sorted(color[0] for color in samples)
        greens = sorted(color[1] for color in samples)
        blues = sorted(color[2] for color in samples)
        middle = len(samples) // 2
        return reds[middle], greens[middle], blues[middle]

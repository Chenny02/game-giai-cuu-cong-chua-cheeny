"""He thong animation tong quat cho sprite frame-based."""

import pygame


class Animation:
    """Animation frame-based co ho tro loop va non-loop."""

    def __init__(self, frames, fps=10, loop=True):
        self.frames = frames if frames else [pygame.Surface((8, 8), pygame.SRCALPHA)]
        self.fps = max(1, fps)
        self.loop = loop
        self.frame_duration = 1.0 / self.fps
        self.index = 0
        self.time_acc = 0.0
        self.finished = False

    def reset(self):
        self.index = 0
        self.time_acc = 0.0
        self.finished = False

    def update(self, delta_time):
        if self.finished and not self.loop:
            return
        if len(self.frames) <= 1:
            if not self.loop:
                self.time_acc += delta_time
                if self.time_acc >= self.frame_duration:
                    self.finished = True
            return

        self.time_acc += delta_time
        while self.time_acc >= self.frame_duration:
            self.time_acc -= self.frame_duration
            self.index += 1
            if self.index >= len(self.frames):
                if self.loop:
                    self.index = 0
                else:
                    self.index = len(self.frames) - 1
                    self.finished = True
                    break

    @property
    def current_frame(self):
        return self.frames[self.index]


class AnimationManager:
    """Quan ly viec switch animation va cache bien doi de tiet kiem FPS.

    Y tuong toi uu:
    - Khong rotate lai frame moi frame.
    - Chi rotate khi frame goc hoac goc xoay thay doi.
    - Goc xoay duoc quantize theo bucket de cache hieu qua hon.
    """

    def __init__(self, animations, initial_state=None, angle_step=10):
        self.animations = animations
        self.state = initial_state or next(iter(animations))
        self.current = self.animations[self.state]
        self.angle_step = max(1, angle_step)
        self.transform_cache = {}

    def switch(self, state, restart=False):
        if state not in self.animations:
            return
        if self.state != state:
            self.state = state
            self.current = self.animations[state]
            self.current.reset()
        elif restart:
            self.current.reset()

    def update(self, delta_time):
        self.current.update(delta_time)

    def get_image(self, angle=0.0, flip_x=False):
        base = self.current.current_frame
        quantized_angle = round(angle / self.angle_step) * self.angle_step
        key = (id(base), quantized_angle, flip_x)
        cached = self.transform_cache.get(key)
        if cached is not None:
            return cached

        image = base
        if flip_x:
            image = pygame.transform.flip(image, True, False)
        if quantized_angle:
            image = pygame.transform.rotozoom(image, quantized_angle, 1.0)

        self.transform_cache[key] = image
        return image


def build_animations_from_sheet(sheet, specs):
    """Tiện ích tạo dict Animation từ SpriteSheet + dict config.

    Hỗ trợ 3 kiểu spec:
    - `row` + `frames`: giữ tương thích với sheet dạng grid cũ
    - `sections`: danh sách vùng `(x, y, w, h, frame_count)` để cắt strip ngang
    - `rects`: danh sách rect thủ công cho atlas không đều
    """

    animations = {}
    for name, spec in specs.items():
        trim = spec.get("trim", True)
        size = spec.get("size")
        pad = spec.get("pad", 0)

        if "rects" in spec:
            frames = sheet.get_frames(spec["rects"], trim=trim, size=size, pad=pad)
        elif "sections" in spec:
            frames = []
            for x, y, w, h, frame_count in spec["sections"]:
                frames.extend(sheet.get_strip(x, y, w, h, frame_count, trim=trim, size=size, pad=pad))
        else:
            _, frames = sheet.get_animation(
                name,
                spec.get("row", 0),
                spec.get("frames", 1),
                start_col=spec.get("start_col", 0),
                trim=trim,
                size=size,
                pad=pad,
            )

        animations[name] = Animation(frames, fps=spec.get("fps", 10), loop=spec.get("loop", True))
    return animations


def build_animations_from_frames(frame_bank, specs):
    """Tạo Animation từ các frame đã load sẵn từ thư mục.

    `frame_bank` có dạng:
    - key: tên state, ví dụ `idle`, `run`, `shoot`
    - value: list Surface theo đúng thứ tự phát animation
    """

    animations = {}
    for name, spec in specs.items():
        frames = frame_bank.get(name)
        if not frames:
            continue
        animations[name] = Animation(frames, fps=spec.get("fps", 10), loop=spec.get("loop", True))
    return animations


def build_directional_animations_from_frames(frame_bank, specs):
    """Build nested Animation dicts from directional frame folders.

    `frame_bank` shape:
    - key: state name, for example `idle`, `run`, `shoot`
    - value: dict[token, list[Surface]]
    """

    animations = {}
    for name, spec in specs.items():
        state_bank = frame_bank.get(name)
        if not state_bank:
            continue
        directional = {}
        for token, frames in state_bank.items():
            if not frames:
                continue
            directional[token] = Animation(frames, fps=spec.get("fps", 10), loop=spec.get("loop", True))
        if directional:
            animations[name] = directional
    return animations

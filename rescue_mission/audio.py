"""Small audio manager with generated fallback SFX.

The project does not ship audio files yet, so this module creates short
placeholder tones at runtime. If pygame's mixer is unavailable, all calls turn
into safe no-ops so headless tests and machines without audio devices keep
working.
"""

from array import array
import math

import pygame


class AudioManager:
    def __init__(self):
        self.enabled = False
        self.master_volume = 0.8
        self.sfx_volume = 0.8
        self.music_volume = 0.5
        self.sounds = {}

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self.enabled = True
        except pygame.error:
            self.enabled = False
            return

        self.sounds = {
            "ui_click": self._tone(640, 0.055, 0.28),
            "shoot": self._tone(880, 0.075, 0.2, falloff=True),
            "enemy_shoot": self._tone(420, 0.09, 0.18, falloff=True),
            "hit": self._noise_tone(220, 0.07, 0.24),
            "hurt": self._tone(150, 0.18, 0.32, falloff=True),
            "enemy_down": self._tone(110, 0.18, 0.22, falloff=True),
            "rescue": self._arpeggio((660, 880, 1320), 0.18, 0.26),
            "boss_attack": self._tone(96, 0.28, 0.28, falloff=True),
            "win": self._arpeggio((523, 659, 784, 1046), 0.28, 0.24),
            "lose": self._arpeggio((330, 247, 196), 0.32, 0.28),
        }

    def play(self, name, volume=1.0):
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        sound.set_volume(max(0.0, min(1.0, self.master_volume * self.sfx_volume * volume)))
        sound.play()

    def change_sfx_volume(self, delta):
        self.sfx_volume = max(0.0, min(1.0, self.sfx_volume + delta))

    def change_music_volume(self, delta):
        self.music_volume = max(0.0, min(1.0, self.music_volume + delta))

    def _tone(self, frequency, duration, volume, falloff=False):
        sample_rate = pygame.mixer.get_init()[0]
        total = max(1, int(sample_rate * duration))
        samples = array("h")
        for index in range(total):
            t = index / sample_rate
            envelope = 1.0 - (index / total) if falloff else 1.0
            value = math.sin(2 * math.pi * frequency * t) * volume * envelope
            samples.append(int(max(-1.0, min(1.0, value)) * 32767))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def _noise_tone(self, frequency, duration, volume):
        sample_rate = pygame.mixer.get_init()[0]
        total = max(1, int(sample_rate * duration))
        samples = array("h")
        seed = 17
        for index in range(total):
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            noise = ((seed / 0x7FFFFFFF) * 2.0) - 1.0
            t = index / sample_rate
            envelope = 1.0 - (index / total)
            wave = math.sin(2 * math.pi * frequency * t)
            samples.append(int((wave * 0.45 + noise * 0.55) * volume * envelope * 32767))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def _arpeggio(self, frequencies, duration, volume):
        sample_rate = pygame.mixer.get_init()[0]
        total = max(1, int(sample_rate * duration))
        samples = array("h")
        segment = max(1, total // len(frequencies))
        for index in range(total):
            frequency = frequencies[min(len(frequencies) - 1, index // segment)]
            t = index / sample_rate
            envelope = 1.0 - (index / total) * 0.35
            value = math.sin(2 * math.pi * frequency * t) * volume * envelope
            samples.append(int(max(-1.0, min(1.0, value)) * 32767))
        return pygame.mixer.Sound(buffer=samples.tobytes())

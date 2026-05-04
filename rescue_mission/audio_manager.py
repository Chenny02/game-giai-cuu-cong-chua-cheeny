"""Advanced audio manager for Rescue Mission: Shadow Kingdom.

Handles background music, sound effects, volume control, and smooth transitions.
"""

import os
from pathlib import Path
from typing import Optional

import pygame

from . import config
from .level_system import LevelSpec


# Music track mapping for all game states and levels
MUSIC_TRACKS = {
    "menu": "assets/audio/music/menu_theme.wav",
    "level_1": "assets/audio/music/level_1_castle_infiltration.wav",
    "level_2": "assets/audio/music/level_2_hunted_run.wav",
    "level_3": "assets/audio/music/level_3_shadow_maze.wav",
    "level_4": "assets/audio/music/level_4_combat_pressure.wav",
    "level_5": "assets/audio/music/level_5_aegis_prime_boss.wav",
    "level_6": "assets/audio/music/level_6_orion_final_boss.wav",
    "victory": "assets/audio/music/victory_theme.wav",
    "game_over": "assets/audio/music/game_over.wav",
}

# Sound effects mapping
SFX_TRACKS = {
    "shoot": "assets/audio/sfx/shoot.wav",
    "hit": "assets/audio/sfx/hit.wav",
    "enemy_die": "assets/audio/sfx/enemy_die.wav",
    "boss_roar": "assets/audio/sfx/boss_roar.wav",
    "pickup": "assets/audio/sfx/pickup.wav",
    "button_click": "assets/audio/sfx/button_click.wav",
    "hurt": "assets/audio/sfx/hurt.wav",
    "enemy_down": "assets/audio/sfx/enemy_down.wav",
    "rescue": "assets/audio/sfx/rescue.wav",
    "skill_cast": "assets/audio/sfx/skill_cast.wav",
    "boss_attack": "assets/audio/sfx/boss_attack.wav",
    "win": "assets/audio/sfx/win.wav",
    "lose": "assets/audio/sfx/lose.wav",
}

# Default volume levels (0.0 - 1.0)
DEFAULT_MUSIC_VOLUME = 0.55
DEFAULT_SFX_VOLUME = 0.75
FADE_OUT_DURATION = 700  # milliseconds


class AdvancedAudioManager:
    """Manages game music, SFX, volume, and smooth transitions."""

    def __init__(self):
        """Initialize the audio manager with safe fallback handling."""
        self.enabled = False
        self.music_volume = DEFAULT_MUSIC_VOLUME
        self.sfx_volume = DEFAULT_SFX_VOLUME
        self.sounds = {}
        self.current_music_key = None
        self.music_fade_out_target = None
        self.music_fade_start_time = None
        self.project_root = config.PROJECT_ROOT

        # Try to initialize pygame mixer
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.enabled = True
            print("[Audio] Mixer initialized successfully.")
        except pygame.error as e:
            self.enabled = False
            print(f"[Audio] Warning: Could not initialize mixer: {e}")
            return

        # Load SFX tracks or use fallback
        self._load_sfx_tracks()

    def _load_sfx_tracks(self):
        """Load sound effects from files. Uses fallback if files don't exist."""
        for key, relative_path in SFX_TRACKS.items():
            file_path = self.project_root / relative_path
            if file_path.exists():
                try:
                    self.sounds[key] = pygame.mixer.Sound(str(file_path))
                    print(f"[Audio] Loaded SFX: {key}")
                except pygame.error as e:
                    print(f"[Audio] Warning: Could not load SFX '{key}': {e}")
            else:
                print(f"[Audio] Warning: SFX file not found: {relative_path}")

    def _get_music_track_key(self, level_spec: LevelSpec) -> str:
        """Determine which music track to play based on level spec.
        
        Args:
            level_spec: The level specification object
            
        Returns:
            Music track key (e.g., 'level_1', 'level_5', etc.)
        """
        if level_spec.number == 1:
            return "level_1"
        elif level_spec.number == 2:
            return "level_2"
        elif level_spec.number == 3:
            return "level_3"
        elif level_spec.number == 4:
            return "level_4"
        elif level_spec.number == 5 or level_spec.boss_profile_key == "aegis_prime":
            return "level_5"
        elif level_spec.number == 6 or level_spec.boss_profile_key == "orion_prime":
            return "level_6"
        else:
            # Fallback for unknown levels
            return f"level_{level_spec.number}"

    def play_music(self, track_key: str, loop: bool = True, fade_in_ms: int = 0) -> bool:
        """Play a music track with optional crossfade.
        
        Args:
            track_key: Key from MUSIC_TRACKS (e.g., 'menu', 'level_1')
            loop: Whether to loop the music (-1 for infinite loop)
            fade_in_ms: Fade in duration in milliseconds (0 for immediate play)
            
        Returns:
            True if music started, False if not available or disabled
        """
        if not self.enabled:
            return False

        # Don't replay if already playing the same track
        if self.current_music_key == track_key and pygame.mixer.music.get_busy():
            return True

        # Get the file path
        if track_key not in MUSIC_TRACKS:
            print(f"[Audio] Warning: Unknown music track: {track_key}")
            return False

        relative_path = MUSIC_TRACKS[track_key]
        file_path = self.project_root / relative_path

        if not file_path.exists():
            print(f"[Audio] Warning: Music file not found: {relative_path}")
            return False

        try:
            # If music is playing, fade it out first
            if pygame.mixer.music.get_busy():
                self._start_fade_out(track_key, loop, fade_in_ms)
            else:
                # Load and play immediately
                pygame.mixer.music.load(str(file_path))
                pygame.mixer.music.set_volume(self.music_volume)
                loops = -1 if loop else 0
                pygame.mixer.music.play(loops, fade_ms=fade_in_ms)
                self.current_music_key = track_key
                print(f"[Audio] Playing music: {track_key}")
            return True

        except pygame.error as e:
            print(f"[Audio] Error loading music '{track_key}': {e}")
            return False

    def _start_fade_out(self, next_track_key: str, next_loop: bool, next_fade_in_ms: int):
        """Start fading out current music before switching to next track."""
        if self.enabled:
            pygame.mixer.music.fadeout(FADE_OUT_DURATION)
            self.music_fade_out_target = (next_track_key, next_loop, next_fade_in_ms)
            self.music_fade_start_time = pygame.time.get_ticks()
            print(f"[Audio] Fading out current track, will switch to: {next_track_key}")

    def update(self):
        """Update audio system. Call this in main game loop.
        
        Handles fade-out completion and music switching.
        """
        if not self.enabled or not self.music_fade_out_target:
            return

        elapsed = pygame.time.get_ticks() - self.music_fade_start_time
        if elapsed >= FADE_OUT_DURATION:
            # Fade out complete, switch to next track
            next_track_key, next_loop, next_fade_in_ms = self.music_fade_out_target
            self.music_fade_out_target = None
            self.music_fade_start_time = None

            if next_track_key in MUSIC_TRACKS:
                relative_path = MUSIC_TRACKS[next_track_key]
                file_path = self.project_root / relative_path
                if file_path.exists():
                    try:
                        pygame.mixer.music.load(str(file_path))
                        pygame.mixer.music.set_volume(self.music_volume)
                        loops = -1 if next_loop else 0
                        pygame.mixer.music.play(loops, fade_ms=next_fade_in_ms)
                        self.current_music_key = next_track_key
                        print(f"[Audio] Switched to music: {next_track_key}")
                    except pygame.error as e:
                        print(f"[Audio] Error switching to '{next_track_key}': {e}")

    def play_level_music(self, level_spec: LevelSpec) -> bool:
        """Play music appropriate for a specific level.
        
        Args:
            level_spec: The level specification object
            
        Returns:
            True if music started, False if not available
        """
        track_key = self._get_music_track_key(level_spec)
        return self.play_music(track_key, loop=True, fade_in_ms=500)

    def play_menu_music(self) -> bool:
        """Play the main menu theme."""
        return self.play_music("menu", loop=True, fade_in_ms=300)

    def play_victory_music(self) -> bool:
        """Play the victory theme when campaign is completed."""
        return self.play_music("victory", loop=False, fade_in_ms=500)

    def play_game_over_music(self) -> bool:
        """Play the game over theme when player loses."""
        return self.play_music("game_over", loop=False, fade_in_ms=400)

    def stop_music(self, fade_out_ms: int = 300):
        """Stop current music with optional fade-out.
        
        Args:
            fade_out_ms: Fade out duration in milliseconds
        """
        if not self.enabled or not pygame.mixer.music.get_busy():
            return

        if fade_out_ms > 0:
            pygame.mixer.music.fadeout(fade_out_ms)
        else:
            pygame.mixer.music.stop()

        self.current_music_key = None
        print("[Audio] Music stopped")

    def pause_music(self):
        """Pause the currently playing music."""
        if not self.enabled:
            return

        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            print("[Audio] Music paused")

    def resume_music(self):
        """Resume the paused music."""
        if not self.enabled:
            return

        if pygame.mixer.music.get_busy():
            pygame.mixer.music.unpause()
            print("[Audio] Music resumed")

    def set_music_volume(self, volume: float):
        """Set music volume (0.0 - 1.0).
        
        Args:
            volume: Volume level (clamped to 0.0-1.0)
        """
        self.music_volume = max(0.0, min(1.0, volume))
        if self.enabled:
            pygame.mixer.music.set_volume(self.music_volume)
        print(f"[Audio] Music volume: {self.music_volume:.1%}")

    def set_sfx_volume(self, volume: float):
        """Set sound effects volume (0.0 - 1.0).
        
        Args:
            volume: Volume level (clamped to 0.0-1.0)
        """
        self.sfx_volume = max(0.0, min(1.0, volume))
        # Update all currently playing SFX
        for sound in self.sounds.values():
            sound.set_volume(self.sfx_volume)
        print(f"[Audio] SFX volume: {self.sfx_volume:.1%}")

    def change_music_volume(self, delta: float):
        """Change music volume by delta amount.
        
        Args:
            delta: Amount to change volume by (e.g., 0.1 or -0.1)
        """
        self.set_music_volume(self.music_volume + delta)

    def change_sfx_volume(self, delta: float):
        """Change SFX volume by delta amount.
        
        Args:
            delta: Amount to change volume by (e.g., 0.1 or -0.1)
        """
        self.set_sfx_volume(self.sfx_volume + delta)

    def play_sfx(self, sfx_key: str, volume: Optional[float] = None):
        """Play a sound effect.
        
        Args:
            sfx_key: Key from SFX_TRACKS (e.g., 'shoot', 'hit')
            volume: Optional volume override (0.0 - 1.0), uses sfx_volume if None
        """
        if not self.enabled:
            return

        sound = self.sounds.get(sfx_key)
        if sound is None:
            print(f"[Audio] Warning: SFX not found: {sfx_key}")
            return

        try:
            actual_volume = volume if volume is not None else self.sfx_volume
            sound.set_volume(actual_volume)
            sound.play()
            print(f"[Audio] Playing SFX: {sfx_key}")
        except pygame.error as e:
            print(f"[Audio] Error playing SFX '{sfx_key}': {e}")

    def get_music_status(self) -> dict:
        """Get current music playback status.
        
        Returns:
            Dictionary with music status info
        """
        return {
            "current_track": self.current_music_key,
            "is_playing": pygame.mixer.music.get_busy() if self.enabled else False,
            "music_volume": self.music_volume,
            "sfx_volume": self.sfx_volume,
            "enabled": self.enabled,
        }

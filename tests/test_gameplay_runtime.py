import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from rescue_mission.assets import AssetManager
from rescue_mission.entities import ENEMY_TYPES, Enemy
from rescue_mission.game import Game
from rescue_mission.level_system import LevelScene, build_level_specs
from rescue_mission.states import GameState


class FakePressedKeys:
    def __init__(self, *pressed_keys):
        self.pressed_keys = set(pressed_keys)

    def __getitem__(self, key):
        return key in self.pressed_keys


class GameplayRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        cls.assets = AssetManager()
        cls.levels = build_level_specs()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def make_scene(self, index):
        return LevelScene(self.assets, self.levels[index])

    def make_key_event(self, char):
        return pygame.event.Event(pygame.KEYDOWN, key=ord(char), unicode=char)

    def make_special_key_event(self, key, unicode=""):
        return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode)

    def submit_cheat_code(self, game, code):
        game.handle_playing_event(self.make_special_key_event(pygame.K_h, unicode="h"))
        for char in code:
            game.handle_playing_event(self.make_key_event(char))
        game.handle_playing_event(self.make_special_key_event(pygame.K_RETURN, unicode="\r"))

    def test_builds_all_six_levels(self):
        self.assertEqual(6, len(self.levels))
        self.assertFalse(self.make_scene(0).maze)
        self.assertFalse(self.make_scene(1).maze)
        self.assertTrue(self.make_scene(2).maze)
        self.assertFalse(self.make_scene(3).level_spec.has_boss)
        self.assertIsNotNone(self.make_scene(4).boss)
        self.assertIsNotNone(self.make_scene(5).boss)
        self.assertTrue(self.make_scene(2).level_spec.guidance_enabled)

    def test_player_directional_frames_load_for_all_eight_headings(self):
        directional = self.assets.directional_animation_frames["player"]
        expected = {"e", "se", "s", "sw", "w", "nw", "n", "ne"}
        self.assertEqual(expected, set(directional["idle"].keys()))
        self.assertEqual(expected, set(directional["run"].keys()))
        self.assertEqual(expected, set(directional["shoot"].keys()))

    def test_boss_and_hostage_directional_frames_load_for_all_eight_headings(self):
        expected = {"e", "se", "s", "sw", "w", "nw", "n", "ne"}
        boss = self.assets.directional_animation_frames["boss"]
        hostage = self.assets.directional_animation_frames["hostage"]
        self.assertEqual(expected, set(boss["idle"].keys()))
        self.assertEqual(expected, set(boss["move"].keys()))
        self.assertEqual(expected, set(hostage["idle"].keys()))
        self.assertEqual(expected, set(hostage["walk"].keys()))

    def test_level_objectives_match_design(self):
        for index in range(3):
            scene = self.make_scene(index)
            scene.player.pos = pygame.Vector2(scene.hostage.pos)
            scene.handle_collisions()
            scene.check_objectives()
            self.assertTrue(scene.hostage.rescued)
            self.assertEqual("win", scene.result)

        pressure_scene = self.make_scene(3)
        pressure_scene.player.pos = pygame.Vector2(pressure_scene.hostage.pos)
        pressure_scene.handle_collisions()
        self.assertFalse(pressure_scene.hostage.rescued)
        pressure_scene.defeated_enemies = pressure_scene.level_spec.kill_target
        pressure_scene.handle_collisions()
        self.assertTrue(pressure_scene.hostage.rescued)
        pressure_scene.check_objectives()
        self.assertEqual("win", pressure_scene.result)

        for index in (4, 5):
            boss_scene = self.make_scene(index)
            boss_scene.player.pos = pygame.Vector2(boss_scene.hostage.pos)
            boss_scene.handle_collisions()
            boss_scene.check_objectives()
            self.assertFalse(boss_scene.hostage.rescued)
            self.assertIsNone(boss_scene.result)

            boss_scene.boss.health = 0
            boss_scene.handle_collisions()
            boss_scene.player.pos = pygame.Vector2(boss_scene.hostage.pos)
            boss_scene.handle_collisions()
            boss_scene.check_objectives()
            self.assertEqual("win", boss_scene.result)

    def test_timers_scale_with_delta_time(self):
        scene = self.make_scene(5)
        initial_time_left = scene.time_left
        initial_spawn_timer = scene.spawn_timer
        initial_primary = scene.boss.primary_timer
        scene.update(0.5)
        self.assertAlmostEqual(initial_time_left - 0.5, scene.time_left, places=3)
        self.assertAlmostEqual(initial_spawn_timer - 0.5, scene.spawn_timer, places=3)
        self.assertAlmostEqual(initial_primary - 0.5, scene.boss.primary_timer, places=3)

    def test_player_can_move_with_arrow_keys(self):
        scene = self.make_scene(0)
        start_pos = pygame.Vector2(scene.player.pos)

        with mock.patch(
            "pygame.key.get_pressed",
            return_value=FakePressedKeys(pygame.K_RIGHT),
        ), mock.patch(
            "pygame.mouse.get_pos",
            return_value=(round(start_pos.x), round(start_pos.y)),
        ), mock.patch(
            "pygame.mouse.get_pressed",
            return_value=(False, False, False),
        ):
            scene.player.update(scene, 1 / 60)

        self.assertGreater(scene.player.pos.x, start_pos.x)
        self.assertEqual(start_pos.y, scene.player.pos.y)

        scene.player.pos = pygame.Vector2(start_pos)
        with mock.patch(
            "pygame.key.get_pressed",
            return_value=FakePressedKeys(pygame.K_UP),
        ), mock.patch(
            "pygame.mouse.get_pos",
            return_value=(round(start_pos.x), round(start_pos.y)),
        ), mock.patch(
            "pygame.mouse.get_pressed",
            return_value=(False, False, False),
        ):
            scene.player.update(scene, 1 / 60)

        self.assertLess(scene.player.pos.y, start_pos.y)
        self.assertEqual(start_pos.x, scene.player.pos.x)

    def test_hostage_stays_inside_world_after_rescue(self):
        scene = self.make_scene(5)
        scene.hostage.rescued = True
        scene.player.pos = pygame.Vector2(scene.world_rect.left + 18, scene.world_rect.top + 18)

        for _ in range(240):
            scene.hostage.update(scene, 1 / 60)
            self.assertTrue(scene.world_rect.collidepoint(scene.hostage.pos))

    def test_hostage_does_not_enter_blocked_maze_cells(self):
        scene = self.make_scene(2)
        scene.hostage.rescued = True
        scene.player.pos = pygame.Vector2(scene.maze.cell_to_world(scene.maze.player_start))
        scene.hostage.pos = pygame.Vector2(scene.maze.cell_to_world(scene.maze.hostage_cell))

        for _ in range(180):
            scene.hostage.update(scene, 1 / 60)
            self.assertTrue(scene.maze.is_walkable_cell(scene.maze.world_to_cell(scene.hostage.pos)))

    def test_energy_shot_spawns_projectile_and_deals_damage(self):
        scene = self.make_scene(3)
        enemy = Enemy((scene.player.pos.x + 40, scene.player.pos.y), self.assets, ENEMY_TYPES["grunt"], scene.level_spec.number)
        scene.enemies.add(enemy)

        self.assertTrue(scene.player.skill.try_cast(scene.player, scene, pygame.Vector2(1, 0)))
        self.assertEqual(1, len(scene.skill_projectiles))
        projectile = next(iter(scene.skill_projectiles))
        projectile.pos = pygame.Vector2(enemy.pos)
        projectile.rect.center = (round(enemy.pos.x), round(enemy.pos.y))
        scene.handle_collisions()

        self.assertLess(enemy.health, enemy.max_health)
        self.assertEqual(0, len(scene.skill_projectiles))
        self.assertLess(scene.player.skill.energy, scene.player.skill.snapshot().max_energy)

    def test_chenny_toggles_invincibility_and_blocks_damage(self):
        game = Game()
        game.state = GameState.PLAYING
        game.scene = game.create_level_scene(0)

        self.submit_cheat_code(game, "chenny")

        self.assertTrue(game.invincible_enabled)
        self.assertTrue(game.scene.player_invincible)
        health_before = game.scene.player.health
        self.assertFalse(game.scene.player.take_damage(20, scene=game.scene))
        self.assertEqual(health_before, game.scene.player.health)

        self.submit_cheat_code(game, "chenny")

        self.assertFalse(game.invincible_enabled)
        self.assertFalse(game.scene.player_invincible)
        self.assertTrue(game.scene.player.take_damage(20, scene=game.scene))
        self.assertEqual(health_before - 20, game.scene.player.health)

    def test_rabbit_finishes_level_with_normal_win_flow(self):
        game = Game()
        game.state = GameState.PLAYING
        game.scene = game.create_level_scene(0)

        self.submit_cheat_code(game, "rabbit")

        self.assertEqual("win", game.scene.result)
        self.assertTrue(game.scene.hostage.rescued)
        game.update()
        self.assertEqual(GameState.DIALOGUE, game.state)
        self.assertEqual("next_level", game.dialogue_next_action)

    def test_rabbit_finishes_boss_level_into_victory_flow(self):
        game = Game()
        game.level_index = len(game.level_specs) - 1
        game.state = GameState.PLAYING
        game.scene = game.create_level_scene(game.level_index)

        self.submit_cheat_code(game, "rabbit")

        self.assertEqual("win", game.scene.result)
        self.assertTrue(game.scene.hostage.rescued)
        self.assertEqual(0, game.scene.boss.health)
        game.update()
        self.assertEqual(GameState.DIALOGUE, game.state)
        self.assertEqual("return_to_menu", game.dialogue_next_action)

    def test_emyeutho_spawns_companion_and_dialogue(self):
        game = Game()
        game.state = GameState.PLAYING
        game.scene = game.create_level_scene(0)

        self.submit_cheat_code(game, "emyeutho")

        self.assertTrue(game.love_rabbit_enabled)
        self.assertIsNotNone(game.scene.love_rabbit)
        self.assertEqual(GameState.DIALOGUE, game.state)
        self.assertEqual("resume_current_level", game.dialogue_next_action)
        self.assertEqual("Thỏ tai đỏ", game.current_dialogue().speaker)

    def test_typing_without_enter_does_not_activate_cheat(self):
        game = Game()
        game.state = GameState.PLAYING
        game.scene = game.create_level_scene(0)

        for char in "chenny":
            game.handle_playing_event(self.make_key_event(char))

        self.assertFalse(game.invincible_enabled)
        self.assertTrue(game.cheat_prompt_active)
        self.assertEqual("enny", game.cheat_input)

    def test_invalid_cheat_code_shows_status_and_does_not_activate(self):
        game = Game()
        game.state = GameState.PLAYING
        game.scene = game.create_level_scene(0)

        self.submit_cheat_code(game, "abc")

        self.assertFalse(game.invincible_enabled)
        self.assertFalse(game.cheat_prompt_active)
        self.assertEqual("", game.cheat_input)
        self.assertEqual("Lệnh hack không hợp lệ.", game.scene.status_message)

    def test_escape_closes_cheat_prompt_without_pausing(self):
        game = Game()
        game.state = GameState.PLAYING
        game.scene = game.create_level_scene(0)

        game.handle_playing_event(self.make_special_key_event(pygame.K_h, unicode="h"))
        game.handle_playing_event(self.make_key_event("c"))
        game.handle_playing_event(self.make_special_key_event(pygame.K_ESCAPE))

        self.assertEqual(GameState.PLAYING, game.state)
        self.assertFalse(game.cheat_prompt_active)
        self.assertEqual("", game.cheat_input)

    def test_invincibility_persists_across_levels_and_resets_on_menu(self):
        game = Game()
        game.invincible_enabled = True
        game.scene = game.create_level_scene(0)
        self.assertTrue(game.scene.player_invincible)

        game.begin_next_level()
        self.assertTrue(game.invincible_enabled)
        self.assertTrue(game.scene.player_invincible)

        game.return_to_menu()
        self.assertFalse(game.invincible_enabled)
        self.assertFalse(game.cheat_prompt_active)
        self.assertEqual("", game.cheat_input)

        game.start_new_campaign()
        self.assertFalse(game.invincible_enabled)
        self.assertFalse(game.scene.player_invincible)

    def test_escape_pauses_and_retry_recreates_current_level(self):
        game = Game()
        game.state = GameState.PLAYING
        game.level_index = 1
        game.scene = game.create_level_scene(game.level_index)
        original_scene = game.scene

        game.handle_playing_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""))
        self.assertEqual(GameState.PAUSED, game.state)

        game.restart_current_level()
        self.assertEqual(GameState.PLAYING, game.state)
        self.assertIsNot(original_scene, game.scene)
        self.assertEqual(2, game.scene.level_spec.number)

    def test_pressure_level_unlocks_hostage_only_after_required_kills(self):
        scene = self.make_scene(3)
        scene.player.pos = pygame.Vector2(scene.hostage.pos)
        scene.handle_collisions()
        self.assertFalse(scene.hostage.rescued)
        self.assertTrue(scene.status_message)
        self.assertIn("14", scene.status_message)

        scene.defeated_enemies = scene.level_spec.kill_target
        scene.handle_collisions()
        self.assertTrue(scene.hostage.rescued)

    def test_lose_flow_opens_retryable_game_over(self):
        game = Game()
        game.state = GameState.PLAYING
        game.level_index = 0
        game.scene = game.create_level_scene(game.level_index)
        game.scene.player.health = 0

        game.update()
        self.assertEqual(GameState.GAME_OVER, game.state)

        game.handle_game_over_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r, unicode="r"))
        self.assertEqual(GameState.PLAYING, game.state)
        self.assertGreater(game.scene.player.health, 0)


if __name__ == "__main__":
    unittest.main()

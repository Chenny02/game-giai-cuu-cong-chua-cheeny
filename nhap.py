import pygame
import sys
import random
import math
import os 
from collections import deque

pygame.init()

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Rescue Mission: Shadow Protocol")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)
big_font = pygame.font.Font(None, 72)

BLACK = (0, 0, 0)
BLUE = (0, 100, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
GRAY = (128, 128, 128)
PURPLE = (200, 0, 200)

player_img = enemy_img = hostage_img = boss_img = bg_img = None

try:
    base_path = os.path.dirname(__file__)
    assets = os.path.join(base_path, "assets")

    player_img  = pygame.image.load(os.path.join(assets, 'player.png')).convert_alpha()
    enemy_img   = pygame.image.load(os.path.join(assets, 'enemy.png')).convert_alpha()
    hostage_img = pygame.image.load(os.path.join(assets, 'hostage.png')).convert_alpha()
    boss_img    = pygame.image.load(os.path.join(assets, 'boss.png')).convert_alpha()
    bg_img      = pygame.image.load(os.path.join(assets, 'bg.png')).convert()

except Exception as e:
    print("Lỗi load ảnh:", e)
    print("Dùng hình mặc định")

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, tx, ty, speed=8):
        super().__init__()
        self.image = pygame.Surface((5, 10))
        self.image.fill(WHITE)
        self.rect = self.image.get_rect(center=(x, y))
        dx, dy = tx - x, ty - y
        dist = math.hypot(dx, dy)
        if dist == 0:
            self.vel_x = 0
            self.vel_y = -speed
        else:
            self.vel_x = dx / dist * speed
            self.vel_y = dy / dist * speed

    def update(self):
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        if not screen.get_rect().colliderect(self.rect):
            self.kill()


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, bullet_group):
        super().__init__()
        self.image = pygame.Surface((50, 50))
        self.image.fill(BLUE)
        if player_img:
            self.image = pygame.transform.scale(player_img, (50, 50))
        self.rect = self.image.get_rect(center=(x, y))

        self.speed = 4
        self.health = 100
        self.bullets = bullet_group
        self.shoot_cooldown = 0
        self.last_dir = pygame.math.Vector2(0, -1)  # mặc định nhìn lên

    def update(self):
        keys = pygame.key.get_pressed()
        move = pygame.math.Vector2(0, 0)

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1

        if move.length_squared() > 0:
            move = move.normalize()
            self.last_dir = move
            self.rect.x += move.x * self.speed
            self.rect.y += move.y * self.speed

        self.rect.clamp_ip(screen.get_rect())

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        # Bắn theo hướng last_dir
        if keys[pygame.K_SPACE] and self.shoot_cooldown <= 0:
            tx = self.rect.centerx + self.last_dir.x * 100
            ty = self.rect.centery + self.last_dir.y * 100
            bullet = Bullet(self.rect.centerx, self.rect.centery, tx, ty, speed=10)
            self.bullets.add(bullet)
            self.shoot_cooldown = 10

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, player, maze=None, enemy_bullets_group=None):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill(RED)
        if enemy_img:
            self.image = pygame.transform.scale(enemy_img, (25, 25))
        self.rect = self.image.get_rect(center=(x, y))

        self.player = player
        self.speed = 2
        self.health = 1
        self.maze = maze
        self.path = []
        self.path_time = 0

        self.enemy_bullets = enemy_bullets_group
        self.shoot_timer = random.randint(30, 120)

    def bfs_path(self):
        if not self.maze or self.path_time > 0:
            return
        grid_size = 20
        start = (self.rect.centerx // grid_size, self.rect.centery // grid_size)
        goal = (self.player.rect.centerx // grid_size, self.player.rect.centery // grid_size)

        if start == goal:
            return

        queue = deque([start])
        came_from = {start: None}
        visited = {start}

        while queue:
            current = queue.popleft()
            if current == goal:
                self.path = []
                while current != start:
                    self.path.append(current)
                    current = came_from[current]
                self.path.reverse()
                self.path_time = 60
                return

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                if (0 <= neighbor[0] < self.maze.width and
                        0 <= neighbor[1] < self.maze.height and
                        self.maze.grid[neighbor[1]][neighbor[0]] == 0 and
                        neighbor not in visited):
                    visited.add(neighbor)
                    queue.append(neighbor)
                    came_from[neighbor] = current

    def update(self):
        self.path_time -= 1
        self.bfs_path()

        if self.path:
            next_pos = self.path[0]
            target_x = next_pos[0] * 20 + 10
            target_y = next_pos[1] * 20 + 10
            dx = target_x - self.rect.centerx
            dy = target_y - self.rect.centery
            dist = math.hypot(dx, dy)
            if dist > 5:
                self.rect.x += (dx / dist) * self.speed
                self.rect.y += (dy / dist) * self.speed
            else:
                self.path.pop(0)
        else:
            dx = self.player.rect.centerx - self.rect.centerx
            dy = self.player.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.rect.x += (dx / dist) * self.speed
                self.rect.y += (dy / dist) * self.speed

        # Bắn đạn về phía player
        if self.enemy_bullets and self.shoot_timer > 0:
            self.shoot_timer -= 1

        if self.enemy_bullets and self.shoot_timer <= 0:
            bullet = Bullet(
                self.rect.centerx,
                self.rect.centery,
                self.player.rect.centerx,
                self.player.rect.centery,
                speed=6
            )
            self.enemy_bullets.add(bullet)
            self.shoot_timer = random.randint(60, 150)
class Hostage(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((20, 30))
        self.image.fill(YELLOW)
        if hostage_img:
            self.image = pygame.transform.scale(hostage_img, (20, 30))
        self.rect = self.image.get_rect(center=(x, y))
        self.rescued = False


class Boss(pygame.sprite.Sprite):
    def __init__(self, x, y, player, enemy_bullets_group):
        super().__init__()
        self.image = pygame.Surface((80, 80))
        self.image.fill(PURPLE)
        if boss_img:
            self.image = pygame.transform.scale(boss_img, (80, 80))
        self.rect = self.image.get_rect(center=(x, y))
        self.player = player
        self.health = 300
        self.max_health = 300
        self.speed = 1.5
        self.phase = 1
        self.shoot_timer = 0
        self.enemy_bullets = enemy_bullets_group

    def update(self):
        self.shoot_timer -= 1
        dx = self.player.rect.centerx - self.rect.centerx
        dy = self.player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 100:
            self.rect.x += (dx / dist) * self.speed
            self.rect.y += (dy / dist) * self.speed

        if self.phase >= 2 and self.shoot_timer <= 0:
            bullet = Bullet(self.rect.centerx, self.rect.centery + 40,
                            self.player.rect.centerx, self.player.rect.centery,
                            speed=6)
            self.enemy_bullets.add(bullet)
            self.shoot_timer = 90

        if self.health < 200:
            self.phase = 2
        if self.health < 100:
            self.phase = 3
            self.speed = 2.5


class Maze:
    def __init__(self, width=40, height=25):
        self.width = width
        self.height = height
        self.grid = [[1] * width for _ in range(height)]
        self.generate_dfs(1, 1)
        self.player_start = (2, 2)
        self.hostage_pos = (width - 3, height - 3)

    def generate_dfs(self, x, y):
        stack = [(x, y)]
        self.grid[y][x] = 0
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]

        while stack:
            cx, cy = stack[-1]
            neighbors = []
            for dx, dy in directions:
                nx, ny = cx + dx * 2, cy + dy * 2
                if (0 < nx < self.width - 1 and 0 < ny < self.height - 1 and
                        self.grid[ny][nx] == 1):
                    neighbors.append((nx, ny))

            if neighbors:
                nx, ny = random.choice(neighbors)
                wx, wy = (cx + nx) // 2, (cy + ny) // 2
                self.grid[wy][wx] = 0
                self.grid[ny][nx] = 0
                stack.append((nx, ny))
            else:
                stack.pop()

    def draw(self, surface, offset_y=0):
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == 1:
                    pygame.draw.rect(surface, GRAY, (x * 20, y * 20 + offset_y, 20, 20))


def draw_hud(timer, score, health, level, boss_health=None):
    pygame.draw.rect(screen, (50, 50, 50), (5, 5, 300, 70), border_radius=10)
    pygame.draw.rect(screen, GREEN, (5, 5, 300, 70), 3, border_radius=10)

    screen.blit(font.render(f"LEVEL {level}", True, WHITE), (15, 10))
    screen.blit(font.render(f"Time: {timer // 60}", True, WHITE), (15, 35))
    screen.blit(font.render(f"Score: {score}", True, GREEN), (15, 60))

    bar_width = 200
    health_width = (health / 100) * bar_width
    pygame.draw.rect(screen, RED, (320, 10, bar_width, 25), border_radius=5)
    pygame.draw.rect(screen, GREEN, (325, 15, health_width, 15), border_radius=3)
    screen.blit(font.render("HEALTH", True, WHITE), (320, 40))

    if boss_health is not None:
        boss_width = (boss_health / 300) * bar_width
        pygame.draw.rect(screen, PURPLE, (550, 10, bar_width, 25), border_radius=5)
        pygame.draw.rect(screen, YELLOW, (555, 15, boss_width, 15), border_radius=3)
        screen.blit(font.render("ORION", True, WHITE), (550, 40))


def main_menu():
    while True:
        screen.fill((20, 20, 40))
        title = big_font.render("RESCUE MISSION", True, WHITE)
        subtitle = font.render("SHADOW PROTOCOL - 2045", True, GREEN)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 200))
        screen.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 290))

        play_rect = pygame.Rect(SCREEN_WIDTH // 2 - 120, 420, 240, 70)
        quit_rect = pygame.Rect(SCREEN_WIDTH // 2 - 120, 520, 240, 70)

        mouse_pos = pygame.mouse.get_pos()
        color_play = GREEN if play_rect.collidepoint(mouse_pos) else (0, 200, 0)
        color_quit = RED if quit_rect.collidepoint(mouse_pos) else (200, 0, 0)

        pygame.draw.rect(screen, color_play, play_rect, border_radius=15)
        pygame.draw.rect(screen, WHITE, play_rect, 3, border_radius=15)
        screen.blit(font.render("START MISSION", True, BLACK),
                    (play_rect.x + 30, play_rect.y + 25))

        pygame.draw.rect(screen, color_quit, quit_rect, border_radius=15)
        pygame.draw.rect(screen, WHITE, quit_rect, 3, border_radius=15)
        screen.blit(font.render("QUIT", True, WHITE),
                    (quit_rect.x + 100, quit_rect.y + 25))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if play_rect.collidepoint(event.pos):
                    return True
                if quit_rect.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()

        pygame.display.flip()
        clock.tick(60)


def play_level(level_num):
    all_sprites = pygame.sprite.Group()
    bullets = pygame.sprite.Group()
    enemy_bullets = pygame.sprite.Group()

    if level_num == 3:
        maze = Maze()
        player = Player(maze.player_start[0] * 20 + 10, maze.player_start[1] * 20 + 10, bullets)
        hostage = Hostage(maze.hostage_pos[0] * 20 + 10, maze.hostage_pos[1] * 20 + 10)
    else:
        maze = None
        player = Player(50, SCREEN_HEIGHT // 2, bullets)
        hostage = Hostage(SCREEN_WIDTH - 100, SCREEN_HEIGHT // 2)

    all_sprites.add(player, hostage, bullets, enemy_bullets)

    enemies = pygame.sprite.Group()
    boss = None

    if level_num == 4:
        boss = Boss(SCREEN_WIDTH // 2, 100, player, enemy_bullets)
        all_sprites.add(boss)

    timer = 180 * 60
    score = 0
    running = True

    while running and timer > 0 and player.health > 0:
        clock.tick(60)
        timer -= 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        player.update()
        bullets.update()
        enemy_bullets.update()
        for enemy in enemies:
            enemy.update()
        if boss:
            boss.update()

        spawn_chance = max(5, 40 - level_num * 5)
        if random.randint(1, spawn_chance) == 1 and len(enemies) < 4 + level_num:
            ex = random.randint(SCREEN_WIDTH - 200, SCREEN_WIDTH)
            ey = random.randint(50, 150)
            enemy = Enemy(ex, ey, player, maze)
            enemies.add(enemy)
            all_sprites.add(enemy)

        for bullet in bullets:
            enemy_hits = pygame.sprite.spritecollide(bullet, enemies, True)
            if enemy_hits:
                score += 20 * len(enemy_hits)
                bullet.kill()

            if boss and pygame.sprite.collide_rect(bullet, boss):
                boss.health -= 15
                bullet.kill()
                score += 50

        if pygame.sprite.spritecollide(player, enemies, True):
            player.health -= 25

        if pygame.sprite.spritecollide(player, enemy_bullets, True):
            player.health -= 10

        if not hostage.rescued and pygame.sprite.collide_rect(player, hostage):
            hostage.rescued = True
            score += 300
            hostage.kill()

        if level_num == 4:
            if boss and boss.health <= 0 and hostage.rescued:
                return True, score
        elif hostage.rescued:
            return True, score

        screen.fill(BLACK)
        if bg_img:
            screen.blit(pygame.transform.scale(bg_img, (SCREEN_WIDTH, SCREEN_HEIGHT)), (0, 0))
        if maze:
            maze.draw(screen)
        all_sprites.draw(screen)
        draw_hud(timer, score, player.health, level_num, boss.health if boss else None)

        pygame.display.flip()

    return False, score


def game_loop():
    if not main_menu():
        return

    total_score = 0
    for level in range(1, 5):
        print(f"Bắt đầu màn {level}...")
        win, score = play_level(level)
        total_score += score

        if not win:
            screen.fill(RED)
            gameover = big_font.render("MISSION FAILED", True, WHITE)
            screen.blit(gameover,
                        (SCREEN_WIDTH // 2 - gameover.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
            restart = font.render("Nhấn ESC để thoát", True, WHITE)
            screen.blit(restart,
                        (SCREEN_WIDTH // 2 - restart.get_width() // 2, SCREEN_HEIGHT // 2 + 20))
            pygame.display.flip()

            waiting = True
            while waiting:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        waiting = False
            return

        screen.fill(GREEN)
        next_text = big_font.render(f"LEVEL {level} COMPLETE", True, BLACK)
        screen.blit(next_text,
                    (SCREEN_WIDTH // 2 - next_text.get_width() // 2, SCREEN_HEIGHT // 2))
        pygame.display.flip()
        pygame.time.wait(2000)

    screen.fill((0, 150, 0))
    victory = big_font.render("MISSION SUCCESS", True, WHITE)
    score_text = font.render(f"Total Score: {total_score}", True, YELLOW)
    screen.blit(victory,
                (SCREEN_WIDTH // 2 - victory.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
    screen.blit(score_text,
                (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2 + 30))
    thanks = font.render("Cảm ơn đã chơi! - Aris đã cứu Lina <3", True, WHITE)
    screen.blit(thanks,
                (SCREEN_WIDTH // 2 - thanks.get_width() // 2, SCREEN_HEIGHT // 2 + 80))
    pygame.display.flip()
    pygame.time.wait(5000)


if __name__ == "__main__":
    game_loop()
    pygame.quit()
    sys.exit()
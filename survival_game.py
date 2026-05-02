import pygame
import random
import math
import sys

pygame.init()

# --- Constants ---
WIDTH, HEIGHT   = 900, 600
FPS             = 60

BG         = (20, 22, 35)
C_PLAYER   = (80, 160, 255)
C_OUTLINE  = (200, 230, 255)
C_SQUARE   = (220, 60, 60)
C_SQ_OUT   = (255, 130, 130)
C_GOAL     = (60, 220, 100)
C_HEART    = (220, 50, 50)
C_HEART_E  = (70, 35, 35)
C_WHITE    = (255, 255, 255)
C_DIM      = (150, 150, 170)
C_YELLOW   = (255, 215, 50)

PLAYER_R    = 16
PLAYER_SPD  = 4.5
SQ_SIZE     = 32
SQ_BASE_V   = 2.3
INV_MS      = 2000          # invincibility duration in ms

TOTAL_LEVELS = 5
SQUARES_PER  = [8, 11, 15, 19, 24]   # squares per level
GOAL_X       = WIDTH - 28             # x position of the goal line

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Survival")
clock = pygame.time.Clock()

F_TITLE = pygame.font.SysFont(None, 84)
F_MED   = pygame.font.SysFont(None, 40)
F_SM    = pygame.font.SysFont(None, 28)


# --- Player ---

class Player:
    def __init__(self):
        self.lives = 3
        self.reset()

    def reset(self):
        self.x = float(PLAYER_R + 44)
        self.y = float(HEIGHT / 2)
        self.inv   = False
        self.inv_t = 0

    def move(self, keys):
        dx = float(keys[pygame.K_d] - keys[pygame.K_a])
        dy = float(keys[pygame.K_s] - keys[pygame.K_w])
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        self.x = max(PLAYER_R, min(WIDTH  - PLAYER_R, self.x + dx * PLAYER_SPD))
        self.y = max(PLAYER_R, min(HEIGHT - PLAYER_R, self.y + dy * PLAYER_SPD))
        if self.inv and pygame.time.get_ticks() - self.inv_t >= INV_MS:
            self.inv = False

    def hit(self):
        if not self.inv:
            self.lives -= 1
            self.inv   = True
            self.inv_t = pygame.time.get_ticks()

    def draw(self, surf):
        # Flash during invincibility
        if self.inv and (pygame.time.get_ticks() - self.inv_t) // 140 % 2:
            return
        p = (int(self.x), int(self.y))
        pygame.draw.circle(surf, C_PLAYER,  p, PLAYER_R)
        pygame.draw.circle(surf, C_OUTLINE, p, PLAYER_R, 2)


# --- Square obstacle ---

class Square:
    def __init__(self, vmul):
        cx, cy = WIDTH // 2, HEIGHT // 2
        self.x = float(random.randint(cx - WIDTH  // 5, cx + WIDTH  // 5))
        self.y = float(random.randint(cy - HEIGHT // 4, cy + HEIGHT // 4))
        self.s = SQ_SIZE
        v  = SQ_BASE_V * vmul * random.uniform(0.75, 1.4)
        a  = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(a) * v
        self.vy = math.sin(a) * v

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.x < 0:                self.x = 0;              self.vx =  abs(self.vx)
        if self.x + self.s > WIDTH:   self.x = WIDTH  - self.s; self.vx = -abs(self.vx)
        if self.y < 0:                self.y = 0;              self.vy =  abs(self.vy)
        if self.y + self.s > HEIGHT:  self.y = HEIGHT - self.s; self.vy = -abs(self.vy)

    def draw(self, surf):
        r = pygame.Rect(int(self.x), int(self.y), self.s, self.s)
        pygame.draw.rect(surf, C_SQUARE, r)
        pygame.draw.rect(surf, C_SQ_OUT, r, 2)

    def hits(self, player):
        # Circle–rectangle collision
        cx = max(self.x, min(player.x, self.x + self.s))
        cy = max(self.y, min(player.y, self.y + self.s))
        return (player.x - cx) ** 2 + (player.y - cy) ** 2 < PLAYER_R ** 2


# --- Helpers ---

def make_level(n):
    vmul = 1.0 + (n - 1) * 0.18
    return [Square(vmul) for _ in range(SQUARES_PER[n - 1])]


def draw_heart(surf, cx, cy, size, color):
    r = size // 4
    pygame.draw.circle(surf, color, (cx - r, cy - 2), r)
    pygame.draw.circle(surf, color, (cx + r, cy - 2), r)
    pygame.draw.polygon(surf, color, [
        (cx - size // 2 + 3, cy + 1),
        (cx + size // 2 - 3, cy + 1),
        (cx, cy + size // 2),
    ])


def draw_hud(surf, player, level):
    hs, hg = 24, 7
    hx, hy = 14, 10
    total = max(3, player.lives)   # always show at least 3 slots
    for i in range(total):
        col = C_HEART if i < player.lives else C_HEART_E
        cx  = hx + i * (hs + hg) + hs // 2
        cy  = hy + hs // 2
        draw_heart(surf, cx, cy, hs, col)

    lv = F_SM.render(f"Level {level} / {TOTAL_LEVELS}", True, C_DIM)
    surf.blit(lv, (WIDTH // 2 - lv.get_width() // 2, 13))

    tip = F_SM.render("Reach the right side  →", True, C_DIM)
    surf.blit(tip, (WIDTH // 2 - tip.get_width() // 2, HEIGHT - 27))


def draw_goal(surf):
    for y in range(0, HEIGHT, 18):
        pygame.draw.line(surf, C_GOAL, (GOAL_X, y), (GOAL_X, min(y + 10, HEIGHT)), 3)
    lbl = F_SM.render("GOAL", True, C_GOAL)
    surf.blit(lbl, (GOAL_X - lbl.get_width() // 2, HEIGHT // 2 - lbl.get_height() // 2))


def render_scene(surf, player, squares, level):
    surf.fill(BG)
    draw_goal(surf)
    for sq in squares:
        sq.draw(surf)
    player.draw(surf)
    draw_hud(surf, player, level)


def overlay(surf, title, sub, tc=C_WHITE):
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 175))
    surf.blit(ov, (0, 0))
    t = F_TITLE.render(title, True, tc)
    surf.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 68))
    if sub:
        s = F_MED.render(sub, True, C_DIM)
        surf.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 + 14))
    pygame.display.flip()


def wait_for_key():
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                return
        clock.tick(FPS)


# --- Main loop ---

def main():
    # Title screen
    screen.fill(BG)
    overlay(screen, "SURVIVAL", "Press any key to begin", C_YELLOW)
    wait_for_key()

    player  = Player()
    level   = 1
    squares = make_level(level)

    while True:
        # Events
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        # Update
        player.move(pygame.key.get_pressed())
        for sq in squares:
            sq.update()

        # Collision — only register one hit per frame
        for sq in squares:
            if sq.hits(player):
                player.hit()
                break

        # Win level: player reached the right side
        if player.x + PLAYER_R >= GOAL_X:
            render_scene(screen, player, squares, level)
            if level == TOTAL_LEVELS:
                overlay(screen, "YOU WIN!", "Congratulations!", C_GOAL)
                wait_for_key()
                return
            overlay(screen, f"Level {level} Clear!", "Press any key  ·  +1 life", C_GOAL)
            wait_for_key()
            level += 1
            player.lives = min(8, player.lives + 1)
            player.reset()
            squares = make_level(level)
            continue

        # Lose: no lives left
        if player.lives <= 0:
            render_scene(screen, player, squares, level)
            overlay(screen, "GAME OVER", "Press any key to exit", C_SQUARE)
            wait_for_key()
            return

        # Draw
        render_scene(screen, player, squares, level)
        pygame.display.flip()
        clock.tick(FPS)


main()
pygame.quit()

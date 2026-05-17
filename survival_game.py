import pygame
import random
import math
import sys

pygame.init()

WIDTH, HEIGHT = 1060, 600
FPS           = 60

BG          = (20, 22, 35)
C_PLAYER    = (255, 255, 255)
C_OUTLINE   = (200, 230, 255)
C_SQUARE    = (220, 60, 60)
C_SQ_OUT    = (255, 130, 130)
C_SQ_FRZ    = (70, 90, 220)
C_SQ_FRZ_O  = (130, 150, 255)
C_BOSS      = (200, 20, 20)
C_BOSS_OUT  = (255, 85, 85)
C_HEART     = (220, 50, 50)
C_HEART_E   = (70, 35, 35)
C_WHITE     = (255, 255, 255)
C_DIM       = (150, 150, 170)
C_YELLOW    = (255, 215, 50)
C_PARRY     = (80, 255, 180)
C_GREEN     = (60, 220, 100)

# Bullet colors per charge tier (0–3)
SHOT_COLORS = [
    (120, 120, 195),  # 0: dim blue-gray (stun)
    (255, 240, 60),   # 1: yellow
    (255, 145, 25),   # 2: orange
    (255, 55, 55),    # 3: red
]

PLAYER_R      = 16
PLAYER_SPD    = 4.5
SQ_SIZE       = 32
SQ_BASE_V     = 2.3
INV_MS        = 500
PARRY_MS      = 1000
PARRY_CD_MS   = 3000
SHOOT_CD_MS   = 10000  # shoot cooldown
FREEZE_MS     = 5000   # parry freeze (squares)
STUN_MS       = 7000   # 0-charge bullet stun

BOSS_SIZE     = 90
BOSS_MAX_HP   = 10

MAX_CHARGES      = 3

# Squares per stage (stage 0–4, every 2 boss HP)
SQ_COUNTS = [11, 14, 18, 22, 27]


def get_stage(boss_hp):
    return min(4, (BOSS_MAX_HP - max(1, boss_hp)) // 2)


screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Survival — Boss Fight")
clock = pygame.time.Clock()

F_TITLE = pygame.font.SysFont(None, 84)
F_BIG   = pygame.font.SysFont(None, 56)
F_MED   = pygame.font.SysFont(None, 40)
F_SM    = pygame.font.SysFont(None, 28)
F_TINY  = pygame.font.SysFont(None, 22)


class Player:
    SPAWN_X = float(PLAYER_R + 44)
    SPAWN_Y = float(HEIGHT / 2)

    def __init__(self):
        self.lives         = 3
        self.x             = self.SPAWN_X
        self.y             = self.SPAWN_Y
        self.inv           = False
        self.inv_t         = 0
        self.inv_dur       = INV_MS
        self.parrying      = False
        self.parry_t       = 0
        self.parry_cd_t    = -PARRY_CD_MS
        self.charges       = 0
        self.shoot_cd_t    = -SHOOT_CD_MS

    def teleport_start(self):
        self.x = self.SPAWN_X
        self.y = self.SPAWN_Y

    def start_inv(self, duration_ms=INV_MS):
        self.inv      = True
        self.inv_t    = pygame.time.get_ticks()
        self.inv_dur  = duration_ms
        self.parrying = False

    def parry_ready(self):
        return pygame.time.get_ticks() - self.parry_cd_t >= PARRY_CD_MS

    def try_parry(self):
        self.inv        = False
        self.parrying   = True
        self.parry_t    = pygame.time.get_ticks()
        self.parry_cd_t = self.parry_t

    def gain_charge(self):
        self.charges = min(MAX_CHARGES, self.charges + 1)

    def shoot_ready(self):
        return pygame.time.get_ticks() - self.shoot_cd_t >= SHOOT_CD_MS

    def shoot(self, tx, ty):
        c = self.charges
        self.charges    = 0
        self.shoot_cd_t = pygame.time.get_ticks()
        return Bullet(self.x, self.y, tx, ty, c)

    def is_immune(self):
        return self.inv or self.parrying

    def move(self, keys):
        dx = float(keys[pygame.K_d] - keys[pygame.K_a])
        dy = float(keys[pygame.K_s] - keys[pygame.K_w])
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        self.x = max(PLAYER_R, min(WIDTH  - PLAYER_R, self.x + dx * PLAYER_SPD))
        self.y = max(PLAYER_R, min(HEIGHT - PLAYER_R, self.y + dy * PLAYER_SPD))
        t = pygame.time.get_ticks()
        if self.inv      and t - self.inv_t   >= self.inv_dur: self.inv      = False
        if self.parrying and t - self.parry_t >= PARRY_MS: self.parrying = False

    def draw(self, surf):
        p = (int(self.x), int(self.y))
        if self.parrying:
            t     = pygame.time.get_ticks()
            pulse = int(abs(math.sin(t / 120)) * 5)
            pygame.draw.circle(surf, C_PARRY, p, PLAYER_R + 8 + pulse, 3)
            pygame.draw.circle(surf, C_PLAYER, p, PLAYER_R)
            pygame.draw.circle(surf, C_PARRY,  p, PLAYER_R, 2)
        elif self.inv and (pygame.time.get_ticks() - self.inv_t) // 70 % 2:
            return
        else:
            pygame.draw.circle(surf, C_PLAYER,  p, PLAYER_R)
            pygame.draw.circle(surf, C_OUTLINE, p, PLAYER_R, 2)


class Square:
    def __init__(self, vmul):
        cx, cy = WIDTH // 2, HEIGHT // 2
        self.x = float(random.randint(cx - WIDTH  // 5, cx + WIDTH  // 5))
        self.y = float(random.randint(cy - HEIGHT // 4, cy + HEIGHT // 4))
        self.s = SQ_SIZE
        v  = SQ_BASE_V * vmul * random.uniform(0.75, 1.4)
        a  = random.uniform(0, 2 * math.pi)
        self.vx        = math.cos(a) * v
        self.vy        = math.sin(a) * v
        self.frozen    = False
        self.freeze_t  = 0
        self.freeze_dur = FREEZE_MS

    def update(self):
        if self.frozen:
            if pygame.time.get_ticks() - self.freeze_t >= self.freeze_dur:
                self.frozen = False
            return
        self.x += self.vx
        self.y += self.vy
        if self.x < 0:               self.x = 0;               self.vx =  abs(self.vx)
        if self.x + self.s > WIDTH:  self.x = WIDTH  - self.s; self.vx = -abs(self.vx)
        if self.y < 0:               self.y = 0;               self.vy =  abs(self.vy)
        if self.y + self.s > HEIGHT: self.y = HEIGHT - self.s; self.vy = -abs(self.vy)

    def freeze(self, duration=FREEZE_MS):
        self.frozen    = True
        self.freeze_t  = pygame.time.get_ticks()
        self.freeze_dur = duration

    def hits_player(self, player):
        if self.frozen:
            return False
        cx = max(self.x, min(player.x, self.x + self.s))
        cy = max(self.y, min(player.y, self.y + self.s))
        return (player.x - cx) ** 2 + (player.y - cy) ** 2 < PLAYER_R ** 2

    def hits_bullet(self, b):
        if self.frozen:
            return False
        cx = max(self.x, min(b.x, self.x + self.s))
        cy = max(self.y, min(b.y, self.y + self.s))
        return (b.x - cx) ** 2 + (b.y - cy) ** 2 < b.r ** 2

    def draw(self, surf):
        r = pygame.Rect(int(self.x), int(self.y), self.s, self.s)
        if self.frozen:
            pygame.draw.rect(surf, C_SQ_FRZ, r)
            pygame.draw.rect(surf, C_SQ_FRZ_O, r, 2)
        else:
            pygame.draw.rect(surf, C_SQUARE, r)
            pygame.draw.rect(surf, C_SQ_OUT, r, 2)


class Boss:
    def __init__(self):
        self.s      = BOSS_SIZE
        self.x      = float(WIDTH - self.s - 20)
        self.base_y = float(HEIGHT // 2 - self.s // 2)
        self.y      = self.base_y
        self.hp     = BOSS_MAX_HP
        self.inv    = False
        self.inv_t  = 0

    def update(self):
        t = pygame.time.get_ticks()
        self.y = self.base_y + math.sin(t / 700) * 18
        if self.inv and t - self.inv_t >= INV_MS:
            self.inv = False

    def take_hit(self, amount=1):
        """Player-contact hit — respects i-frames."""
        if not self.inv:
            self.hp    = max(0, self.hp - amount)
            self.inv   = True
            self.inv_t = pygame.time.get_ticks()

    def bullet_hit(self, amount):
        """Bullet hit — bypasses i-frames."""
        self.hp = max(0, self.hp - amount)

    def hits_player(self, player):
        cx = max(self.x, min(player.x, self.x + self.s))
        cy = max(self.y, min(player.y, self.y + self.s))
        return (player.x - cx) ** 2 + (player.y - cy) ** 2 < PLAYER_R ** 2

    def hits_bullet(self, b):
        cx = max(self.x, min(b.x, self.x + self.s))
        cy = max(self.y, min(b.y, self.y + self.s))
        return (b.x - cx) ** 2 + (b.y - cy) ** 2 < b.r ** 2

    def draw(self, surf):
        t  = pygame.time.get_ticks()
        rx = int(self.x)
        ry = int(self.y)
        r  = pygame.Rect(rx, ry, self.s, self.s)

        glow_r = int(abs(math.sin(t / 400)) * 8 + 4)
        glow   = pygame.Rect(rx - glow_r, ry - glow_r,
                             self.s + glow_r * 2, self.s + glow_r * 2)
        pygame.draw.rect(surf, (80, 10, 10), glow)

        if self.inv and (t - self.inv_t) // 55 % 2:
            pygame.draw.rect(surf, (255, 210, 210), r)
        else:
            pygame.draw.rect(surf, C_BOSS, r)
        pygame.draw.rect(surf, C_BOSS_OUT, r, 4)

        num = F_BIG.render(str(max(0, self.hp)), True, C_WHITE)
        surf.blit(num, (rx + self.s // 2 - num.get_width() // 2,
                        ry + self.s // 2 - num.get_height() // 2))


class Bullet:
    def __init__(self, x, y, tx, ty, charges):
        self.charges = charges
        dx = tx - x
        dy = ty - y
        length = math.sqrt(dx * dx + dy * dy) or 1

        if charges == 0:
            self.r        = PLAYER_R // 2
            speed         = PLAYER_SPD * 1.5
            self.max_hits = 1
            self.stun     = True
            self.boss_dmg = 0
        elif charges == 1:
            self.r        = PLAYER_R // 2
            speed         = PLAYER_SPD * 1.5
            self.max_hits = 1
            self.stun     = False
            self.boss_dmg = 1
        elif charges == 2:
            self.r        = PLAYER_R
            speed         = PLAYER_SPD * 2
            self.max_hits = 3   # pierces up to 2 more after first hit
            self.stun     = False
            self.boss_dmg = 2
        else:  # 3 charges
            self.r        = PLAYER_R * 2
            speed         = PLAYER_SPD * 4
            self.max_hits = 9999  # all enemies
            self.stun     = False
            self.boss_dmg = 3

        self.x       = float(x)
        self.y       = float(y)
        self.vx      = dx / length * speed
        self.vy      = dy / length * speed
        self.sq_hits = 0
        self.active  = True
        self.color   = SHOT_COLORS[charges]

    def update(self):
        self.x += self.vx
        self.y += self.vy
        r2 = self.r * 2
        if self.x < -r2 or self.x > WIDTH + r2 or self.y < -r2 or self.y > HEIGHT + r2:
            self.active = False

    def draw(self, surf):
        p = (int(self.x), int(self.y))
        pygame.draw.circle(surf, self.color, p, self.r)
        pygame.draw.circle(surf, C_WHITE, p, self.r, 1)


def make_squares(boss_hp):
    stage = get_stage(boss_hp)
    vmul  = 1.0 + stage * 0.18
    return [Square(vmul) for _ in range(SQ_COUNTS[stage])]


def draw_heart(surf, cx, cy, size, color):
    r = size // 4
    pygame.draw.circle(surf, color, (cx - r, cy - 2), r)
    pygame.draw.circle(surf, color, (cx + r, cy - 2), r)
    pygame.draw.polygon(surf, color, [
        (cx - size // 2 + 3, cy + 1),
        (cx + size // 2 - 3, cy + 1),
        (cx, cy + size // 2),
    ])


def draw_hud(surf, player, boss):
    hs, hg = 24, 7
    hy = 10

    # --- Player hearts (top-left) ---
    for i in range(3):
        col = C_HEART if i < player.lives else C_HEART_E
        draw_heart(surf, 14 + i * (hs + hg) + hs // 2, hy + hs // 2, hs, col)

    # --- Charge orbs (below player hearts) ---
    orb_r = 9
    orb_y = hy + hs + 16
    shot_col = SHOT_COLORS[player.charges] if player.charges > 0 else SHOT_COLORS[0]
    for i in range(MAX_CHARGES):
        ox  = 14 + i * (orb_r * 2 + 5) + orb_r
        col = shot_col if i < player.charges else (35, 38, 55)
        pygame.draw.circle(surf, col, (ox, orb_y), orb_r)
        pygame.draw.circle(surf, C_DIM, (ox, orb_y), orb_r, 1)

    # --- Boss hearts (top-right, smaller to fit 10) ---
    bhs, bhg = 18, 4
    for i in range(BOSS_MAX_HP):
        col = C_HEART if i < boss.hp else C_HEART_E
        bx  = WIDTH - 14 - (BOSS_MAX_HP - i) * (bhs + bhg) + bhs // 2
        draw_heart(surf, bx, hy + bhs // 2, bhs, col)
    boss_lbl = F_TINY.render("BOSS", True, C_DIM)
    surf.blit(boss_lbl, (WIDTH - 14 - boss_lbl.get_width(), hy + bhs + 5))

    # --- Parry bar (center-bottom) ---
    bw, bh = 130, 10
    bx     = WIDTH // 2 - bw // 2
    by     = HEIGHT - 46
    if player.parrying:
        elapsed = pygame.time.get_ticks() - player.parry_t
        pct     = max(0.0, 1.0 - elapsed / PARRY_MS)
        pygame.draw.rect(surf, (30, 60, 45), (bx, by, bw, bh))
        pygame.draw.rect(surf, C_PARRY, (bx, by, int(bw * pct), bh))
        lbl = F_SM.render("PARRY ACTIVE", True, C_PARRY)
        surf.blit(lbl, (WIDTH // 2 - lbl.get_width() // 2, by - 22))
    else:
        cd_elapsed = pygame.time.get_ticks() - player.parry_cd_t
        cd_pct     = min(1.0, cd_elapsed / PARRY_CD_MS)
        ready      = cd_pct >= 1.0
        pygame.draw.rect(surf, (30, 40, 35), (bx, by, bw, bh))
        pygame.draw.rect(surf, C_PARRY if ready else (80, 130, 110),
                         (bx, by, int(bw * cd_pct), bh))
        secs_left = max(0, PARRY_CD_MS - cd_elapsed) // 1000 + (0 if ready else 1)
        lbl_text  = "F — PARRY" if ready else f"F — PARRY  {secs_left}s"
        lbl = F_TINY.render(lbl_text, True, C_PARRY if ready else C_DIM)
        surf.blit(lbl, (WIDTH // 2 - lbl.get_width() // 2, by - 18))

    tip = F_TINY.render("WASD — move     LMB — shoot", True, C_DIM)
    surf.blit(tip, (WIDTH // 2 - tip.get_width() // 2, HEIGHT - 20))


def render_scene(surf, player, squares, boss, bullets):
    surf.fill(BG)
    boss.draw(surf)
    for sq in squares:
        sq.draw(surf)
    for b in bullets:
        b.draw(surf)
    player.draw(surf)
    draw_hud(surf, player, boss)


def overlay(surf, title, sub="", tc=C_WHITE):
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


def main():
    while True:
        screen.fill(BG)
        overlay(screen, "BOSS FIGHT", "Press any key to begin", C_YELLOW)
        wait_for_key()

        player  = Player()
        boss    = Boss()
        squares = make_squares(boss.hp)
        bullets = []
        cur_stage = get_stage(boss.hp)

        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if e.key == pygame.K_f and not player.parrying and player.parry_ready():
                        player.try_parry()
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and player.shoot_ready():
                    mx, my = pygame.mouse.get_pos()
                    bullets.append(player.shoot(mx, my))

            player.move(pygame.key.get_pressed())
            boss.update()
            for sq in squares:
                sq.update()

            # --- Bullet updates and collisions ---
            dead_bullets  = []
            dead_squares  = []
            for b in bullets:
                b.update()
                if not b.active:
                    dead_bullets.append(b)
                    continue

                # Boss hit (always stops the bullet)
                if b.boss_dmg > 0 and boss.hits_bullet(b):
                    boss.bullet_hit(b.boss_dmg)
                    new_stage = get_stage(boss.hp)
                    if new_stage != cur_stage and boss.hp > 0:
                        cur_stage = new_stage
                        squares = make_squares(boss.hp)
                    b.active = False
                    dead_bullets.append(b)
                    continue

                # Square hits (with pierce)
                for sq in squares:
                    if sq not in dead_squares and sq.hits_bullet(b):
                        if b.stun:
                            sq.freeze(STUN_MS)
                        else:
                            dead_squares.append(sq)
                        b.sq_hits += 1
                        if b.sq_hits >= b.max_hits:
                            b.active = False
                            dead_bullets.append(b)
                            break

            squares = [sq for sq in squares if sq not in dead_squares]
            bullets = [b  for b  in bullets if b  not in dead_bullets]

            # --- Boss collision (player touch) ---
            if boss.hits_player(player):
                if player.parrying:
                    # Failed parry: lose 1 HP, teleport, 0.5s i-frames
                    player.lives   -= 1
                    player.parrying = False
                    player.teleport_start()
                    player.start_inv()
                elif not player.is_immune():
                    # Normal touch: gain HP, boss loses 1 HP, teleport
                    player.lives = min(3, player.lives + 1)
                    boss.take_hit(1)
                    new_stage = get_stage(boss.hp)
                    if new_stage != cur_stage and boss.hp > 0:
                        cur_stage = new_stage
                        squares = make_squares(boss.hp)
                    player.teleport_start()
                    player.start_inv()

            # --- Win ---
            if boss.hp <= 0:
                render_scene(screen, player, squares, boss, bullets)
                overlay(screen, "BOSS DEFEATED!", "Press any key to play again", C_GREEN)
                wait_for_key()
                break

            # --- Square collision (player) ---
            for sq in squares:
                if sq.hits_player(player):
                    if player.parrying:
                        sq.freeze(FREEZE_MS)
                        player.parrying = False
                        player.gain_charge()   # +1 charge on successful parry
                    elif not player.is_immune():
                        player.lives -= 1
                        player.start_inv()
                    break

            # --- Lose ---
            if player.lives <= 0:
                render_scene(screen, player, squares, boss, bullets)
                overlay(screen, "GAME OVER", "Press any key to play again", C_SQUARE)
                wait_for_key()
                break

            render_scene(screen, player, squares, boss, bullets)
            pygame.display.flip()
            clock.tick(FPS)


main()
pygame.quit()

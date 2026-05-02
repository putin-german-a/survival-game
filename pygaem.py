import pygame
import time
pygame.init()
FPS = 2
speed = 5
# Код, описывающий окно программы
width = 400  # Ширина окна
height = 400  # Высота окна
screen = pygame.display.set_mode([width, height])
fon = [0, 0, 0]
obj = [255, 0, 0]
game_run = True
while game_run:
    for i in pygame.event.get():
        if i.type == pygame.QUIT:
            game_run = False
        screen.fill(fon)
        pygame.draw.rect(screen, obj, [100, 100], 200)
        pygame.draw.rect(screen, obj, [150, 150], 100)
        pygame.display.flip()
        clock.tick(FPS)
pygame.quit()
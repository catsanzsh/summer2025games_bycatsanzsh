import asyncio
import platform
import pygame
from pygame.locals import *

# Initialize Pygame
pygame.init()

# Set up the display
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario Bros 3 - Simplified")

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# Player class
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((50, 50))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.x = 100
        self.rect.y = HEIGHT - self.rect.height - 10
        self.vel_x = 0
        self.vel_y = 0
        self.is_jumping = False

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[K_LEFT]:
            self.vel_x = -5
        elif keys[K_RIGHT]:
            self.vel_x = 5
        else:
            self.vel_x = 0
        if keys[K_SPACE] and not self.is_jumping:
            self.is_jumping = True
            self.vel_y = -10
        # Apply gravity
        self.vel_y += 0.5
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        # Check boundaries
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > WIDTH:
            self.rect.right = WIDTH
        if self.rect.bottom > HEIGHT:
            self.rect.bottom = HEIGHT
            self.is_jumping = False

# Platform class
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

# Create sprite groups
all_sprites = pygame.sprite.Group()
platforms = pygame.sprite.Group()

# Create player
player = Player()
all_sprites.add(player)

# Create platforms
p1 = Platform(300, HEIGHT - 100, 200, 20)
p2 = Platform(500, HEIGHT - 200, 200, 20)
platforms.add(p1, p2)
all_sprites.add(p1, p2)

# Game loop
FPS = 60
clock = pygame.time.Clock()

async def main():
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

        all_sprites.update()

        # Check for collisions
        hits = pygame.sprite.spritecollide(player, platforms, False)
        if hits:
            if player.vel_y > 0:  # Falling down
                player.rect.bottom = hits[0].rect.top
                player.vel_y = 0
                player.is_jumping = False

        screen.fill(WHITE)
        all_sprites.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)
        await asyncio.sleep(1.0 / FPS)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())

pygame.quit()

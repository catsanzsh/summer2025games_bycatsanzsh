import pygame
import sys
import random

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario Bros 1X")
clock = pygame.time.Clock()

# Colors (SNES palette)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (85, 107, 255)
GREEN = (85, 170, 85)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
SKY_BLUE = (135, 206, 235)
BROWN = (139, 69, 19)
FLAG_RED = (220, 20, 60)
FLAG_POLE = (200, 200, 200)

# Game states
MENU = "menu"
SELECT = "select"
PLAYING = "playing"
GAME_OVER = "game_over"
LEVEL_COMPLETE = "level_complete"
state = MENU

# Fonts
title_font = pygame.font.Font(None, 64)
font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)

# Level data (5 simple levels)
levels = [
    [(100, 500, 200, 20), (300, 400, 200, 20), (500, 300, 200, 20)],
    [(50, 500, 150, 20), (250, 400, 150, 20), (450, 300, 150, 20), (650, 200, 100, 20)],
    [(100, 500, 300, 20), (450, 400, 150, 20), (300, 300, 100, 20), (100, 200, 100, 20)],
    [(100, 500, 100, 20), (250, 400, 100, 20), (400, 300, 100, 20), (550, 200, 100, 20), (700, 100, 100, 20)],
    [(50, 500, 100, 20), (200, 450, 100, 20), (350, 400, 100, 20), (500, 350, 100, 20), (650, 300, 100, 20)]
]

# Selected level
current_level_index = 0
current_level = []
flag_positions = [(700, 280), (700, 180), (600, 180), (700, 80), (700, 280)]
coins = []

# Player setup
player = pygame.Rect(50, HEIGHT - 60, 30, 40)
player_velocity_y = 0
on_ground = False
facing_right = True
player_lives = 3
score = 0
player_invincible = False
invincible_timer = 0

# Enemy
enemies = []
enemy_velocity = 2
enemy_color = RED

# Game timer
level_start_time = 0
level_time_limit = 60  # seconds

# Animation variables
coin_animation_frames = []
for i in range(8):
    size = 20 - abs(4 - i) * 2
    coin_animation_frames.append(size)
coin_frame = 0

# Particle effects
particles = []

# Background clouds
clouds = []
for _ in range(5):
    x = random.randint(0, WIDTH)
    y = random.randint(50, 200)
    speed = random.uniform(0.1, 0.3)
    clouds.append([x, y, speed])

def create_particles(x, y, color, count=5):
    for _ in range(count):
        size = random.randint(2, 5)
        speed_x = random.uniform(-1, 1)
        speed_y = random.uniform(-2, 0)
        lifetime = random.randint(20, 40)
        particles.append([x, y, speed_x, speed_y, size, color, lifetime])

def reset_level(index):
    global current_level, enemies, player, coins, player_velocity_y, level_start_time
    current_level = [pygame.Rect(*rect) for rect in levels[index]]
    player.topleft = (50, HEIGHT - 60)
    player_velocity_y = 0
    
    # Create enemies based on level
    enemies = []
    if index == 0:
        enemies.append(pygame.Rect(400, HEIGHT - 60, 30, 40))
    elif index == 1:
        enemies.append(pygame.Rect(300, HEIGHT - 60, 30, 40))
        enemies.append(pygame.Rect(600, 300, 30, 40))
    elif index == 2:
        enemies.append(pygame.Rect(200, 400, 30, 40))
        enemies.append(pygame.Rect(500, 300, 30, 40))
    elif index == 3:
        enemies.append(pygame.Rect(150, 500, 30, 40))
        enemies.append(pygame.Rect(400, 300, 30, 40))
        enemies.append(pygame.Rect(650, 100, 30, 40))
    elif index == 4:
        enemies.append(pygame.Rect(100, 450, 30, 40))
        enemies.append(pygame.Rect(350, 400, 30, 40))
        enemies.append(pygame.Rect(600, 300, 30, 40))
    
    # Create coins
    coins = []
    for platform in current_level:
        if platform.width > 40:  # Only add coins to platforms wide enough
            for i in range(platform.width // 50):
                coin_x = platform.x + 20 + i * 50
                coin_y = platform.top - 30
                coins.append(pygame.Rect(coin_x, coin_y, 20, 20))
    
    level_start_time = pygame.time.get_ticks()

def draw_menu():
    screen.fill(SKY_BLUE)
    
    # Draw clouds
    for cloud in clouds:
        pygame.draw.circle(screen, WHITE, (int(cloud[0]), int(cloud[1])), 25)
        pygame.draw.circle(screen, WHITE, (int(cloud[0]) + 20, int(cloud[1]) - 10), 20)
        pygame.draw.circle(screen, WHITE, (int(cloud[0]) + 40, int(cloud[1])), 25)
    
    # Draw ground
    pygame.draw.rect(screen, GREEN, (0, HEIGHT - 20, WIDTH, 20))
    
    # Draw title
    title = title_font.render("Super Mario Bros 1X", True, RED)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 100))
    
    # Draw player character
    pygame.draw.rect(screen, RED, (WIDTH // 2 - 15, HEIGHT // 2 - 20, 30, 40))
    pygame.draw.circle(screen, (255, 200, 150), (WIDTH // 2, HEIGHT // 2 - 30), 10)
    
    # Draw prompt
    prompt = font.render("Press ENTER to Start", True, WHITE)
    screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 + 50))
    
    # Draw copyright
    copyright = small_font.render("© 2023 DeepSeek-R1", True, WHITE)
    screen.blit(copyright, (WIDTH // 2 - copyright.get_width() // 2, HEIGHT - 40))

def draw_select():
    screen.fill(SKY_BLUE)
    
    # Draw clouds
    for cloud in clouds:
        pygame.draw.circle(screen, WHITE, (int(cloud[0]), int(cloud[1])), 25)
        pygame.draw.circle(screen, WHITE, (int(cloud[0]) + 20, int(cloud[1]) - 10), 20)
        pygame.draw.circle(screen, WHITE, (int(cloud[0]) + 40, int(cloud[1])), 25)
    
    # Draw title
    title = title_font.render("Select Level", True, WHITE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
    
    # Draw level boxes
    for i in range(5):
        x = 150 + (i % 3) * 200
        y = 150 + (i // 3) * 150
        color = YELLOW if i == current_level_index else BLUE
        
        pygame.draw.rect(screen, color, (x, y, 80, 80))
        level_text = font.render(str(i + 1), True, WHITE)
        screen.blit(level_text, (x + 40 - level_text.get_width() // 2, y + 40 - level_text.get_height() // 2))
    
    # Draw instructions
    instructions = font.render("Use ARROWS to select, ENTER to play", True, WHITE)
    screen.blit(instructions, (WIDTH // 2 - instructions.get_width() // 2, HEIGHT - 100))

def draw_game():
    screen.fill(SKY_BLUE)
    
    # Draw clouds
    for cloud in clouds:
        pygame.draw.circle(screen, WHITE, (int(cloud[0]), int(cloud[1])), 25)
        pygame.draw.circle(screen, WHITE, (int(cloud[0]) + 20, int(cloud[1]) - 10), 20)
        pygame.draw.circle(screen, WHITE, (int(cloud[0]) + 40, int(cloud[1])), 25)
    
    # Draw platforms
    for platform in current_level:
        pygame.draw.rect(screen, GREEN, platform)
        # Draw platform details
        pygame.draw.rect(screen, BROWN, (platform.x, platform.y, platform.width, 5))
    
    # Draw coins
    global coin_frame
    coin_frame = (coin_frame + 0.2) % len(coin_animation_frames)
    for coin in coins:
        size = coin_animation_frames[int(coin_frame)]
        offset = (20 - size) // 2
        pygame.draw.circle(screen, YELLOW, 
                          (coin.x + coin.width // 2, coin.y + coin.height // 2), 
                          size // 2)
    
    # Draw flag
    flag_x, flag_y = flag_positions[current_level_index]
    pygame.draw.rect(screen, FLAG_POLE, (flag_x, flag_y, 5, 50))
    pygame.draw.polygon(screen, FLAG_RED, [
        (flag_x + 5, flag_y + 5),
        (flag_x + 30, flag_y + 15),
        (flag_x + 5, flag_y + 25)
    ])
    
    # Draw player
    player_color = (200, 50, 50) if player_invincible and invincible_timer % 10 < 5 else RED
    pygame.draw.rect(screen, player_color, player)
    
    # Draw player details
    head_color = (255, 200, 150)
    if player_invincible and invincible_timer % 10 < 5:
        head_color = (200, 170, 130)
    
    pygame.draw.circle(screen, head_color, 
                      (player.x + player.width // 2, player.y + 10), 
                      10)
    
    # Draw hat
    hat_width = 20 if facing_right else -20
    pygame.draw.rect(screen, BLUE, 
                   (player.x + player.width // 2 - 10, player.y - 5, hat_width, 5))
    
    # Draw enemies
    for enemy in enemies:
        pygame.draw.rect(screen, enemy_color, enemy)
        # Draw enemy eyes
        eye_offset = -5 if enemy_velocity > 0 else 5
        pygame.draw.circle(screen, WHITE, 
                         (enemy.x + enemy.width // 2 + eye_offset, enemy.y + 15), 
                         4)
    
    # Draw particles
    for particle in particles[:]:
        x, y, speed_x, speed_y, size, color, lifetime = particle
        pygame.draw.circle(screen, color, (int(x), int(y)), size)
    
    # Draw HUD
    pygame.draw.rect(screen, (50, 50, 50), (0, 0, WIDTH, 30))
    
    # Draw lives
    lives_text = font.render(f"Lives: {player_lives}", True, WHITE)
    screen.blit(lives_text, (10, 5))
    
    # Draw score
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 5))
    
    # Draw timer
    elapsed = (pygame.time.get_ticks() - level_start_time) // 1000
    remaining = max(0, level_time_limit - elapsed)
    timer_text = font.render(f"Time: {remaining}", True, WHITE)
    screen.blit(timer_text, (WIDTH - timer_text.get_width() - 10, 5))

def draw_game_over():
    screen.fill((50, 0, 0))
    game_over = title_font.render("GAME OVER", True, RED)
    screen.blit(game_over, (WIDTH // 2 - game_over.get_width() // 2, HEIGHT // 2 - 50))
    
    score_text = font.render(f"Final Score: {score}", True, WHITE)
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2 + 20))
    
    prompt = font.render("Press R to Restart", True, WHITE)
    screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 + 80))

def draw_level_complete():
    screen.fill(SKY_BLUE)
    complete = title_font.render("LEVEL COMPLETE!", True, YELLOW)
    screen.blit(complete, (WIDTH // 2 - complete.get_width() // 2, HEIGHT // 2 - 50))
    
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2 + 20))
    
    prompt = font.render("Press ENTER for Next Level", True, WHITE)
    screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 + 80))

# Initialize the first level
reset_level(current_level_index)

# Main game loop
while True:
    dt = clock.tick(60) / 1000.0  # Delta time in seconds
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if state == MENU and event.key == pygame.K_RETURN:
                state = SELECT
            
            elif state == SELECT:
                if event.key == pygame.K_LEFT and current_level_index > 0:
                    current_level_index -= 1
                elif event.key == pygame.K_RIGHT and current_level_index < 4:
                    current_level_index += 1
                elif event.key == pygame.K_RETURN:
                    reset_level(current_level_index)
                    state = PLAYING
            
            elif state == GAME_OVER and event.key == pygame.K_r:
                player_lives = 3
                score = 0
                current_level_index = 0
                reset_level(current_level_index)
                state = PLAYING
            
            elif state == LEVEL_COMPLETE and event.key == pygame.K_RETURN:
                current_level_index += 1
                if current_level_index >= len(levels):
                    current_level_index = 0
                    state = MENU
                else:
                    reset_level(current_level_index)
                    state = PLAYING

    keys = pygame.key.get_pressed()

    # Update clouds
    for cloud in clouds:
        cloud[0] -= cloud[2]
        if cloud[0] < -50:
            cloud[0] = WIDTH + 50
            cloud[1] = random.randint(50, 200)

    # Update particles
    for particle in particles[:]:
        particle[0] += particle[2]  # x velocity
        particle[1] += particle[3]  # y velocity
        particle[3] += 0.1  # gravity
        particle[6] -= 1  # decrease lifetime
        
        if particle[6] <= 0:
            particles.remove(particle)

    if state == PLAYING:
        # Horizontal movement
        if keys[pygame.K_LEFT]:
            player.x -= MOVE_SPEED
            facing_right = False
        if keys[pygame.K_RIGHT]:
            player.x += MOVE_SPEED
            facing_right = True

        # Jump
        if keys[pygame.K_SPACE] and on_ground:
            player_velocity_y = JUMP_STRENGTH
            on_ground = False
            create_particles(player.x + player.width // 2, player.bottom, YELLOW, 10)

        # Apply gravity
        player_velocity_y += GRAVITY
        player.y += player_velocity_y

        # Boundary check
        if player.left < 0:
            player.left = 0
        if player.right > WIDTH:
            player.right = WIDTH

        # Collision with ground
        if player.bottom >= HEIGHT:
            player.bottom = HEIGHT
            player_velocity_y = 0
            on_ground = True

        # Collision with platforms
        on_ground = False
        for platform in current_level:
            if player.colliderect(platform) and player_velocity_y > 0:
                player.bottom = platform.top
                player_velocity_y = 0
                on_ground = True

        # Enemy movement
        for enemy in enemies[:]:
            enemy.x += enemy_velocity
            
            # Turn around at edges
            if enemy.left <= 0 or enemy.right >= WIDTH:
                enemy_velocity *= -1
                
            # Fall if not on platform
            on_platform = False
            for platform in current_level:
                if enemy.colliderect(platform) and enemy_velocity_y >= 0:
                    enemy.bottom = platform.top
                    enemy_velocity_y = 0
                    on_platform = True
                    break
            
            if not on_platform and enemy.bottom < HEIGHT:
                enemy_velocity_y += GRAVITY
                enemy.y += enemy_velocity_y
            else:
                enemy_velocity_y = 0

        # Enemy collision
        if player_invincible:
            invincible_timer -= 1
            if invincible_timer <= 0:
                player_invincible = False
        else:
            for enemy in enemies[:]:
                if player.colliderect(enemy):
                    player_lives -= 1
                    player_invincible = True
                    invincible_timer = 60
                    create_particles(player.x + player.width // 2, player.y + player.height // 2, RED, 15)
                    
                    if player_lives <= 0:
                        state = GAME_OVER
                    else:
                        player.topleft = (50, HEIGHT - 60)
                        player_velocity_y = 0
                    break

        # Coin collection
        for coin in coins[:]:
            if player.colliderect(coin):
                coins.remove(coin)
                score += 100
                create_particles(coin.x + coin.width // 2, coin.y + coin.height // 2, YELLOW, 10)

        # Flag collision (level complete)
        flag_x, flag_y = flag_positions[current_level_index]
        flag_rect = pygame.Rect(flag_x, flag_y, 30, 50)
        if player.colliderect(flag_rect):
            score += (level_time_limit - (pygame.time.get_ticks() - level_start_time) // 1000) * 10
            state = LEVEL_COMPLETE

        # Time check
        elapsed = (pygame.time.get_ticks() - level_start_time) // 1000
        if elapsed >= level_time_limit:
            player_lives -= 1
            if player_lives <= 0:
                state = GAME_OVER
            else:
                reset_level(current_level_index)

    # Draw current state
    if state == MENU:
        draw_menu()
    elif state == SELECT:
        draw_select()
    elif state == PLAYING:
        draw_game()
    elif state == GAME_OVER:
        draw_game_over()
    elif state == LEVEL_COMPLETE:
        draw_level_complete()

    pygame.display.flip()

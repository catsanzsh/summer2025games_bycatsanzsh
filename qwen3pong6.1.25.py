import pygame
import sys
import random
import math  # For tone generation

# Initialize Pygame and Mixer
pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Paddles and Ball
PADDLE_WIDTH, PADDLE_HEIGHT = 15, 100
BALL_SIZE = 15

left_paddle = pygame.Rect(50, HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
right_paddle = pygame.Rect(WIDTH - 65, HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
ball = pygame.Rect(WIDTH // 2 - BALL_SIZE // 2, HEIGHT // 2 - BALL_SIZE // 2, BALL_SIZE, BALL_SIZE)

# Movement
paddle_speed = 7
ball_speed_x = 5 * random.choice((1, -1))
ball_speed_y = 5 * random.choice((1, -1))

# Scores
left_score = 0
right_score = 0

# Game state
game_over = False
font = pygame.font.Font(None, 74)

# Sound Generation
def generate_tone(frequency=440, duration=0.1, volume=0.5):
    """Generates a sine wave tone as a pygame Sound."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    buffer = bytearray()
    for i in range(n_samples):
        sample = int(32767 * volume * math.sin(2 * math.pi * frequency * i / sample_rate))
        buffer.extend(sample.to_bytes(2, 'little', signed=True))
    return pygame.mixer.Sound(buffer=buffer)

# Create sound effects
bounce_sound = generate_tone(700, 0.05)
score_sound = generate_tone(440, 0.2)

def reset_ball():
    global ball_speed_x, ball_speed_y
    ball.center = (WIDTH // 2, HEIGHT // 2)
    ball_speed_x *= random.choice((1, -1))
    ball_speed_y *= random.choice((1, -1))

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    if not game_over:
        # Player control (left paddle) with mouse
        mouse_y = pygame.mouse.get_pos()[1]
        left_paddle.centery = mouse_y
        left_paddle.y = max(0, min(HEIGHT - PADDLE_HEIGHT, left_paddle.y))

        # AI (right paddle)
        if right_paddle.centery < ball.centery and right_paddle.bottom < HEIGHT:
            right_paddle.y += paddle_speed
        elif right_paddle.centery > ball.centery and right_paddle.top > 0:
            right_paddle.y -= paddle_speed

        # Ball movement
        ball.x += ball_speed_x
        ball.y += ball_speed_y

        # Collisions
        if ball.top <= 0 or ball.bottom >= HEIGHT:
            ball_speed_y *= -1
            bounce_sound.play()
        if ball.colliderect(left_paddle) or ball.colliderect(right_paddle):
            ball_speed_x *= -1
            bounce_sound.play()

        # Scoring
        if ball.left <= 0:
            right_score += 1
            score_sound.play()
            reset_ball()
        if ball.right >= WIDTH:
            left_score += 1
            score_sound.play()
            reset_ball()

        # Win/Loss condition
        if left_score >= 5 or right_score >= 5:
            game_over = True

    # Drawing
    screen.fill(BLACK)
    pygame.draw.rect(screen, WHITE, left_paddle)
    pygame.draw.rect(screen, WHITE, right_paddle)
    pygame.draw.rect(screen, WHITE, ball)
    pygame.draw.aaline(screen, WHITE, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT))

    # Score display
    score_text = font.render(f"{left_score}   {right_score}", True, WHITE)
    screen.blit(score_text, (WIDTH // 2 - 60, 20))

    # Game over message and restart prompt
    if game_over:
        message = font.render("GAME OVER", True, WHITE)
        prompt = font.render("RESTART? Y/N", True, WHITE)
        screen.blit(message, (WIDTH // 2 - 100, HEIGHT // 2 - 60))
        screen.blit(prompt, (WIDTH // 2 - 120, HEIGHT // 2 + 20))
        pygame.display.flip()

        # Wait for input
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_y:
                        left_score = right_score = 0
                        game_over = False
                        reset_ball()
                        waiting = False
                    elif event.key == pygame.K_n:
                        pygame.quit()
                        sys.exit()

    pygame.display.flip()
    clock.tick(60)

import pygame
import sys
import random

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario World X - Anikiti Hack Style!") # Updated Caption
clock = pygame.time.Clock()

# --- SMW-inspired Constants & Player Physics ---
PLAYER_ACCEL = 0.28           # How quickly Mario speeds up
PLAYER_DECEL = 0.35           # How quickly Mario slows down (friction)
PLAYER_MAX_WALK_SPEED = 4.0   # Max speed walking
PLAYER_MAX_RUN_SPEED = 6.0    # Max speed running (conceptual, needs run button)
PLAYER_JUMP_INITIAL = -15.5   # Initial upward velocity for jump
PLAYER_JUMP_HOLD_FORCE = -0.5 # Additional upward force while jump is held
PLAYER_JUMP_HOLD_FRAMES_MAX = 12 # Max frames jump hold force is applied
GRAVITY_PLAYER = 0.72         # Gravity affecting player
GRAVITY_ENEMY = 0.75          # Gravity affecting enemies
GRAVITY_ITEM = 0.4            # Gravity affecting items like mushrooms

ENEMY_BASE_SPEED = 1.8
KOOPA_SHELL_SPEED = 7.0
STOMP_BOUNCE = -8            # How high Mario bounces after stomping an enemy
INVINCIBILITY_DURATION = 120 # Frames for invincibility after hit/power-up
POWERUP_REVEAL_DURATION = 30 # Frames a powerup takes to 'emerge' from a block
COIN_SPIN_SPEED = 0.3
PARTICLE_GRAVITY = 0.15

# Player States
S_SMALL = 'small'
S_SUPER = 'super'
# S_CAPE = 'cape' # Future

# Player Dimensions
PLAYER_SMALL_WIDTH, PLAYER_SMALL_HEIGHT = 28, 32
PLAYER_SUPER_WIDTH, PLAYER_SUPER_HEIGHT = 30, 48 # Taller and slightly wider

# Colors (SNES-inspired palette, some SMW specific)
WHITE = (252, 252, 252)
BLACK = (0, 0, 0)
SKY_BLUE = (90, 140, 255) # SMW Sky Blue
MARIO_RED = (255, 0, 0) # Brighter Red for Mario
MARIO_BLUE_OVERALLS = (0, 80, 255) # SMW Blue
MARIO_SKIN = (252, 220, 160) # Peachy skin
MARIO_HAIR_BROWN = (101, 67, 33)
MARIO_SHOE_BROWN = (130, 60, 0) # More orangey-brown for shoes

GROUND_GREEN = (0, 160, 0) # SMW Lush Green
GROUND_BROWN = (120, 80, 0) # SMW Dirt Brown
PLATFORM_BRICK_RED = (200, 76, 12) # Keep for some variety
PLATFORM_BRICK_MORTAR = (150, 150, 150)
QUESTION_BLOCK_YELLOW = (255, 200, 0) # SMW ? Block Yellow
QUESTION_BLOCK_SHADOW = (180, 130, 0)
USED_BLOCK_BROWN = (160, 110, 70) # SMW Used Block

GOOMBA_BROWN = (200, 120, 50) # SMW Goomba Brown
GOOMBA_FEET = (150, 90, 30)
GOOMBA_EYE_WHITE = (252, 252, 252)

KOOPA_GREEN_BODY = (0, 180, 0)
KOOPA_GREEN_SHELL = (0, 140, 0)
KOOPA_GREEN_SHELL_HIGHLIGHT = (50, 200, 50)
KOOPA_FEET_HANDS = (255, 224, 100) # Yellowish

MUSHROOM_RED = (255, 0, 0)
MUSHROOM_STEM = (252, 220, 160)
MUSHROOM_SPOTS = WHITE

GOAL_TAPE_COLOR = (220,220,0) # Yellowish tape
GOAL_POST_COLOR = (100,100,100) # Grey posts

# Game states
MENU = "menu"
SELECT = "select"
PLAYING = "playing"
GAME_OVER = "game_over"
LEVEL_COMPLETE = "level_complete"
PLAYER_DIED_TRANSITION = "player_died_transition" # For death animation/pause
state = MENU

# Fonts
title_font = pygame.font.Font(None, 80) # Even bigger
font = pygame.font.Font(None, 36) # Slightly smaller for HUD consistency
small_font = pygame.font.Font(None, 28)

# --- Level Data ---
# Properties: 'question': {'content': 'coin'/'powerup', 'active': True, 'hit_timer': 0, 'original_y': y}
# Powerup gives mushroom if small, fireflower/cape if super (eventually)
levels_platforms_data = [
    [
        (0, HEIGHT - 40, WIDTH, 40, 'ground'),
        (150, HEIGHT - 120, 60, 20, 'brick'), (230, HEIGHT - 180, 40, 40, 'question', {'content': 'powerup', 'active': True}),
        (350, HEIGHT - 140, 80, 20, 'brick'), (450, HEIGHT - 220, 40, 40, 'question', {'content': 'coin', 'active': True}),
        (600, HEIGHT - 100, 100, 20, 'ground'),
    ],
    [
        (0, HEIGHT - 40, 150, 40, 'ground'), (250, HEIGHT - 40, 150, 40, 'ground'),
        (50, HEIGHT - 150, 60, 20, 'brick'), (120, HEIGHT - 250, 40, 40, 'question', {'content': 'coin', 'active': True}),
        (300, HEIGHT - 180, 80, 20, 'brick'), (400, HEIGHT - 180, 40, 40, 'question', {'content': 'powerup', 'active': True}),
        (550, HEIGHT - 120, 60, 20, 'brick'),
    ],
    # Added a level 3 for Koopa demonstration
    [
        (0, HEIGHT - 40, WIDTH, 40, 'ground'),
        (100, HEIGHT - 100, 40, 40, 'question', {'content': 'powerup', 'active': True}),
        (200, HEIGHT - 160, 80, 20, 'brick'),
        (350, HEIGHT - 100, 40, 40, 'question', {'content': 'coin', 'active': True}),
        (450, HEIGHT - 220, 80, 20, 'brick'),
        (600, HEIGHT - 100, 40, 40, 'question', {'content': 'coin', 'active': True}),
    ],
     [ # Old level 3, now 4
        (0, HEIGHT - 40, 100, 40, 'ground'),
        (50, HEIGHT - 180, 40, 20, 'brick'), (150, HEIGHT - 280, 40, 20, 'brick'),
        (250, HEIGHT - 380, 40, 40, 'question', {'content': 'powerup', 'active': True}),
        (400, HEIGHT - 150, 100, 20, 'ground'), (425, HEIGHT - 190, 40, 40, 'question', {'content': 'coin', 'active': True}),
        (550, HEIGHT - 250, 60, 20, 'brick'), (650, HEIGHT - 350, 60, 20, 'brick'),
    ],
    [ # Old level 4, now 5 - Enemy Gauntlet
        (0, HEIGHT - 40, WIDTH, 40, 'ground'),
        (100, HEIGHT - 100, 50, 20, 'brick'), (200, HEIGHT - 100, 50, 20, 'brick'),
        (300, HEIGHT - 140, 40, 40, 'question', {'content': 'powerup', 'active': True}),
        (400, HEIGHT - 160, 50, 20, 'brick'), (500, HEIGHT - 160, 50, 20, 'brick'),
        (600, HEIGHT - 220, 40, 40, 'question', {'content': 'coin', 'active': True}),
    ],
]
current_level_platforms = []

# Goal Tape (SMW Style)
GOAL_TAPE_WIDTH = 10
GOAL_TAPE_HEIGHT_TOTAL = 150 # Total height of the area the tape can be
GOAL_TAPE_MOVING_HEIGHT = 30 # Actual height of the tape sprite
goal_posts_data = [ # (x_center_of_structure, y_bottom_of_structure)
    (720, HEIGHT - 40), (720, HEIGHT - 40), (720, HEIGHT - 40),
    (720, HEIGHT - 40), (720, HEIGHT - 40)
]
goal_tape_y_offset = 0 # For animating the tape moving up/down
goal_tape_direction = 1

items = [] # {'rect': Rect, 'type': 'mushroom'/'coin_anim', 'vx': speed, 'vy': 0, 'on_ground': False, 'spawn_timer': 0, 'data': {}}
# coin_anim is for coins popping from blocks
MUSHROOM_WIDTH, MUSHROOM_HEIGHT = 24, 24
MUSHROOM_SPEED = 1.2
COIN_ANIM_DURATION = 30 # Frames coin pops up then fades
COIN_ANIM_SPEED_Y = -5

# Player setup
player_rect = pygame.Rect(50, HEIGHT - PLAYER_SMALL_HEIGHT - 40, PLAYER_SMALL_WIDTH, PLAYER_SMALL_HEIGHT)
player_vx = 0
player_vy = 0
on_ground = False
facing_right = True
player_lives = 3
score = 0
player_invincible = False
invincible_timer = 0
player_state = S_SMALL
jump_hold_frames_count = 0
player_death_timer = 0 # For death animation delay

# Enemy setup
# Each enemy: {'rect': Rect, 'vx': speed, 'vy': 0, 'type': 'goomba'/'koopa', 'on_ground': False, 'stomped_timer': 0, 'state': 'walking'/'shell_idle'/'shell_sliding' (for koopa)}
enemies = []
GOOMBA_WIDTH, GOOMBA_HEIGHT = 30, 30
KOOPA_WIDTH, KOOPA_HEIGHT = 30, 42 # Koopas are taller
KOOPA_SHELL_HEIGHT = 24

# Game timer
level_start_time = 0
level_time_limit = 150 # SMW timers are often higher

# Animation variables
coin_animation_frames = []
for i in range(8):
    offset = (i / 8.0) * (20 / 2.0)
    coin_animation_frames.append(offset)
coin_frame_index = 0

# Particle effects
particles = []

# Background Elements (Could be expanded with SMW style layers)
clouds = []
for _ in range(6): # Fewer, larger SMW clouds
    x = random.randint(0, WIDTH)
    y = random.randint(30, 150)
    speed = random.uniform(0.1, 0.3) # Slower, more distant clouds
    size_w = random.randint(60, 120)
    size_h = random.randint(20, 40)
    clouds.append([x, y, speed, size_w, size_h])

hills = [] # SMW has very characteristic rounded hills
for i in range(3):
    h_w = random.randint(150, 300)
    h_h = random.randint(60, 120)
    h_x = random.randint(-50, WIDTH + 50)
    h_y = HEIGHT - 40 - h_h + random.randint(0,20) # Vary base height slightly
    hills.append({'rect': pygame.Rect(h_x, h_y, h_w, h_h),
                  'color1': (random.randint(0,80), random.randint(140,200), random.randint(0,80)), # Darker Green
                  'color2': (random.randint(40,120), random.randint(180,240), random.randint(40,120)), # Lighter Green
                  'speed_mod': random.uniform(0.2, 0.5)})

bushes = [] # SMW bushes are often clusters of rounded shapes
for i in range(4):
    num_clumps = random.randint(2,4)
    clumps = []
    base_x = random.randint(-30, WIDTH + 30)
    base_y = HEIGHT - 40 - random.randint(10,30)
    base_w = random.randint(40, 70)
    base_h = random.randint(25, 40)
    for _ in range(num_clumps):
        cl_w = base_w * random.uniform(0.4, 0.7)
        cl_h = base_h * random.uniform(0.4, 0.7)
        cl_x = base_x + random.uniform(-base_w*0.2, base_w*0.2)
        cl_y = base_y + random.uniform(-base_h*0.1, base_h*0.1)
        clumps.append(pygame.Rect(cl_x,cl_y,cl_w,cl_h))

    bushes.append({'clumps':clumps, 'base_rect': pygame.Rect(base_x, base_y, base_w, base_h),
                   'color': (random.randint(0,100), random.randint(100,180), random.randint(0,100)),
                   'speed_mod': random.uniform(0.4, 0.7)})


# HUD Item Box
item_box_rect = pygame.Rect(WIDTH // 2 - 22, 8, 44, 44) # SMW style
stored_item_type = None # 'mushroom', 'cape', 'fireflower' etc.

def update_player_size():
    global current_player_width, current_player_height
    old_bottom = player_rect.bottom
    old_centerx = player_rect.centerx
    if player_state == S_SUPER:
        current_player_width = PLAYER_SUPER_WIDTH
        current_player_height = PLAYER_SUPER_HEIGHT
    else: # Small
        current_player_width = PLAYER_SMALL_WIDTH
        current_player_height = PLAYER_SMALL_HEIGHT
    player_rect.width = current_player_width
    player_rect.height = current_player_height
    player_rect.bottom = old_bottom
    player_rect.centerx = old_centerx


def create_particles(x, y, color, count=10, intensity=1, particle_gravity=PARTICLE_GRAVITY):
    for _ in range(count):
        size = random.randint(2, 5)
        speed_x = random.uniform(-1.5, 1.5) * intensity
        speed_y = random.uniform(-2.5, -0.5) * intensity
        lifetime = random.randint(20, 50)
        particles.append([x, y, speed_x, speed_y, size, color, lifetime, particle_gravity])

def spawn_item(item_type, pos_rect):
    global items
    item_rect = pygame.Rect(pos_rect.centerx - MUSHROOM_WIDTH // 2, pos_rect.top - MUSHROOM_HEIGHT, MUSHROOM_WIDTH, MUSHROOM_HEIGHT)
    new_item = {'rect': item_rect, 'type': item_type, 'vx': MUSHROOM_SPEED, 'vy': 0, 'on_ground': False, 'spawn_timer': POWERUP_REVEAL_DURATION, 'original_y': item_rect.y}
    
    if item_type == 'mushroom':
        items.append(new_item)
    elif item_type == 'coin_anim':
        new_item['vy'] = COIN_ANIM_SPEED_Y
        new_item['vx'] = random.uniform(-0.5, 0.5)
        new_item['duration'] = COIN_ANIM_DURATION
        items.append(new_item)


def reset_level(index):
    global current_level_platforms, enemies, player_rect, player_vy, player_vx
    global level_start_time, items, on_ground, player_state # Don't reset score or lives here
    global goal_tape_y_offset, goal_tape_direction

    current_level_platforms = []
    for p_data_tuple in levels_platforms_data[index]:
        p_data = list(p_data_tuple) # Make mutable if needed
        platform_rect = pygame.Rect(p_data[0], p_data[1], p_data[2], p_data[3])
        platform_type = p_data[4]
        properties = p_data[5] if len(p_data) > 5 else {}
        # Ensure 'original_y' and 'hit_timer' for question blocks
        if platform_type == 'question':
            properties['original_y'] = platform_rect.y
            properties['hit_timer'] = 0
        current_level_platforms.append({'rect': platform_rect, 'type': platform_type, 'original_y_ref': platform_rect.y, **properties})

    # Player position and state reset on new level (not on death within level before this func)
    # Player state (small/super) should persist if just moving to next level,
    # but on explicit reset_level call (like from menu or game over), it might reset.
    # For now, player_state is managed outside this on death.
    update_player_size() # Ensure player_rect matches player_state
    player_rect.bottomleft = (50, HEIGHT - 40) # Start on the ground
    player_vy = 0
    player_vx = 0
    on_ground = True # Start on ground

    items = []
    enemies = []
    base_y = HEIGHT - GOOMBA_HEIGHT - 40

    # Define enemies per level (example with Goombas and Koopas)
    if index == 0:
        enemies.append({'rect': pygame.Rect(300, base_y, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': -ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
        enemies.append({'rect': pygame.Rect(500, HEIGHT - 220 - GOOMBA_HEIGHT, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
    elif index == 1:
        enemies.append({'rect': pygame.Rect(450, base_y - KOOPA_HEIGHT + GOOMBA_HEIGHT, KOOPA_WIDTH, KOOPA_HEIGHT), 'vx': -ENEMY_BASE_SPEED, 'vy': 0, 'type': 'koopa', 'state': 'walking', 'on_ground': False, 'stomped_timer': 0, 'original_vx': -ENEMY_BASE_SPEED})
        enemies.append({'rect': pygame.Rect(350, HEIGHT - 180 - GOOMBA_HEIGHT, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': -ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
    elif index == 2: # Koopa showcase
        enemies.append({'rect': pygame.Rect(250, base_y - KOOPA_HEIGHT + GOOMBA_HEIGHT, KOOPA_WIDTH, KOOPA_HEIGHT), 'vx': -ENEMY_BASE_SPEED, 'vy': 0, 'type': 'koopa', 'state': 'walking', 'on_ground': False, 'stomped_timer': 0, 'original_vx': -ENEMY_BASE_SPEED})
        enemies.append({'rect': pygame.Rect(400, base_y, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
        enemies.append({'rect': pygame.Rect(550, base_y - KOOPA_HEIGHT + GOOMBA_HEIGHT, KOOPA_WIDTH, KOOPA_HEIGHT), 'vx': ENEMY_BASE_SPEED, 'vy': 0, 'type': 'koopa', 'state': 'walking', 'on_ground': False, 'stomped_timer': 0, 'original_vx': ENEMY_BASE_SPEED})
    # Add more for other levels as needed...
    elif index == 3: # Old 2, now 4
        enemies.append({'rect': pygame.Rect(80, HEIGHT - 180 - GOOMBA_HEIGHT, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
        enemies.append({'rect': pygame.Rect(450, HEIGHT - 150 - GOOMBA_HEIGHT, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': -ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
        enemies.append({'rect': pygame.Rect(600, HEIGHT - 250 - KOOPA_HEIGHT + GOOMBA_HEIGHT, KOOPA_WIDTH, KOOPA_HEIGHT), 'vx': ENEMY_BASE_SPEED, 'vy': 0, 'type': 'koopa', 'state':'walking', 'on_ground': False, 'stomped_timer': 0, 'original_vx': ENEMY_BASE_SPEED})
    elif index == 4: # Old 3, now 5 Enemy Gauntlet
        for i in range(3):
            enemies.append({'rect': pygame.Rect(150 + i*150, base_y, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': -ENEMY_BASE_SPEED if i%2==0 else ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
        enemies.append({'rect': pygame.Rect(250, base_y - KOOPA_HEIGHT + GOOMBA_HEIGHT, KOOPA_WIDTH, KOOPA_HEIGHT), 'vx': -ENEMY_BASE_SPEED, 'vy': 0, 'type': 'koopa', 'state':'walking', 'on_ground': False, 'stomped_timer': 0, 'original_vx': -ENEMY_BASE_SPEED})
        enemies.append({'rect': pygame.Rect(500, base_y - KOOPA_HEIGHT + GOOMBA_HEIGHT, KOOPA_WIDTH, KOOPA_HEIGHT), 'vx': ENEMY_BASE_SPEED, 'vy': 0, 'type': 'koopa', 'state':'walking', 'on_ground': False, 'stomped_timer': 0, 'original_vx': ENEMY_BASE_SPEED})


    level_start_time = pygame.time.get_ticks()
    goal_tape_y_offset = 0
    goal_tape_direction = 1

def player_dies():
    global player_lives, player_state, state, player_invincible, invincible_timer, player_death_timer, player_vx, player_vy
    player_lives -= 1
    create_particles(player_rect.centerx, player_rect.centery, MARIO_RED, 40, intensity=2.5)
    player_state = S_SMALL # Revert to small Mario on death
    update_player_size()
    player_invincible = True # Invincibility on respawn
    invincible_timer = INVINCIBILITY_DURATION // 2 # Shorter respawn invincibility

    if player_lives <= 0:
        state = GAME_OVER
    else:
        # Player death animation/pause
        state = PLAYER_DIED_TRANSITION
        player_death_timer = 90 # Frames for death fall/pause
        player_vx = 0
        player_vy = -10 # Small hop up
        # Level will be reset after player_death_timer expires

def draw_menu():
    screen.fill(SKY_BLUE)
    for hill in hills:
        pygame.draw.ellipse(screen, hill['color1'], hill['rect'])
        pygame.draw.ellipse(screen, hill['color2'], (hill['rect'].x + hill['rect'].width *0.1, hill['rect'].y + hill['rect'].height*0.1, hill['rect'].width*0.8, hill['rect'].height*0.8))
    for bush_data in bushes:
        for clump in bush_data['clumps']: pygame.draw.ellipse(screen, bush_data['color'], clump)

    for cloud_data in clouds: pygame.draw.ellipse(screen, WHITE, (int(cloud_data[0]), int(cloud_data[1]), cloud_data[3], cloud_data[4]))
    pygame.draw.rect(screen, GROUND_GREEN, (0, HEIGHT - 40, WIDTH, 40))
    pygame.draw.rect(screen, GROUND_BROWN, (0, HEIGHT - 30, WIDTH, 30))

    title_text = title_font.render("Super Mario World X", True, WHITE)
    title_shadow = title_font.render("Super Mario World X", True, (50,50,150)) # Blueish shadow
    screen.blit(title_shadow, (WIDTH // 2 - title_text.get_width() // 2 + 4, HEIGHT // 3 - 50 + 4))
    screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 3 - 50))
    
    temp_player_draw_rect = pygame.Rect(WIDTH // 2 - PLAYER_SUPER_WIDTH // 2, HEIGHT - 40 - PLAYER_SUPER_HEIGHT - 20, PLAYER_SUPER_WIDTH, PLAYER_SUPER_HEIGHT)
    draw_player_sprite(screen, temp_player_draw_rect, S_SUPER, True, True, 0, 0) # Draw Super Mario

    prompt = font.render("Press ENTER to Start", True, WHITE)
    prompt_shadow = font.render("Press ENTER to Start", True, BLACK)
    screen.blit(prompt_shadow, (WIDTH // 2 - prompt.get_width() // 2 + 2, HEIGHT // 2 + 102))
    screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 + 100))
    
    copyright_text = small_font.render("Cat-san SMW Engine - Rev X", True, WHITE)
    screen.blit(copyright_text, (WIDTH // 2 - copyright_text.get_width() // 2, HEIGHT - 35))

def draw_select():
    screen.fill(SKY_BLUE)
    for cloud_data in clouds: pygame.draw.ellipse(screen, WHITE, (int(cloud_data[0]), int(cloud_data[1]), cloud_data[3], cloud_data[4]))
    pygame.draw.rect(screen, GROUND_GREEN, (0, HEIGHT - 40, WIDTH, 40))

    title = title_font.render("Select Sector", True, WHITE) # Changed "Level" to "Sector"
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
    
    num_levels = len(levels_platforms_data)
    box_size = 70 # Slightly smaller boxes
    padding = 15
    cols = 4 # Allow more levels to be shown easily
    start_x = (WIDTH - (cols * box_size + (cols - 1) * padding)) // 2
    start_y = 160

    for i in range(num_levels):
        col = i % cols
        row = i // cols
        x = start_x + col * (box_size + padding)
        y = start_y + row * (box_size + padding + 15)
        
        color = QUESTION_BLOCK_YELLOW if i == current_level_index else MARIO_BLUE_OVERALLS
        border_color = BLACK
        
        pygame.draw.rect(screen, color, (x, y, box_size, box_size), border_radius=8)
        pygame.draw.rect(screen, border_color, (x, y, box_size, box_size), 3, border_radius=8)
        
        level_text_val = str(i + 1)
        # For World-Level format like "1-1"
        # world_num = (i // 4) + 1 # Example: 4 levels per world
        # stage_num = (i % 4) + 1
        # level_text_val = f"{world_num}-{stage_num}"
        
        level_text = font.render(level_text_val, True, WHITE if color == MARIO_BLUE_OVERALLS else BLACK)
        screen.blit(level_text, (x + box_size // 2 - level_text.get_width() // 2, y + box_size // 2 - level_text.get_height() // 2))
    
    instructions = small_font.render("Use ARROWS to select, ENTER to warp!", True, WHITE)
    screen.blit(instructions, (WIDTH // 2 - instructions.get_width() // 2, HEIGHT - 70))


def draw_player_sprite(surface, rect, current_state, p_facing_right, p_on_ground, p_vx, p_vy):
    skin_color = MARIO_SKIN
    hair_color = MARIO_HAIR_BROWN
    cap_shirt_color = MARIO_RED
    overalls_color = MARIO_BLUE_OVERALLS
    shoe_color = MARIO_SHOE_BROWN

    # Animation state (simple walk cycle)
    is_walking = p_on_ground and abs(p_vx) > 0.5
    walk_frame = (pygame.time.get_ticks() // 120) % 2 # 2 frames for walk cycle

    # Jumping/Falling pose
    in_air_pose = not p_on_ground

    # Base rect for calculations
    x, y, w, h = rect.x, rect.y, rect.width, rect.height

    if current_state == S_SMALL:
        # Small Mario - more compact, rounder
        # Head (slightly larger proportionally)
        head_radius = w * 0.45
        head_cx = x + w / 2
        head_cy = y + head_radius * 1.1

        # Cap
        pygame.draw.rect(surface, cap_shirt_color, (head_cx - head_radius * 0.9, head_cy - head_radius * 1.3, head_radius * 1.8, head_radius * 0.8)) # Main cap
        brim_x = head_cx + (head_radius * 0.3 if p_facing_right else -head_radius * 1.1)
        pygame.draw.rect(surface, cap_shirt_color, (brim_x, head_cy - head_radius * 0.7, head_radius * 0.8, head_radius * 0.4)) # Brim

        pygame.draw.circle(surface, skin_color, (int(head_cx), int(head_cy)), int(head_radius)) # Head

        # Eyes (simple)
        eye_off_x = head_radius * 0.3 * (1 if p_facing_right else -1)
        pygame.draw.circle(surface, BLACK, (int(head_cx + eye_off_x), int(head_cy - head_radius * 0.1)), 2)

        # Body (shirt part)
        body_h = h * 0.45
        body_y = head_cy + head_radius * 0.7
        pygame.draw.rect(surface, cap_shirt_color, (x + w * 0.1, body_y, w * 0.8, body_h))

        # Overalls (very small part)
        overalls_h = h * 0.2
        pygame.draw.rect(surface, overalls_color, (x + w * 0.15, body_y + body_h * 0.7, w * 0.7, overalls_h))
        
        # Shoes
        shoe_w = w * 0.4
        shoe_h = h * 0.25
        shoe_y_base = y + h - shoe_h
        if p_facing_right:
            pygame.draw.ellipse(surface, shoe_color, (x + w * 0.5, shoe_y_base, shoe_w, shoe_h))
            if is_walking and walk_frame == 1: pygame.draw.ellipse(surface, shoe_color, (x + w * 0.1, shoe_y_base + shoe_h*0.2, shoe_w*0.8, shoe_h*0.8)) # Trailing foot
        else:
            pygame.draw.ellipse(surface, shoe_color, (x + w * 0.1, shoe_y_base, shoe_w, shoe_h))
            if is_walking and walk_frame == 1: pygame.draw.ellipse(surface, shoe_color, (x + w * 0.5, shoe_y_base + shoe_h*0.2, shoe_w*0.8, shoe_h*0.8))


    elif current_state == S_SUPER:
        # Super Mario - Taller, more defined
        # Head
        head_radius = w * 0.30
        head_cx = x + w / 2
        head_cy = y + head_radius * 1.2

        # Cap
        pygame.draw.rect(surface, cap_shirt_color, (head_cx - head_radius * 1.0, head_cy - head_radius * 1.4, head_radius * 2.0, head_radius * 1.0))
        brim_x = head_cx + (head_radius * 0.5 if p_facing_right else -head_radius * 1.3)
        pygame.draw.rect(surface, cap_shirt_color, (brim_x, head_cy - head_radius * 0.6, head_radius * 0.8, head_radius * 0.5))

        pygame.draw.circle(surface, skin_color, (int(head_cx), int(head_cy)), int(head_radius)) # Head

        # Eyes
        eye_off_x = head_radius * 0.4 * (1 if p_facing_right else -1)
        pygame.draw.circle(surface, BLACK, (int(head_cx + eye_off_x), int(head_cy - head_radius * 0.1)), 3)
        
        # Torso (Overalls with shirt underneath)
        torso_top_y = head_cy + head_radius * 0.8
        shirt_sleeve_w = w * 0.3
        shirt_sleeve_h = h * 0.20
        
        overalls_main_w = w * 0.7
        overalls_main_h = h * 0.45
        overalls_main_x = x + (w - overalls_main_w) / 2
        overalls_main_y = torso_top_y + shirt_sleeve_h * 0.3
        
        # Shirt (visible parts)
        pygame.draw.rect(surface, cap_shirt_color, (overalls_main_x - shirt_sleeve_w*0.1, torso_top_y, shirt_sleeve_w, shirt_sleeve_h)) # Left arm base
        pygame.draw.rect(surface, cap_shirt_color, (overalls_main_x + overalls_main_w - shirt_sleeve_w*0.9, torso_top_y, shirt_sleeve_w, shirt_sleeve_h)) # Right arm base
        pygame.draw.rect(surface, cap_shirt_color, (overalls_main_x, overalls_main_y - h*0.05, overalls_main_w, h*0.1)) # Chest part of shirt


        # Overalls main body
        pygame.draw.rect(surface, overalls_color, (overalls_main_x, overalls_main_y, overalls_main_w, overalls_main_h))
        # Straps
        strap_w = w * 0.15
        pygame.draw.rect(surface, overalls_color, (head_cx - strap_w*1.5, torso_top_y, strap_w, h * 0.2))
        pygame.draw.rect(surface, overalls_color, (head_cx + strap_w*0.5, torso_top_y, strap_w, h * 0.2))

        # Legs (part of overalls)
        leg_w = overalls_main_w * 0.45
        leg_h = h * 0.25
        leg_y = overalls_main_y + overalls_main_h - leg_h * 0.3
        pygame.draw.rect(surface, overalls_color, (overalls_main_x, leg_y, leg_w, leg_h))
        pygame.draw.rect(surface, overalls_color, (overalls_main_x + overalls_main_w - leg_w, leg_y, leg_w, leg_h))

        # Shoes
        shoe_w = w * 0.4
        shoe_h = h * 0.18
        shoe_y_base = y + h - shoe_h
        
        if in_air_pose: # Jumping/falling pose - feet tucked a bit
            shoe_y_offset = -shoe_h * 0.2
            if p_facing_right:
                 pygame.draw.ellipse(surface, shoe_color, (x + w * 0.45, shoe_y_base + shoe_y_offset, shoe_w, shoe_h))
            else:
                 pygame.draw.ellipse(surface, shoe_color, (x + w * 0.15, shoe_y_base + shoe_y_offset, shoe_w, shoe_h))
        elif is_walking:
            if p_facing_right:
                pygame.draw.ellipse(surface, shoe_color, (x + w * (0.55 if walk_frame == 0 else 0.45) , shoe_y_base, shoe_w, shoe_h)) # Leading
                pygame.draw.ellipse(surface, shoe_color, (x + w * 0.1, shoe_y_base + shoe_h*0.1, shoe_w*0.9, shoe_h*0.9)) # Trailing
            else:
                pygame.draw.ellipse(surface, shoe_color, (x + w * (0.05 if walk_frame == 0 else 0.15) , shoe_y_base, shoe_w, shoe_h)) # Leading
                pygame.draw.ellipse(surface, shoe_color, (x + w * 0.5, shoe_y_base + shoe_h*0.1, shoe_w*0.9, shoe_h*0.9)) # Trailing
        else: # Standing
             if p_facing_right: pygame.draw.ellipse(surface, shoe_color, (x + w * 0.5, shoe_y_base, shoe_w, shoe_h))
             else: pygame.draw.ellipse(surface, shoe_color, (x + w * 0.1, shoe_y_base, shoe_w, shoe_h))


    # Invincibility flash
    if player_invincible and (invincible_timer // 5) % 2 == 0: # Faster flash
        flash_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        flash_surface.fill((255, 255, 255, 100)) # Semi-transparent white
        surface.blit(flash_surface, rect.topleft)


def draw_goomba(surface, enemy_data):
    rect = enemy_data['rect']
    walk_anim_offset = 0
    if enemy_data.get('vx', 0) != 0 : # Bobbing if walking
        walk_anim_offset = int((pygame.time.get_ticks() // 200) % 2) * -2


    if enemy_data.get('stomped_timer', 0) > 0: # Squashed Goomba
        squashed_height = rect.height // 2.5
        pygame.draw.ellipse(surface, GOOMBA_BROWN, (rect.x, rect.bottom - squashed_height, rect.width, squashed_height))
        # No eyes for squashed usually, or simple X
        return

    # Body (more mushroom-like head for SMW Goomba)
    body_rect = pygame.Rect(rect.x, rect.y + walk_anim_offset, rect.width, rect.height * 0.8)
    pygame.draw.ellipse(surface, GOOMBA_BROWN, body_rect)
    
    # Feet
    foot_width = rect.width // 2.5
    foot_height = rect.height // 3
    foot_y = body_rect.bottom - foot_height * 0.6
    pygame.draw.ellipse(surface, GOOMBA_FEET, (rect.left + rect.width * 0.05, foot_y, foot_width, foot_height))
    pygame.draw.ellipse(surface, GOOMBA_FEET, (rect.right - rect.width * 0.05 - foot_width, foot_y, foot_width, foot_height))
    
    # Eyes (SMW Goombas have angrier, larger eyes)
    eye_radius = rect.width // 5
    eye_y = body_rect.centery - rect.height * 0.05
    left_eye_x = body_rect.centerx - rect.width // 5
    right_eye_x = body_rect.centerx + rect.width // 5
    
    # Whites of eyes
    pygame.draw.ellipse(surface, GOOMBA_EYE_WHITE, (left_eye_x - eye_radius//2, eye_y - eye_radius//1.5, eye_radius, eye_radius * 1.2))
    pygame.draw.ellipse(surface, GOOMBA_EYE_WHITE, (right_eye_x - eye_radius//2, eye_y - eye_radius//1.5, eye_radius, eye_radius * 1.2))
    # Pupils
    pupil_off_x = 1 if enemy_data.get('vx',0) > 0 else -1
    pygame.draw.circle(surface, BLACK, (left_eye_x + pupil_off_x, eye_y), eye_radius // 2.5)
    pygame.draw.circle(surface, BLACK, (right_eye_x + pupil_off_x, eye_y), eye_radius // 2.5)
    # Angry brows (Thick lines)
    pygame.draw.line(surface, BLACK, (left_eye_x - eye_radius*0.6, eye_y - eye_radius*0.7), (left_eye_x + eye_radius*0.2, eye_y - eye_radius*0.3), 3)
    pygame.draw.line(surface, BLACK, (right_eye_x + eye_radius*0.6, eye_y - eye_radius*0.7), (right_eye_x - eye_radius*0.2, eye_y - eye_radius*0.3), 3)

def draw_koopa(surface, enemy_data):
    rect = enemy_data['rect']
    state = enemy_data.get('state', 'walking')
    e_vx = enemy_data.get('vx', 0)

    shell_color = KOOPA_GREEN_SHELL
    body_color = KOOPA_GREEN_BODY
    limb_color = KOOPA_FEET_HANDS # Yellowish for SMW Koopas

    if state == 'shell_idle' or state == 'shell_sliding':
        shell_rect_h = rect.height * 0.7 # Shell is shorter
        shell_rect_y = rect.bottom - shell_rect_h
        shell_rect = pygame.Rect(rect.x, shell_rect_y, rect.width, shell_rect_h)
        pygame.draw.ellipse(surface, shell_color, shell_rect)
        # Shell details (simple lines)
        pygame.draw.ellipse(surface, KOOPA_GREEN_SHELL_HIGHLIGHT, (shell_rect.x + shell_rect.width*0.1, shell_rect.y + shell_rect.height*0.1, shell_rect.width*0.8, shell_rect.height*0.5))
        pygame.draw.line(surface, BLACK, (shell_rect.centerx, shell_rect.top + 2), (shell_rect.centerx, shell_rect.bottom -2), 1)
        pygame.draw.line(surface, BLACK, (shell_rect.left + 2, shell_rect.centery), (shell_rect.right -2, shell_rect.centery), 1)
        if state == 'shell_sliding' and (pygame.time.get_ticks() // 100) % 2 == 0 : # Sparkles for sliding
            sparkle_x = shell_rect.centerx + random.randint(-5,5) * (1 if e_vx > 0 else -1)
            sparkle_y = shell_rect.centery + random.randint(-5,5)
            pygame.draw.circle(surface, WHITE, (sparkle_x, sparkle_y), 2)
        return

    # Walking Koopa
    walk_anim_offset = int((pygame.time.get_ticks() // 200) % 2) * -2 # Bobbing
    
    # Shell (on back)
    shell_w = rect.width * 1.1 # Shell slightly wider than body
    shell_h = rect.height * 0.65
    shell_x = rect.centerx - shell_w / 2
    shell_y = rect.y + rect.height * 0.1 + walk_anim_offset
    pygame.draw.ellipse(surface, shell_color, (shell_x, shell_y, shell_w, shell_h))
    pygame.draw.ellipse(surface, KOOPA_GREEN_SHELL_HIGHLIGHT, (shell_x + shell_w*0.1, shell_y + shell_h*0.1, shell_w*0.8, shell_h*0.4))


    # Head
    head_r = rect.width * 0.35
    head_x_offset = rect.width * 0.1 * (1 if e_vx >= 0 else -1) # Head slightly forward
    head_cx = rect.centerx + head_x_offset
    head_cy = rect.y + head_r * 0.9 + walk_anim_offset
    pygame.draw.ellipse(surface, body_color, (head_cx - head_r, head_cy - head_r*0.8, head_r*2, head_r*1.6)) # Snout shape
    
    # Eyes (simple ovals)
    eye_r = head_r * 0.3
    eye_y = head_cy - head_r * 0.1
    eye_x_facing = head_cx + head_r * 0.3 * (1 if e_vx >=0 else -1)
    pygame.draw.ellipse(surface, WHITE, (eye_x_facing - eye_r, eye_y - eye_r, eye_r*1.5, eye_r*2))
    pygame.draw.circle(surface, BLACK, (int(eye_x_facing), int(eye_y)), int(eye_r*0.5))


    # Feet/Legs
    foot_w = rect.width * 0.3
    foot_h = rect.height * 0.25
    foot_y = rect.bottom - foot_h
    # Basic alternating feet for walk
    if (pygame.time.get_ticks() // 150) % 2 == 0:
        pygame.draw.ellipse(surface, limb_color, (rect.centerx - foot_w*1.2, foot_y, foot_w, foot_h))
        pygame.draw.ellipse(surface, limb_color, (rect.centerx + foot_w*0.2, foot_y + foot_h*0.2, foot_w, foot_h*0.8))
    else:
        pygame.draw.ellipse(surface, limb_color, (rect.centerx - foot_w*1.2, foot_y + foot_h*0.2, foot_w, foot_h*0.8))
        pygame.draw.ellipse(surface, limb_color, (rect.centerx + foot_w*0.2, foot_y, foot_w, foot_h))

    # Arms (tiny, often not very visible)
    arm_w, arm_h = rect.width*0.15, rect.height*0.2
    arm_y = rect.y + rect.height*0.4 + walk_anim_offset
    if e_vx >= 0: # Facing right
        pygame.draw.ellipse(surface, limb_color, (rect.centerx + rect.width*0.1, arm_y, arm_w, arm_h))
    else: # Facing left
        pygame.draw.ellipse(surface, limb_color, (rect.centerx - rect.width*0.25, arm_y, arm_w, arm_h))


def draw_platform(surface, platform_data):
    rect = platform_data['rect']
    ptype = platform_data['type']
    
    current_y = rect.y # For hit animation
    if 'hit_timer' in platform_data and platform_data['hit_timer'] > 0:
        offset = abs(platform_data['hit_timer'] - 10) # Simple up/down bump (10 frames up, 10 down)
        current_y = platform_data['original_y_ref'] - (5 - offset // 2) if offset < 10 else platform_data['original_y_ref'] # Max bump 5px
        rect.y = current_y


    if ptype == 'ground':
        pygame.draw.rect(surface, GROUND_GREEN, rect)
        pygame.draw.rect(surface, GROUND_BROWN, (rect.x, rect.y + 8, rect.width, rect.height - 8)) # Thicker dirt
        for i in range(rect.width // 25): # SMW style grass tufts are more like rounded edges
            pygame.draw.circle(surface, GROUND_GREEN, (rect.x + 12 + i * 25, rect.y + 4), 8)
    elif ptype == 'brick':
        pygame.draw.rect(surface, PLATFORM_BRICK_RED, rect)
        bw, bh = 20, 10 # Brick dimensions
        for r_idx, r_y in enumerate(range(rect.top, rect.bottom, bh)):
            pygame.draw.line(surface, PLATFORM_BRICK_MORTAR, (rect.left, r_y), (rect.right, r_y), 1)
            for c_idx, c_x in enumerate(range(rect.left, rect.right, bw)):
                stagger = bw // 2 if r_idx % 2 == 0 else 0
                if c_x + stagger < rect.right:
                     pygame.draw.line(surface, PLATFORM_BRICK_MORTAR, (c_x + stagger, r_y), (c_x + stagger, r_y + bh if r_y + bh <= rect.bottom else rect.bottom ), 1)

    elif ptype == 'question':
        is_active = platform_data.get('active', False)
        block_color = QUESTION_BLOCK_YELLOW if is_active else USED_BLOCK_BROWN
        shadow_color = QUESTION_BLOCK_SHADOW if is_active else (120,80,50) # Darker Used Brown

        pygame.draw.rect(surface, BLACK, (rect.x-1, rect.y-1, rect.width+2, rect.height+2), border_radius=5) # Black outline SMW style
        pygame.draw.rect(surface, block_color, rect, border_radius=4)
        
        if is_active:
            # SMW '?' is specific
            q_font_size = int(rect.height * 0.7)
            q_font_snes = pygame.font.Font(None, q_font_size) # Use default for now
            q_mark = q_font_snes.render("?", True, WHITE if (pygame.time.get_ticks()//150)%2 == 0 else BLACK) # Flashing ?
            q_rect = q_mark.get_rect(center=(rect.centerx, rect.centery + rect.height*0.05))
            surface.blit(q_mark, q_rect)
            # Rivets/bolts (SMW has 4 bolts)
            bolt_size = max(2, rect.width // 10)
            bolt_positions = [
                (rect.left + bolt_size//2 + 2, rect.top + bolt_size//2 + 2),
                (rect.right - bolt_size//2 - 2, rect.top + bolt_size//2 + 2),
                (rect.left + bolt_size//2 + 2, rect.bottom - bolt_size//2 - 2),
                (rect.right - bolt_size//2 - 2, rect.bottom - bolt_size//2 - 2)
            ]
            for bp_x, bp_y in bolt_positions:
                pygame.draw.circle(surface, BLACK, (bp_x, bp_y), bolt_size//2)
        else: # Used block - often plain in SMW
            pygame.draw.rect(surface, shadow_color, (rect.x+2, rect.y+2, rect.width-4, rect.height-4), border_radius=3)


    if 'hit_timer' in platform_data and platform_data['hit_timer'] > 0: # Put original y back after drawing
        rect.y = platform_data['original_y_ref']


def draw_coin_sprite(surface, rect, frame_offset_unused): # Using rect for animated coin from block
    # Simplified coin pop animation
    pygame.draw.circle(surface, QUESTION_BLOCK_YELLOW, rect.center, rect.width // 2)
    pygame.draw.circle(surface, (255,255,100), rect.center, rect.width // 2.5) # Highlight
    coin_font = pygame.font.Font(None, int(rect.height*0.8))
    dollar_sign = coin_font.render("$", True, BLACK) # Or a C or something
    surface.blit(dollar_sign, dollar_sign.get_rect(center=rect.center))


def draw_mushroom(surface, item_data):
    rect = item_data['rect']
    # Cap
    cap_rect = pygame.Rect(rect.x, rect.y, rect.width, rect.height * 0.65)
    pygame.draw.ellipse(surface, MUSHROOM_RED, cap_rect)
    # Spots
    spot_r = rect.width * 0.15
    pygame.draw.circle(surface, MUSHROOM_SPOTS, (cap_rect.centerx - rect.width*0.2, cap_rect.centery - rect.height*0.05), spot_r)
    pygame.draw.circle(surface, MUSHROOM_SPOTS, (cap_rect.centerx + rect.width*0.2, cap_rect.centery - rect.height*0.05), spot_r)
    pygame.draw.circle(surface, MUSHROOM_SPOTS, (cap_rect.centerx, cap_rect.centery + rect.height*0.1), spot_r)
    # Stem
    stem_h = rect.height * 0.45
    stem_w = rect.width * 0.5
    stem_rect = pygame.Rect(rect.centerx - stem_w/2, cap_rect.bottom - stem_h*0.2, stem_w, stem_h)
    pygame.draw.rect(surface, MUSHROOM_STEM, stem_rect)
    # Eyes (simple dots for SMW mushrooms)
    eye_r = rect.width * 0.08
    eye_y = cap_rect.bottom - stem_h * 0.5
    pygame.draw.circle(surface, BLACK, (rect.centerx - rect.width*0.15, eye_y), eye_r)
    pygame.draw.circle(surface, BLACK, (rect.centerx + rect.width*0.15, eye_y), eye_r)


def draw_game():
    screen.fill(SKY_BLUE)
    
    # Parallax background elements
    for hill in hills:
        # Draw main hill shape
        pygame.draw.ellipse(screen, hill['color1'], hill['rect'])
        # Draw highlight/lighter inner part
        highlight_rect = pygame.Rect(hill['rect'].x + hill['rect'].width * 0.1,
                                     hill['rect'].y + hill['rect'].height * 0.05,
                                     hill['rect'].width * 0.8,
                                     hill['rect'].height * 0.7)
        pygame.draw.ellipse(screen, hill['color2'], highlight_rect)

    for bush_data in bushes:
        for clump_rect in bush_data['clumps']:
            pygame.draw.ellipse(screen, bush_data['color'], clump_rect)
            # Simple shadow/darker part for depth
            shadow_clump = clump_rect.copy()
            shadow_clump.width *= 0.8
            shadow_clump.height *= 0.6
            shadow_clump.centerx = clump_rect.centerx
            shadow_clump.centery = clump_rect.centery + clump_rect.height*0.1
            pygame.draw.ellipse(screen, (max(0,bush_data['color'][0]-30),max(0,bush_data['color'][1]-30),max(0,bush_data['color'][2]-30)), shadow_clump)


    for cloud_data in clouds:
        base_x, base_y, _, size_w, size_h = cloud_data
        # SMW clouds are often composed of multiple overlapping circles/ellipses
        pygame.draw.ellipse(screen, WHITE, (int(base_x), int(base_y), int(size_w), int(size_h)))
        pygame.draw.ellipse(screen, WHITE, (int(base_x + size_w*0.3), int(base_y - size_h*0.2), int(size_w*0.7), int(size_h*0.8)))
        pygame.draw.ellipse(screen, WHITE, (int(base_x - size_w*0.2), int(base_y + size_h*0.1), int(size_w*0.6), int(size_h*0.7)))
        # Inner shadow/detail for clouds
        pygame.draw.ellipse(screen, (225,225,225), (int(base_x+4), int(base_y+4), int(size_w-8), int(size_h-8)))


    # Draw platforms
    for p_data in current_level_platforms:
        draw_platform(screen, p_data)
            
    # Draw items (mushrooms, animated coins from blocks)
    global coin_frame_index
    coin_frame_index = (coin_frame_index + COIN_SPIN_SPEED) % len(coin_animation_frames) # For future collectible coins
    for item_data in items:
        if item_data['spawn_timer'] > 0: continue # Item is 'emerging' from block, not fully visible/interactive
        if item_data['type'] == 'mushroom':
            draw_mushroom(screen, item_data)
        elif item_data['type'] == 'coin_anim': # The coin that pops from a block
            draw_coin_sprite(screen, item_data['rect'], 0) # frame_offset not used here

    # Draw Goal Tape (SMW Style)
    goal_x_center, goal_y_bottom = goal_posts_data[current_level_index]
    post_width = 15
    post_height = GOAL_TAPE_HEIGHT_TOTAL + 20
    # Left Post
    pygame.draw.rect(screen, GOAL_POST_COLOR, (goal_x_center - GOAL_TAPE_WIDTH*2 - post_width, goal_y_bottom - post_height, post_width, post_height))
    pygame.draw.circle(screen, (50,50,50), (goal_x_center - GOAL_TAPE_WIDTH*2 - post_width//2, goal_y_bottom - post_height), post_width//1.5)
    # Right Post
    pygame.draw.rect(screen, GOAL_POST_COLOR, (goal_x_center + GOAL_TAPE_WIDTH*2, goal_y_bottom - post_height, post_width, post_height))
    pygame.draw.circle(screen, (50,50,50), (goal_x_center + GOAL_TAPE_WIDTH*2 + post_width//2, goal_y_bottom - post_height), post_width//1.5)
    
    # Moving Tape
    tape_base_y = goal_y_bottom - GOAL_TAPE_HEIGHT_TOTAL
    current_tape_y = tape_base_y + goal_tape_y_offset
    pygame.draw.rect(screen, GOAL_TAPE_COLOR, (goal_x_center - GOAL_TAPE_WIDTH // 2, current_tape_y, GOAL_TAPE_WIDTH, GOAL_TAPE_MOVING_HEIGHT))
    pygame.draw.rect(screen, BLACK, (goal_x_center - GOAL_TAPE_WIDTH // 2, current_tape_y, GOAL_TAPE_WIDTH, GOAL_TAPE_MOVING_HEIGHT),1) # Outline

    # Draw player
    if state != PLAYER_DIED_TRANSITION: # Don't draw normal player during death anim
        draw_player_sprite(screen, player_rect, player_state, facing_right, on_ground, player_vx, player_vy)
    
    # Draw enemies
    for enemy_data in enemies:
        if enemy_data.get('stomped_timer', 0) > 0 and enemy_data['type'] == 'goomba': # Goomba being stomped
            draw_goomba(screen, enemy_data) # Draw squashed
        elif enemy_data.get('state', '') == 'shell_idle' or enemy_data.get('state', '') == 'shell_sliding': # Koopa shell
            draw_koopa(screen, enemy_data)
        elif enemy_data.get('type') == 'goomba':
            draw_goomba(screen, enemy_data)
        elif enemy_data.get('type') == 'koopa':
            draw_koopa(screen, enemy_data)

    # Draw particles
    for p_data in particles:
        pygame.draw.circle(screen, p_data[5], (int(p_data[0]), int(p_data[1])), int(p_data[4]))
    
    # Draw HUD (SMW Style)
    hud_y_offset = 10
    # Score (Top-Left) - "MARIO" \n "SCORE"
    mario_label = small_font.render("MARIO", True, WHITE)
    screen.blit(mario_label, (20, hud_y_offset))
    score_val_text = font.render(f"{score:07d}", True, WHITE) # SMW often has 7 digits with leading zeros
    screen.blit(score_val_text, (20, hud_y_offset + 20))

    # Lives (Next to score) - Using a mini player head icon and "x LIVES"
    # Draw a mini Mario head for lives icon
    life_icon_rect = pygame.Rect(130, hud_y_offset + 5, PLAYER_SMALL_WIDTH // 1.5, PLAYER_SMALL_HEIGHT // 1.5)
    draw_player_sprite(screen, life_icon_rect, S_SMALL, True, True, 0, 0) # Simplified call
    
    lives_text = font.render(f"x {player_lives}", True, WHITE)
    screen.blit(lives_text, (130 + life_icon_rect.width + 5, hud_y_offset + 12))

    # Item Box (Top-Center)
    pygame.draw.rect(screen, BLACK, (item_box_rect.x-2, item_box_rect.y-2, item_box_rect.width+4, item_box_rect.height+4), border_radius=5)
    pygame.draw.rect(screen, (50,50,80), item_box_rect, border_radius=4) # Dark blue BG
    if stored_item_type == 'mushroom':
        icon_rect = pygame.Rect(0,0, MUSHROOM_WIDTH*0.8, MUSHROOM_HEIGHT*0.8)
        icon_rect.center = item_box_rect.center
        draw_mushroom(screen, {'rect': icon_rect}) # Draw a small mushroom icon
    # Add other item icons (Cape, Fire Flower) here later

    # Coins (Top-Right) - Coin icon and count
    coin_icon_rect = pygame.Rect(WIDTH - 120, hud_y_offset + 5, 20, 20) # Placeholder for coin icon
    pygame.draw.circle(screen, QUESTION_BLOCK_YELLOW, coin_icon_rect.center, 10)
    pygame.draw.circle(screen, (200,150,0), coin_icon_rect.center, 8)
    # We don't have a separate coin counter variable yet, using score as placeholder concept
    # coin_count_text = font.render(f"x {score//100}", True, WHITE) # Example: 1 coin = 100 score
    # screen.blit(coin_count_text, (WIDTH - 120 + coin_icon_rect.width + 5, hud_y_offset + 8))


    # Timer (Below coins, Top-Right)
    elapsed = (pygame.time.get_ticks() - level_start_time) // 1000
    remaining_time = max(0, level_time_limit - elapsed)
    timer_label_text = small_font.render("TIME", True, WHITE)
    screen.blit(timer_label_text, (WIDTH - 80, hud_y_offset + 2)) # Timer label above value
    timer_text = font.render(f"{remaining_time:03d}", True, WHITE)
    screen.blit(timer_text, (WIDTH - timer_text.get_width() - 15, hud_y_offset + 20))


def draw_game_over():
    screen.fill(BLACK) # SMW Game Over is often black
    game_over_text = title_font.render("GAME OVER", True, MARIO_RED)
    screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 3))
    
    score_text_val = font.render(f"FINAL SCORE: {score}", True, WHITE)
    screen.blit(score_text_val, (WIDTH // 2 - score_text_val.get_width() // 2, HEIGHT // 2 + 20))
    
    prompt = font.render("Press R to Try Again", True, WHITE) # Changed "Mission" to "Try Again"
    screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 + 100))

def draw_level_complete(): # SMW "Mario's House / Course Clear" style
    screen.fill(SKY_BLUE) # Or a specific course clear background
    
    # Could draw a mini "Mario gives thumbs up" or similar here
    temp_player_draw_rect = pygame.Rect(WIDTH // 2 - PLAYER_SUPER_WIDTH, HEIGHT // 2 - PLAYER_SUPER_HEIGHT - 20, PLAYER_SUPER_WIDTH*1.5, PLAYER_SUPER_HEIGHT*1.5)
    draw_player_sprite(screen, temp_player_draw_rect, player_state if player_state == S_SUPER else S_SUPER, True, True, 0, 0)


    complete_text = title_font.render("AREA CLEAR!", True, (255,255,100)) # Yellow text
    complete_shadow = title_font.render("AREA CLEAR!", True, BLACK)
    screen.blit(complete_shadow, (WIDTH // 2 - complete_text.get_width() // 2 + 3, HEIGHT // 3 + 3))
    screen.blit(complete_text, (WIDTH // 2 - complete_text.get_width() // 2, HEIGHT // 3))
    
    score_val_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_val_text, (WIDTH // 2 - score_val_text.get_width() // 2, HEIGHT // 1.8))
    
    time_bonus = max(0, level_time_limit - ((pygame.time.get_ticks() - level_start_time) // 1000)) * 50 # SMW time bonus can be significant
    bonus_text = font.render(f"Time Bonus: {time_bonus}", True, WHITE)
    screen.blit(bonus_text, (WIDTH // 2 - bonus_text.get_width() // 2, HEIGHT // 1.8 + 40))

    next_prompt_text = "ENTER for Next Sector" if current_level_index < len(levels_platforms_data) -1 else "ENTER for Title Screen"
    prompt = font.render(next_prompt_text, True, WHITE)
    screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 1.8 + 100))


current_level_index = 0
reset_level(current_level_index)
update_player_size() # Initialize player rect size based on state

running = True
while running:
    dt = clock.tick(60) / 1000.0 
    actual_dt_for_physics = min(dt, 0.033) # Cap dt to prevent physics glitches on lag spikes

    keys = pygame.key.get_pressed() # Get key state once per frame

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if state == MENU and event.key == pygame.K_RETURN:
                state = SELECT
                score = 0
                player_lives = 3
                player_state = S_SMALL
                stored_item_type = None
                update_player_size()
                current_level_index = 0 
            
            elif state == SELECT:
                if event.key == pygame.K_LEFT:
                    current_level_index = (current_level_index - 1 + len(levels_platforms_data)) % len(levels_platforms_data)
                elif event.key == pygame.K_RIGHT:
                    current_level_index = (current_level_index + 1) % len(levels_platforms_data)
                elif event.key == pygame.K_RETURN:
                    reset_level(current_level_index) # player_state persists from select screen (e.g. if returning from game over)
                    state = PLAYING
            
            elif state == PLAYING:
                if event.key == pygame.K_SPACE: # Jump
                    if on_ground:
                        player_vy = PLAYER_JUMP_INITIAL
                        on_ground = False
                        jump_hold_frames_count = PLAYER_JUMP_HOLD_FRAMES_MAX
                        create_particles(player_rect.centerx, player_rect.bottom, WHITE, 8, intensity=0.8)
                # Placeholder for using stored item (SMW uses X or A)
                # if event.key == pygame.K_x and stored_item_type:
                #    # Use item logic here
                #    stored_item_type = None 
            
            elif state == GAME_OVER and event.key == pygame.K_r:
                player_lives = 3
                score = 0
                player_state = S_SMALL
                stored_item_type = None
                update_player_size()
                current_level_index = 0
                state = SELECT 
            
            elif state == LEVEL_COMPLETE and event.key == pygame.K_RETURN:
                current_level_index += 1
                if current_level_index >= len(levels_platforms_data):
                    state = MENU # Or a "Game Beat!" screen
                else:
                    reset_level(current_level_index)
                    state = PLAYING

    # --- State Updates ---
    # Update background elements (clouds, etc.)
    for cloud_data in clouds:
        cloud_data[0] -= cloud_data[2] * (60 * actual_dt_for_physics)
        if cloud_data[0] < -cloud_data[3]:
            cloud_data[0] = WIDTH + random.randint(0,50)
            cloud_data[1] = random.randint(30, 150)
    for hill in hills: hill['rect'].x -= hill['speed_mod'] * (60 * actual_dt_for_physics) * 0.3 # Slower parallax
    for bush_data in bushes:
        bush_data['base_rect'].x -= bush_data['speed_mod'] * (60 * actual_dt_for_physics) * 0.6
        for clump in bush_data['clumps']: clump.x -= bush_data['speed_mod'] * (60 * actual_dt_for_physics) * 0.6


    # Update particles
    particles = [p for p in particles if p[6] > 0 and p[4] > 0] # Filter out dead particles
    for p_data in particles:
        p_data[0] += p_data[2] * (60 * actual_dt_for_physics)
        p_data[1] += p_data[3] * (60 * actual_dt_for_physics)
        p_data[3] += p_data[7] # Particle gravity
        p_data[4] -= 0.08 # Shrink
        p_data[6] -= 1    # Lifetime

    # Update question block hit animation
    for p_data in current_level_platforms:
        if p_data['type'] == 'question' and p_data.get('hit_timer', 0) > 0:
            p_data['hit_timer'] -=1


    if state == PLAYER_DIED_TRANSITION:
        player_vy += GRAVITY_PLAYER * (60 * actual_dt_for_physics) # Apply gravity for death fall
        player_rect.y += player_vy * (60 * actual_dt_for_physics)
        player_death_timer -=1
        if player_death_timer <= 0:
            reset_level(current_level_index) # Reset to current level state
            state = PLAYING
            # Player will be invincible from player_dies()

    elif state == PLAYING:
        # Horizontal movement with acceleration/deceleration
        target_vx = 0
        if keys[pygame.K_LEFT]:
            target_vx = -PLAYER_MAX_WALK_SPEED
            facing_right = False
        if keys[pygame.K_RIGHT]:
            target_vx = PLAYER_MAX_WALK_SPEED
            facing_right = True

        if target_vx != 0: # Accelerating
            if abs(player_vx) < abs(target_vx):
                player_vx += PLAYER_ACCEL * (1 if target_vx > 0 else -1)
                player_vx = max(-abs(target_vx), min(abs(target_vx), player_vx)) # Clamp to target_vx magnitude
            elif (player_vx > 0 and target_vx < 0) or (player_vx < 0 and target_vx > 0) : # 빠르게 방향 전환
                 player_vx += PLAYER_ACCEL * 2 * (1 if target_vx > 0 else -1) # Faster turn
        else: # Decelerating
            if abs(player_vx) > PLAYER_DECEL:
                player_vx -= PLAYER_DECEL * (1 if player_vx > 0 else -1)
            else:
                player_vx = 0
        
        player_rect.x += player_vx * (60 * actual_dt_for_physics)

        # Vertical movement (Jump & Gravity)
        if keys[pygame.K_SPACE] and jump_hold_frames_count > 0 and player_vy < 0: # Apply jump hold force if still ascending
            player_vy += PLAYER_JUMP_HOLD_FORCE # Negative force is upward
            jump_hold_frames_count -= 1
        else:
            jump_hold_frames_count = 0 # Stop applying hold force if key released or max duration reached

        player_vy += GRAVITY_PLAYER * (60 * actual_dt_for_physics)
        player_vy = min(player_vy, 15) # Terminal velocity
        player_rect.y += player_vy * (60 * actual_dt_for_physics)
        
        # Boundary check (sides of screen) - SMW usually lets you go slightly off-screen if level scrolls
        if player_rect.left < 0: player_rect.left = 0
        if player_rect.right > WIDTH: player_rect.right = WIDTH
        
        # Fall off screen / Pit death
        if player_rect.top > HEIGHT + player_rect.height : # Well below screen
             if not player_invincible : # Prevent multi-deaths if already in death anim
                player_dies()


        # Platform collision
        on_ground_this_frame = False
        player_collided_horizontally = False

        # Sort platforms by Y then X - can sometimes help with tricky corner cases but not essential here
        # current_level_platforms.sort(key=lambda p: (p['rect'].top, p['rect'].left))

        for p_data in current_level_platforms:
            platform_rect = p_data['rect']
            if player_rect.colliderect(platform_rect):
                # Vertical collision (landing or hitting head)
                if player_vy > 0 and player_rect.bottom - player_vy * (60*actual_dt_for_physics) <= platform_rect.top +1 : # Landing (+1 for precision)
                    player_rect.bottom = platform_rect.top
                    player_vy = 0
                    on_ground_this_frame = True
                    if not on_ground: create_particles(player_rect.midbottom[0], player_rect.bottom, WHITE, 3, intensity=0.3) # landing puff

                elif player_vy < 0 and player_rect.top - player_vy * (60*actual_dt_for_physics) >= platform_rect.bottom -1 : # Hitting head
                    player_rect.top = platform_rect.bottom
                    player_vy = 1.5 # Bonk head, fall back down
                    
                    if p_data['type'] == 'question' and p_data.get('active', False):
                        p_data['active'] = False
                        p_data['hit_timer'] = 20 # Frames for block bump animation
                        create_particles(platform_rect.centerx, platform_rect.top, QUESTION_BLOCK_YELLOW, 15, intensity=0.8)
                        score += 100 # For hitting block
                        
                        content = p_data.get('content', 'coin')
                        if content == 'powerup':
                            if player_state == S_SMALL:
                                spawn_item('mushroom', platform_rect)
                            else: # Player is Super, spawn coin or future powerup (e.g. Cape Feather)
                                spawn_item('coin_anim', platform_rect)
                                score += 100 # For coin from block
                        elif content == 'coin':
                            spawn_item('coin_anim', platform_rect)
                            score += 100 # For coin from block

                    elif p_data['type'] == 'brick': # Breakable bricks if super (TODO)
                         create_particles(platform_rect.centerx, player_rect.top, PLATFORM_BRICK_MORTAR, 8)
                
                # Horizontal collision (after vertical resolved as much as possible)
                # Re-check collision, as vertical adjustment might have resolved it
                if player_rect.colliderect(platform_rect): # Check again after vertical resolve
                    if player_vx > 0 and player_rect.right - player_vx * (60*actual_dt_for_physics) <= platform_rect.left +1:
                        player_rect.right = platform_rect.left
                        player_vx = 0 
                        player_collided_horizontally = True
                    elif player_vx < 0 and player_rect.left - player_vx * (60*actual_dt_for_physics) >= platform_rect.right -1:
                        player_rect.left = platform_rect.right
                        player_vx = 0
                        player_collided_horizontally = True
        on_ground = on_ground_this_frame


        # Enemy logic
        # Iterate backwards for safe removal
        for i in range(len(enemies) - 1, -1, -1):
            enemy_data = enemies[i]
            enemy_rect = enemy_data['rect']

            # Koopa shell sliding logic before general movement for shells
            if enemy_data.get('state') == 'shell_sliding':
                enemy_rect.x += enemy_data['vx'] * (60*actual_dt_for_physics)
                # Shell collision with other enemies
                for j in range(len(enemies) - 1, -1, -1):
                    if i == j: continue # Don't collide with self
                    other_enemy = enemies[j]
                    if other_enemy.get('stomped_timer',0) > 0 or other_enemy.get('state','none') in ['shell_idle', 'shell_sliding']: continue # Already hit or also a shell

                    if enemy_rect.colliderect(other_enemy['rect']):
                        create_particles(other_enemy['rect'].centerx, other_enemy['rect'].centery, (100,100,100), 15, intensity=1.5)
                        score += 200 # For shell hitting enemy
                        enemies.pop(j)
                        if j < i: i -=1 # Adjust current index if item before it was removed
                        # Shell could break or reverse here, for now it continues
                # Shell collision with walls (simple screen bounds or platforms)
                if enemy_rect.left <= 0 or enemy_rect.right >= WIDTH:
                    enemy_data['vx'] *= -1
                for p_data in current_level_platforms: # Shell hits platform wall
                    plat_rect = p_data['rect']
                    if enemy_rect.colliderect(plat_rect):
                        if (enemy_data['vx'] > 0 and enemy_rect.right > plat_rect.left and enemy_rect.left < plat_rect.left) or \
                           (enemy_data['vx'] < 0 and enemy_rect.left < plat_rect.right and enemy_rect.right > plat_rect.right):
                            enemy_data['vx'] *= -1
                            # Minor repositioning to prevent sticking
                            if enemy_data['vx'] < 0: enemy_rect.left = plat_rect.right 
                            else: enemy_rect.right = plat_rect.left
                            break 
                # Shell can fall off ledges
                enemy_data['vy'] += GRAVITY_ENEMY * (60*actual_dt_for_physics)
                enemy_rect.y += enemy_data['vy'] * (60*actual_dt_for_physics)
                # Shell platform collision (landing) - simplified
                shell_on_ground = False
                for p_data in current_level_platforms:
                    if enemy_rect.colliderect(p_data['rect']) and enemy_data['vy'] > 0 and enemy_rect.bottom - enemy_data['vy'] * (60*actual_dt_for_physics) <= p_data['rect'].top +1:
                        enemy_rect.bottom = p_data['rect'].top
                        enemy_data['vy'] = 0
                        shell_on_ground = True
                        break
                enemy_data['on_ground'] = shell_on_ground


            # Stomped Goomba or idle Koopa shell logic
            elif enemy_data.get('stomped_timer', 0) > 0 and enemy_data['type'] == 'goomba':
                enemy_data['stomped_timer'] -=1
                if enemy_data['stomped_timer'] == 0:
                    enemies.pop(i)
                continue
            elif enemy_data.get('state') == 'shell_idle': # Koopa shell is idle, apply gravity
                enemy_data['vy'] += GRAVITY_ENEMY * (60*actual_dt_for_physics)
                enemy_rect.y += enemy_data['vy'] * (60*actual_dt_for_physics)
                shell_on_ground = False
                for p_data in current_level_platforms:
                    if enemy_rect.colliderect(p_data['rect']) and enemy_data['vy'] > 0 and enemy_rect.bottom - enemy_data['vy']*(60*actual_dt_for_physics) <= p_data['rect'].top+1:
                        enemy_rect.bottom = p_data['rect'].top
                        enemy_data['vy'] = 0
                        shell_on_ground = True
                        break
                enemy_data['on_ground'] = shell_on_ground
                 # Check for player kicking the idle shell
                if player_rect.colliderect(enemy_rect) and not player_invincible:
                    enemy_data['state'] = 'shell_sliding'
                    enemy_data['vx'] = KOOPA_SHELL_SPEED * (1 if player_rect.centerx < enemy_rect.centerx else -1) # Kick away from player
                    player_vy = STOMP_BOUNCE * 0.5 # Tiny bounce for player
                    score += 50 # Points for kicking shell
                    create_particles(enemy_rect.centerx, enemy_rect.centery, KOOPA_GREEN_SHELL_HIGHLIGHT, 10)
                continue # Skip normal movement for idle shell

            # Normal enemy movement (Goomba, Walking Koopa)
            else:
                enemy_rect.x += enemy_data['vx'] * (60*actual_dt_for_physics)
                enemy_data['vy'] += GRAVITY_ENEMY * (60*actual_dt_for_physics)
                enemy_rect.y += enemy_data['vy'] * (60*actual_dt_for_physics)
            
                enemy_on_ground_this_frame = False
                for p_data in current_level_platforms:
                    platform_rect_check = p_data['rect']
                    if enemy_rect.colliderect(platform_rect_check):
                        if enemy_data['vy'] >= 0 and enemy_rect.bottom - enemy_data['vy']*(60*actual_dt_for_physics) <= platform_rect_check.top +1:
                            enemy_rect.bottom = platform_rect_check.top
                            enemy_data['vy'] = 0
                            enemy_on_ground_this_frame = True
                        elif (enemy_data['vx'] > 0 and enemy_rect.right > platform_rect_check.left and enemy_rect.left < platform_rect_check.left) or \
                             (enemy_data['vx'] < 0 and enemy_rect.left < platform_rect_check.right and enemy_rect.right > platform_rect_check.right):
                            if enemy_on_ground_this_frame or enemy_data.get('on_ground'): # Only turn if on ground and hits wall, or was on ground previously
                                enemy_data['vx'] *= -1
                                if enemy_data['type'] == 'koopa': enemy_data['original_vx'] *= -1 # sync original
                                # Push out of wall slightly
                                if enemy_data['vx'] < 0: enemy_rect.left = platform_rect_check.right +1
                                else: enemy_rect.right = platform_rect_check.left -1

                enemy_data['on_ground'] = enemy_on_ground_this_frame

                # Turn at screen edges or if about to fall off a platform (simple check)
                if enemy_rect.left <= 0 and enemy_data['vx'] < 0:
                    enemy_data['vx'] *= -1
                    if enemy_data['type'] == 'koopa': enemy_data['original_vx'] *= -1
                if enemy_rect.right >= WIDTH and enemy_data['vx'] > 0:
                    enemy_data['vx'] *= -1
                    if enemy_data['type'] == 'koopa': enemy_data['original_vx'] *= -1

                if enemy_data['on_ground'] and enemy_data['type'] != 'koopa_shell': # Koopa shells can fall
                    gap_check_x = enemy_rect.centerx + (enemy_data['vx'] * (enemy_rect.width * 0.6))
                    gap_check_y = enemy_rect.bottom + 5
                    found_ground_ahead = False
                    for pform in current_level_platforms:
                        if pform['rect'].collidepoint(gap_check_x, gap_check_y):
                            found_ground_ahead = True
                            break
                    if not found_ground_ahead:
                        enemy_data['vx'] *= -1
                        if enemy_data['type'] == 'koopa': enemy_data['original_vx'] *= -1


            # Player-Enemy collision (for active enemies)
            if player_rect.colliderect(enemy_rect) and not player_invincible:
                if enemy_data.get('stomped_timer',0) > 0: continue # Already stomped goomba
                if enemy_data.get('state', '') == 'shell_idle': continue # Handled by kick logic above
                if enemy_data.get('state', '') == 'shell_sliding' and abs(player_vy) < 2: # Hit by sliding shell NOT by stomping it
                     if player_state == S_SUPER:
                        player_state = S_SMALL
                        update_player_size()
                        player_invincible = True
                        invincible_timer = INVINCIBILITY_DURATION
                        create_particles(player_rect.centerx, player_rect.centery, MARIO_RED, 20)
                     else:
                        player_dies()
                     continue


                # Stomp Check (player falling, hits top of enemy)
                # Player must be above the enemy's center and falling, and not recently bounced
                is_stomp = player_vy > 1.0 and (player_rect.bottom - player_vy*(60*actual_dt_for_physics) <= enemy_rect.top + enemy_rect.height * 0.5)

                if is_stomp:
                    player_vy = STOMP_BOUNCE # Bounce player
                    on_ground = False # No longer on ground after bounce
                    score += 200

                    if enemy_data['type'] == 'goomba':
                        enemy_data['stomped_timer'] = 30 # Squashed Goomba animation
                        enemy_data['vx'] = 0
                        create_particles(enemy_rect.centerx, enemy_rect.top, GOOMBA_BROWN, 15, intensity=1.2)
                    elif enemy_data['type'] == 'koopa':
                        koopa_state = enemy_data.get('state', 'walking')
                        if koopa_state == 'walking':
                            enemy_data['state'] = 'shell_idle'
                            enemy_data['vx'] = 0
                            enemy_data['rect'].height = KOOPA_SHELL_HEIGHT # Adjust rect for shell form
                            enemy_data['rect'].bottom = enemy_rect.bottom # Keep feet on ground
                            create_particles(enemy_rect.centerx, enemy_rect.top, KOOPA_GREEN_SHELL, 15)
                        elif koopa_state == 'shell_sliding': # Stomping a sliding shell stops it
                            enemy_data['state'] = 'shell_idle'
                            enemy_data['vx'] = 0
                            create_particles(enemy_rect.centerx, enemy_rect.centery, WHITE, 10)

                else: # Player hit by side or from below (damage)
                    if player_state == S_SUPER:
                        player_state = S_SMALL
                        update_player_size()
                        player_invincible = True
                        invincible_timer = INVINCIBILITY_DURATION
                        player_vy = -3 # slight knockback pop
                        create_particles(player_rect.centerx, player_rect.centery, MARIO_RED, 20)
                    else: # Small Mario gets hit
                        player_dies()
                    # Break from enemy loop after taking damage or stomping to avoid multi-hits in one frame
                    break 

        if player_invincible:
            invincible_timer -= 1
            if invincible_timer <= 0:
                player_invincible = False
        
        # Item collection (Mushrooms, Coins from blocks that are now items)
        for i in range(len(items) - 1, -1, -1):
            item_data = items[i]
            item_rect = item_data['rect']

            if item_data['spawn_timer'] > 0: # Item emerging from block
                item_data['spawn_timer'] -= 1
                item_rect.y = item_data['original_y'] - (POWERUP_REVEAL_DURATION - item_data['spawn_timer']) * (MUSHROOM_HEIGHT / POWERUP_REVEAL_DURATION)
                continue # Not interactive yet

            if item_data['type'] == 'mushroom':
                # Mushroom movement
                item_rect.x += item_data['vx'] * (60*actual_dt_for_physics)
                item_data['vy'] += GRAVITY_ITEM * (60*actual_dt_for_physics)
                item_rect.y += item_data['vy'] * (60*actual_dt_for_physics)

                # Mushroom platform collision
                item_on_ground = False
                for p_data in current_level_platforms:
                    platform_rect_item = p_data['rect']
                    if item_rect.colliderect(platform_rect_item):
                        if item_data['vy'] >= 0 and item_rect.bottom - item_data['vy']*(60*actual_dt_for_physics) <= platform_rect_item.top +1:
                            item_rect.bottom = platform_rect_item.top
                            item_data['vy'] = 0
                            item_on_ground = True
                        # Mushroom horizontal collision with walls (turn around)
                        elif (item_data['vx'] > 0 and item_rect.right > platform_rect_item.left and item_rect.left < platform_rect_item.left) or \
                             (item_data['vx'] < 0 and item_rect.left < platform_rect_item.right and item_rect.right > platform_rect_item.right):
                            if item_on_ground: # Only turn if on ground and hits wall
                                 item_data['vx'] *= -1
                item_data['on_ground'] = item_on_ground
                if (item_rect.left <=0 and item_data['vx'] < 0) or (item_rect.right >= WIDTH and item_data['vx'] > 0) : item_data['vx'] *= -1


                if player_rect.colliderect(item_rect):
                    items.pop(i)
                    score += 1000 # SMW gives 1000 for powerup
                    if player_state == S_SMALL:
                        player_state = S_SUPER
                        update_player_size()
                        player_invincible = True # Short invincibility during/after transform
                        invincible_timer = INVINCIBILITY_DURATION // 2
                        # TODO: Transformation animation
                    # If already super, could store mushroom or give points
                    elif stored_item_type is None: # Store it if no item stored
                        stored_item_type = 'mushroom' # Placeholder for now
                    create_particles(item_rect.centerx, item_rect.centery, MUSHROOM_RED, 20)
            
            elif item_data['type'] == 'coin_anim':
                item_data['rect'].y += item_data['vy'] * (60*actual_dt_for_physics)
                item_data['rect'].x += item_data['vx'] * (60*actual_dt_for_physics)
                item_data['vy'] += GRAVITY_ITEM * 0.5 * (60*actual_dt_for_physics) # Coin falls back down a bit slower
                item_data['duration'] -= 1
                if item_data['duration'] <= 0:
                    items.pop(i)
                    create_particles(item_rect.centerx, item_rect.centery, QUESTION_BLOCK_YELLOW, 5, intensity=0.5)


        # Goal Tape collision (level complete)
        goal_struct_x, goal_struct_y_bottom = goal_posts_data[current_level_index]
        tape_actual_y = (goal_struct_y_bottom - GOAL_TAPE_HEIGHT_TOTAL) + goal_tape_y_offset
        goal_tape_rect_actual = pygame.Rect(goal_struct_x - GOAL_TAPE_WIDTH // 2, tape_actual_y, GOAL_TAPE_WIDTH, GOAL_TAPE_MOVING_HEIGHT)

        if player_rect.colliderect(goal_tape_rect_actual):
            hit_pos_on_tape = (player_rect.centery - tape_actual_y) / GOAL_TAPE_MOVING_HEIGHT # 0 (top) to 1 (bottom)
            base_score = 1000
            # SMW gives variable points/stars for hitting different parts of tape
            # For now, just fixed points + time
            time_bonus = max(0, level_time_limit - ((pygame.time.get_ticks() - level_start_time) // 1000)) * 50
            score += base_score + time_bonus
            state = LEVEL_COMPLETE
            create_particles(player_rect.centerx, player_rect.top, GOAL_TAPE_COLOR, 40, intensity=2.5)

        # Animate Goal Tape
        goal_tape_y_offset += goal_tape_direction * 0.8 * (60 * actual_dt_for_physics) # Slower tape movement
        if goal_tape_y_offset > GOAL_TAPE_HEIGHT_TOTAL - GOAL_TAPE_MOVING_HEIGHT:
            goal_tape_y_offset = GOAL_TAPE_HEIGHT_TOTAL - GOAL_TAPE_MOVING_HEIGHT
            goal_tape_direction = -1
        elif goal_tape_y_offset < 0:
            goal_tape_y_offset = 0
            goal_tape_direction = 1


        # Time check
        elapsed_time_seconds = (pygame.time.get_ticks() - level_start_time) // 1000
        if elapsed_time_seconds >= level_time_limit:
            if not player_invincible : player_dies() # Lose a life if time runs out


    # --- Drawing ---
    if state == MENU:
        draw_menu()
    elif state == SELECT:
        draw_select()
    elif state == PLAYING or state == PLAYER_DIED_TRANSITION: # Draw game for both, PLAYER_DIED_TRANSITION just has player falling
        draw_game()
    elif state == GAME_OVER:
        draw_game_over()
    elif state == LEVEL_COMPLETE:
        draw_level_complete()

    pygame.display.flip()

pygame.quit()
sys.exit()

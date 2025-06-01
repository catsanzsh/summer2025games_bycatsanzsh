import pygame
import sys
import random
import numpy as np # For sound generation

# Initialize Pygame & Mixer
pygame.init()
SOUND_ENABLED = False
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512) # Mono, 16-bit
    pygame.mixer.set_num_channels(16) # Increase if many sounds overlap
    SOUND_ENABLED = True
    print("Pygame Mixer initialized successfully.")
except pygame.error as e:
    print(f"Warning: Pygame Mixer could not be initialized. Sound will be disabled. Error: {e}")
    SOUND_ENABLED = False


WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario World X - Anikiti Hack Style!") # Updated Caption
clock = pygame.time.Clock()

# --- Sound Generation ---
SAMPLE_RATE = 44100
MAX_AMP_INT16 = 32767

def generate_waveform(duration_s, frequency, shape='sine', amplitude=0.5, phase_offset=0.0, duty_cycle=0.5):
    num_samples = int(duration_s * SAMPLE_RATE)
    if num_samples <= 0: return np.array([], dtype=float)
    t = np.linspace(0, duration_s, num_samples, endpoint=False)
    
    if shape == 'sine':
        wave = np.sin(2 * np.pi * frequency * t + phase_offset)
    elif shape == 'square':
        # duty cycle for square wave:
        # wave = amplitude * (2 * (np.mod(t * frequency, 1) < duty_cycle) - 1) # more control
        wave = np.sign(np.sin(2 * np.pi * frequency * t + phase_offset)) # simpler 50%
    elif shape == 'sawtooth': 
        wave = 2 * (t * frequency - np.floor(0.5 + t * frequency))
    elif shape == 'noise':
        wave = np.random.uniform(-1, 1, num_samples)
    elif shape == 'triangle':
        wave = 2 * np.abs(2 * (t * frequency - np.floor(t * frequency + 0.5))) - 1
    else: 
        wave = np.sin(2 * np.pi * frequency * t + phase_offset)
        
    return wave * amplitude

def generate_sweep_waveform(duration_s, freq_start, freq_end, shape='sine', amplitude=0.5):
    num_samples = int(duration_s * SAMPLE_RATE)
    if num_samples <= 0: return np.array([], dtype=float)
    t = np.linspace(0, duration_s, num_samples, endpoint=False)
    
    phi_t = 2 * np.pi * (freq_start * t + (freq_end - freq_start) * (t**2 / (2 * duration_s)))
    
    if shape == 'sine':
        wave = np.sin(phi_t)
    elif shape == 'square':
        wave = np.sign(np.sin(phi_t))
    elif shape == 'sawtooth':
        # True swept sawtooth is more complex with phase resets, approximate with sine for now
        # Or use: (freq_start * t + (freq_end - freq_start) * (t**2 / (2 * duration_s)))
        # This term is the integral of f(t) for phase.
        # Sawtooth: wave = 2 * ( (phi_t / (2*np.pi)) - np.floor(0.5 + (phi_t / (2*np.pi))) )
        # This is experimental for swept sawtooth, might sound weird
        current_freq_t = freq_start + (freq_end - freq_start) * (t / duration_s)
        phase_saw = np.cumsum(2 * np.pi * current_freq_t / SAMPLE_RATE) # more stable phase
        wave = 2 * ( (phase_saw / (2*np.pi)) % 1.0) - 1.0 # Corrected sawtooth generation
        wave = wave - np.mean(wave) # DC offset correction might be needed
    else:
        wave = np.sin(phi_t)
        
    return wave * amplitude

def apply_envelope(waveform, attack_s, decay_s, sustain_level=0.0, release_s=0.0):
    total_samples = len(waveform)
    if total_samples == 0: return waveform

    attack_samples = int(attack_s * SAMPLE_RATE)
    decay_samples = int(decay_s * SAMPLE_RATE)
    release_samples = int(release_s * SAMPLE_RATE)

    envelope = np.ones(total_samples)
    
    # Attack phase
    current_sample = 0
    if attack_samples > 0:
        limit = min(attack_samples, total_samples)
        envelope[current_sample:limit] = np.linspace(0, 1, limit - current_sample)
        current_sample = limit

    # Decay phase
    if decay_samples > 0 and current_sample < total_samples:
        limit = min(current_sample + decay_samples, total_samples)
        envelope[current_sample:limit] = np.linspace(1, sustain_level, limit - current_sample)
        current_sample = limit

    # Sustain phase (everything between decay and start of release)
    sustain_end_sample = total_samples - release_samples
    if current_sample < sustain_end_sample:
        envelope[current_sample:sustain_end_sample] = sustain_level
        current_sample = sustain_end_sample
    
    # Release phase
    if release_samples > 0 and current_sample < total_samples:
        limit = min(current_sample + release_samples, total_samples) # Should be just total_samples
        # Determine amplitude at start of release for smooth transition
        amp_at_release_start = sustain_level
        if current_sample > 0 and current_sample <= total_samples: # if release starts after decay/sustain
             amp_at_release_start = envelope[current_sample-1]

        envelope[current_sample:limit] = np.linspace(amp_at_release_start, 0, limit-current_sample)

    return waveform * envelope


def create_sound_from_waveform(waveform_float):
    if not SOUND_ENABLED or waveform_float is None or len(waveform_float) == 0:
        return None
    waveform_float = np.clip(waveform_float, -1.0, 1.0) # Ensure clipping
    waveform_int16 = (waveform_float * MAX_AMP_INT16).astype(np.int16)
    try:
        sound = pygame.sndarray.make_sound(waveform_int16)
        return sound
    except Exception as e:
        print(f"Error creating sound object: {e}")
        return None

sfx = {} 

if SOUND_ENABLED:
    # Jump Sound
    jump_wave = generate_sweep_waveform(duration_s=0.15, freq_start=500, freq_end=900, shape='sine', amplitude=0.25)
    jump_wave = apply_envelope(jump_wave, attack_s=0.01, decay_s=0.14, sustain_level=0.0)
    sfx['jump'] = create_sound_from_waveform(jump_wave)

    # Coin Sound
    coin_wave = generate_waveform(duration_s=0.1, frequency=1900, shape='triangle', amplitude=0.25) 
    coin_wave = apply_envelope(coin_wave, attack_s=0.005, decay_s=0.095, sustain_level=0.0)
    sfx['coin'] = create_sound_from_waveform(coin_wave)
    sfx['coin_block'] = sfx['coin'] 

    # Stomp Goomba
    stomp_wave = generate_waveform(duration_s=0.18, frequency=130, shape='square', amplitude=0.35)
    stomp_noise = generate_waveform(duration_s=0.18, frequency=1, shape='noise', amplitude=0.15) 
    stomp_combined = stomp_wave * 0.6 + stomp_noise * 0.4
    stomp_combined = apply_envelope(stomp_combined, attack_s=0.01, decay_s=0.17, sustain_level=0.0)
    sfx['stomp_goomba'] = create_sound_from_waveform(stomp_combined)

    # Stomp Koopa (to shell)
    stomp_koopa_wave = generate_waveform(duration_s=0.15, frequency=160, shape='sawtooth', amplitude=0.3)
    stomp_koopa_wave = apply_envelope(stomp_koopa_wave, attack_s=0.005, decay_s=0.145)
    sfx['stomp_koopa_to_shell'] = create_sound_from_waveform(stomp_koopa_wave)
    sfx['stomp_koopa_shell_stop'] = create_sound_from_waveform(generate_waveform(0.1, 200, 'square', 0.3))


    # Powerup Appears (from block)
    powerup_appear_wave = generate_sweep_waveform(duration_s=0.35, freq_start=300, freq_end=1200, shape='sine', amplitude=0.25)
    powerup_appear_wave = apply_envelope(powerup_appear_wave, attack_s=0.02, decay_s=0.20, sustain_level=0.2, release_s=0.13)
    sfx['powerup_appears'] = create_sound_from_waveform(powerup_appear_wave)

    # Powerup Collect (Mushroom)
    note1_pc = generate_waveform(0.07, 523, 'triangle', 0.25); note1_pc = apply_envelope(note1_pc, 0.005, 0.065) # C5
    note2_pc = generate_waveform(0.07, 659, 'triangle', 0.25); note2_pc = apply_envelope(note2_pc, 0.005, 0.065) # E5
    note3_pc = generate_waveform(0.10, 784, 'triangle', 0.25); note3_pc = apply_envelope(note3_pc, 0.005, 0.095) # G5
    pause_pc = np.zeros(int(0.015 * SAMPLE_RATE))
    powerup_collect_wave = np.concatenate((note1_pc, pause_pc, note2_pc, pause_pc, note3_pc))
    sfx['powerup_collect'] = create_sound_from_waveform(powerup_collect_wave)
    
    # Player Hit (Shrink from Super to Small)
    player_hit_wave = generate_sweep_waveform(duration_s=0.25, freq_start=600, freq_end=250, shape='sawtooth', amplitude=0.35)
    player_hit_wave = apply_envelope(player_hit_wave, attack_s=0.01, decay_s=0.24)
    sfx['player_hit'] = create_sound_from_waveform(player_hit_wave)

    # Player Death
    death_hit_pd = generate_waveform(0.12, 350, 'square', 0.4); death_hit_pd=apply_envelope(death_hit_pd,0.005,0.115)
    death_fall_pd = generate_sweep_waveform(duration_s=0.7, freq_start=250, freq_end=40, shape='sawtooth', amplitude=0.4)
    death_fall_pd = apply_envelope(death_fall_pd, attack_s=0.0, decay_s=0.7)
    player_death_wave = np.concatenate((death_hit_pd, death_fall_pd))
    sfx['player_death'] = create_sound_from_waveform(player_death_wave)

    # Block Hit / Bump
    block_hit_wave = generate_waveform(duration_s=0.09, frequency=220, shape='square', amplitude=0.3)
    block_hit_wave = apply_envelope(block_hit_wave, attack_s=0.01, decay_s=0.08)
    sfx['block_hit'] = create_sound_from_waveform(block_hit_wave) # For inactive blocks
    sfx['block_bump'] = create_sound_from_waveform(generate_waveform(0.12, 250, 'sine', 0.32)) # For active question block bump

    # Kick Shell
    kick_shell_wave = generate_waveform(duration_s=0.06, frequency=900, shape='square', amplitude=0.35) 
    kick_shell_noise = generate_waveform(duration_s=0.06, frequency=1, shape='noise', amplitude=0.1)
    kick_shell_combined = kick_shell_wave * 0.7 + kick_shell_noise * 0.3
    kick_shell_combined = apply_envelope(kick_shell_combined, attack_s=0.002, decay_s=0.058)
    sfx['kick_shell'] = create_sound_from_waveform(kick_shell_combined)
    
    # Menu Select/Navigate
    sfx['menu_navigate'] = create_sound_from_waveform(apply_envelope(generate_waveform(0.05, 500, 'sine', 0.2),0.005,0.045))
    sfx['menu_select'] = create_sound_from_waveform(apply_envelope(generate_waveform(0.07, 750, 'sine', 0.25),0.005,0.065))


    # Goal Tape / Level Complete
    lc_n1 = generate_waveform(0.10, 523*1.2, 'triangle', 0.30); lc_n1 = apply_envelope(lc_n1, 0.01, 0.09) 
    lc_n2 = generate_waveform(0.10, 659*1.2, 'triangle', 0.30); lc_n2 = apply_envelope(lc_n2, 0.01, 0.09) 
    lc_n3 = generate_waveform(0.15, 784*1.2, 'triangle', 0.30); lc_n3 = apply_envelope(lc_n3, 0.01, 0.14) 
    lc_n4 = generate_waveform(0.20, 1046*1.2, 'triangle', 0.30); lc_n4 = apply_envelope(lc_n4, 0.01, 0.19) # Higher C
    lc_pause = np.zeros(int(0.02 * SAMPLE_RATE))
    level_complete_wave = np.concatenate((lc_n1, lc_pause, lc_n2, lc_pause, lc_n3, lc_pause,lc_n4))
    sfx['level_complete'] = create_sound_from_waveform(level_complete_wave)

    # Generic "Break Brick" sound
    break_brick_noise = generate_waveform(duration_s=0.20, frequency=1, shape='noise', amplitude=0.4) 
    break_brick_env = np.concatenate([
        np.linspace(0,1,int(0.01*SAMPLE_RATE)), 
        np.exp(-np.linspace(0,4,int(0.19*SAMPLE_RATE))) # Faster, sharper exponential decay
    ])
    if len(break_brick_env) > len(break_brick_noise): break_brick_env = break_brick_env[:len(break_brick_noise)]
    elif len(break_brick_noise) > len(break_brick_env): break_brick_noise = break_brick_noise[:len(break_brick_env)]
    break_brick_wave = break_brick_noise * break_brick_env if len(break_brick_noise)>0 else np.array([])
    sfx['brick_break'] = create_sound_from_waveform(break_brick_wave)


def play_sfx(sound_name):
    if SOUND_ENABLED and sound_name in sfx and sfx[sound_name]:
        # Find a free channel or play on any
        channel = pygame.mixer.find_channel(True) # True means force find a channel
        if channel:
            channel.play(sfx[sound_name])
        # else: sfx[sound_name].play() # Fallback if find_channel returns None (shouldn't with force=True)

# --- SMW-inspired Constants & Player Physics ---
PLAYER_ACCEL = 0.28      
# ... (rest of your existing constants, colors, etc. up to game state variables)

# --- SMW-inspired Constants & Player Physics ---
# PLAYER_ACCEL = 0.28           # How quickly Mario speeds up # Duplicated line from above, remove
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
SKY_BLUE = (90, 140, 255) 
MARIO_RED = (255, 0, 0) 
MARIO_BLUE_OVERALLS = (0, 80, 255) 
MARIO_SKIN = (252, 220, 160) 
MARIO_HAIR_BROWN = (101, 67, 33)
MARIO_SHOE_BROWN = (130, 60, 0) 

GROUND_GREEN = (0, 160, 0) 
GROUND_BROWN = (120, 80, 0) 
PLATFORM_BRICK_RED = (200, 76, 12) 
PLATFORM_BRICK_MORTAR = (150, 150, 150)
QUESTION_BLOCK_YELLOW = (255, 200, 0) 
QUESTION_BLOCK_SHADOW = (180, 130, 0)
USED_BLOCK_BROWN = (160, 110, 70) 

GOOMBA_BROWN = (200, 120, 50) 
GOOMBA_FEET = (150, 90, 30)
GOOMBA_EYE_WHITE = (252, 252, 252)

KOOPA_GREEN_BODY = (0, 180, 0)
KOOPA_GREEN_SHELL = (0, 140, 0)
KOOPA_GREEN_SHELL_HIGHLIGHT = (50, 200, 50)
KOOPA_FEET_HANDS = (255, 224, 100) 

MUSHROOM_RED = (255, 0, 0)
MUSHROOM_STEM = (252, 220, 160)
MUSHROOM_SPOTS = WHITE

GOAL_TAPE_COLOR = (220,220,0) 
GOAL_POST_COLOR = (100,100,100) 

# Game states
MENU = "menu"
SELECT = "select"
PLAYING = "playing"
GAME_OVER = "game_over"
LEVEL_COMPLETE = "level_complete"
PLAYER_DIED_TRANSITION = "player_died_transition" 
state = MENU

# Fonts
title_font = pygame.font.Font(None, 80) 
font = pygame.font.Font(None, 36) 
small_font = pygame.font.Font(None, 28)

# --- Level Data ---
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
    [
        (0, HEIGHT - 40, WIDTH, 40, 'ground'),
        (100, HEIGHT - 100, 40, 40, 'question', {'content': 'powerup', 'active': True}),
        (200, HEIGHT - 160, 80, 20, 'brick'),
        (350, HEIGHT - 100, 40, 40, 'question', {'content': 'coin', 'active': True}),
        (450, HEIGHT - 220, 80, 20, 'brick'),
        (600, HEIGHT - 100, 40, 40, 'question', {'content': 'coin', 'active': True}),
    ],
     [ 
        (0, HEIGHT - 40, 100, 40, 'ground'),
        (50, HEIGHT - 180, 40, 20, 'brick'), (150, HEIGHT - 280, 40, 20, 'brick'),
        (250, HEIGHT - 380, 40, 40, 'question', {'content': 'powerup', 'active': True}),
        (400, HEIGHT - 150, 100, 20, 'ground'), (425, HEIGHT - 190, 40, 40, 'question', {'content': 'coin', 'active': True}),
        (550, HEIGHT - 250, 60, 20, 'brick'), (650, HEIGHT - 350, 60, 20, 'brick'),
    ],
    [ 
        (0, HEIGHT - 40, WIDTH, 40, 'ground'),
        (100, HEIGHT - 100, 50, 20, 'brick'), (200, HEIGHT - 100, 50, 20, 'brick'),
        (300, HEIGHT - 140, 40, 40, 'question', {'content': 'powerup', 'active': True}),
        (400, HEIGHT - 160, 50, 20, 'brick'), (500, HEIGHT - 160, 50, 20, 'brick'),
        (600, HEIGHT - 220, 40, 40, 'question', {'content': 'coin', 'active': True}),
    ],
]
current_level_platforms = []

GOAL_TAPE_WIDTH = 10
GOAL_TAPE_HEIGHT_TOTAL = 150 
GOAL_TAPE_MOVING_HEIGHT = 30 
goal_posts_data = [ 
    (720, HEIGHT - 40), (720, HEIGHT - 40), (720, HEIGHT - 40),
    (720, HEIGHT - 40), (720, HEIGHT - 40)
]
goal_tape_y_offset = 0 
goal_tape_direction = 1

items = [] 
MUSHROOM_WIDTH, MUSHROOM_HEIGHT = 24, 24
MUSHROOM_SPEED = 1.2
COIN_ANIM_DURATION = 30 
COIN_ANIM_SPEED_Y = -5

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
player_death_timer = 0 

enemies = []
GOOMBA_WIDTH, GOOMBA_HEIGHT = 30, 30
KOOPA_WIDTH, KOOPA_HEIGHT = 30, 42 
KOOPA_SHELL_HEIGHT = 24

level_start_time = 0
level_time_limit = 150 

coin_animation_frames = []
for i in range(8):
    offset = (i / 8.0) * (20 / 2.0)
    coin_animation_frames.append(offset)
coin_frame_index = 0

particles = []

clouds = []
for _ in range(6): 
    x = random.randint(0, WIDTH)
    y = random.randint(30, 150)
    speed = random.uniform(0.1, 0.3) 
    size_w = random.randint(60, 120)
    size_h = random.randint(20, 40)
    clouds.append([x, y, speed, size_w, size_h])

hills = [] 
for i in range(3):
    h_w = random.randint(150, 300)
    h_h = random.randint(60, 120)
    h_x = random.randint(-50, WIDTH + 50)
    h_y = HEIGHT - 40 - h_h + random.randint(0,20) 
    hills.append({'rect': pygame.Rect(h_x, h_y, h_w, h_h),
                  'color1': (random.randint(0,80), random.randint(140,200), random.randint(0,80)), 
                  'color2': (random.randint(40,120), random.randint(180,240), random.randint(40,120)), 
                  'speed_mod': random.uniform(0.2, 0.5)})

bushes = [] 
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


item_box_rect = pygame.Rect(WIDTH // 2 - 22, 8, 44, 44) 
stored_item_type = None 

def update_player_size():
    global current_player_width, current_player_height
    old_bottom = player_rect.bottom
    old_centerx = player_rect.centerx
    if player_state == S_SUPER:
        current_player_width = PLAYER_SUPER_WIDTH
        current_player_height = PLAYER_SUPER_HEIGHT
    else: 
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
    global items, score # Added score here for coin spawn
    item_rect = pygame.Rect(pos_rect.centerx - MUSHROOM_WIDTH // 2, pos_rect.top - MUSHROOM_HEIGHT, MUSHROOM_WIDTH, MUSHROOM_HEIGHT)
    new_item = {'rect': item_rect, 'type': item_type, 'vx': MUSHROOM_SPEED, 'vy': 0, 'on_ground': False, 'spawn_timer': POWERUP_REVEAL_DURATION, 'original_y': item_rect.y}
    
    if item_type == 'mushroom':
        play_sfx('powerup_appears')
        items.append(new_item)
    elif item_type == 'coin_anim':
        play_sfx('coin_block')
        score += 100 # Score for coin from block
        new_item['vy'] = COIN_ANIM_SPEED_Y
        new_item['vx'] = random.uniform(-0.5, 0.5)
        new_item['duration'] = COIN_ANIM_DURATION
        new_item['spawn_timer'] = 0 # Coins appear instantly, no reveal animation
        items.append(new_item)


def reset_level(index):
    global current_level_platforms, enemies, player_rect, player_vy, player_vx
    global level_start_time, items, on_ground # player_state persists
    global goal_tape_y_offset, goal_tape_direction

    current_level_platforms = []
    for p_data_tuple in levels_platforms_data[index]:
        p_data = list(p_data_tuple) 
        platform_rect = pygame.Rect(p_data[0], p_data[1], p_data[2], p_data[3])
        platform_type = p_data[4]
        properties = p_data[5] if len(p_data) > 5 else {}
        if platform_type == 'question':
            properties['original_y'] = platform_rect.y
            properties['hit_timer'] = 0
        current_level_platforms.append({'rect': platform_rect, 'type': platform_type, 'original_y_ref': platform_rect.y, **properties})

    update_player_size() 
    player_rect.bottomleft = (50, HEIGHT - 40) 
    player_vy = 0
    player_vx = 0
    on_ground = True 

    items = []
    enemies = []
    base_y = HEIGHT - GOOMBA_HEIGHT - 40

    if index == 0:
        enemies.append({'rect': pygame.Rect(300, base_y, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': -ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
        enemies.append({'rect': pygame.Rect(500, HEIGHT - 220 - GOOMBA_HEIGHT, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
    elif index == 1:
        enemies.append({'rect': pygame.Rect(450, base_y - KOOPA_HEIGHT + GOOMBA_HEIGHT, KOOPA_WIDTH, KOOPA_HEIGHT), 'vx': -ENEMY_BASE_SPEED, 'vy': 0, 'type': 'koopa', 'state': 'walking', 'on_ground': False, 'stomped_timer': 0, 'original_vx': -ENEMY_BASE_SPEED})
        enemies.append({'rect': pygame.Rect(350, HEIGHT - 180 - GOOMBA_HEIGHT, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': -ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
    elif index == 2: 
        enemies.append({'rect': pygame.Rect(250, base_y - KOOPA_HEIGHT + GOOMBA_HEIGHT, KOOPA_WIDTH, KOOPA_HEIGHT), 'vx': -ENEMY_BASE_SPEED, 'vy': 0, 'type': 'koopa', 'state': 'walking', 'on_ground': False, 'stomped_timer': 0, 'original_vx': -ENEMY_BASE_SPEED})
        enemies.append({'rect': pygame.Rect(400, base_y, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
        enemies.append({'rect': pygame.Rect(550, base_y - KOOPA_HEIGHT + GOOMBA_HEIGHT, KOOPA_WIDTH, KOOPA_HEIGHT), 'vx': ENEMY_BASE_SPEED, 'vy': 0, 'type': 'koopa', 'state': 'walking', 'on_ground': False, 'stomped_timer': 0, 'original_vx': ENEMY_BASE_SPEED})
    elif index == 3: 
        enemies.append({'rect': pygame.Rect(80, HEIGHT - 180 - GOOMBA_HEIGHT, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
        enemies.append({'rect': pygame.Rect(450, HEIGHT - 150 - GOOMBA_HEIGHT, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': -ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
        enemies.append({'rect': pygame.Rect(600, HEIGHT - 250 - KOOPA_HEIGHT + GOOMBA_HEIGHT, KOOPA_WIDTH, KOOPA_HEIGHT), 'vx': ENEMY_BASE_SPEED, 'vy': 0, 'type': 'koopa', 'state':'walking', 'on_ground': False, 'stomped_timer': 0, 'original_vx': ENEMY_BASE_SPEED})
    elif index == 4: 
        for i in range(3):
            enemies.append({'rect': pygame.Rect(150 + i*150, base_y, GOOMBA_WIDTH, GOOMBA_HEIGHT), 'vx': -ENEMY_BASE_SPEED if i%2==0 else ENEMY_BASE_SPEED, 'vy': 0, 'type': 'goomba', 'on_ground': False, 'stomped_timer': 0})
        enemies.append({'rect': pygame.Rect(250, base_y - KOOPA_HEIGHT + GOOMBA_HEIGHT, KOOPA_WIDTH, KOOPA_HEIGHT), 'vx': -ENEMY_BASE_SPEED, 'vy': 0, 'type': 'koopa', 'state':'walking', 'on_ground': False, 'stomped_timer': 0, 'original_vx': -ENEMY_BASE_SPEED})
        enemies.append({'rect': pygame.Rect(500, base_y - KOOPA_HEIGHT + GOOMBA_HEIGHT, KOOPA_WIDTH, KOOPA_HEIGHT), 'vx': ENEMY_BASE_SPEED, 'vy': 0, 'type': 'koopa', 'state':'walking', 'on_ground': False, 'stomped_timer': 0, 'original_vx': ENEMY_BASE_SPEED})


    level_start_time = pygame.time.get_ticks()
    goal_tape_y_offset = 0
    goal_tape_direction = 1

def player_dies():
    global player_lives, player_state, state, player_invincible, invincible_timer, player_death_timer, player_vx, player_vy
    play_sfx('player_death')
    player_lives -= 1
    create_particles(player_rect.centerx, player_rect.centery, MARIO_RED, 40, intensity=2.5)
    player_state = S_SMALL 
    update_player_size()
    player_invincible = True 
    invincible_timer = INVINCIBILITY_DURATION // 2 

    if player_lives <= 0:
        state = GAME_OVER
    else:
        state = PLAYER_DIED_TRANSITION
        player_death_timer = 90 
        player_vx = 0
        player_vy = -10 
        
# --- Drawing Functions (draw_menu, draw_select, draw_player_sprite, etc.) ---
# These are large, so I'll put "..." and assume they are the same as before
# unless a sound needs to be triggered from a draw function (unlikely for SFX).
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
    title_shadow = title_font.render("Super Mario World X", True, (50,50,150)) 
    screen.blit(title_shadow, (WIDTH // 2 - title_text.get_width() // 2 + 4, HEIGHT // 3 - 50 + 4))
    screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 3 - 50))
    
    temp_player_draw_rect = pygame.Rect(WIDTH // 2 - PLAYER_SUPER_WIDTH // 2, HEIGHT - 40 - PLAYER_SUPER_HEIGHT - 20, PLAYER_SUPER_WIDTH, PLAYER_SUPER_HEIGHT)
    draw_player_sprite(screen, temp_player_draw_rect, S_SUPER, True, True, 0, 0) 

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

    title = title_font.render("Select Sector", True, WHITE) 
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
    
    num_levels = len(levels_platforms_data)
    box_size = 70 
    padding = 15
    cols = 4 
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

    is_walking = p_on_ground and abs(p_vx) > 0.5
    walk_frame = (pygame.time.get_ticks() // 120) % 2 

    in_air_pose = not p_on_ground
    x, y, w, h = rect.x, rect.y, rect.width, rect.height

    if current_state == S_SMALL:
        head_radius = w * 0.45
        head_cx = x + w / 2
        head_cy = y + head_radius * 1.1
        pygame.draw.rect(surface, cap_shirt_color, (head_cx - head_radius * 0.9, head_cy - head_radius * 1.3, head_radius * 1.8, head_radius * 0.8)) 
        brim_x = head_cx + (head_radius * 0.3 if p_facing_right else -head_radius * 1.1)
        pygame.draw.rect(surface, cap_shirt_color, (brim_x, head_cy - head_radius * 0.7, head_radius * 0.8, head_radius * 0.4)) 
        pygame.draw.circle(surface, skin_color, (int(head_cx), int(head_cy)), int(head_radius)) 
        eye_off_x = head_radius * 0.3 * (1 if p_facing_right else -1)
        pygame.draw.circle(surface, BLACK, (int(head_cx + eye_off_x), int(head_cy - head_radius * 0.1)), 2)
        body_h = h * 0.45
        body_y = head_cy + head_radius * 0.7
        pygame.draw.rect(surface, cap_shirt_color, (x + w * 0.1, body_y, w * 0.8, body_h))
        overalls_h = h * 0.2
        pygame.draw.rect(surface, overalls_color, (x + w * 0.15, body_y + body_h * 0.7, w * 0.7, overalls_h))
        shoe_w = w * 0.4
        shoe_h = h * 0.25
        shoe_y_base = y + h - shoe_h
        if p_facing_right:
            pygame.draw.ellipse(surface, shoe_color, (x + w * 0.5, shoe_y_base, shoe_w, shoe_h))
            if is_walking and walk_frame == 1: pygame.draw.ellipse(surface, shoe_color, (x + w * 0.1, shoe_y_base + shoe_h*0.2, shoe_w*0.8, shoe_h*0.8)) 
        else:
            pygame.draw.ellipse(surface, shoe_color, (x + w * 0.1, shoe_y_base, shoe_w, shoe_h))
            if is_walking and walk_frame == 1: pygame.draw.ellipse(surface, shoe_color, (x + w * 0.5, shoe_y_base + shoe_h*0.2, shoe_w*0.8, shoe_h*0.8))
    elif current_state == S_SUPER:
        head_radius = w * 0.30
        head_cx = x + w / 2
        head_cy = y + head_radius * 1.2
        pygame.draw.rect(surface, cap_shirt_color, (head_cx - head_radius * 1.0, head_cy - head_radius * 1.4, head_radius * 2.0, head_radius * 1.0))
        brim_x = head_cx + (head_radius * 0.5 if p_facing_right else -head_radius * 1.3)
        pygame.draw.rect(surface, cap_shirt_color, (brim_x, head_cy - head_radius * 0.6, head_radius * 0.8, head_radius * 0.5))
        pygame.draw.circle(surface, skin_color, (int(head_cx), int(head_cy)), int(head_radius)) 
        eye_off_x = head_radius * 0.4 * (1 if p_facing_right else -1)
        pygame.draw.circle(surface, BLACK, (int(head_cx + eye_off_x), int(head_cy - head_radius * 0.1)), 3)
        torso_top_y = head_cy + head_radius * 0.8
        shirt_sleeve_w = w * 0.3
        shirt_sleeve_h = h * 0.20
        overalls_main_w = w * 0.7
        overalls_main_h = h * 0.45
        overalls_main_x = x + (w - overalls_main_w) / 2
        overalls_main_y = torso_top_y + shirt_sleeve_h * 0.3
        pygame.draw.rect(surface, cap_shirt_color, (overalls_main_x - shirt_sleeve_w*0.1, torso_top_y, shirt_sleeve_w, shirt_sleeve_h)) 
        pygame.draw.rect(surface, cap_shirt_color, (overalls_main_x + overalls_main_w - shirt_sleeve_w*0.9, torso_top_y, shirt_sleeve_w, shirt_sleeve_h)) 
        pygame.draw.rect(surface, cap_shirt_color, (overalls_main_x, overalls_main_y - h*0.05, overalls_main_w, h*0.1)) 
        pygame.draw.rect(surface, overalls_color, (overalls_main_x, overalls_main_y, overalls_main_w, overalls_main_h))
        strap_w = w * 0.15
        pygame.draw.rect(surface, overalls_color, (head_cx - strap_w*1.5, torso_top_y, strap_w, h * 0.2))
        pygame.draw.rect(surface, overalls_color, (head_cx + strap_w*0.5, torso_top_y, strap_w, h * 0.2))
        leg_w = overalls_main_w * 0.45
        leg_h = h * 0.25
        leg_y = overalls_main_y + overalls_main_h - leg_h * 0.3
        pygame.draw.rect(surface, overalls_color, (overalls_main_x, leg_y, leg_w, leg_h))
        pygame.draw.rect(surface, overalls_color, (overalls_main_x + overalls_main_w - leg_w, leg_y, leg_w, leg_h))
        shoe_w = w * 0.4
        shoe_h = h * 0.18
        shoe_y_base = y + h - shoe_h
        if in_air_pose: 
            shoe_y_offset = -shoe_h * 0.2
            if p_facing_right:
                 pygame.draw.ellipse(surface, shoe_color, (x + w * 0.45, shoe_y_base + shoe_y_offset, shoe_w, shoe_h))
            else:
                 pygame.draw.ellipse(surface, shoe_color, (x + w * 0.15, shoe_y_base + shoe_y_offset, shoe_w, shoe_h))
        elif is_walking:
            if p_facing_right:
                pygame.draw.ellipse(surface, shoe_color, (x + w * (0.55 if walk_frame == 0 else 0.45) , shoe_y_base, shoe_w, shoe_h)) 
                pygame.draw.ellipse(surface, shoe_color, (x + w * 0.1, shoe_y_base + shoe_h*0.1, shoe_w*0.9, shoe_h*0.9)) 
            else:
                pygame.draw.ellipse(surface, shoe_color, (x + w * (0.05 if walk_frame == 0 else 0.15) , shoe_y_base, shoe_w, shoe_h)) 
                pygame.draw.ellipse(surface, shoe_color, (x + w * 0.5, shoe_y_base + shoe_h*0.1, shoe_w*0.9, shoe_h*0.9)) 
        else: 
             if p_facing_right: pygame.draw.ellipse(surface, shoe_color, (x + w * 0.5, shoe_y_base, shoe_w, shoe_h))
             else: pygame.draw.ellipse(surface, shoe_color, (x + w * 0.1, shoe_y_base, shoe_w, shoe_h))

    if player_invincible and (invincible_timer // 5) % 2 == 0: 
        flash_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        flash_surface.fill((255, 255, 255, 100)) 
        surface.blit(flash_surface, rect.topleft)

def draw_goomba(surface, enemy_data):
    rect = enemy_data['rect']
    walk_anim_offset = 0
    if enemy_data.get('vx', 0) != 0 : 
        walk_anim_offset = int((pygame.time.get_ticks() // 200) % 2) * -2

    if enemy_data.get('stomped_timer', 0) > 0: 
        squashed_height = rect.height // 2.5
        pygame.draw.ellipse(surface, GOOMBA_BROWN, (rect.x, rect.bottom - squashed_height, rect.width, squashed_height))
        return

    body_rect = pygame.Rect(rect.x, rect.y + walk_anim_offset, rect.width, rect.height * 0.8)
    pygame.draw.ellipse(surface, GOOMBA_BROWN, body_rect)
    foot_width = rect.width // 2.5
    foot_height = rect.height // 3
    foot_y = body_rect.bottom - foot_height * 0.6
    pygame.draw.ellipse(surface, GOOMBA_FEET, (rect.left + rect.width * 0.05, foot_y, foot_width, foot_height))
    pygame.draw.ellipse(surface, GOOMBA_FEET, (rect.right - rect.width * 0.05 - foot_width, foot_y, foot_width, foot_height))
    eye_radius = rect.width // 5
    eye_y = body_rect.centery - rect.height * 0.05
    left_eye_x = body_rect.centerx - rect.width // 5
    right_eye_x = body_rect.centerx + rect.width // 5
    pygame.draw.ellipse(surface, GOOMBA_EYE_WHITE, (left_eye_x - eye_radius//2, eye_y - eye_radius//1.5, eye_radius, eye_radius * 1.2))
    pygame.draw.ellipse(surface, GOOMBA_EYE_WHITE, (right_eye_x - eye_radius//2, eye_y - eye_radius//1.5, eye_radius, eye_radius * 1.2))
    pupil_off_x = 1 if enemy_data.get('vx',0) > 0 else -1
    pygame.draw.circle(surface, BLACK, (left_eye_x + pupil_off_x, eye_y), eye_radius // 2.5)
    pygame.draw.circle(surface, BLACK, (right_eye_x + pupil_off_x, eye_y), eye_radius // 2.5)
    pygame.draw.line(surface, BLACK, (left_eye_x - eye_radius*0.6, eye_y - eye_radius*0.7), (left_eye_x + eye_radius*0.2, eye_y - eye_radius*0.3), 3)
    pygame.draw.line(surface, BLACK, (right_eye_x + eye_radius*0.6, eye_y - eye_radius*0.7), (right_eye_x - eye_radius*0.2, eye_y - eye_radius*0.3), 3)

def draw_koopa(surface, enemy_data):
    rect = enemy_data['rect']
    state = enemy_data.get('state', 'walking')
    e_vx = enemy_data.get('vx', 0)

    shell_color = KOOPA_GREEN_SHELL
    body_color = KOOPA_GREEN_BODY
    limb_color = KOOPA_FEET_HANDS 

    if state == 'shell_idle' or state == 'shell_sliding':
        shell_rect_h = rect.height * 0.7 
        shell_rect_y = rect.bottom - shell_rect_h
        shell_rect = pygame.Rect(rect.x, shell_rect_y, rect.width, shell_rect_h)
        pygame.draw.ellipse(surface, shell_color, shell_rect)
        pygame.draw.ellipse(surface, KOOPA_GREEN_SHELL_HIGHLIGHT, (shell_rect.x + shell_rect.width*0.1, shell_rect.y + shell_rect.height*0.1, shell_rect.width*0.8, shell_rect.height*0.5))
        pygame.draw.line(surface, BLACK, (shell_rect.centerx, shell_rect.top + 2), (shell_rect.centerx, shell_rect.bottom -2), 1)
        pygame.draw.line(surface, BLACK, (shell_rect.left + 2, shell_rect.centery), (shell_rect.right -2, shell_rect.centery), 1)
        if state == 'shell_sliding' and (pygame.time.get_ticks() // 100) % 2 == 0 : 
            sparkle_x = shell_rect.centerx + random.randint(-5,5) * (1 if e_vx > 0 else -1)
            sparkle_y = shell_rect.centery + random.randint(-5,5)
            pygame.draw.circle(surface, WHITE, (sparkle_x, sparkle_y), 2)
        return

    walk_anim_offset = int((pygame.time.get_ticks() // 200) % 2) * -2 
    shell_w = rect.width * 1.1 
    shell_h = rect.height * 0.65
    shell_x = rect.centerx - shell_w / 2
    shell_y = rect.y + rect.height * 0.1 + walk_anim_offset
    pygame.draw.ellipse(surface, shell_color, (shell_x, shell_y, shell_w, shell_h))
    pygame.draw.ellipse(surface, KOOPA_GREEN_SHELL_HIGHLIGHT, (shell_x + shell_w*0.1, shell_y + shell_h*0.1, shell_w*0.8, shell_h*0.4))
    head_r = rect.width * 0.35
    head_x_offset = rect.width * 0.1 * (1 if e_vx >= 0 else -1) 
    head_cx = rect.centerx + head_x_offset
    head_cy = rect.y + head_r * 0.9 + walk_anim_offset
    pygame.draw.ellipse(surface, body_color, (head_cx - head_r, head_cy - head_r*0.8, head_r*2, head_r*1.6)) 
    eye_r = head_r * 0.3
    eye_y = head_cy - head_r * 0.1
    eye_x_facing = head_cx + head_r * 0.3 * (1 if e_vx >=0 else -1)
    pygame.draw.ellipse(surface, WHITE, (eye_x_facing - eye_r, eye_y - eye_r, eye_r*1.5, eye_r*2))
    pygame.draw.circle(surface, BLACK, (int(eye_x_facing), int(eye_y)), int(eye_r*0.5))
    foot_w = rect.width * 0.3
    foot_h = rect.height * 0.25
    foot_y = rect.bottom - foot_h
    if (pygame.time.get_ticks() // 150) % 2 == 0:
        pygame.draw.ellipse(surface, limb_color, (rect.centerx - foot_w*1.2, foot_y, foot_w, foot_h))
        pygame.draw.ellipse(surface, limb_color, (rect.centerx + foot_w*0.2, foot_y + foot_h*0.2, foot_w, foot_h*0.8))
    else:
        pygame.draw.ellipse(surface, limb_color, (rect.centerx - foot_w*1.2, foot_y + foot_h*0.2, foot_w, foot_h*0.8))
        pygame.draw.ellipse(surface, limb_color, (rect.centerx + foot_w*0.2, foot_y, foot_w, foot_h))
    arm_w, arm_h = rect.width*0.15, rect.height*0.2
    arm_y = rect.y + rect.height*0.4 + walk_anim_offset
    if e_vx >= 0: 
        pygame.draw.ellipse(surface, limb_color, (rect.centerx + rect.width*0.1, arm_y, arm_w, arm_h))
    else: 
        pygame.draw.ellipse(surface, limb_color, (rect.centerx - rect.width*0.25, arm_y, arm_w, arm_h))

def draw_platform(surface, platform_data):
    rect = platform_data['rect']
    ptype = platform_data['type']
    current_y = rect.y 
    if 'hit_timer' in platform_data and platform_data['hit_timer'] > 0:
        offset = abs(platform_data['hit_timer'] - 10) 
        current_y = platform_data['original_y_ref'] - (5 - offset // 2) if offset < 10 else platform_data['original_y_ref'] 
        rect.y = current_y

    if ptype == 'ground':
        pygame.draw.rect(surface, GROUND_GREEN, rect)
        pygame.draw.rect(surface, GROUND_BROWN, (rect.x, rect.y + 8, rect.width, rect.height - 8)) 
        for i in range(rect.width // 25): 
            pygame.draw.circle(surface, GROUND_GREEN, (rect.x + 12 + i * 25, rect.y + 4), 8)
    elif ptype == 'brick':
        pygame.draw.rect(surface, PLATFORM_BRICK_RED, rect)
        bw, bh = 20, 10 
        for r_idx, r_y in enumerate(range(rect.top, rect.bottom, bh)):
            pygame.draw.line(surface, PLATFORM_BRICK_MORTAR, (rect.left, r_y), (rect.right, r_y), 1)
            for c_idx, c_x in enumerate(range(rect.left, rect.right, bw)):
                stagger = bw // 2 if r_idx % 2 == 0 else 0
                if c_x + stagger < rect.right:
                     pygame.draw.line(surface, PLATFORM_BRICK_MORTAR, (c_x + stagger, r_y), (c_x + stagger, r_y + bh if r_y + bh <= rect.bottom else rect.bottom ), 1)
    elif ptype == 'question':
        is_active = platform_data.get('active', False)
        block_color = QUESTION_BLOCK_YELLOW if is_active else USED_BLOCK_BROWN
        shadow_color = QUESTION_BLOCK_SHADOW if is_active else (120,80,50) 
        pygame.draw.rect(surface, BLACK, (rect.x-1, rect.y-1, rect.width+2, rect.height+2), border_radius=5) 
        pygame.draw.rect(surface, block_color, rect, border_radius=4)
        if is_active:
            q_font_size = int(rect.height * 0.7)
            q_font_snes = pygame.font.Font(None, q_font_size) 
            q_mark = q_font_snes.render("?", True, WHITE if (pygame.time.get_ticks()//150)%2 == 0 else BLACK) 
            q_rect = q_mark.get_rect(center=(rect.centerx, rect.centery + rect.height*0.05))
            surface.blit(q_mark, q_rect)
            bolt_size = max(2, rect.width // 10)
            bolt_positions = [
                (rect.left + bolt_size//2 + 2, rect.top + bolt_size//2 + 2),
                (rect.right - bolt_size//2 - 2, rect.top + bolt_size//2 + 2),
                (rect.left + bolt_size//2 + 2, rect.bottom - bolt_size//2 - 2),
                (rect.right - bolt_size//2 - 2, rect.bottom - bolt_size//2 - 2)
            ]
            for bp_x, bp_y in bolt_positions:
                pygame.draw.circle(surface, BLACK, (bp_x, bp_y), bolt_size//2)
        else: 
            pygame.draw.rect(surface, shadow_color, (rect.x+2, rect.y+2, rect.width-4, rect.height-4), border_radius=3)

    if 'hit_timer' in platform_data and platform_data['hit_timer'] > 0: 
        rect.y = platform_data['original_y_ref']

def draw_coin_sprite(surface, rect, frame_offset_unused): 
    pygame.draw.circle(surface, QUESTION_BLOCK_YELLOW, rect.center, rect.width // 2)
    pygame.draw.circle(surface, (255,255,100), rect.center, rect.width // 2.5) 
    coin_font = pygame.font.Font(None, int(rect.height*0.8))
    dollar_sign = coin_font.render("$", True, BLACK) 
    surface.blit(dollar_sign, dollar_sign.get_rect(center=rect.center))

def draw_mushroom(surface, item_data):
    rect = item_data['rect']
    cap_rect = pygame.Rect(rect.x, rect.y, rect.width, rect.height * 0.65)
    pygame.draw.ellipse(surface, MUSHROOM_RED, cap_rect)
    spot_r = rect.width * 0.15
    pygame.draw.circle(surface, MUSHROOM_SPOTS, (cap_rect.centerx - rect.width*0.2, cap_rect.centery - rect.height*0.05), spot_r)
    pygame.draw.circle(surface, MUSHROOM_SPOTS, (cap_rect.centerx + rect.width*0.2, cap_rect.centery - rect.height*0.05), spot_r)
    pygame.draw.circle(surface, MUSHROOM_SPOTS, (cap_rect.centerx, cap_rect.centery + rect.height*0.1), spot_r)
    stem_h = rect.height * 0.45
    stem_w = rect.width * 0.5
    stem_rect = pygame.Rect(rect.centerx - stem_w/2, cap_rect.bottom - stem_h*0.2, stem_w, stem_h)
    pygame.draw.rect(surface, MUSHROOM_STEM, stem_rect)
    eye_r = rect.width * 0.08
    eye_y = cap_rect.bottom - stem_h * 0.5
    pygame.draw.circle(surface, BLACK, (rect.centerx - rect.width*0.15, eye_y), eye_r)
    pygame.draw.circle(surface, BLACK, (rect.centerx + rect.width*0.15, eye_y), eye_r)

def draw_game():
    screen.fill(SKY_BLUE)
    for hill in hills:
        pygame.draw.ellipse(screen, hill['color1'], hill['rect'])
        highlight_rect = pygame.Rect(hill['rect'].x + hill['rect'].width * 0.1,
                                     hill['rect'].y + hill['rect'].height * 0.05,
                                     hill['rect'].width * 0.8,
                                     hill['rect'].height * 0.7)
        pygame.draw.ellipse(screen, hill['color2'], highlight_rect)
    for bush_data in bushes:
        for clump_rect in bush_data['clumps']:
            pygame.draw.ellipse(screen, bush_data['color'], clump_rect)
            shadow_clump = clump_rect.copy()
            shadow_clump.width *= 0.8
            shadow_clump.height *= 0.6
            shadow_clump.centerx = clump_rect.centerx
            shadow_clump.centery = clump_rect.centery + clump_rect.height*0.1
            pygame.draw.ellipse(screen, (max(0,bush_data['color'][0]-30),max(0,bush_data['color'][1]-30),max(0,bush_data['color'][2]-30)), shadow_clump)
    for cloud_data in clouds:
        base_x, base_y, _, size_w, size_h = cloud_data
        pygame.draw.ellipse(screen, WHITE, (int(base_x), int(base_y), int(size_w), int(size_h)))
        pygame.draw.ellipse(screen, WHITE, (int(base_x + size_w*0.3), int(base_y - size_h*0.2), int(size_w*0.7), int(size_h*0.8)))
        pygame.draw.ellipse(screen, WHITE, (int(base_x - size_w*0.2), int(base_y + size_h*0.1), int(size_w*0.6), int(size_h*0.7)))
        pygame.draw.ellipse(screen, (225,225,225), (int(base_x+4), int(base_y+4), int(size_w-8), int(size_h-8)))
    for p_data in current_level_platforms:
        draw_platform(screen, p_data)
    global coin_frame_index
    coin_frame_index = (coin_frame_index + COIN_SPIN_SPEED) % len(coin_animation_frames) 
    for item_data in items:
        if item_data['spawn_timer'] > 0: continue 
        if item_data['type'] == 'mushroom':
            draw_mushroom(screen, item_data)
        elif item_data['type'] == 'coin_anim': 
            draw_coin_sprite(screen, item_data['rect'], 0) 
    goal_x_center, goal_y_bottom = goal_posts_data[current_level_index]
    post_width = 15
    post_height = GOAL_TAPE_HEIGHT_TOTAL + 20
    pygame.draw.rect(screen, GOAL_POST_COLOR, (goal_x_center - GOAL_TAPE_WIDTH*2 - post_width, goal_y_bottom - post_height, post_width, post_height))
    pygame.draw.circle(screen, (50,50,50), (goal_x_center - GOAL_TAPE_WIDTH*2 - post_width//2, goal_y_bottom - post_height), post_width//1.5)
    pygame.draw.rect(screen, GOAL_POST_COLOR, (goal_x_center + GOAL_TAPE_WIDTH*2, goal_y_bottom - post_height, post_width, post_height))
    pygame.draw.circle(screen, (50,50,50), (goal_x_center + GOAL_TAPE_WIDTH*2 + post_width//2, goal_y_bottom - post_height), post_width//1.5)
    tape_base_y = goal_y_bottom - GOAL_TAPE_HEIGHT_TOTAL
    current_tape_y = tape_base_y + goal_tape_y_offset
    pygame.draw.rect(screen, GOAL_TAPE_COLOR, (goal_x_center - GOAL_TAPE_WIDTH // 2, current_tape_y, GOAL_TAPE_WIDTH, GOAL_TAPE_MOVING_HEIGHT))
    pygame.draw.rect(screen, BLACK, (goal_x_center - GOAL_TAPE_WIDTH // 2, current_tape_y, GOAL_TAPE_WIDTH, GOAL_TAPE_MOVING_HEIGHT),1) 
    if state != PLAYER_DIED_TRANSITION: 
        draw_player_sprite(screen, player_rect, player_state, facing_right, on_ground, player_vx, player_vy)
    for enemy_data in enemies:
        if enemy_data.get('stomped_timer', 0) > 0 and enemy_data['type'] == 'goomba': 
            draw_goomba(screen, enemy_data) 
        elif enemy_data.get('state', '') == 'shell_idle' or enemy_data.get('state', '') == 'shell_sliding': 
            draw_koopa(screen, enemy_data)
        elif enemy_data.get('type') == 'goomba':
            draw_goomba(screen, enemy_data)
        elif enemy_data.get('type') == 'koopa':
            draw_koopa(screen, enemy_data)
    for p_data in particles:
        pygame.draw.circle(screen, p_data[5], (int(p_data[0]), int(p_data[1])), int(p_data[4]))
    hud_y_offset = 10
    mario_label = small_font.render("MARIO", True, WHITE)
    screen.blit(mario_label, (20, hud_y_offset))
    score_val_text = font.render(f"{score:07d}", True, WHITE) 
    screen.blit(score_val_text, (20, hud_y_offset + 20))
    life_icon_rect = pygame.Rect(130, hud_y_offset + 5, PLAYER_SMALL_WIDTH // 1.5, PLAYER_SMALL_HEIGHT // 1.5)
    draw_player_sprite(screen, life_icon_rect, S_SMALL, True, True, 0, 0) 
    lives_text = font.render(f"x {player_lives}", True, WHITE)
    screen.blit(lives_text, (130 + life_icon_rect.width + 5, hud_y_offset + 12))
    pygame.draw.rect(screen, BLACK, (item_box_rect.x-2, item_box_rect.y-2, item_box_rect.width+4, item_box_rect.height+4), border_radius=5)
    pygame.draw.rect(screen, (50,50,80), item_box_rect, border_radius=4) 
    if stored_item_type == 'mushroom':
        icon_rect = pygame.Rect(0,0, MUSHROOM_WIDTH*0.8, MUSHROOM_HEIGHT*0.8)
        icon_rect.center = item_box_rect.center
        draw_mushroom(screen, {'rect': icon_rect}) 
    coin_icon_rect = pygame.Rect(WIDTH - 120, hud_y_offset + 5, 20, 20) 
    pygame.draw.circle(screen, QUESTION_BLOCK_YELLOW, coin_icon_rect.center, 10)
    pygame.draw.circle(screen, (200,150,0), coin_icon_rect.center, 8)
    elapsed = (pygame.time.get_ticks() - level_start_time) // 1000
    remaining_time = max(0, level_time_limit - elapsed)
    timer_label_text = small_font.render("TIME", True, WHITE)
    screen.blit(timer_label_text, (WIDTH - 80, hud_y_offset + 2)) 
    timer_text = font.render(f"{remaining_time:03d}", True, WHITE)
    screen.blit(timer_text, (WIDTH - timer_text.get_width() - 15, hud_y_offset + 20))

def draw_game_over():
    screen.fill(BLACK) 
    game_over_text = title_font.render("GAME OVER", True, MARIO_RED)
    screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 3))
    score_text_val = font.render(f"FINAL SCORE: {score}", True, WHITE)
    screen.blit(score_text_val, (WIDTH // 2 - score_text_val.get_width() // 2, HEIGHT // 2 + 20))
    prompt = font.render("Press R to Try Again", True, WHITE) 
    screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 + 100))

def draw_level_complete(): 
    screen.fill(SKY_BLUE) 
    temp_player_draw_rect = pygame.Rect(WIDTH // 2 - PLAYER_SUPER_WIDTH, HEIGHT // 2 - PLAYER_SUPER_HEIGHT - 20, PLAYER_SUPER_WIDTH*1.5, PLAYER_SUPER_HEIGHT*1.5)
    draw_player_sprite(screen, temp_player_draw_rect, player_state if player_state == S_SUPER else S_SUPER, True, True, 0, 0)
    complete_text = title_font.render("AREA CLEAR!", True, (255,255,100)) 
    complete_shadow = title_font.render("AREA CLEAR!", True, BLACK)
    screen.blit(complete_shadow, (WIDTH // 2 - complete_text.get_width() // 2 + 3, HEIGHT // 3 + 3))
    screen.blit(complete_text, (WIDTH // 2 - complete_text.get_width() // 2, HEIGHT // 3))
    score_val_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_val_text, (WIDTH // 2 - score_val_text.get_width() // 2, HEIGHT // 1.8))
    time_bonus = max(0, level_time_limit - ((pygame.time.get_ticks() - level_start_time) // 1000)) * 50 
    bonus_text = font.render(f"Time Bonus: {time_bonus}", True, WHITE)
    screen.blit(bonus_text, (WIDTH // 2 - bonus_text.get_width() // 2, HEIGHT // 1.8 + 40))
    next_prompt_text = "ENTER for Next Sector" if current_level_index < len(levels_platforms_data) -1 else "ENTER for Title Screen"
    prompt = font.render(next_prompt_text, True, WHITE)
    screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 1.8 + 100))
# --- End of Drawing Functions ---


current_level_index = 0
reset_level(current_level_index)
update_player_size() 

running = True
while running:
    dt = clock.tick(60) / 1000.0 
    actual_dt_for_physics = min(dt, 0.033) 

    keys = pygame.key.get_pressed() 

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if state == MENU and event.key == pygame.K_RETURN:
                play_sfx('menu_select')
                state = SELECT
                score = 0
                player_lives = 3
                player_state = S_SMALL
                stored_item_type = None
                update_player_size()
                current_level_index = 0 
            
            elif state == SELECT:
                if event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                    play_sfx('menu_navigate')
                    if event.key == pygame.K_LEFT:
                        current_level_index = (current_level_index - 1 + len(levels_platforms_data)) % len(levels_platforms_data)
                    elif event.key == pygame.K_RIGHT:
                        current_level_index = (current_level_index + 1) % len(levels_platforms_data)
                elif event.key == pygame.K_RETURN:
                    play_sfx('menu_select')
                    reset_level(current_level_index) 
                    state = PLAYING
            
            elif state == PLAYING:
                if event.key == pygame.K_SPACE: 
                    if on_ground:
                        play_sfx('jump')
                        player_vy = PLAYER_JUMP_INITIAL
                        on_ground = False
                        jump_hold_frames_count = PLAYER_JUMP_HOLD_FRAMES_MAX
                        create_particles(player_rect.centerx, player_rect.bottom, WHITE, 8, intensity=0.8)
            
            elif state == GAME_OVER and event.key == pygame.K_r:
                play_sfx('menu_select')
                player_lives = 3
                score = 0
                player_state = S_SMALL
                stored_item_type = None
                update_player_size()
                current_level_index = 0
                state = SELECT 
            
            elif state == LEVEL_COMPLETE and event.key == pygame.K_RETURN:
                play_sfx('menu_select')
                current_level_index += 1
                if current_level_index >= len(levels_platforms_data):
                    state = MENU 
                else:
                    reset_level(current_level_index)
                    state = PLAYING

    # --- State Updates ---
    for cloud_data in clouds:
        cloud_data[0] -= cloud_data[2] * (60 * actual_dt_for_physics)
        if cloud_data[0] < -cloud_data[3]:
            cloud_data[0] = WIDTH + random.randint(0,50)
            cloud_data[1] = random.randint(30, 150)
    for hill in hills: hill['rect'].x -= hill['speed_mod'] * (60 * actual_dt_for_physics) * 0.3 
    for bush_data in bushes:
        bush_data['base_rect'].x -= bush_data['speed_mod'] * (60 * actual_dt_for_physics) * 0.6
        for clump in bush_data['clumps']: clump.x -= bush_data['speed_mod'] * (60 * actual_dt_for_physics) * 0.6

    particles = [p for p in particles if p[6] > 0 and p[4] > 0] 
    for p_data in particles:
        p_data[0] += p_data[2] * (60 * actual_dt_for_physics)
        p_data[1] += p_data[3] * (60 * actual_dt_for_physics)
        p_data[3] += p_data[7] 
        p_data[4] -= 0.08 
        p_data[6] -= 1    

    for p_data in current_level_platforms:
        if p_data['type'] == 'question' and p_data.get('hit_timer', 0) > 0:
            p_data['hit_timer'] -=1

    if state == PLAYER_DIED_TRANSITION:
        player_vy += GRAVITY_PLAYER * (60 * actual_dt_for_physics) 
        player_rect.y += player_vy * (60 * actual_dt_for_physics)
        player_death_timer -=1
        if player_death_timer <= 0:
            reset_level(current_level_index) 
            state = PLAYING
            
    elif state == PLAYING:
        target_vx = 0
        if keys[pygame.K_LEFT]:
            target_vx = -PLAYER_MAX_WALK_SPEED
            facing_right = False
        if keys[pygame.K_RIGHT]:
            target_vx = PLAYER_MAX_WALK_SPEED
            facing_right = True

        if target_vx != 0: 
            if abs(player_vx) < abs(target_vx):
                player_vx += PLAYER_ACCEL * (1 if target_vx > 0 else -1)
                player_vx = max(-abs(target_vx), min(abs(target_vx), player_vx)) 
            elif (player_vx > 0 and target_vx < 0) or (player_vx < 0 and target_vx > 0) : 
                 player_vx += PLAYER_ACCEL * 2 * (1 if target_vx > 0 else -1) 
        else: 
            if abs(player_vx) > PLAYER_DECEL:
                player_vx -= PLAYER_DECEL * (1 if player_vx > 0 else -1)
            else:
                player_vx = 0
        player_rect.x += player_vx * (60 * actual_dt_for_physics)

        if keys[pygame.K_SPACE] and jump_hold_frames_count > 0 and player_vy < 0: 
            player_vy += PLAYER_JUMP_HOLD_FORCE 
            jump_hold_frames_count -= 1
        else:
            jump_hold_frames_count = 0 

        player_vy += GRAVITY_PLAYER * (60 * actual_dt_for_physics)
        player_vy = min(player_vy, 15) 
        player_rect.y += player_vy * (60 * actual_dt_for_physics)
        
        if player_rect.left < 0: player_rect.left = 0
        if player_rect.right > WIDTH: player_rect.right = WIDTH
        
        if player_rect.top > HEIGHT + player_rect.height : 
             if not player_invincible : 
                player_dies()

        on_ground_this_frame = False
        player_collided_horizontally = False

        for p_data in current_level_platforms:
            platform_rect = p_data['rect']
            if player_rect.colliderect(platform_rect):
                if player_vy > 0 and player_rect.bottom - player_vy * (60*actual_dt_for_physics) <= platform_rect.top +1 : 
                    player_rect.bottom = platform_rect.top
                    player_vy = 0
                    on_ground_this_frame = True
                    if not on_ground: create_particles(player_rect.midbottom[0], player_rect.bottom, WHITE, 3, intensity=0.3)

                elif player_vy < 0 and player_rect.top - player_vy * (60*actual_dt_for_physics) >= platform_rect.bottom -1 : 
                    player_rect.top = platform_rect.bottom
                    player_vy = 1.5 
                    
                    if p_data['type'] == 'question' and p_data.get('active', False):
                        play_sfx('block_bump')
                        p_data['active'] = False
                        p_data['hit_timer'] = 20 
                        create_particles(platform_rect.centerx, platform_rect.top, QUESTION_BLOCK_YELLOW, 15, intensity=0.8)
                        score += 100 
                        
                        content = p_data.get('content', 'coin')
                        if content == 'powerup':
                            if player_state == S_SMALL:
                                spawn_item('mushroom', platform_rect)
                            else: 
                                spawn_item('coin_anim', platform_rect)
                                # score already added in spawn_item for coin_anim
                        elif content == 'coin':
                            spawn_item('coin_anim', platform_rect)
                            # score already added in spawn_item for coin_anim

                    elif p_data['type'] == 'brick': 
                        if player_state == S_SUPER : # Only super mario can break bricks (conceptual)
                            play_sfx('brick_break')
                            # current_level_platforms.remove(p_data) # Remove brick - careful with list mod
                            create_particles(platform_rect.centerx, player_rect.top, PLATFORM_BRICK_RED, 20, intensity=1.5)
                            # TODO: Implement brick breaking properly by removing or changing type
                        else:
                            play_sfx('block_hit')
                            create_particles(platform_rect.centerx, player_rect.top, PLATFORM_BRICK_MORTAR, 8)
                
                if player_rect.colliderect(platform_rect): 
                    if player_vx > 0 and player_rect.right - player_vx * (60*actual_dt_for_physics) <= platform_rect.left +1:
                        player_rect.right = platform_rect.left
                        player_vx = 0 
                        player_collided_horizontally = True
                    elif player_vx < 0 and player_rect.left - player_vx * (60*actual_dt_for_physics) >= platform_rect.right -1:
                        player_rect.left = platform_rect.right
                        player_vx = 0
                        player_collided_horizontally = True
        on_ground = on_ground_this_frame

        for i in range(len(enemies) - 1, -1, -1):
            enemy_data = enemies[i]
            enemy_rect = enemy_data['rect']

            if enemy_data.get('state') == 'shell_sliding':
                enemy_rect.x += enemy_data['vx'] * (60*actual_dt_for_physics)
                for j in range(len(enemies) - 1, -1, -1):
                    if i == j: continue 
                    other_enemy = enemies[j]
                    if other_enemy.get('stomped_timer',0) > 0 or other_enemy.get('state','none') in ['shell_idle', 'shell_sliding']: continue 
                    if enemy_rect.colliderect(other_enemy['rect']):
                        play_sfx('kick_shell') # Shell hitting another enemy
                        create_particles(other_enemy['rect'].centerx, other_enemy['rect'].centery, (100,100,100), 15, intensity=1.5)
                        score += 200 
                        enemies.pop(j)
                        if j < i: i -=1 
                if enemy_rect.left <= 0 or enemy_rect.right >= WIDTH:
                    enemy_data['vx'] *= -1
                for p_data in current_level_platforms: 
                    plat_rect = p_data['rect']
                    if enemy_rect.colliderect(plat_rect):
                        if (enemy_data['vx'] > 0 and enemy_rect.right > plat_rect.left and enemy_rect.left < plat_rect.left) or \
                           (enemy_data['vx'] < 0 and enemy_rect.left < plat_rect.right and enemy_rect.right > plat_rect.right):
                            enemy_data['vx'] *= -1
                            if enemy_data['vx'] < 0: enemy_rect.left = plat_rect.right 
                            else: enemy_rect.right = plat_rect.left
                            break 
                enemy_data['vy'] += GRAVITY_ENEMY * (60*actual_dt_for_physics)
                enemy_rect.y += enemy_data['vy'] * (60*actual_dt_for_physics)
                shell_on_ground = False
                for p_data in current_level_platforms:
                    if enemy_rect.colliderect(p_data['rect']) and enemy_data['vy'] > 0 and enemy_rect.bottom - enemy_data['vy'] * (60*actual_dt_for_physics) <= p_data['rect'].top +1:
                        enemy_rect.bottom = p_data['rect'].top
                        enemy_data['vy'] = 0
                        shell_on_ground = True
                        break
                enemy_data['on_ground'] = shell_on_ground
            elif enemy_data.get('stomped_timer', 0) > 0 and enemy_data['type'] == 'goomba':
                enemy_data['stomped_timer'] -=1
                if enemy_data['stomped_timer'] == 0:
                    enemies.pop(i)
                continue
            elif enemy_data.get('state') == 'shell_idle': 
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
                if player_rect.colliderect(enemy_rect) and not player_invincible:
                    play_sfx('kick_shell')
                    enemy_data['state'] = 'shell_sliding'
                    enemy_data['vx'] = KOOPA_SHELL_SPEED * (1 if player_rect.centerx < enemy_rect.centerx else -1) 
                    player_vy = STOMP_BOUNCE * 0.5 
                    score += 50 
                    create_particles(enemy_rect.centerx, enemy_rect.centery, KOOPA_GREEN_SHELL_HIGHLIGHT, 10)
                continue 
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
                            if enemy_on_ground_this_frame or enemy_data.get('on_ground'): 
                                enemy_data['vx'] *= -1
                                if enemy_data['type'] == 'koopa': enemy_data['original_vx'] *= -1 
                                if enemy_data['vx'] < 0: enemy_rect.left = platform_rect_check.right +1
                                else: enemy_rect.right = platform_rect_check.left -1
                enemy_data['on_ground'] = enemy_on_ground_this_frame
                if enemy_rect.left <= 0 and enemy_data['vx'] < 0:
                    enemy_data['vx'] *= -1
                    if enemy_data['type'] == 'koopa': enemy_data['original_vx'] *= -1
                if enemy_rect.right >= WIDTH and enemy_data['vx'] > 0:
                    enemy_data['vx'] *= -1
                    if enemy_data['type'] == 'koopa': enemy_data['original_vx'] *= -1
                if enemy_data['on_ground'] and enemy_data['type'] != 'koopa_shell': 
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

            if player_rect.colliderect(enemy_rect) and not player_invincible:
                if enemy_data.get('stomped_timer',0) > 0: continue 
                if enemy_data.get('state', '') == 'shell_idle': continue 
                if enemy_data.get('state', '') == 'shell_sliding' and abs(player_vy) < 2: 
                     if player_state == S_SUPER:
                        play_sfx('player_hit')
                        player_state = S_SMALL
                        update_player_size()
                        player_invincible = True
                        invincible_timer = INVINCIBILITY_DURATION
                        create_particles(player_rect.centerx, player_rect.centery, MARIO_RED, 20)
                     else:
                        player_dies() 
                     continue
                is_stomp = player_vy > 1.0 and (player_rect.bottom - player_vy*(60*actual_dt_for_physics) <= enemy_rect.top + enemy_rect.height * 0.5)
                if is_stomp:
                    player_vy = STOMP_BOUNCE 
                    on_ground = False 
                    score += 200
                    if enemy_data['type'] == 'goomba':
                        play_sfx('stomp_goomba')
                        enemy_data['stomped_timer'] = 30 
                        enemy_data['vx'] = 0
                        create_particles(enemy_rect.centerx, enemy_rect.top, GOOMBA_BROWN, 15, intensity=1.2)
                    elif enemy_data['type'] == 'koopa':
                        koopa_state = enemy_data.get('state', 'walking')
                        if koopa_state == 'walking':
                            play_sfx('stomp_koopa_to_shell')
                            enemy_data['state'] = 'shell_idle'
                            enemy_data['vx'] = 0
                            enemy_data['rect'].height = KOOPA_SHELL_HEIGHT 
                            enemy_data['rect'].bottom = enemy_rect.bottom 
                            create_particles(enemy_rect.centerx, enemy_rect.top, KOOPA_GREEN_SHELL, 15)
                        elif koopa_state == 'shell_sliding': 
                            play_sfx('stomp_koopa_shell_stop')
                            enemy_data['state'] = 'shell_idle'
                            enemy_data['vx'] = 0
                            create_particles(enemy_rect.centerx, enemy_rect.centery, WHITE, 10)
                else: 
                    if player_state == S_SUPER:
                        play_sfx('player_hit')
                        player_state = S_SMALL
                        update_player_size()
                        player_invincible = True
                        invincible_timer = INVINCIBILITY_DURATION
                        player_vy = -3 
                        create_particles(player_rect.centerx, player_rect.centery, MARIO_RED, 20)
                    else: 
                        player_dies()
                    break 
        if player_invincible:
            invincible_timer -= 1
            if invincible_timer <= 0:
                player_invincible = False
        
        for i in range(len(items) - 1, -1, -1):
            item_data = items[i]
            item_rect = item_data['rect']

            if item_data['spawn_timer'] > 0: 
                item_data['spawn_timer'] -= 1
                item_rect.y = item_data['original_y'] - (POWERUP_REVEAL_DURATION - item_data['spawn_timer']) * (MUSHROOM_HEIGHT / POWERUP_REVEAL_DURATION)
                continue 

            if item_data['type'] == 'mushroom':
                item_rect.x += item_data['vx'] * (60*actual_dt_for_physics)
                item_data['vy'] += GRAVITY_ITEM * (60*actual_dt_for_physics)
                item_rect.y += item_data['vy'] * (60*actual_dt_for_physics)
                item_on_ground = False
                for p_data in current_level_platforms:
                    platform_rect_item = p_data['rect']
                    if item_rect.colliderect(platform_rect_item):
                        if item_data['vy'] >= 0 and item_rect.bottom - item_data['vy']*(60*actual_dt_for_physics) <= platform_rect_item.top +1:
                            item_rect.bottom = platform_rect_item.top
                            item_data['vy'] = 0
                            item_on_ground = True
                        elif (item_data['vx'] > 0 and item_rect.right > platform_rect_item.left and item_rect.left < platform_rect_item.left) or \
                             (item_data['vx'] < 0 and item_rect.left < platform_rect_item.right and item_rect.right > platform_rect_item.right):
                            if item_on_ground: 
                                 item_data['vx'] *= -1
                item_data['on_ground'] = item_on_ground
                if (item_rect.left <=0 and item_data['vx'] < 0) or (item_rect.right >= WIDTH and item_data['vx'] > 0) : item_data['vx'] *= -1

                if player_rect.colliderect(item_rect):
                    play_sfx('powerup_collect')
                    items.pop(i)
                    score += 1000 
                    if player_state == S_SMALL:
                        player_state = S_SUPER
                        update_player_size()
                        player_invincible = True 
                        invincible_timer = INVINCIBILITY_DURATION // 2
                    elif stored_item_type is None: 
                        stored_item_type = 'mushroom' 
                    create_particles(item_rect.centerx, item_rect.centery, MUSHROOM_RED, 20)
            
            elif item_data['type'] == 'coin_anim':
                item_data['rect'].y += item_data['vy'] * (60*actual_dt_for_physics)
                item_data['rect'].x += item_data['vx'] * (60*actual_dt_for_physics)
                item_data['vy'] += GRAVITY_ITEM * 0.5 * (60*actual_dt_for_physics) 
                item_data['duration'] -= 1
                if item_data['duration'] <= 0:
                    items.pop(i)
                    create_particles(item_rect.centerx, item_rect.centery, QUESTION_BLOCK_YELLOW, 5, intensity=0.5)

        goal_struct_x, goal_struct_y_bottom = goal_posts_data[current_level_index]
        tape_actual_y = (goal_struct_y_bottom - GOAL_TAPE_HEIGHT_TOTAL) + goal_tape_y_offset
        goal_tape_rect_actual = pygame.Rect(goal_struct_x - GOAL_TAPE_WIDTH // 2, tape_actual_y, GOAL_TAPE_WIDTH, GOAL_TAPE_MOVING_HEIGHT)

        if player_rect.colliderect(goal_tape_rect_actual):
            play_sfx('level_complete')
            hit_pos_on_tape = (player_rect.centery - tape_actual_y) / GOAL_TAPE_MOVING_HEIGHT 
            base_score = 1000
            time_bonus = max(0, level_time_limit - ((pygame.time.get_ticks() - level_start_time) // 1000)) * 50
            score += base_score + time_bonus
            state = LEVEL_COMPLETE
            create_particles(player_rect.centerx, player_rect.top, GOAL_TAPE_COLOR, 40, intensity=2.5)

        goal_tape_y_offset += goal_tape_direction * 0.8 * (60 * actual_dt_for_physics) 
        if goal_tape_y_offset > GOAL_TAPE_HEIGHT_TOTAL - GOAL_TAPE_MOVING_HEIGHT:
            goal_tape_y_offset = GOAL_TAPE_HEIGHT_TOTAL - GOAL_TAPE_MOVING_HEIGHT
            goal_tape_direction = -1
        elif goal_tape_y_offset < 0:
            goal_tape_y_offset = 0
            goal_tape_direction = 1

        elapsed_time_seconds = (pygame.time.get_ticks() - level_start_time) // 1000
        if elapsed_time_seconds >= level_time_limit:
            if not player_invincible : player_dies() 


    # --- Drawing ---
    if state == MENU:
        draw_menu()
    elif state == SELECT:
        draw_select()
    elif state == PLAYING or state == PLAYER_DIED_TRANSITION: 
        draw_game()
    elif state == GAME_OVER:
        draw_game_over()
    elif state == LEVEL_COMPLETE:
        draw_level_complete()

    pygame.display.flip()

pygame.quit()
sys.exit()

import pygame
import socket
import threading
import json
import random
import time
import sys
import math

# --- Constants ---
SCREEN_W, SCREEN_H = 800, 480
TILE = 32
FPS = 60
NET_TICK = 0.02
UDP_PORT = 6000
BROADCAST = '<broadcast>'
POWERUPS = ['mushroom', 'fire', 'shell', 'star', 'mini', 'mega']
BACKGROUND_COLOR = (123, 187, 251)
FONT_NAME = 'consolas'
ICE_PROJECTILE_COLOR = (140, 200, 255)
LEVEL = [
    {'x': 0, 'y': SCREEN_H-TILE, 'w': SCREEN_W, 'h': TILE, 'type': 'solid'},
    {'x': 120, 'y': 360, 'w': TILE*3, 'h': 16, 'type': 'platform'},
    {'x': 400, 'y': 300, 'w': TILE*2, 'h': TILE, 'type': 'pipeL'},
    {'x': 500, 'y': 300, 'w': TILE*2, 'h': TILE, 'type': 'pipeR'},
]
COIN_SPAWNS = [(200, 300), (400, 280), (600, 200), (700, 360)]

# --- Globals for network ---
remotes = {}
remote_lock = threading.Lock()
running = True

def listener(local_id):
    global remotes, running
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.1)
    sock.bind(('', UDP_PORT))
    
    while running:
        try:
            data, addr = sock.recvfrom(1024)
            msg = json.loads(data.decode('utf-8'))
            if msg['pid'] == local_id:
                continue
                
            with remote_lock:
                if msg['pid'] not in remotes:
                    color = (msg['color_r'], msg['color_g'], msg['color_b'])
                    remotes[msg['pid']] = Player(msg['pid'], color, msg['x'], msg['y'])
                
                p = remotes[msg['pid']]
                p.x = msg['x']
                p.y = msg['y']
                p.vx = msg['vx']
                p.vy = msg['vy']
                p.facing = msg['facing']
                p.ground = msg['ground']
                p.state = msg['state']
                p.power = msg['power']
                p.stars = msg['stars']
                p.lives = msg['lives']
                p.coins = msg['coins']
                p.projectiles = msg['projectiles']
                p.dead = msg['dead']
                p.invuln = msg['invuln']
                p.respawn = msg['respawn']
                p.score = msg['score']
                p.frozen_timer = msg['frozen_timer']
                
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Network error: {e}")

# --- Game Classes ---
class Player:
    def __init__(self, pid, color, x, y):
        self.pid = pid
        self.color = color
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.lives = 3
        self.respawn = 0
        self.stars = 0
        self.state = None
        self.power = []
        self.facing = 1
        self.ground = False
        self.dead = False
        self.invuln = 0
        self.projectiles = []
        self.score = 0
        self.frozen_timer = 0
        self.coins = 0
        self.jump_timer = 0
        self.hurt_timer = 0
        self.width = TILE
        self.height = TILE * 2

    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def update(self, keys, level, players, items, star_drops, ice_blocks):
        if self.dead:
            if self.respawn > 0:
                self.respawn -= 1
            return
        
        if self.frozen_timer > 0:
            self.frozen_timer -= 1
            return
        
        # Movement physics
        self.vy += 0.5  # Gravity
        self.vx *= 0.85  # Friction
        
        # Apply velocity
        self.x += self.vx
        self.y += self.vy
        
        # Collision with level
        self.ground = False
        player_rect = self.rect()
        for plat in level:
            plat_rect = pygame.Rect(plat['x'], plat['y'], plat['w'], plat['h'])
            if player_rect.colliderect(plat_rect):
                if plat['type'] == 'solid' or plat['type'] == 'pipeL' or plat['type'] == 'pipeR':
                    if self.vy > 0 and player_rect.bottom > plat_rect.top and player_rect.top < plat_rect.top:
                        self.y = plat_rect.top - self.height
                        self.vy = 0
                        self.ground = True
                    elif self.vy < 0 and player_rect.top < plat_rect.bottom and player_rect.bottom > plat_rect.bottom:
                        self.y = plat_rect.bottom
                        self.vy = 0
                    if self.vx > 0 and player_rect.right > plat_rect.left and player_rect.left < plat_rect.left:
                        self.x = plat_rect.left - self.width
                    elif self.vx < 0 and player_rect.left < plat_rect.right and player_rect.right > plat_rect.right:
                        self.x = plat_rect.right
        
        # Key controls
        if keys['left']:
            self.vx = max(self.vx - 0.8, -5)
            self.facing = -1
        if keys['right']:
            self.vx = min(self.vx + 0.8, 5)
            self.facing = 1
        if keys['jump'] and self.ground and self.jump_timer <= 0:
            self.vy = -12
            self.jump_timer = 10
        
        # Fire projectiles
        if keys['fire'] and 'fire' in self.power:
            self.projectiles.append({
                'x': self.x + (self.width//2) + (self.facing * 20),
                'y': self.y + 10,
                'vx': self.facing * 8,
                'type': 'fire'
            })
        
        # Ice projectiles
        if keys['fire'] and 'ice' in self.power:
            self.projectiles.append({
                'x': self.x + (self.width//2) + (self.facing * 20),
                'y': self.y + 10,
                'vx': self.facing * 6,
                'type': 'ice'
            })
        
        # Update projectiles
        for proj in self.projectiles[:]:
            proj['x'] += proj['vx']
            if proj['x'] < 0 or proj['x'] > SCREEN_W:
                self.projectiles.remove(proj)
        
        # Collect coins
        for player in players:
            if player is not self and not player.dead:
                player_rect = player.rect()
                if player_rect.colliderect(self.rect()):
                    if self.stars > 0:
                        player.die(players, star_drops)
                        self.stars -= 1
                        self.score += 100
        
        # Update timers
        if self.jump_timer > 0:
            self.jump_timer -= 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.hurt_timer > 0:
            self.hurt_timer -= 1
        
        # Boundary check
        if self.y > SCREEN_H:
            self.die(players, star_drops)

    def die(self, players, star_drops):
        if self.invuln > 0 or self.dead:
            return
            
        self.lives -= 1
        self.dead = True
        self.respawn = FPS * 3 if self.lives > 0 else -1
        
        # Drop stars
        for _ in range(self.stars):
            star_drops.append(StarDrop(self.x, self.y))
        self.stars = 0
        
        # Respawn position
        if self.lives > 0:
            self.x = random.randint(100, SCREEN_W - 100)
            self.y = 100
            self.vx = 0
            self.vy = 0
            self.invuln = FPS * 2

class Star:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.timer = 0

    def update(self, players):
        self.timer += 1
        for player in players:
            if not player.dead and math.hypot(self.x - player.x, self.y - player.y) < 30:
                player.stars = min(player.stars + 1, 3)
                self.timer = -999  # Collected
                return

    def draw(self, win):
        size = 20 + math.sin(self.timer * 0.1) * 5
        pygame.draw.circle(win, (255, 255, 0), (int(self.x), int(self.y)), int(size))
        points = []
        for i in range(8):
            angle = math.pi * i / 4 + self.timer * 0.05
            px = self.x + math.cos(angle) * (size + 5)
            py = self.y + math.sin(angle) * (size + 5)
            points.append((px, py))
        pygame.draw.polygon(win, (255, 200, 0), points)

class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.active = True
        self.timer = 0

    def update(self, players):
        self.timer += 1
        for player in players:
            if self.active and not player.dead and math.hypot(self.x - player.x, self.y - player.y) < 30:
                player.coins += 1
                player.score += 10
                self.active = False

    def draw(self, win):
        if not self.active:
            return
        y_offset = math.sin(self.timer * 0.1) * 5
        pygame.draw.circle(win, (255, 215, 0), (int(self.x), int(self.y + y_offset)), 8)
        pygame.draw.circle(win, (200, 150, 0), (int(self.x), int(self.y + y_offset)), 8, 2)

class Item:
    def __init__(self, t, x, y):
        self.t = t
        self.x = x
        self.y = y
        self.active = True
        self.vy = -1
        self.bounce = 0

    def update(self, players, level, ice_blocks):
        self.bounce += 0.1
        self.y += math.sin(self.bounce) * 0.5
        
        for player in players:
            if self.active and not player.dead and math.hypot(self.x - player.x, self.y - player.y) < 30:
                if self.t == 'star':
                    player.stars = min(player.stars + 1, 3)
                elif self.t not in player.power:
                    player.power.append(self.t)
                    if self.t == 'fire' and 'ice' in player.power:
                        player.power.remove('ice')
                    elif self.t == 'ice' and 'fire' in player.power:
                        player.power.remove('fire')
                self.active = False
                player.score += 50

    def draw(self, win):
        if not self.active:
            return
        
        # Draw item based on type
        if self.t == 'mushroom':
            pygame.draw.rect(win, (220, 100, 100), (self.x - 10, self.y - 10, 20, 20))
        elif self.t == 'fire':
            pygame.draw.circle(win, (255, 100, 0), (int(self.x), int(self.y)), 10)
        elif self.t == 'star':
            pygame.draw.circle(win, (255, 255, 0), (int(self.x), int(self.y)), 12)
        elif self.t == 'shell':
            pygame.draw.ellipse(win, (100, 200, 100), (self.x - 12, self.y - 8, 24, 16))

class StarDrop:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-8, -4)
        self.timer = FPS * 10  # 10 seconds to live

    def update(self, players):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2  # Gravity
        self.timer -= 1
        
        # Bounce on ground
        if self.y > SCREEN_H - 20:
            self.y = SCREEN_H - 20
            self.vy = -self.vy * 0.7
            
        # Collect by players
        for player in players:
            if not player.dead and math.hypot(self.x - player.x, self.y - player.y) < 30:
                player.stars = min(player.stars + 1, 3)
                self.timer = -999  # Collected

    def draw(self, win):
        pygame.draw.circle(win, (255, 255, 0), (int(self.x), int(self.y)), 10)
        pygame.draw.circle(win, (255, 200, 0), (int(self.x), int(self.y)), 10, 2)

class IceBlock:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.active = True
        self.timer = FPS * 5  # 5 seconds to melt

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.active = False

    def draw(self, win):
        alpha = min(255, int(self.timer / (FPS * 5) * 200) + 55)
        s = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.rect(s, (180, 220, 255, alpha), (0, 0, 30, 30))
        pygame.draw.rect(s, (140, 200, 255, alpha), (0, 0, 30, 30), 2)
        win.blit(s, (self.x - 15, self.y - 15))

# --- MarioLegacy Game ---
class MarioLegacy:
    def __init__(self, win):
        self.win = win
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(FONT_NAME, 24)
        self.big_font = pygame.font.SysFont(FONT_NAME, 32)
        self.title_font = pygame.font.SysFont(FONT_NAME, 56)
        self.game_state = "menu"
        self.winner_pid = None
        self.menu_selection = 0
        self.sounds = {}
        self.reset_game_vars()

    def play_sound(self, sound_name, loop=False):
        pass  # Sound implementation omitted for brevity

    def reset_game_vars(self):
        global remotes, running
        self.local_id = str(random.randint(1000, 9999))
        is_player_one_style = random.choice([True, False])
        p1_color = (220, 50, 50) if is_player_one_style else (50, 180, 50)
        p1_x = 100 if is_player_one_style else SCREEN_W - 150
        self.p1 = Player(self.local_id, p1_color, p1_x, SCREEN_H - TILE * 3)
        self.star_drops = []
        self.items = []
        self.world_star = Star(SCREEN_W // 2, 100)
        self.coins = [Coin(x, y) for (x, y) in COIN_SPAWNS]
        self.ice_blocks = []
        self.item_spawn_timer = FPS * 10
        self.max_items_on_map = 3
        running = True
        with remote_lock:
            remotes.clear()
        self.game_active = True
        self.game_over_timer = 0
        self.last_send_time = 0
        if not hasattr(self, 'sock') or self.sock._closed:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.key_map = {
            'left': pygame.K_LEFT, 'right': pygame.K_RIGHT,
            'jump': pygame.K_z, 'down': pygame.K_DOWN,
            'run': pygame.K_LSHIFT, 'fire': pygame.K_x,
            'menu_up': pygame.K_UP, 'menu_down': pygame.K_DOWN, 'menu_select': pygame.K_RETURN
        }
        self.keys_pressed = {k_name: False for k_name in self.key_map}
        if not hasattr(self, 'net_thread') or not self.net_thread.is_alive():
            self.net_thread = threading.Thread(target=listener, args=(self.local_id,), daemon=True)
            self.net_thread.start()
        self.winner_pid = None

    def handle_events(self):
        global running
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game_active = False
                running = False
                return True
            if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                is_pressed = event.type == pygame.KEYDOWN
                for key_name, key_code in self.key_map.items():
                    if event.key == key_code:
                        self.keys_pressed[key_name] = is_pressed
            if event.type == pygame.KEYDOWN:
                if self.game_state == "menu":
                    if event.key == self.key_map['menu_down']:
                        self.menu_selection = (self.menu_selection + 1) % 2
                    if event.key == self.key_map['menu_up']:
                        self.menu_selection = (self.menu_selection - 1 + 2) % 2
                    if event.key == self.key_map['menu_select']:
                        if self.menu_selection == 0:
                            self.game_state = "playing"
                            self.reset_game_vars()
                        elif self.menu_selection == 1:
                            self.game_active = False
                            running = False
                            return True
                elif self.game_state == "game_over":
                    if event.key == pygame.K_r or event.key == self.key_map['menu_select']:
                        self.game_state = "menu"
        return False

    def update_network(self):
        if time.time() - self.last_send_time > NET_TICK:
            self.last_send_time = time.time()
            msg_payload = {
                'pid': self.local_id,
                'x': self.p1.x, 'y': self.p1.y,
                'vx': self.p1.vx, 'vy': self.p1.vy,
                'facing': self.p1.facing, 'ground': self.p1.ground,
                'state': self.p1.state, 'power': self.p1.power,
                'stars': self.p1.stars, 'lives': self.p1.lives, 'coins': self.p1.coins,
                'projectiles': self.p1.projectiles,
                'dead': self.p1.dead, 'invuln': self.p1.invuln,
                'respawn': self.p1.respawn, 'score': self.p1.score,
                'frozen_timer': self.p1.frozen_timer,
                'color_r': self.p1.color[0], 'color_g': self.p1.color[1], 'color_b': self.p1.color[2],
            }
            try:
                self.sock.sendto(json.dumps(msg_payload).encode('utf-8'), (BROADCAST, UDP_PORT))
            except (OSError, Exception):
                pass

    def update_game_logic(self):
        all_player_objects = [self.p1]
        with remote_lock:
            remote_player_list = list(remotes.values())
            all_player_objects.extend(remote_player_list)
            
        self.world_star.update(all_player_objects)
        for coin_obj in self.coins[:]:
            coin_obj.update(all_player_objects)
            if not coin_obj.active: 
                self.coins.remove(coin_obj)
                
        if self.p1.coins >= 8 and not self.p1.dead:
            self.p1.coins -= 8
            item_x = self.p1.x + random.uniform(-TILE, TILE)
            item_y = self.p1.y - TILE * 2
            item_x = max(TILE, min(item_x, SCREEN_W - TILE * 2))
            item_y = max(TILE, min(item_y, SCREEN_H - TILE * 3))
            available_powerups = [p for p in POWERUPS if p != 'star']
            if available_powerups:
                self.items.append(Item(random.choice(available_powerups), item_x, item_y))
                
        self.item_spawn_timer -= 1
        if self.item_spawn_timer <= 0 and len(self.items) < self.max_items_on_map:
            self.item_spawn_timer = FPS * random.randint(8, 15)
            spawn_x = random.randint(TILE, SCREEN_W - TILE * 2)
            spawn_y = random.randint(TILE * 2, SCREEN_H // 2)
            self.items.append(Item(random.choice(POWERUPS), spawn_x, spawn_y))
            
        for item_obj in self.items[:]:
            item_obj.update(all_player_objects, LEVEL, self.ice_blocks)
            if not item_obj.active: 
                self.items.remove(item_obj)
                
        for ib_obj in self.ice_blocks[:]:
            ib_obj.update()
            if not ib_obj.active: 
                self.ice_blocks.remove(ib_obj)
                
        for drop_obj in self.star_drops[:]:
            drop_obj.update(all_player_objects)
            if drop_obj.timer <= 0: 
                self.star_drops.remove(drop_obj)
                
        self.p1.update(self.keys_pressed, LEVEL, all_player_objects, self.items, self.star_drops, self.ice_blocks)
        
        # Game over conditions
        if not self.p1.dead and self.p1.lives <= 0 and self.p1.respawn != -1:
            self.p1.die([], self.star_drops)
            
        if len(all_player_objects) >= 2:
            p1_effectively_out = self.p1.lives <= 0 and self.p1.respawn == -1
            num_opponents_active = 0
            potential_winner = None
            for rp in remote_player_list:
                if rp.lives > 0 or rp.respawn > 0:
                    num_opponents_active += 1
                    potential_winner = rp.pid
                    
            if p1_effectively_out and num_opponents_active == 1 and potential_winner:
                self.winner_pid = potential_winner
                self.game_state = "game_over"
            elif not p1_effectively_out and num_opponents_active == 0 and remote_player_list:
                self.winner_pid = self.p1.pid
                self.game_state = "game_over"
            elif p1_effectively_out and num_opponents_active == 0:
                self.winner_pid = "DRAW"
                self.game_state = "game_over"
                
        elif len(all_player_objects) == 1 and self.p1.lives <= 0 and self.p1.respawn == -1:
            self.winner_pid = "GAME OVER"
            self.game_state = "game_over"

    def draw_player_visuals(self, win, player_obj):
        pr = player_obj.rect()
        base_color = player_obj.color
        display_color = base_color
        
        if player_obj.state == 'fire': 
            display_color = (230, 80, 20)
        elif player_obj.state == 'ice': 
            display_color = (120, 180, 240)
        elif player_obj.state == 'mega': 
            display_color = (80, 80, 80)
        elif player_obj.state == 'mini': 
            display_color = (int(player_obj.color[0] * 0.8), 
                             int(player_obj.color[1] * 0.8), 
                             int(player_obj.color[2] * 0.8))
        
        pygame.draw.rect(win, display_color, pr, border_radius=6)
        
        # Draw eyes
        eye_offset = 5
        pygame.draw.circle(win, (255, 255, 255), 
                          (int(pr.centerx - eye_offset * player_obj.facing), int(pr.y + 15)), 6)
        pygame.draw.circle(win, (0, 0, 0), 
                          (int(pr.centerx - eye_offset * player_obj.facing), int(pr.y + 15)), 3)
        
        if player_obj.invuln > 0:
            if (player_obj.invuln // (FPS // 10)) % 2 == 0:
                overlay_alpha = 100 + math.sin(time.time() * 30) * 50
                inv_color = (255, 255, 150, int(max(0, min(255, overlay_alpha)))) if 'star' in player_obj.power else (200, 200, 200, int(max(0, min(255, overlay_alpha * 0.7))))
                s = pygame.Surface((pr.width, pr.height), pygame.SRCALPHA)
                s.fill(inv_color)
                win.blit(s, pr.topleft)
                
            if 'star' in player_obj.power:
                star_aura_colors = [(255, 0, 0), (255, 165, 0), (255, 255, 0), 
                                  (0, 255, 0), (0, 0, 255), (75, 0, 130), (238, 130, 238)]
                aura_idx = int(time.time() * 10) % len(star_aura_colors)
                pygame.draw.rect(win, (*star_aura_colors[aura_idx], 70), 
                                pr.inflate(6, 6), border_radius=8)
                
        if player_obj.frozen_timer > 0:
            f_alpha = 150 + math.sin(time.time() * 15) * 55
            frozen_surf = pygame.Surface(pr.size, pygame.SRCALPHA)
            frozen_surf.fill((180, 220, 255, int(f_alpha)))
            for _ in range(3):
                sp_x = random.randint(0, pr.width - 2)
                sp_y = random.randint(0, pr.height - 2)
                sp_l = random.randint(2, 5)
                pygame.draw.line(frozen_surf, (220, 240, 255, 200), 
                               (sp_x, sp_y), 
                               (sp_x + random.randint(-sp_l, sp_l), sp_y + random.randint(-sp_l, sp_l)), 1)
            win.blit(frozen_surf, pr.topleft)

    def draw_hud(self):
        # Player stats
        stats = f"Lives: {self.p1.lives}  Stars: {self.p1.stars}  Coins: {self.p1.coins}  Score: {self.p1.score}"
        text = self.font.render(stats, True, (255, 255, 255))
        pygame.draw.rect(self.win, (0, 0, 0, 150), (5, 5, text.get_width() + 10, 30))
        self.win.blit(text, (10, 10))
        
        # Star indicator
        for i in range(3):
            color = (255, 215, 0) if i < self.p1.stars else (100, 100, 100)
            pygame.draw.circle(self.win, color, (SCREEN_W - 30 - i * 30, 30), 10)
        
        # Remote players
        with remote_lock:
            y_pos = 50
            for pid, remote in remotes.items():
                stats = f"P{pid[:3]}: Lives {remote.lives} Stars {remote.stars}"
                text = self.font.render(stats, True, remote.color)
                self.win.blit(text, (SCREEN_W - text.get_width() - 10, y_pos))
                y_pos += 30

    def draw_game_elements(self):
        self.win.fill(BACKGROUND_COLOR)
        
        # Draw background hills
        for i in range(3):
            hill_color = (90 + i * 20, 160 - i * 15, 230 - i * 10)
            offset_x = (time.time() * (i + 1) * 5) % SCREEN_W
            pygame.draw.ellipse(self.win, hill_color, 
                              pygame.Rect(offset_x - SCREEN_W, SCREEN_H - 100 - i * 30, SCREEN_W, 100 + i * 20))
            pygame.draw.ellipse(self.win, hill_color, 
                              pygame.Rect(offset_x, SCREEN_H - 100 - i * 30, SCREEN_W, 100 + i * 20))
        
        # Draw platforms
        for plat_data in LEVEL:
            color_map = {'solid': (100, 80, 70), 'platform': (60, 180, 90), 
                        'pipeL': (0, 150, 0), 'pipeR': (0, 150, 0)}
            plat_color = color_map.get(plat_data['type'], (150, 150, 150))
            pygame.draw.rect(self.win, plat_color, 
                           (plat_data['x'], plat_data['y'], plat_data['w'], plat_data['h']))
            
            if plat_data['type'] in ['pipeL', 'pipeR']:
                pygame.draw.rect(self.win, (0, 120, 0), 
                               (plat_data['x'], plat_data['y'], plat_data['w'], TILE // 3))
        
        # Draw game objects
        for ib_obj in self.ice_blocks:
            ib_obj.draw(self.win)
            
        self.world_star.draw(self.win)
        
        for coin_obj in self.coins:
            coin_obj.draw(self.win)
            
        for item_obj in self.items:
            item_obj.draw(self.win)
            
        for drop_obj in self.star_drops:
            drop_obj.draw(self.win)
            
        # Draw players
        if not self.p1.dead or self.p1.respawn > 0:
            self.draw_player_visuals(self.win, self.p1)
            
        with remote_lock:
            for pid_key, remote_p_obj in remotes.items():
                if not remote_p_obj.dead or remote_p_obj.respawn > 0:
                    self.draw_player_visuals(self.win, remote_p_obj)
                    
        # Draw projectiles
        for p_data in self.p1.projectiles:
            p_color = (255, 60, 20) if p_data.get('type') == 'fire' else (170, 210, 240)
            pygame.draw.circle(self.win, p_color, (int(p_data['x']), int(p_data['y'])), 
                             7 if p_data.get('type') == 'ice' else 9)
        
        self.draw_hud()

    def draw_menu(self):
        self.win.fill((70, 130, 230))
        
        # Title
        title = self.title_font.render("MARIO LEGACY", True, (255, 255, 255))
        title_shadow = self.title_font.render("MARIO LEGACY", True, (50, 80, 150))
        self.win.blit(title_shadow, (SCREEN_W // 2 - title.get_width() // 2 + 3, 103))
        self.win.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 100))
        
        # Version
        version = self.font.render("2025 PC PORT 1.0A", True, (220, 220, 220))
        self.win.blit(version, (SCREEN_W // 2 - version.get_width() // 2, 160))
        
        # Menu options
        options = ["START GAME", "EXIT"]
        y_pos = 250
        
        for i, option in enumerate(options):
            color = (255, 255, 100) if i == self.menu_selection else (255, 255, 255)
            text = self.big_font.render(option, True, color)
            self.win.blit(text, (SCREEN_W // 2 - text.get_width() // 2, y_pos))
            y_pos += 60
            
        # Player preview
        preview_size = 80
        pygame.draw.rect(self.win, self.p1.color, 
                        (SCREEN_W // 2 - preview_size // 2, 360, preview_size, preview_size * 2), 
                        border_radius=10)
        
        # Instructions
        inst = self.font.render("Use ARROWS to navigate, ENTER to select", True, (200, 200, 255))
        self.win.blit(inst, (SCREEN_W // 2 - inst.get_width() // 2, SCREEN_H - 50))

    def draw_game_over(self):
        self.win.fill((40, 40, 80))
        
        if self.winner_pid == self.p1.pid:
            text = self.title_font.render("VICTORY!", True, (255, 255, 100))
        elif self.winner_pid == "DRAW":
            text = self.title_font.render("DRAW GAME", True, (200, 200, 200))
        else:
            text = self.title_font.render("GAME OVER", True, (255, 100, 100))
            
        self.win.blit(text, (SCREEN_W // 2 - text.get_width() // 2, 150))
        
        score_text = self.big_font.render(f"Final Score: {self.p1.score}", True, (255, 255, 255))
        self.win.blit(score_text, (SCREEN_W // 2 - score_text.get_width() // 2, 250))
        
        restart = self.font.render("Press ENTER to return to menu", True, (200, 255, 200))
        self.win.blit(restart, (SCREEN_W // 2 - restart.get_width() // 2, 350))

    def run(self):
        while self.game_active:
            if self.handle_events():
                break
                
            if self.game_state == "playing":
                self.update_network()
                self.update_game_logic()
                self.draw_game_elements()
            elif self.game_state == "menu":
                self.draw_menu()
            elif self.game_state == "game_over":
                self.draw_game_over()
                
            pygame.display.flip()
            self.clock.tick(FPS)
            
        pygame.quit()
        sys.exit()

# --- Main ---
if __name__ == "__main__":
    pygame.init()
    win = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Mario Legacy! 2025 PC PORT 1.0A")
    game = MarioLegacy(win)
    game.run()

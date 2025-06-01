# test.py
import pygame, socket, threading, json, random, time, sys, math

# --- CONFIG ---
SCREEN_W, SCREEN_H = 800, 480
TILE = 32
FPS = 60
PLAYER_W, PLAYER_H = TILE, TILE*2
GRAVITY = 1.0
JUMP_VEL = -18
RUN_ACC = 2.0
MAX_RUN = 7.5
FRICTION = 1.1
NET_TICK = 0.02
UDP_PORT = 6000
BROADCAST = '<broadcast>'
POWERUPS = ['mushroom', 'fire', 'shell', 'star', 'mini', 'mega']
BACKGROUND_COLOR = (123, 187, 251)
FONT_NAME = 'consolas'

# --- LEVEL DATA ---
LEVEL = [
    # Ground layer
    {'x': 0, 'y': SCREEN_H-TILE, 'w': SCREEN_W, 'h': TILE, 'type': 'solid'},
    # Platforms
    {'x': 120, 'y': 360, 'w': TILE*3, 'h': 16, 'type': 'platform'},
    {'x': 520, 'y': 300, 'w': TILE*3, 'h': 16, 'type': 'platform'},
    {'x': 320, 'y': 210, 'w': TILE*4, 'h': 16, 'type': 'platform'},
    # Pipes for wrap-around
    {'x': -TILE*2, 'y': SCREEN_H-TILE*2, 'w': TILE*2, 'h': TILE*2, 'type': 'pipeL'},
    {'x': SCREEN_W, 'y': SCREEN_H-TILE*2, 'w': TILE*2, 'h': TILE*2, 'type': 'pipeR'},
]

STAR_SPAWNS = [
    (SCREEN_W//2, SCREEN_H//2-80),
    (140, 320), (620, 320),
    (330, 190), (470, 190)
]

COIN_SPAWNS = [
    (170, 328), (630, 328), (350, 178), (450, 178)
]

# --- PLAYER CLASS ---
class Player:
    def __init__(self, pid, color, x, y):
        self.pid = pid
        self.color = color
        self.x, self.y = x, y
        self.vx = self.vy = 0
        self.facing = 1
        self.ground = False
        self.state = 'normal'
        self.power = []
        self.invuln = 0
        self.dead = 0
        self.jumping = False
        self.wall_timer = 0
        self.last_wall = 0
        self.gp = False
        self.shoot_cool = 0
        self.fireballs = []
        self.stars = 0
        self.lives = 3
        self.coins = 0
        self.respawn = 0
        self.score = 0

    def rect(self):
        h = TILE if 'mini' in self.power else (TILE if self.state=='small' else TILE*2)
        w = TILE//2 if 'mini' in self.power else TILE
        return pygame.Rect(int(self.x), int(self.y), w, h)

    def update(self, keys, level, other, items, drops):
        if self.dead or self.respawn: return
        if self.invuln: self.invuln -= 1
        
        # --- Horizontal movement ---
        left = keys.get('left')
        right = keys.get('right')
        run = keys.get('run')
        acc = RUN_ACC * (1.3 if run else 1)
        
        if left:   self.vx -= acc
        if right:  self.vx += acc
        self.facing = -1 if left else (1 if right else self.facing)
        
        if not (left or right):
            self.vx /= FRICTION
            if abs(self.vx) < 0.1: self.vx = 0
        self.vx = max(-MAX_RUN, min(self.vx, MAX_RUN))
        
        # --- Wall jump detection ---
        touching_wall, wall_dir = self.check_wall_collision(level)
        
        # --- Jump ---
        if keys.get('jump'):
            if self.ground:
                self.vy = JUMP_VEL * (1.25 if 'mini' in self.power else 1)
                self.jumping = True
            elif touching_wall and not self.jumping and self.wall_timer==0:
                self.vy = JUMP_VEL * 0.92
                self.vx = 10 * (-wall_dir)
                self.wall_timer = 12
                
        if self.wall_timer: self.wall_timer -= 1
        if not keys.get('jump'): self.jumping = False
        
        # --- Gravity ---
        self.vy += GRAVITY * (0.5 if 'mini' in self.power else 1)
        if self.vy > 18: self.vy = 18
        if self.vy < -25: self.vy = -25
        
        # --- Ground pound ---
        if keys.get('down') and not self.ground and not self.gp:
            self.gp = True
            self.vy = 16
        if self.gp and self.ground:
            self.gp = False
            
        # --- Apply movement ---
        oldx, oldy = self.x, self.y
        self.x += self.vx
        self.y += self.vy
        pr = self.rect()
        
        # --- Collision detection ---
        self.ground = False
        self.handle_collisions(level, oldx, oldy, pr)
        
        # --- Wrap pipes ---
        if self.x < -TILE:  self.x = SCREEN_W-TILE
        if self.x > SCREEN_W: self.x = 0
        
        # --- Fireballs ---
        self.handle_fireballs(keys)
        
        # --- PvP interactions ---
        self.handle_pvp(other, drops, items)
        
        # --- Respawn handling ---
        if self.y > SCREEN_H+TILE*2:
            self.die(items, drops)
            
        # --- End respawn ---
        if self.respawn>0:
            self.respawn -= 1
            if self.respawn==0:
                self.x, self.y = random.choice([(100,50),(600,50),(350,100)])
                self.dead = 0
                self.invuln = 40
                
    def check_wall_collision(self, level):
        touching_wall = False
        wall_dir = 0
        pr = self.rect()
        
        for plat in level:
            r = pygame.Rect(plat['x'], plat['y'], plat['w'], plat['h'])
            if pr.move(2,0).colliderect(r):
                touching_wall = True
                wall_dir = 1
            elif pr.move(-2,0).colliderect(r):
                touching_wall = True
                wall_dir = -1
                
        return touching_wall, wall_dir
        
    def handle_collisions(self, level, oldx, oldy, pr):
        for plat in level:
            platrect = pygame.Rect(plat['x'], plat['y'], plat['w'], plat['h'])
            
            if pr.colliderect(platrect):
                # Collision from above
                if oldy+pr.height <= platrect.y and self.vy >= 0:
                    self.y = platrect.y - pr.height
                    self.vy = 0
                    self.ground = True
                # Collision from right
                elif oldx+pr.width <= platrect.x and self.vx > 0:
                    self.x = platrect.x - pr.width
                    self.vx = 0
                # Collision from left
                elif oldx >= platrect.x+platrect.width and self.vx < 0:
                    self.x = platrect.x + platrect.width
                    self.vx = 0
                # Collision from below
                elif oldy >= platrect.y+platrect.height and self.vy < 0:
                    self.y = platrect.y + platrect.height
                    self.vy = 0
                    
    def handle_fireballs(self, keys):
        if 'fire' in self.power and keys.get('fire') and self.shoot_cool == 0:
            if len(self.fireballs)<2:
                fx = self.x + self.facing*TILE
                fy = self.y + TILE//2
                self.fireballs.append({'x':fx, 'y':fy, 'vx':self.facing*10, 'vy':-2, 'ttl':90})
                self.shoot_cool = 15
                
        if self.shoot_cool: self.shoot_cool -= 1
        
        # Update fireballs
        for f in self.fireballs:
            f['x'] += f['vx']
            f['y'] += f['vy']
            f['vy'] += 0.8
            if f['y']>SCREEN_H-TILE: 
                f['y']=SCREEN_H-TILE
                f['vy']=-7
            f['ttl']-=1
            
        self.fireballs = [f for f in self.fireballs if 0<f['x']<SCREEN_W and f['ttl']>0]
        
    def handle_pvp(self, other, drops, items):
        if other and not self.dead and not other.dead:
            pr = self.rect()
            orc = other.rect()
            
            if pr.colliderect(orc):
                # Stomp attack
                if self.vy > 2 and self.y+pr.height-12 < other.y+8:
                    if other.invuln==0:
                        other.get_hit(self, items, drops, gp=self.gp)
                        self.vy = JUMP_VEL*0.75
                        self.score += 100
                # Ground pound attack
                elif self.gp and self.vy>10:
                    if other.invuln==0:
                        other.get_hit(self, items, drops, gp=True)
                        self.vy = JUMP_VEL*0.65
                        self.score += 200
                        
    def get_hit(self, attacker, items, drops, gp=False):
        if self.invuln: return
        
        if 'star' in attacker.power:
            self.die(items, drops)
            return
            
        if self.state in ('fire','shell'):
            self.state = 'big'
            self.power = [p for p in self.power if p not in ('fire','shell')]
            self.invuln = 60
        elif self.state=='big':
            self.state='small'
            self.invuln=60
        else:
            self.die(items, drops)
            
        # Star drop
        n = 3 if gp else 1
        drops.append({
            'x':self.x+TILE//2, 
            'y':self.y, 
            'n':min(n,self.stars), 
            'vx':random.randint(-5,5),
            'timer': 120
        })
        self.stars = max(0, self.stars-n)
        
    def die(self, items, drops):
        self.dead = 1
        self.lives -= 1
        drops.append({
            'x':self.x+TILE//2, 
            'y':self.y, 
            'n':self.stars, 
            'vx':random.randint(-7,7),
            'timer': 180
        })
        self.stars = 0
        self.respawn = FPS*2
        self.x, self.y = -1000, -1000

# --- NETWORK ---
running = True
remotes = {}
remote_lock = threading.Lock()

def listener(local_id):
    global remotes, running
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', UDP_PORT))
    s.settimeout(1.0)
    
    while running:
        try:
            d, addr = s.recvfrom(4096)
            m = json.loads(d.decode('utf8'))
            pid = m.get('pid')
            if pid==local_id: continue
            
            with remote_lock:
                if pid not in remotes:
                    remotes[pid] = Player(pid, (0,200,0), 100, 50)
                rp = remotes[pid]
                
                # Update attributes
                for k in ('x','y','vx','vy','facing','ground','state','stars','lives','power','dead','invuln','score'):
                    if k in m: setattr(rp, k, m[k])
                    
                rp.fireballs = m.get('fireballs',[])
                rp.respawn = m.get('respawn',0)
                
        except socket.timeout: continue
        except Exception: continue
        
    s.close()

# --- GAME OBJECTS ---
class Star:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.taken = 0
        self.timer = 0
        self.active = True
        
    def update(self, player):
        if not self.taken and self.active:
            srect = pygame.Rect(self.x, self.y, TILE, TILE)
            if player.rect().colliderect(srect):
                self.taken = 1
                player.stars += 1
                self.timer = 60*10
                player.score += 50
        else:
            self.timer -= 1
            if self.timer <= 0:
                self.active = True
                self.taken = 0
                self.x, self.y = random.choice(STAR_SPAWNS)
                
    def draw(self, win):
        if not self.taken and self.active:
            pygame.draw.polygon(win, (255,255,70), [
                (self.x+16, self.y), (self.x+22, self.y+12), (self.x+34, self.y+12),
                (self.x+24, self.y+20), (self.x+28, self.y+32), (self.x+16, self.y+25),
                (self.x+4, self.y+32), (self.x+8, self.y+20), (self.x-2, self.y+12),
                (self.x+10, self.y+12)
            ])

class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.taken = 0
        self.active = True
        self.bounce = 0
        
    def update(self, player):
        self.bounce = (self.bounce + 0.1) % (2 * math.pi)
        if not self.taken and self.active:
            if player.rect().colliderect(pygame.Rect(self.x, self.y, TILE//2, TILE//2)):
                self.taken = 1
                player.coins += 1
                player.score += 10
                
    def draw(self, win):
        if not self.taken and self.active:
            offset = math.sin(self.bounce) * 3
            pygame.draw.circle(win, (255,210,30), (self.x, self.y - offset), TILE//4)

class Item:
    def __init__(self, type, x, y):
        self.type = type
        self.x = x
        self.y = y
        self.active = True
        self.vy = -7
        
    def update(self, player):
        if self.active:
            self.y += self.vy
            self.vy += 0.7
            if self.y > SCREEN_H-TILE: 
                self.y = SCREEN_H-TILE
                self.vy = 0
                
            if self.active and player.rect().colliderect(pygame.Rect(self.x, self.y, TILE, TILE)):
                self.active = False
                player.state = self.type
                if self.type not in player.power: 
                    player.power.append(self.type)
                if self.type=='mini': 
                    player.state='mini'
                if self.type=='mega': 
                    player.state='mega'
                    
    def draw(self, win):
        if self.active:
            colors = {
                'mushroom': (255,0,0),
                'fire': (255,120,0),
                'shell': (70,70,255),
                'star': (200,0,255),
                'mini': (90,255,255),
                'mega': (0,0,0)
            }
            pygame.draw.rect(win, colors.get(self.type, (255,255,255)), 
                            (self.x, self.y, TILE, TILE))

class StarDrop:
    def __init__(self, x, y, n, vx):
        self.x = x
        self.y = y
        self.n = n
        self.vx = vx
        self.timer = 180
        self.vy = -3
        
    def update(self, player):
        self.timer -= 1
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1
        
        if self.n > 0 and abs(self.x - player.x) < 48 and abs(self.y - player.y) < 64:
            player.stars += self.n
            self.n = 0
            player.score += self.n * 5
            
    def draw(self, win):
        if self.n > 0:
            for i in range(self.n):
                x_offset = i * 9
                pygame.draw.polygon(win, (255,255,150), [
                    (self.x-6+x_offset, self.y), 
                    (self.x-4+x_offset, self.y+8), 
                    (self.x+4+x_offset, self.y+8),
                    (self.x-2+x_offset, self.y+14), 
                    (self.x+2+x_offset, self.y+14)
                ])

# --- MAIN GAME ---
class Game:
    def __init__(self):
        pygame.init()
        self.win = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Enhanced Mario Vs Luigi Engine")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(FONT_NAME, 26)
        self.big_font = pygame.font.SysFont(FONT_NAME, 48)
        self.reset_game()
        
    def reset_game(self):
        # Player setup
        self.local_id = str(random.randint(1000,9999))
        color = (200,0,0) if random.randint(0,1) else (0,150,0)
        x = 100 if color==(200,0,0) else 600
        self.p1 = Player(self.local_id, color, x, 50)
        
        # Game objects
        self.drops = []
        self.items = []
        self.star = Star(SCREEN_W//2, 100)
        self.coins = [Coin(x, y) for (x, y) in COIN_SPAWNS]
        self.star_timer = 60*5
        
        # Networking
        global remotes
        with remote_lock:
            remotes = {}
            
        self.running = True
        self.game_over = False
        self.last_send = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Controls
        self.key_map = {
            'left': pygame.K_LEFT, 
            'right': pygame.K_RIGHT, 
            'jump': pygame.K_z, 
            'down': pygame.K_DOWN, 
            'run': pygame.K_LSHIFT, 
            'fire': pygame.K_x
        }
        self.keys = {k: False for k in self.key_map}
        
        # Start network thread
        self.net_thread = threading.Thread(target=listener, args=(self.local_id,), daemon=True)
        self.net_thread.start()
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                self.running = False
                return
                
            if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                val = event.type == pygame.KEYDOWN
                for k, kk in self.key_map.items():
                    if event.key == kk: 
                        self.keys[k] = val
                        
                # Restart game on game over
                if self.game_over and event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    self.reset_game()
                    
    def update_network(self):
        now = time.time()
        if now - self.last_send > NET_TICK:
            self.last_send = now
            msg = {
                'pid': self.local_id, 
                'x': self.p1.x, 'y': self.p1.y, 
                'vx': self.p1.vx, 'vy': self.p1.vy, 
                'facing': self.p1.facing,
                'ground': self.p1.ground, 'state': self.p1.state, 
                'stars': self.p1.stars, 'lives': self.p1.lives,
                'power': self.p1.power, 'fireballs': self.p1.fireballs, 
                'dead': self.p1.dead, 'invuln': self.p1.invuln, 
                'respawn': self.p1.respawn,
                'score': self.p1.score
            }
            try:
                self.sock.sendto(json.dumps(msg).encode('utf8'), (BROADCAST, UDP_PORT))
            except Exception: 
                pass
                
    def update_game_objects(self):
        # Update star
        self.star.update(self.p1)
        
        # Update coins
        for coin in self.coins:
            coin.update(self.p1)
            
        # Coin collection bonus
        if self.p1.coins >= 8:
            self.p1.coins = 0
            self.items.append(Item(random.choice(POWERUPS), self.p1.x+TILE//2, self.p1.y-20))
            
        # Update items
        for item in self.items:
            item.update(self.p1)
        self.items = [item for item in self.items if item.active]
        
        # Update star drops
        for drop in self.drops:
            drop.update(self.p1)
        self.drops = [drop for drop in self.drops if drop.n > 0 and drop.timer > 0]
        
        # Update player
        other = None
        with remote_lock:
            if remotes:
                other = list(remotes.values())[0]
                
        self.p1.update(self.keys, LEVEL, other, self.items, self.drops)
        
    def draw_game(self):
        # Background
        self.win.fill(BACKGROUND_COLOR)
        
        # Level
        for plat in LEVEL:
            c = (100,100,100) if plat['type']=='solid' else (60,200,60)
            pygame.draw.rect(self.win, c, (plat['x'],plat['y'],plat['w'],plat['h']))
        
        # Game objects
        self.star.draw(self.win)
        for coin in self.coins:
            coin.draw(self.win)
        for item in self.items:
            item.draw(self.win)
        for drop in self.drops:
            drop.draw(self.win)
            
        # Players
        pygame.draw.rect(self.win, self.p1.color, self.p1.rect(), border_radius=8)
        
        # Draw remote players
        with remote_lock:
            for pid, rp in remotes.items():
                pygame.draw.rect(self.win, rp.color, rp.rect(), border_radius=8)
                for f in rp.fireballs:
                    pygame.draw.circle(self.win, (255,100,0), (int(f['x']),int(f['y'])), 10)
                    
        # Draw local fireballs
        for f in self.p1.fireballs:
            pygame.draw.circle(self.win, (255,40,10), (int(f['x']),int(f['y'])), 10)
            
        # HUD
        self.draw_hud()
        
        # Invulnerability effect
        if self.p1.invuln: 
            pygame.draw.rect(self.win, (255,255,255), self.p1.rect(), 4)
            
        # Game over screen
        if self.game_over:
            self.draw_game_over()
            
        pygame.display.flip()
        
    def draw_hud(self):
        # Player stats
        stats = f"Stars: {self.p1.stars}   Lives: {self.p1.lives}   Coins: {self.p1.coins}   Score: {self.p1.score}"
        self.win.blit(self.font.render(stats, True, (0,0,0)), (10, 10))
        
        # Remote player stats
        with remote_lock:
            if remotes:
                other = list(remotes.values())[0]
                remote_stats = f"Remote Stars: {other.stars}   Lives: {other.lives}   Score: {other.score}"
                self.win.blit(self.font.render(remote_stats, True, (0,80,0)), (10, 40))
                
    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0,0,0,180))
        self.win.blit(overlay, (0,0))
        
        text = self.big_font.render("GAME OVER", True, (255,50,50))
        restart = self.font.render("Press R to Restart", True, (255,255,255))
        
        self.win.blit(text, (SCREEN_W//2 - text.get_width()//2, SCREEN_H//2 - 50))
        self.win.blit(restart, (SCREEN_W//2 - restart.get_width()//2, SCREEN_H//2 + 20))
        
    def check_game_over(self):
        if self.p1.lives <= 0:
            self.game_over = True
            
    def run(self):
        while self.running:
            self.handle_events()
            if not self.running:
                break
                
            if not self.game_over:
                self.update_network()
                self.update_game_objects()
                self.check_game_over()
                
            self.draw_game()
            self.clock.tick(FPS)
            
        # Cleanup
        global running
        running = False
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()

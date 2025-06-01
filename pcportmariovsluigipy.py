
# test.py
import pygame, socket, threading, json, random, time, sys, math

# --- CONFIG ---
SCREEN_W, SCREEN_H = 800, 480
TILE = 32
FPS = 60
PLAYER_W, PLAYER_H = TILE, TILE*2   # Super size
GRAVITY = 1.0
JUMP_VEL = -18
RUN_ACC = 2.0
MAX_RUN = 7.5
FRICTION = 1.1
NET_TICK = 0.02
UDP_PORT = 6000
BROADCAST = '<broadcast>'
POWERUPS = ['mushroom', 'fire', 'shell', 'star', 'mini', 'mega']

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
        self.state = 'normal' # or: big, fire, shell, star, mini, mega
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

    def rect(self):
        h = TILE if 'mini' in self.power else (TILE if self.state=='small' else TILE*2)
        w = TILE//2 if 'mini' in self.power else TILE
        return pygame.Rect(int(self.x), int(self.y), w, h)

    def update(self, keys, level, other, items, drops):
        if self.dead or self.respawn: return
        if self.invuln: self.invuln -= 1
        # --- Horizontal movement
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
        # --- Wall jump: check if against wall, allow for a small window
        touching_wall = False
        wall_dir = 0
        for plat in level:
            r = pygame.Rect(plat['x'], plat['y'], plat['w'], plat['h'])
            pr = self.rect()
            if pr.move(2,0).colliderect(r):
                touching_wall = True
                wall_dir = 1
            elif pr.move(-2,0).colliderect(r):
                touching_wall = True
                wall_dir = -1
        # --- Jump
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
        # --- Gravity
        self.vy += GRAVITY * (0.5 if 'mini' in self.power else 1)
        if self.vy > 18: self.vy = 18
        if self.vy < -25: self.vy = -25
        # --- Ground pound
        if keys.get('down') and not self.ground and not self.gp:
            self.gp = True
            self.vy = 16
        if self.gp and self.ground:
            self.gp = False
        # --- Apply movement
        oldx, oldy = self.x, self.y
        self.x += self.vx
        self.y += self.vy
        pr = self.rect()
        # --- Collision (ground/platform)
        self.ground = False
        for plat in level:
            platrect = pygame.Rect(plat['x'], plat['y'], plat['w'], plat['h'])
            # X axis
            if pr.colliderect(platrect):
                if oldy+pr.height <= platrect.y and self.vy >= 0:  # Falling on top
                    self.y = platrect.y - pr.height
                    self.vy = 0
                    self.ground = True
                elif oldx+pr.width <= platrect.x and self.vx > 0:
                    self.x = platrect.x - pr.width
                    self.vx = 0
                elif oldx >= platrect.x+platrect.width and self.vx < 0:
                    self.x = platrect.x + platrect.width
                    self.vx = 0
                elif oldy >= platrect.y+platrect.height and self.vy < 0:
                    self.y = platrect.y + platrect.height
                    self.vy = 0
        # --- Wrap pipes
        if self.x < -TILE:  self.x = SCREEN_W-TILE
        if self.x > SCREEN_W: self.x = 0
        # --- Fireballs (if fire mode)
        if 'fire' in self.power and keys.get('fire') and self.shoot_cool == 0:
            if len(self.fireballs)<2:
                fx = self.x + self.facing*TILE
                fy = self.y + TILE//2
                self.fireballs.append({'x':fx, 'y':fy, 'vx':self.facing*10, 'vy':-2, 'ttl':90})
                self.shoot_cool = 15
        if self.shoot_cool: self.shoot_cool -= 1
        # --- Update fireballs
        for f in self.fireballs:
            f['x'] += f['vx']
            f['y'] += f['vy']
            f['vy'] += 0.8
            if f['y']>SCREEN_H-TILE: f['y']=SCREEN_H-TILE; f['vy']=-7
            f['ttl']-=1
        self.fireballs = [f for f in self.fireballs if 0<f['x']<SCREEN_W and f['ttl']>0]
        # --- PvP stomp / ground pound
        if other and not self.dead and not other.dead:
            orc = other.rect()
            if pr.colliderect(orc):
                if self.vy > 2 and self.y+pr.height-12 < other.y+8:  # Stomp
                    if other.invuln==0:
                        other.get_hit(self, items, drops, gp=self.gp)
                        self.vy = JUMP_VEL*0.75
                elif self.gp and self.vy>10: # Ground pound
                    if other.invuln==0:
                        other.get_hit(self, items, drops, gp=True)
                        self.vy = JUMP_VEL*0.65
        # --- Respawn handling
        if self.y > SCREEN_H+TILE*2:
            self.die(items, drops)
        # --- End respawn
        if self.respawn>0:
            self.respawn -= 1
            if self.respawn==0:
                self.x, self.y = random.choice([(100,50),(600,50),(350,100)])
                self.dead = 0
                self.invuln = 40
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
        drops.append({'x':self.x+TILE//2, 'y':self.y, 'n':min(n,self.stars), 'vx':random.randint(-5,5)})
        self.stars = max(0, self.stars-n)
    def die(self, items, drops):
        self.dead = 1
        self.lives -= 1
        drops.append({'x':self.x+TILE//2, 'y':self.y, 'n':self.stars, 'vx':random.randint(-7,7)})
        self.stars = 0
        self.respawn = FPS*2
        self.x, self.y = -1000, -1000  # Offscreen

# --- NETWORK ---
running = True
remotes = {}
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
            if pid not in remotes:
                remotes[pid] = Player(pid, (0,200,0), 100, 50)
            rp = remotes[pid]
            for k in ('x','y','vx','vy','facing','ground','state','stars','lives','power','dead','invuln'):
                if k in m: setattr(rp, k, m[k])
            rp.fireballs = m.get('fireballs',[])
            rp.respawn = m.get('respawn',0)
        except socket.timeout: continue
        except Exception: continue
    s.close()

# --- MAIN LOOP ---
def main():
    global running, remotes
    pygame.init()
    win = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Zero-Shot Mario Vs Luigi Engine - CatSDK Edition")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('consolas', 26)
    # --- Multiplayer setup
    local_id = str(random.randint(1000,9999))
    color = (200,0,0) if random.randint(0,1) else (0,150,0)
    x = 100 if color==(200,0,0) else 600
    p1 = Player(local_id, color, x, 50)
    drops = []
    items = []
    remote_id = None
    # --- Networking
    t = threading.Thread(target=listener, args=(local_id,), daemon=True)
    t.start()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    last_send = 0
    # --- Controls
    key_map = {'left':pygame.K_LEFT, 'right':pygame.K_RIGHT, 'jump':pygame.K_z, 'down':pygame.K_DOWN, 'run':pygame.K_LSHIFT, 'fire':pygame.K_x}
    keys = {k:False for k in key_map}
    # --- Star spawn
    star_timer = 60*5
    star = {'x':SCREEN_W//2, 'y':100, 'taken':0}
    # --- Coins
    coins = [{'x':x,'y':y,'taken':0} for (x,y) in COIN_SPAWNS]
    # --- Main
    while running:
        dt = clock.tick(FPS)
        # --- Input
        for event in pygame.event.get():
            if event.type==pygame.QUIT: running=False
            if event.type==pygame.KEYDOWN or event.type==pygame.KEYUP:
                val = event.type==pygame.KEYDOWN
                for k,kk in key_map.items():
                    if event.key==kk: keys[k]=val
        # --- Star respawn
        if not star['taken']:
            srect = pygame.Rect(star['x'], star['y'], TILE, TILE)
            if p1.rect().colliderect(srect):
                star['taken']=1
                p1.stars += 1
                star_timer = 60*10
        else:
            star_timer -= 1
            if star_timer<=0:
                sx,sy = random.choice(STAR_SPAWNS)
                star = {'x':sx, 'y':sy, 'taken':0}
        # --- Coin collect
        for c in coins:
            if not c['taken'] and p1.rect().colliderect(pygame.Rect(c['x'],c['y'],TILE//2,TILE//2)):
                c['taken']=1
                p1.coins+=1
                if p1.coins>=8:
                    p1.coins=0
                    # Drop a random item
                    px,py = p1.x+TILE//2,p1.y-20
                    items.append({'type':random.choice(POWERUPS),'x':px,'y':py,'active':1,'vy':-7})
        # --- Item pickup
        for it in items:
            if it['active'] and p1.rect().colliderect(pygame.Rect(it['x'],it['y'],TILE,TILE)):
                it['active']=0
                p1.state = it['type']
                if it['type'] not in p1.power: p1.power.append(it['type'])
                if it['type']=='mini': p1.state='mini'
                if it['type']=='mega': p1.state='mega'
        # --- Gravity on items
        for it in items:
            if it['active']:
                it['y']+=it.get('vy',0)
                it['vy']=it.get('vy',0)+0.7
                if it['y']>SCREEN_H-TILE: it['y']=SCREEN_H-TILE; it['vy']=0
        # --- Star drop pickup
        for d in drops:
            if d['n']>0 and abs(d['x']-p1.x)<48 and abs(d['y']-p1.y)<64:
                p1.stars += d['n']
                d['n']=0
        drops = [d for d in drops if d['n']>0]
        # --- PvP
        other = None
        if remotes:
            other = list(remotes.values())[0]
        p1.update(keys, LEVEL, other, items, drops)
        if other: other.update({}, LEVEL, p1, items, drops)
        # --- Send network state
        now = time.time()
        if now-last_send>NET_TICK:
            last_send=now
            msg = {'pid':local_id, 'x':p1.x, 'y':p1.y, 'vx':p1.vx, 'vy':p1.vy, 'facing':p1.facing,
                   'ground':p1.ground, 'state':p1.state, 'stars':p1.stars, 'lives':p1.lives,
                   'power':p1.power, 'fireballs':p1.fireballs, 'dead':p1.dead, 'invuln':p1.invuln, 'respawn':p1.respawn}
            try:
                sock.sendto(json.dumps(msg).encode('utf8'), (BROADCAST, UDP_PORT))
            except Exception: pass
        # --- Draw ---
        win.fill((123,187,251))
        # Level
        for plat in LEVEL:
            c = (100,100,100) if plat['type']=='solid' else (60,200,60)
            pygame.draw.rect(win, c, (plat['x'],plat['y'],plat['w'],plat['h']))
        # Star
        if not star['taken']:
            pygame.draw.polygon(win, (255,255,70), [(star['x']+16,star['y']),
                                                    (star['x']+22,star['y']+12),
                                                    (star['x']+34,star['y']+12),
                                                    (star['x']+24,star['y']+20),
                                                    (star['x']+28,star['y']+32),
                                                    (star['x']+16,star['y']+25),
                                                    (star['x']+4,star['y']+32),
                                                    (star['x']+8,star['y']+20),
                                                    (star['x']-2,star['y']+12),
                                                    (star['x']+10,star['y']+12)])
        # Coins
        for c in coins:
            if not c['taken']:
                pygame.draw.circle(win, (255,210,30), (c['x'],c['y']), TILE//4)
        # Items
        for it in items:
            if it['active']:
                col = (255,0,0) if it['type']=='mushroom' else (255,120,0) if it['type']=='fire' else (70,70,255) if it['type']=='shell' else (200,0,255) if it['type']=='star' else (90,255,255) if it['type']=='mini' else (0,0,0)
                pygame.draw.rect(win, col, (it['x'],it['y'],TILE,TILE))
        # Drops
        for d in drops:
            if d['n']>0:
                for i in range(d['n']):
                    pygame.draw.polygon(win, (255,255,150), [(d['x']-6+i*9,d['y']),(d['x']-4+i*9,d['y']+8),(d['x']+4+i*9,d['y']+8),(d['x']-2+i*9,d['y']+14),(d['x']+2+i*9,d['y']+14)])
        # Players
        pygame.draw.rect(win, p1.color, p1.rect(), border_radius=8)
        if other:
            pygame.draw.rect(win, other.color, other.rect(), border_radius=8)
            for f in other.fireballs:
                pygame.draw.circle(win, (255,100,0), (int(f['x']),int(f['y'])), 10)
        # Fireballs (local)
        for f in p1.fireballs:
            pygame.draw.circle(win, (255,40,10), (int(f['x']),int(f['y'])), 10)
        # HUD
        win.blit(font.render(f"Stars: {p1.stars}   Lives: {p1.lives}   Coins: {p1.coins}   Power: {','.join(p1.power)}",1,(0,0,0)),(10,10))
        if other:
            win.blit(font.render(f"Remote Stars: {other.stars}   Lives: {other.lives}   Power: {','.join(other.power)}",1,(0,80,0)),(10,40))
        if p1.invuln: pygame.draw.rect(win,(255,255,255),p1.rect(),4)
        pygame.display.flip()
    # --- Cleanup ---
    running=False
    pygame.quit()
    sys.exit()

if __name__=="__main__":
    main()

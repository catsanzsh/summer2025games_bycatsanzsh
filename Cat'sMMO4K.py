# test.py

import pygame
import socket
import threading
import json
import random
import time
import sys

# -----------------------------------------------------------------------------
# CONFIGURATION CONSTANTS
# -----------------------------------------------------------------------------

SCREEN_WIDTH   = 640
SCREEN_HEIGHT  = 480
PLAYER_WIDTH   = 32
PLAYER_HEIGHT  = 32
GRAVITY        = 0.5
JUMP_SPEED     = -10
MOVE_SPEED     = 5

UDP_PORT       = 5000          # UDP port for P2P broadcasts
BROADCAST_ADDR = '<broadcast>' # Use broadcast address for LAN

NETWORK_TICK   = 0.05          # Seconds between sending state updates

# -----------------------------------------------------------------------------
# PLAYER CLASS
# -----------------------------------------------------------------------------

class Player:
    def __init__(self, player_id, x, y):
        self.player_id = player_id
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.on_ground = False

    def update(self, keys_pressed, platforms):
        # Horizontal movement
        if keys_pressed.get("left", False):
            self.vx = -MOVE_SPEED
        elif keys_pressed.get("right", False):
            self.vx = MOVE_SPEED
        else:
            self.vx = 0

        # Jump
        if keys_pressed.get("jump", False) and self.on_ground:
            self.vy = JUMP_SPEED
            self.on_ground = False

        # Apply gravity
        self.vy += GRAVITY

        # Update position
        self.x += self.vx
        self.y += self.vy

        # Collision detection with platforms
        self.on_ground = False
        for platform in platforms:
            px, py, pw, ph = platform
            if (self.x + PLAYER_WIDTH > px and
                self.x < px + pw and
                self.y + PLAYER_HEIGHT > py and
                self.y < py + ph):
                # Collision detected; if falling, place on top
                if self.vy > 0:
                    self.y = py - PLAYER_HEIGHT
                    self.vy = 0
                    self.on_ground = True

        # Keep inside screen
        if self.x < 0:
            self.x = 0
        elif self.x + PLAYER_WIDTH > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - PLAYER_WIDTH
        if self.y < 0:
            self.y = 0
            self.vy = 0
        elif self.y + PLAYER_HEIGHT > SCREEN_HEIGHT:
            self.y = SCREEN_HEIGHT - PLAYER_HEIGHT
            self.vy = 0
            self.on_ground = True

    def to_dict(self):
        return {
            "player_id": self.player_id,
            "x": self.x,
            "y": self.y,
            "vx": self.vx,
            "vy": self.vy
        }

    def from_dict(self, data):
        self.x = data["x"]
        self.y = data["y"]
        self.vx = data["vx"]
        self.vy = data["vy"]

# -----------------------------------------------------------------------------
# RENDERING FUNCTIONS
# -----------------------------------------------------------------------------

def draw_player(screen, player):
    rect = pygame.Rect(int(player.x), int(player.y), PLAYER_WIDTH, PLAYER_HEIGHT)
    pygame.draw.rect(screen, (255, 0, 0), rect)

def draw_platforms(screen, platforms):
    for p in platforms:
        pygame.draw.rect(screen, (0, 180, 0), p)

# -----------------------------------------------------------------------------
# NETWORKING (UDP BROADCAST LISTENER)
# -----------------------------------------------------------------------------

running = True
remote_players = {}  # key: player_id, value: Player instance

def network_listener(local_id):
    """
    Listens on UDP_PORT for broadcasted state updates.
    Updates remote_players dict when new data is received.
    """
    global running, remote_players

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind to all interfaces on UDP_PORT to receive broadcasts
    sock.bind(('', UDP_PORT))
    sock.settimeout(1.0)

    while running:
        try:
            data, addr = sock.recvfrom(1024)
            try:
                message = json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            if message.get("type") != "update":
                continue

            pid = message.get("player_id")
            if pid is None or pid == local_id:
                continue  # ignore malformed or own messages

            pstate = message.get("state", {})
            x = pstate.get("x"); y = pstate.get("y")
            vx = pstate.get("vx"); vy = pstate.get("vy")
            if x is None or y is None or vx is None or vy is None:
                continue

            # If new player, spawn at given coordinates
            if pid not in remote_players:
                new_player = Player(pid, x, y)
                new_player.vx = vx
                new_player.vy = vy
                remote_players[pid] = new_player
            else:
                remote_players[pid].from_dict(pstate)

        except socket.timeout:
            continue
        except Exception:
            continue

    sock.close()

# -----------------------------------------------------------------------------
# MAIN GAME LOGIC
# -----------------------------------------------------------------------------

def main():
    global running, remote_players

    # Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("P2P Mario-Style Game")
    clock = pygame.time.Clock()

    # Platforms (x, y, width, height)
    platforms = [
        (0, SCREEN_HEIGHT - 40, SCREEN_WIDTH, 40),  # ground
        (100, 300, 100, 10),
        (300, 200, 150, 10)
    ]

    # Keys pressed state
    keys_pressed = {"left": False, "right": False, "jump": False}

    # Generate a random ID for this player
    local_id = str(random.randint(1000, 9999))
    # Spawn local player near top
    local_player = Player(local_id,
                          random.randint(0, SCREEN_WIDTH - PLAYER_WIDTH),
                          50)

    # Start network listener thread
    listener_thread = threading.Thread(target=network_listener, args=(local_id,), daemon=True)
    listener_thread.start()

    # Setup UDP socket for broadcasting state
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    last_network_send = 0.0

    # Main loop
    while running:
        dt = clock.tick(60) / 1000.0  # Delta time in seconds

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    keys_pressed["left"] = True
                elif event.key == pygame.K_RIGHT:
                    keys_pressed["right"] = True
                elif event.key == pygame.K_SPACE:
                    keys_pressed["jump"] = True

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    keys_pressed["left"] = False
                elif event.key == pygame.K_RIGHT:
                    keys_pressed["right"] = False
                elif event.key == pygame.K_SPACE:
                    keys_pressed["jump"] = False

        # Update local player physics
        local_player.update(keys_pressed, platforms)

        # Broadcast local player state at fixed intervals
        now = time.time()
        if now - last_network_send >= NETWORK_TICK:
            last_network_send = now
            message = {
                "type": "update",
                "player_id": local_id,
                "state": local_player.to_dict()
            }
            try:
                send_sock.sendto(json.dumps(message).encode('utf-8'),
                                 (BROADCAST_ADDR, UDP_PORT))
            except Exception:
                pass

        # Rendering
        screen.fill((135, 206, 235))  # sky blue
        draw_platforms(screen, platforms)
        draw_player(screen, local_player)

        # Draw remote players
        for pid, rp in list(remote_players.items()):
            draw_player(screen, rp)

        pygame.display.flip()

    # Cleanup
    send_sock.close()
    running = False
    listener_thread.join(timeout=1.0)
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

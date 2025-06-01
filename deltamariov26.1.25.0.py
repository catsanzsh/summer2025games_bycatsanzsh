from ursina import *
import time as pytime  # for precise timing (used in jump combo logic)
import cProfile  # for profiling performance

# Initialize Ursina app with optimizations
app = Ursina(vsync=False, size=(800, 600))  # Disable VSync for uncapped FPS, lower resolution for performance
window.title = "Super Mario 64 Recreation"
# window.fullscreen = True  # (Optionally enable fullscreen after testing)
window.fps_counter.enabled = True  # Show FPS counter for performance monitoring

# Constants and tuning parameters
MOVE_SPEED       = 8.0    # maximum running speed on ground
ACCELERATION     = 15.0   # how quickly Mario accelerates to MOVE_SPEED
FRICTION         = 10.0   # how quickly Mario decelerates when not pressing movement
AIR_CONTROL      = 4.0    # horizontal acceleration factor in air (less than on ground)
GRAVITY          = 8.0    # gravity strength (units/sec^2)
JUMP_VELOCITY    = 7.0    # initial jump velocity for normal jump
DOUBLE_JUMP_VEL  = 8.5    # initial jump velocity for double jump (higher)
TRIPLE_JUMP_VEL  = 10.0   # initial jump velocity for triple jump (highest)
LONG_JUMP_VEL    = 6.0    # initial upward velocity for long jump (lower arc)
LONG_JUMP_SPEED  = 12.0   # horizontal speed boost during long jump
BACKFLIP_VEL     = 10.0   # initial upward velocity for backflip (high jump)
WALL_KICK_VEL    = 7.5    # initial upward velocity for wall kick jump
WALL_KICK_PUSH   = 6.5    # horizontal push speed for wall kick (away from wall)
GROUND_POUND_VEL = -20.0  # downward velocity for ground pound
JUMP_COMBO_TIME  = 0.5    # max time (seconds) between consecutive jumps in a combo

# Player (Mario) entity setup
class Mario(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use low-poly Mario model and appropriate scale
        self.model = 'mario'            # ensure 'mario.obj' is low-poly
        self.texture = 'mario_texture'  # texture if available
        self.scale_y = 1.0
        self.origin_y = -0.5            # pivot at feet for easier handling
        self.collider = 'box'           # simple collider for physics

        # Movement state
        self.velocity = Vec3(0, 0, 0)   # (vx, vy, vz) in world space
        self.grounded = False
        self.jump_count = 0            # 0=none, 1=single, 2=double, 3=triple performed
        self.last_jump_time = 0.0      # time of last jump press
        self.crouching = False
        self.long_jump_active = False  # True when performing a long jump

    def update(self):
        # Handle horizontal movement input
        move_input = Vec3(0, 0, 0)
        dir_forward = Vec3(camera.forward.x, 0, camera.forward.z).normalized()
        dir_right   = Vec3(camera.right.x,   0, camera.right.z).normalized()
        move_input += dir_forward * (held_keys['w'] - held_keys['s'])
        move_input += dir_right   * (held_keys['d'] - held_keys['a'])

        # Apply acceleration or friction based on input
        if move_input.length() > 0:
            move_dir = move_input.normalized()
            accel = ACCELERATION if self.grounded else AIR_CONTROL
            target_vel = move_dir * MOVE_SPEED
            self.velocity.x = lerp(self.velocity.x, target_vel.x, accel * time.dt)
            self.velocity.z = lerp(self.velocity.z, target_vel.z, accel * time.dt)

            # Rotate Mario to face move direction
            target_yaw = math.degrees(math.atan2(move_dir.x, move_dir.z))
            self.rotation_y = lerp_angle(self.rotation_y, target_yaw, 10 * time.dt)
        else:
            if self.grounded:
                self.velocity.x = lerp(self.velocity.x, 0, FRICTION * time.dt)
                self.velocity.z = lerp(self.velocity.z, 0, FRICTION * time.dt)

        # Maintain long jump forward speed
        if self.long_jump_active and not self.grounded:
            forward_vec = Vec3(math.sin(math.radians(self.rotation_y)), 0, math.cos(math.radians(self.rotation_y))).normalized()
            self.velocity.x = forward_vec.x * LONG_JUMP_SPEED
            self.velocity.z = forward_vec.z * LONG_JUMP_SPEED
        elif self.grounded:
            self.long_jump_active = False

        # Horizontal collision detection
        if abs(self.velocity.x) > 1e-3 or abs(self.velocity.z) > 1e-3:
            move_direction = Vec3(self.velocity.x, 0, self.velocity.z) * time.dt
            ray_origin = self.position + Vec3(0, 0.5, 0)
            hit_info = raycast(ray_origin, move_direction.normalized(), distance=move_direction.length() + 0.1, ignore=(self,), debug=False)
            if hit_info.hit and hit_info.world_normal.y < 0.7:
                wall_normal = Vec3(hit_info.world_normal.x, 0, hit_info.world_normal.z).normalized()
                horizontal_vel = Vec3(self.velocity.x, 0, self.velocity.z)
                normal_comp = horizontal_vel.dot(wall_normal)
                horizontal_vel -= wall_normal * normal_comp
                self.velocity.x = horizontal_vel.x
                self.velocity.z = horizontal_vel.z
            self.position += Vec3(self.velocity.x, 0, self.velocity.z) * time.dt

        # Vertical movement and ground collision
        self.velocity.y -= GRAVITY * time.dt

        if self.velocity.y < 0:  # Falling
            fall_distance = abs(self.velocity.y * time.dt)
            ray_start = self.position + Vec3(0, 0.1, 0)
            hit_info = raycast(ray_start, Vec3(0, -1, 0), distance=fall_distance + 0.2, ignore=(self,), debug=False)
            if hit_info.hit:
                self.y = hit_info.world_point.y
                self.velocity.y = 0
                self.grounded = True
                self.long_jump_active = False
            else:
                self.position.y += self.velocity.y * time.dt
                self.grounded = False
        elif self.velocity.y > 0:  # Jumping
            self.position.y += self.velocity.y * time.dt
            hit_info = raycast(self.position, Vec3(0, 1, 0), distance=0.1, ignore=(self,), debug=False)
            if hit_info.hit and hit_info.world_normal.y < 0.1:
                self.velocity.y = 0
            self.grounded = False

    def input(self, key):
        # Crouch input
        if key in ('left shift', 'right shift', 'control', 'left control'):
            if self.grounded:
                self.crouching = True
        elif key in ('left shift up', 'right shift up', 'control up', 'left control up'):
            self.crouching = False

        # Jump input
        if key == 'space':
            if self.grounded:
                current_time = pytime.time()
                if current_time - self.last_jump_time > JUMP_COMBO_TIME:
                    self.jump_count = 0
                if self.crouching:
                    move_horiz = Vec3(self.velocity.x, 0, self.velocity.z).length()
                    if move_horiz > 1e-2:
                        # Long jump
                        self.velocity.y = LONG_JUMP_VEL
                        self.long_jump_active = True
                        self.grounded = False
                        self.jump_count = 0
                        self.last_jump_time = current_time
                    else:
                        # Backflip
                        self.velocity.y = BACKFLIP_VEL
                        self.velocity.x = -math.sin(math.radians(self.rotation_y)) * 5.0
                        self.velocity.z = -math.cos(math.radians(self.rotation_y)) * 5.0
                        self.grounded = False
                        self.jump_count = 0
                        self.last_jump_time = current_time
                else:
                    # Normal jump sequence
                    if self.jump_count == 0:
                        self.velocity.y = JUMP_VELOCITY
                        self.jump_count = 1
                    elif self.jump_count == 1:
                        self.velocity.y = DOUBLE_JUMP_VEL
                        self.jump_count = 2
                    elif self.jump_count == 2:
                        self.velocity.y = TRIPLE_JUMP_VEL
                        self.jump_count = 0
                    self.grounded = False
                    self.last_jump_time = current_time
            else:
                # Wall kick
                wall_check = raycast(self.position + Vec3(0, 0.5, 0), Vec3(self.velocity.x, 0, self.velocity.z).normalized(), distance=0.6, ignore=(self,))
                if wall_check.hit and wall_check.world_normal.y < 0.7:
                    normal = Vec3(wall_check.world_normal.x, 0, wall_check.world_normal.z).normalized()
                    self.velocity.y = WALL_KICK_VEL
                    self.velocity.x = -normal.x * WALL_KICK_PUSH
                    self.velocity.z = -normal.z * WALL_KICK_PUSH
                    self.jump_count = 0
                    self.grounded = False
                    target_yaw = math.degrees(math.atan2(-normal.x, -normal.z))
                    self.rotation_y = target_yaw

# Create Mario entity
player = Mario(position=(0, 0, 0))

# Camera setup: third-person
camera.parent = player
camera.position = Vec3(0, 2.5, -7)
camera.rotation_x = 20
camera.rotation_y = 0
camera.rotation_z = 0

# Level setup: simple ground for testing
ground = Entity(model='plane', texture='white_cube', color=color.light_gray, collider='box', scale=(50, 1, 50), position=(0, -1, 0))
# Note: For actual level, use a single low-poly mesh, e.g., level = Entity(model='level_mesh', collider='mesh', scale=1)

# Lighting
directional_light = DirectionalLight(y=2, rotation=(45, -45, 45))
directional_light.color = color.white

# Sky
sky = Sky(color=color.cyan)

# Run the game with profiling
if __name__ == "__main__":
    cProfile.run("app.run()", sort="time")  # Profile to identify bottlenecks

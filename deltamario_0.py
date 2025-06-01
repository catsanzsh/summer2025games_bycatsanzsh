from ursina import *  
import time as pytime  # for precise timing (used in jump combo logic)

# Initialize Ursina app
app = Ursina()  
window.title = "Super Mario 64 Recreation"  
# window.fullscreen = True  # (Optionally enable fullscreen)  
# window.fps_counter.enabled = False  # Hide FPS counter if not needed  

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
GROUND_POUND_VEL = -20.0  # downward velocity for ground pound (if implemented)  
JUMP_COMBO_TIME  = 0.5    # max time (seconds) between consecutive jumps in a combo  

# Player (Mario) entity setup
class Mario(Entity):  
    def __init__(self, **kwargs):  
        super().__init__(**kwargs)  
        # Use low-poly Mario model and appropriate scale  
        self.model = 'mario'            # ensure 'mario.obj' or equivalent is in assets  
        self.texture = 'mario_texture'  # texture if available  
        self.scale_y = 1.0  
        self.origin_y = -0.5            # pivot at feet for easier handling  
        self.collider = 'box'           # simple collider for physics (approximate Mario's body)  

        # Movement state  
        self.velocity = Vec3(0, 0, 0)   # (vx, vy, vz) in world space  
        self.grounded = False  
        self.jump_count = 0            # 0=none, 1=single, 2=double, 3=triple performed  
        self.last_jump_time = 0.0      # time of last jump press  
        self.crouching = False  
        self.long_jump_active = False  # True when performing a long jump (for horizontal boost)  

    def update(self):  
        # Handle horizontal movement input  
        move_input = Vec3(0, 0, 0)  
        # Use camera-relative directions for movement on XZ plane  
        dir_forward = Vec3(camera.forward.x, 0, camera.forward.z).normalized()  
        dir_right   = Vec3(camera.right.x,   0, camera.right.z).normalized()  
        # get input axis from WASD/arrow keys  
        move_input += dir_forward * (held_keys['w'] - held_keys['s'])  
        move_input += dir_right   * (held_keys['d'] - held_keys['a'])  

        # Check if Mario is on the ground  
        # (Ground check via raycast downward – done later after moving vertically)  

        # Apply acceleration or friction based on input  
        if move_input.length() > 0:  
            move_dir = move_input.normalized()  
            # If on ground, accelerate faster; if in air, use reduced control  
            accel = ACCELERATION if self.grounded else AIR_CONTROL  
            # Gradually adjust velocity.xz toward target direction * max speed  
            target_vel = move_dir * MOVE_SPEED  
            self.velocity.x = lerp(self.velocity.x, target_vel.x, accel * time.dt)  
            self.velocity.z = lerp(self.velocity.z, target_vel.z, accel * time.dt)  

            # Rotate Mario to face move direction  
            # Compute target yaw from move direction vector  
            target_yaw = math.degrees(math.atan2(move_dir.x, move_dir.z))  
            # Smoothly rotate towards target_yaw  
            self.rotation_y = lerp_angle(self.rotation_y, target_yaw, 10 * time.dt)  
        else:  
            # No input: apply friction (only on ground) to gradually stop  
            if self.grounded:  
                self.velocity.x = lerp(self.velocity.x, 0, FRICTION * time.dt)  
                self.velocity.z = lerp(self.velocity.z, 0, FRICTION * time.dt)  
            # In air, if no input, we leave horizontal velocity mostly unchanged (minor air drag can be added if needed)  
            # self.velocity.x, self.velocity.z could be slightly reduced for air drag, but not necessary for now  

        # If a long jump is active, maintain its forward speed  
        if self.long_jump_active:  
            # In long jump, we give Mario a constant forward boost in the direction he's facing  
            # Ensure we only apply while in air after the jump  
            if not self.grounded:  
                forward_vec = Vec3(math.sin(math.radians(self.rotation_y)), 0, math.cos(math.radians(self.rotation_y)))  
                forward_vec = forward_vec.normalized()  
                self.velocity.x = forward_vec.x * LONG_JUMP_SPEED  
                self.velocity.z = forward_vec.z * LONG_JUMP_SPEED  
            else:  
                # Landed, long jump ends  
                self.long_jump_active = False  

        # Horizontal collision detection (using raycast)  
        # Cast a ray in the direction of intended movement to see if a wall is hit  
        if abs(self.velocity.x) > 1e-3 or abs(self.velocity.z) > 1e-3:  
            move_direction = Vec3(self.velocity.x, 0, self.velocity.z) * time.dt  
            ray_origin = self.position + Vec3(0, 0.5, 0)  # a bit above ground to detect walls  
            hit_info = raycast(ray_origin, move_direction.normalized(), distance=move_direction.length() + 0.1, ignore=(self,), debug=False)  
            if hit_info.hit:  
                # Check if the hit is essentially a wall (surface normal mostly horizontal)  
                if hit_info.world_normal.y < 0.7:  # normal not pointing significantly up -> treat as wall  
                    # Slide along wall: remove component of velocity into the wall  
                    wall_normal = Vec3(hit_info.world_normal.x, 0, hit_info.world_normal.z).normalized()  
                    # Project horizontal velocity onto wall normal  
                    horizontal_vel = Vec3(self.velocity.x, 0, self.velocity.z)  
                    # Compute component in direction of wall normal  
                    normal_comp = horizontal_vel.dot(wall_normal)  
                    # Subtract that component  
                    horizontal_vel -= wall_normal * normal_comp  
                    self.velocity.x = horizontal_vel.x  
                    self.velocity.z = horizontal_vel.z  
                # (If the surface is a steep slope or wall, the above handles it. If it's a gentle slope, the ray might not hit due to origin offset.)  
            # Move horizontally after adjusting for collisions  
            self.position += Vec3(self.velocity.x, 0, self.velocity.z) * time.dt  
        else:  
            # No horizontal movement, no need to check collisions; just ensure position stays  
            # (We still perform vertical movement below.)  
            pass  

        # Vertical movement and ground collision  
        # Apply gravity  
        self.velocity.y -= GRAVITY * time.dt  

        # If Mario is performing a ground pound (not implemented fully), increase downward velocity  
        # (Ground pound trigger could be: if crouch pressed in air, set self.velocity.y = -GROUND_POUND_VEL)  

        # Move vertically with collision check  
        # Cast a ray down from the current position to detect the ground below  
        if self.velocity.y < 0:  # Falling downward  
            # Calculate how far down we intend to move this frame  
            fall_distance = abs(self.velocity.y * time.dt)  
            ray_start = self.position + Vec3(0, 0.1, 0)  # a little above current position  
            hit_info = raycast(ray_start, Vec3(0, -1, 0), distance=fall_distance + 0.2, ignore=(self,), debug=False)  
            if hit_info.hit:  
                # Ground detected below  
                ground_y = hit_info.world_point.y  
                # Snap Mario to ground and stop falling  
                self.y = ground_y  
                self.velocity.y = 0  
                self.grounded = True  
                # Reset long jump state if he lands  
                self.long_jump_active = False  
            else:  
                # No ground directly within fall_distance  
                self.position.y += self.velocity.y * time.dt  
                self.grounded = False  
        elif self.velocity.y > 0:  # Moving upward (jumping)  
            # Move up and check for ceiling collision  
            self.position.y += self.velocity.y * time.dt  
            # Cast a short ray upward to see if we hit a ceiling  
            hit_info = raycast(self.position, Vec3(0, 1, 0), distance=0.1, ignore=(self,), debug=False)  
            if hit_info.hit and hit_info.world_normal.y < 0.1:  
                # If a ceiling or overhang is just above  
                self.velocity.y = 0  # bump head and stop upward movement  
            self.grounded = False  
        else:  
            # velocity.y == 0 (could be on ground or at peak of jump momentarily)  
            # We don't change position.y in this case, just keep grounded state as is  
            pass  

        # **Coyote time**: allow a short grace period to still count as grounded after falling  
        # (If needed, check a timer for when grounded became False and allow jumps during small window.)  

        # Camera follow is handled by parenting (see camera setup below), so no explicit update needed here  
        # End of update()  

    def input(self, key):  
        # Process jump and crouch related inputs  
        # Crouch key detection  
        if key == 'left shift' or key == 'right shift' or key == 'control' or key == 'left control':  
            if self.grounded:  
                self.crouching = True  
        if key == 'left shift up' or key == 'right shift up' or key == 'control up' or key == 'left control up':  
            if self.crouching:  
                self.crouching = False  

        # Jump key pressed  
        if key == 'space':  
            # Grounded jump actions  
            if self.grounded:  
                # Check if crouching for long jump or backflip  
                if self.crouching:  
                    # Determine if moving or not  
                    move_horiz = Vec3(self.velocity.x, 0, self.velocity.z).length()  
                    if move_horiz > 1e-2:  
                        # Long jump: running + crouch + jump  
                        self.velocity.y = LONG_JUMP_VEL  
                        self.long_jump_active = True  
                        # Give an immediate forward boost; further boosts happen in update()  
                        self.grounded = False  
                        self.jump_count = 0  # reset normal jump chain  
                        self.last_jump_time = pytime.time()  
                    else:  
                        # Backflip: crouching stationary + jump  
                        self.velocity.y = BACKFLIP_VEL  
                        # Give a backward push as well (opposite of facing direction)  
                        # If Mario is facing forward (rotation_y), apply backward velocity  
                        self.velocity.x = -math.sin(math.radians(self.rotation_y)) * 5.0  # slight backward push  
                        self.velocity.z = -math.cos(math.radians(self.rotation_y)) * 5.0  
                        self.grounded = False  
                        self.jump_count = 0  
                        self.last_jump_time = pytime.time()  
                    return  # long jump or backflip executed, exit  
                # Not crouching: normal jump sequence  
                current_time = pytime.time()  
                # If too much time passed since last jump in combo, reset combo  
                if current_time - self.last_jump_time > JUMP_COMBO_TIME:  
                    self.jump_count = 0  
                # Perform appropriate jump based on jump_count state  
                if self.jump_count == 0:  
                    # Single jump  
                    self.velocity.y = JUMP_VELOCITY  
                    self.jump_count = 1  
                    self.grounded = False  
                    self.last_jump_time = current_time  
                elif self.jump_count == 1:  
                    # Double jump (Mario has landed quickly after first jump)  
                    self.velocity.y = DOUBLE_JUMP_VEL  
                    self.jump_count = 2  
                    self.grounded = False  
                    self.last_jump_time = current_time  
                elif self.jump_count == 2:  
                    # Triple jump  
                    self.velocity.y = TRIPLE_JUMP_VEL  
                    self.jump_count = 0  # reset after triple (chain complete)  
                    self.grounded = False  
                    self.last_jump_time = current_time  
                # Note: jump_count is not reset on landing between single->double or double->triple, unless timeout occurs  
            else:  
                # In-air jump actions (wall kicks or ground pound)  
                # Check for wall kick possibility  
                # Use a raycast forward (same as horizontal collision detection) to see if touching a wall  
                wall_check = raycast(self.position + Vec3(0, 0.5, 0), Vec3(self.velocity.x, 0, self.velocity.z).normalized(), distance=0.6, ignore=(self,))  
                if wall_check.hit and wall_check.world_normal.y < 0.7:  
                    # Wall is close in front, do wall jump  
                    # Determine wall normal and flip velocity  
                    normal = Vec3(wall_check.world_normal.x, 0, wall_check.world_normal.z).normalized()  
                    # Bounce off: set upward velocity and push away from wall  
                    self.velocity.y = WALL_KICK_VEL  
                    # Push horizontally opposite the wall  
                    self.velocity.x = -normal.x * WALL_KICK_PUSH  
                    self.velocity.z = -normal.z * WALL_KICK_PUSH  
                    # Reset any jump combo – wall kick is separate  
                    self.jump_count = 0  
                    self.grounded = False  
                    # Optionally, orient Mario away from wall for consistency (not necessary for mechanics)  
                    target_yaw = math.degrees(math.atan2(-normal.x, -normal.z))  
                    self.rotation_y = target_yaw  
                else:  
                    # (Optional) Ground pound: crouch in air to drop faster  
                    # If the player presses jump in-air with no wall, we do nothing (no double jump mid-air in Mario 64)  
                    pass  

# Create Mario entity (player)  
player = Mario()  
player.position = Vec3(0, 0, 0)  # starting position at origin (adjust if needed)  

# Camera setup: third-person camera following Mario  
camera.parent = player  
camera.position = Vec3(0, 2.5, -7)   # behind and above Mario  
camera.rotation_x = 20              # tilt the camera downward a bit  
camera.rotation_y = 0               # no offset yaw relative to player (always behind him)  
camera.rotation_z = 0  

# Ensure the camera is facing toward Mario initially  
# (Because camera is parented to player, it will always look from behind; we use look_at if needed to adjust pitch)  
# camera.look_at(player.position + Vec3(0,1,0))  # not strictly necessary due to parenting and rotation_x set  

# Load or create the level environment  
# It’s assumed that the level model has appropriate colliders.  
# Example for a custom level model:  
# level = Entity(model='level_mesh', collider='mesh', scale=1)  

# If no custom level, use a simple flat ground for testing (uncomment if needed):  
# ground = Entity(model='plane', texture='white_cube', color=color.light_gray, collider='box', scale=(50,1,50), position=(0,-1,0))  

# Lighting (optional): add a directional light for better visibility  
directional_light = DirectionalLight(y=2, rotation=(45, -45, 45))  
directional_light.color = color.white  

# Sky (optional): a simple sky texture or color  
# sky = Sky()  # Ursina’s default sky  
# sky.color = color.cyan  

# Run the game  
app.run()  

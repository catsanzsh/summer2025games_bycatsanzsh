from ursina import *
from math import sin
import time

# --------------------------------------------------
# Ultra Mario – Ursina NX2 Tech Demo (bug‑fixed)
# --------------------------------------------------
# ‣ WASD / Arrow keys    = Move & turn
# ‣ Space                = Jump
# --------------------------------------------------

# Custom colours that aren’t provided by Ursina’s default palette
color_brown       = color.rgb(139,  69,  19)
color_light_gray  = color.rgb(200, 200, 200)

class UltraMario(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # --- physical collider (invisible) ---
        self.model    = None
        self.color    = color.red
        self.collider = 'box'
        self.scale    = (0.8, 2, 0.8)
        self.origin_y = -0.5    # feet are at Y‑0

        # --- visible mesh & sub‑parts ---
        self.visual   = Entity(parent=self, model='cube',  color=color.red,   scale=(1,1,1))
        self.hat      = Entity(parent=self.visual, model='cube', color=color.red,
                               scale=(1.1, 0.4, 1.1), position=(0, 0.6, 0))
        self.eye_l    = Entity(parent=self.visual, model='sphere', color=color.white,
                               scale=.2, position=(-.16, .8, .41))
        self.eye_r    = Entity(parent=self.visual, model='sphere', color=color.white,
                               scale=.2, position=( .16, .8, .41))
        self.pupil_l  = Entity(parent=self.eye_l, model='sphere', color=color.black,
                               scale=.5, z=-.05)
        self.pupil_r  = Entity(parent=self.eye_r, model='sphere', color=color.black,
                               scale=.5, z=-.05)

        # --- movement parameters ---
        self.speed            = 5
        self.jump_height      = 0.6
        self.jump_duration    = 0.35
        self.gravity_strength = 1.5
        self.velocity_y       = 0
        self.grounded         = False

    # --------------------------------------------------
    # Engine calls update() 60×/s
    # --------------------------------------------------
    def update(self):
        # ---------- horizontal movement ----------
        move_dir = Vec3(0,0,0)
        if held_keys['w'] or held_keys['up arrow']:
            move_dir += self.forward
        if held_keys['s'] or held_keys['down arrow']:
            move_dir += self.back
        if held_keys['a'] or held_keys['left arrow']:
            self.rotation_y -= 100 * time.dt
        if held_keys['d'] or held_keys['right arrow']:
            self.rotation_y += 100 * time.dt

        if move_dir:
            move_dir = move_dir.normalized()
            # simple collision probe in walking direction
            ray = raycast(self.world_position, move_dir, distance=self.speed * time.dt + .1,
                          ignore=[self] + self.children)  # ignore self + visuals
            if not ray.hit:
                self.position += move_dir * self.speed * time.dt
            # head‑bob effect (visual only)
            self.visual.y = sin(time.time() * 10) * .05
        else:
            self.visual.y = 0

        # ---------- gravity & vertical motion ----------
        self.velocity_y -= self.gravity_strength * time.dt
        self.y += self.velocity_y * time.dt

        ground_ray = raycast(self.world_position + Vec3(0,.1,0), self.down,
                             distance=.6, ignore=[self] + self.children)
        if ground_ray.hit and self.velocity_y <= 0:
            # snap to floor
            self.y        = ground_ray.world_point.y + .01
            self.velocity_y = 0
            self.grounded   = True
        else:
            self.grounded = False

        # ---------- fall‑out respawn ----------
        if self.y < -20:
            self.respawn()

    # --------------------------------------------------
    def input(self, key):
        if key == 'space' and self.grounded:
            # initial jump impulse
            self.velocity_y = self.jump_height / self.jump_duration
            self.grounded   = False
            # squash & stretch on jump (visual only)
            self.visual.animate_scale_y(2.2, duration=.1, curve=curve.out_quad)
            self.visual.animate_scale_y(1,   duration=.1, delay=.2, curve=curve.in_quad)

    # --------------------------------------------------
    def respawn(self):
        self.position  = (0, 5, 0)
        self.velocity_y = 0
        t = Text("Fell off! Respawning…", origin=(0,0), scale=2)
        destroy(t, delay=2)

# --------------------------------------------------
# Scene setup
# --------------------------------------------------
app = Ursina()

window.title              = 'Ultra Mario! NX2 Tech Demo'
window.borderless         = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# Ground & platforms
Entity(model='plane', collider='box', scale=50, texture='white_cube',
       texture_scale=(50,50), color=color.rgb(50,180,50))

Entity(model='cube', collider='box', color=color_brown,  position=( 5, 1.5,  5), scale=(5, .5, 3))
Entity(model='cube', collider='box', color=color.orange, position=(-7, 2.5,  3), scale=(4, .5, 4))
Entity(model='cube', collider='box', color=color.gray,   position=( 0, 3.5, -8), scale=(6, .5, 2))
Entity(model='cube', collider='box', color=color_light_gray,
       position=(10, 1,  -5), scale=(8, .5, 4), rotation_x=-20)

# Player
player = UltraMario(position=(0,1,-2))

# Camera
camera.pivot      = player
camera.position   = (0, 6, -16)
camera.rotation_x = 20
camera.add_script(SmoothFollow(target=player, offset=[0,4,-12], speed=4))

# Lighting & sky
sun = DirectionalLight(shadows=True, y=50, z=-20)
sun.look_at(Vec3(0,-1,-1))
AmbientLight(color=color.rgba(100,100,100, .1))
Sky()

# UI text
Text("Ultra Mario! NX2 – Ursina Tech Demo", y=.45, origin=(0,0))
Text("WASD/Arrows to Move | Space to Jump",  y=.4,  origin=(0,0), scale=.8)

app.run()

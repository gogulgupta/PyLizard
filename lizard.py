"""
╔══════════════════════════════════════════════════════╗
║         REALISTIC LIZARD - Pure Python (Tkinter)     ║
║         Mouse follow karo — lizard peeche aayega!    ║
║         4K Quality rendering                         ║
╚══════════════════════════════════════════════════════╝

Kaise chalayein:
    python lizard.py

Controls:
    - Mouse hilao  → lizard follow karega
    - ESC           → band karo
"""

import tkinter as tk
import math
import random
import time

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
WIDTH, HEIGHT = 1920, 1080        # 4K ke liye: 3840, 2160 (slow ho sakta hai)
BG_COLOR = "#12100a"
FPS = 60
SEGS = 60                          # spine ke segments (zyada = zyada smooth)

# ─────────────────────────────────────────
#  UTILITY FUNCTIONS
# ─────────────────────────────────────────

def lerp(a, b, t):
    """Do numbers ke beech smooth interpolation"""
    return a + (b - a) * t

def clamp(v, mn, mx):
    """Value ko range mein rakhna"""
    return max(mn, min(mx, v))

def dist(ax, ay, bx, by):
    """Do points ke beech distance"""
    return math.hypot(bx - ax, by - ay)

def angle_between(ax, ay, bx, by):
    """Do points ke beech angle"""
    return math.atan2(by - ay, bx - ax)

def polar_to_xy(cx, cy, angle, radius):
    """Center se angle aur radius pe point nikalna"""
    return cx + math.cos(angle) * radius, cy + math.sin(angle) * radius

def rotate_point(px, py, cx, cy, angle):
    """Point ko center ke around rotate karna"""
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    px -= cx
    py -= cy
    return cx + px * cos_a - py * sin_a, cy + px * sin_a + py * cos_a

def hex_to_rgb(hex_color):
    """#rrggbb → (r, g, b)"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    """(r,g,b) → #rrggbb"""
    r = int(clamp(r, 0, 255))
    g = int(clamp(g, 0, 255))
    b = int(clamp(b, 0, 255))
    return f'#{r:02x}{g:02x}{b:02x}'

def blend_color(c1_hex, c2_hex, t):
    """Do colors ke beech blend (0=c1, 1=c2)"""
    r1, g1, b1 = hex_to_rgb(c1_hex)
    r2, g2, b2 = hex_to_rgb(c2_hex)
    return rgb_to_hex(
        lerp(r1, r2, t),
        lerp(g1, g2, t),
        lerp(b1, b2, t)
    )

def darken(hex_color, amount=0.3):
    """Color ko dark karna"""
    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_hex(r * (1 - amount), g * (1 - amount), b * (1 - amount))

def lighten(hex_color, amount=0.3):
    """Color ko light karna"""
    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_hex(
        r + (255 - r) * amount,
        g + (255 - g) * amount,
        b + (255 - b) * amount
    )

def alpha_blend(bg_hex, fg_hex, alpha):
    """Alpha blending (0=transparent, 1=opaque)"""
    return blend_color(bg_hex, fg_hex, alpha)

# ─────────────────────────────────────────
#  BODY WIDTH PROFILE
# ─────────────────────────────────────────

def body_width(i):
    """
    Har segment ki width define karta hai:
    head → neck → belly → hips → tail
    """
    total = SEGS
    t = i / total

    if i < 3:
        return lerp(8, 20, i / 3)          # Head build-up
    elif i < 7:
        return lerp(20, 13, (i-3) / 4)     # Neck taper
    elif i < 15:
        return lerp(13, 18, (i-7) / 8)     # Shoulder expand
    elif i < 30:
        return lerp(18, 20, (i-15) / 15)   # Belly (widest)
    elif i < 40:
        return lerp(20, 11, (i-30) / 10)   # Hip taper
    elif i < 50:
        return lerp(11, 5, (i-40) / 10)    # Tail start
    else:
        return lerp(5, 0.8, (i-50) / (SEGS-50))  # Tail tip

# ─────────────────────────────────────────
#  SKIN COLOR PROFILE
# ─────────────────────────────────────────

SKIN_COLORS = [
    (0,   "#5a7a3a"),   # head - medium green
    (0.1, "#4a6e30"),   # neck - darker
    (0.3, "#6b8c45"),   # torso - bright
    (0.5, "#527838"),   # mid body
    (0.7, "#3d5e28"),   # hips
    (1.0, "#243518"),   # tail tip - very dark
]

def get_skin_color(i):
    """Segment index se skin color"""
    t = i / SEGS
    for idx in range(len(SKIN_COLORS) - 1):
        t0, c0 = SKIN_COLORS[idx]
        t1, c1 = SKIN_COLORS[idx + 1]
        if t0 <= t <= t1:
            local_t = (t - t0) / (t1 - t0)
            return blend_color(c0, c1, local_t)
    return SKIN_COLORS[-1][1]

# ─────────────────────────────────────────
#  LIZARD CLASS
# ─────────────────────────────────────────

class Lizard:
    def __init__(self, start_x, start_y):
        # Spine: list of [x, y] points
        self.spine = [[start_x, start_y] for _ in range(SEGS)]

        # Tongue state
        self.tongue_out = 0.0
        self.tongue_dir = 1
        self.tongue_speed = random.uniform(0.03, 0.07)

        # Time counter
        self.t = 0.0

        # Speed tracker (for walk cycle)
        self.speed = 0.0

        # Leg positions (pre-computed)
        self.leg_configs = [
            {"seg": 10, "side": -1, "phase": 0.0},          # Front-left
            {"seg": 10, "side":  1, "phase": math.pi},       # Front-right
            {"seg": 22, "side": -1, "phase": math.pi},       # Back-left
            {"seg": 22, "side":  1, "phase": 0.0},           # Back-right
        ]

        # Blink
        self.blink = 0.0
        self.blink_timer = random.uniform(2, 5)

    def update(self, mouse_x, mouse_y, dt):
        """Physics update — mouse ke peeche aata hai"""
        self.t += dt * 50

        # Head smoothly follows mouse
        self.spine[0][0] += (mouse_x - self.spine[0][0]) * 0.12
        self.spine[0][1] += (mouse_y - self.spine[0][1]) * 0.12

        # Speed calculate karo
        self.speed = dist(self.spine[0][0], self.spine[0][1], mouse_x, mouse_y)
        wave_amp = clamp(self.speed * 0.04, 0.2, 3.5)

        # Chain follow with wave
        for i in range(1, SEGS):
            wave_x = math.sin(self.t * 0.12 - i * 0.22) * wave_amp * (0.2 if i < 8 else 1.0)
            wave_y = math.cos(self.t * 0.10 - i * 0.18) * wave_amp * 0.3

            dx = self.spine[i-1][0] - self.spine[i][0]
            dy = self.spine[i-1][1] - self.spine[i][1]
            follow = max(0.07, 0.28 - i * 0.002)

            self.spine[i][0] += dx * follow + wave_x
            self.spine[i][1] += dy * follow + wave_y

        # Tongue update
        self.tongue_out += self.tongue_dir * self.tongue_speed
        if self.tongue_out >= 1.0:
            self.tongue_out = 1.0
            self.tongue_dir = -1
        elif self.tongue_out <= 0.0:
            self.tongue_out = 0.0
            # Random pause before next flick
            self.tongue_dir = 1 if random.random() > 0.3 else 0
            self.tongue_speed = random.uniform(0.03, 0.08)

        # Blink timer
        self.blink_timer -= dt
        if self.blink_timer <= 0:
            self.blink = 1.0
            self.blink_timer = random.uniform(3, 7)
        if self.blink > 0:
            self.blink -= dt * 8
            self.blink = max(0, self.blink)

    def get_normals(self, i):
        """Segment i ke normal vector (perpendicular)"""
        if i < SEGS - 1:
            dx = self.spine[i+1][0] - self.spine[i][0]
            dy = self.spine[i+1][1] - self.spine[i][1]
        else:
            dx = self.spine[i][0] - self.spine[i-1][0]
            dy = self.spine[i][1] - self.spine[i-1][1]
        length = math.hypot(dx, dy) or 1
        return -dy / length, dx / length  # nx, ny

# ─────────────────────────────────────────
#  RENDERER CLASS
# ─────────────────────────────────────────

class LizardRenderer:
    def __init__(self, canvas, lizard):
        self.canvas = canvas
        self.liz = lizard

    def render(self):
        """Ek frame draw karna"""
        self.draw_shadow()
        self.draw_body()
        self.draw_belly_stripe()
        self.draw_dorsal_scales()
        self.draw_legs()
        self.draw_head()
        self.draw_spots()

    # ── Shadow ────────────────────────────────
    def draw_shadow(self):
        liz = self.liz
        # Soft ellipse shadows under body
        for i in range(5, SEGS - 10, 4):
            sx, sy = liz.spine[i]
            w = body_width(i)
            # Shadow ellipse
            self.canvas.create_oval(
                sx - w * 1.8 + 5, sy - w * 0.5 + 12,
                sx + w * 1.8 + 5, sy + w * 0.5 + 12,
                fill="#060400", outline="", tags="frame"
            )

    # ── Main Body ─────────────────────────────
    def draw_body(self):
        liz = self.liz
        c = self.canvas

        # Build left/right edge polygons per segment
        # Draw from tail to head (painter's algorithm)
        for i in range(SEGS - 2, -1, -1):
            ax, ay = liz.spine[i]
            bx, by = liz.spine[i+1]

            # Normals at this point and next
            nx0, ny0 = liz.get_normals(i)
            nx1, ny1 = liz.get_normals(i+1 if i+1 < SEGS else i)

            w0 = body_width(i)
            w1 = body_width(i+1 if i+1 < SEGS else i)

            # 4 corner points of this body segment quad
            lx0, ly0 = ax + nx0 * w0, ay + ny0 * w0
            rx0, ry0 = ax - nx0 * w0, ay - ny0 * w0
            lx1, ly1 = bx + nx1 * w1, by + ny1 * w1
            rx1, ry1 = bx - nx1 * w1, by - ny1 * w1

            # Skin color for this segment
            color = get_skin_color(i)

            # Main quad
            c.create_polygon(
                lx0, ly0, lx1, ly1, rx1, ry1, rx0, ry0,
                fill=color, outline="", smooth=True, tags="frame"
            )

            # Outline (dark edge)
            outline_c = darken(color, 0.4)
            c.create_line(lx0, ly0, lx1, ly1, fill=outline_c, width=1, tags="frame")
            c.create_line(rx0, ry0, rx1, ry1, fill=outline_c, width=1, tags="frame")

    # ── Belly Stripe ──────────────────────────
    def draw_belly_stripe(self):
        liz = self.liz
        c = self.canvas
        pts = []
        for i in range(5, SEGS - 5):
            x, y = liz.spine[i]
            pts.extend([x, y])
        if len(pts) >= 4:
            c.create_line(*pts, fill="#c8d898", width=3, smooth=True, tags="frame")
            c.create_line(*pts, fill="#e0eaaa", width=1, smooth=True, tags="frame")

    # ── Dorsal Scales (ridge bumps) ───────────
    def draw_dorsal_scales(self):
        liz = self.liz
        c = self.canvas
        for i in range(6, SEGS - 12, 3):
            ax, ay = liz.spine[i]
            bx, by = liz.spine[i+1]
            seg_angle = math.atan2(by - ay, bx - ax)

            w = body_width(i)
            scale_h = w * 0.45
            scale_w = w * 0.3

            # Spine angle perpendicular mein scale
            tip_x = ax + math.cos(seg_angle - math.pi/2) * (w * 0.8)
            tip_y = ay + math.sin(seg_angle - math.pi/2) * (w * 0.8)

            base_l_x = ax + math.cos(seg_angle) * scale_w
            base_l_y = ay + math.sin(seg_angle) * scale_w
            base_r_x = ax - math.cos(seg_angle) * scale_w
            base_r_y = ay - math.sin(seg_angle) * scale_w

            dark = darken(get_skin_color(i), 0.35)
            c.create_polygon(
                base_l_x, base_l_y,
                tip_x, tip_y,
                base_r_x, base_r_y,
                fill=dark, outline=darken(dark, 0.3), tags="frame"
            )

    # ── Legs ──────────────────────────────────
    def draw_legs(self):
        liz = self.liz
        c = self.canvas

        walk_speed = clamp(liz.speed * 0.04, 0, 1)

        for lj in liz.leg_configs:
            si = lj["seg"]
            side = lj["side"]
            phase = lj["phase"]

            ax, ay = liz.spine[si]
            bx, by = liz.spine[min(si+1, SEGS-1)]

            # Segment direction
            seg_dx = bx - ax
            seg_dy = by - ay
            seg_len = math.hypot(seg_dx, seg_dy) or 1

            # Normal (perpendicular)
            nx = -seg_dy / seg_len
            ny = seg_dx / seg_len

            w = body_width(si)

            # Hip position (where leg meets body)
            hip_x = ax + nx * w * side
            hip_y = ay + ny * w * side

            # Body direction angle
            body_ang = math.atan2(seg_dy, seg_dx)

            # Leg spreads outward
            leg_ang = body_ang + side * (math.pi / 2.3)

            # Walk cycle
            lift_cycle = math.sin(liz.t * 0.1 + phase)
            fwd = math.cos(liz.t * 0.1 + phase) * 0.4

            thigh_len = 28
            shin_len = 26

            # Knee
            knee_ang = leg_ang + fwd
            knee_x = hip_x + math.cos(knee_ang) * thigh_len
            knee_y = hip_y + math.sin(knee_ang) * thigh_len

            # Foot (with lift during walk)
            foot_ang = knee_ang + fwd * 0.8
            lift_amount = max(0, lift_cycle) * 14 * walk_speed
            foot_x = knee_x + math.cos(foot_ang) * shin_len
            foot_y = knee_y + math.sin(foot_ang) * shin_len - lift_amount

            # Thigh
            c.create_line(
                hip_x, hip_y, knee_x, knee_y,
                fill="#2e4418", width=7, capstyle=tk.ROUND, tags="frame"
            )
            c.create_line(
                hip_x, hip_y, knee_x, knee_y,
                fill="#3d5820", width=4, capstyle=tk.ROUND, tags="frame"
            )

            # Shin
            c.create_line(
                knee_x, knee_y, foot_x, foot_y,
                fill="#243010", width=5, capstyle=tk.ROUND, tags="frame"
            )
            c.create_line(
                knee_x, knee_y, foot_x, foot_y,
                fill="#304018", width=3, capstyle=tk.ROUND, tags="frame"
            )

            # Foot pad
            c.create_oval(
                foot_x - 4, foot_y - 4,
                foot_x + 4, foot_y + 4,
                fill="#1a2010", outline="", tags="frame"
            )

            # 5 Toes (real lizard jaisi!)
            for toe_num in range(-2, 3):
                toe_ang = foot_ang + toe_num * 0.25
                # Outer toes shorter, middle longest
                toe_len = 10 - abs(toe_num) * 1.5
                toe_ex, toe_ey = polar_to_xy(foot_x, foot_y, toe_ang, toe_len)

                c.create_line(
                    foot_x, foot_y, toe_ex, toe_ey,
                    fill="#121808", width=2, capstyle=tk.ROUND, tags="frame"
                )
                # Claw tip
                claw_ex, claw_ey = polar_to_xy(toe_ex, toe_ey, toe_ang, 3)
                c.create_line(
                    toe_ex, toe_ey, claw_ex, claw_ey,
                    fill="#0a1005", width=1, capstyle=tk.ROUND, tags="frame"
                )

    # ── Head ──────────────────────────────────
    def draw_head(self):
        liz = self.liz
        c = self.canvas

        hx, hy = liz.spine[0]
        h2x, h2y = liz.spine[3]
        head_ang = math.atan2(h2y - hy, h2x - hx)

        # Head shape (triangle with bezier feel via polygon)
        def hp(local_x, local_y):
            """Local coords → world coords"""
            rx, ry = rotate_point(
                hx + local_x, hy + local_y,
                hx, hy, head_ang
            )
            return rx, ry

        # ── Head base polygon ──
        snout = hp(32, 0)
        top_l = hp(20, -14)
        back_l = hp(-8, -14)
        neck_l = hp(-20, -10)
        chin   = hp(-20, 10)
        neck_r = hp(-8, 14)
        back_r = hp(20, 14)
        top_r  = hp(32, 0)    # same as snout but from right

        head_pts = [
            *snout, *top_l, *back_l, *neck_l,
            *chin, *neck_r, *back_r
        ]

        # Head fill
        c.create_polygon(*head_pts, fill="#5a7a3a", outline="#1e3010", width=1, smooth=True, tags="frame")

        # Head shading (top slightly lighter)
        shade_pts = [*hp(28, 0), *hp(18, -11), *hp(-5, -11), *hp(-15, -7), *hp(-5, -2), *hp(15, -2)]
        c.create_polygon(*shade_pts, fill="#6b8c45", outline="", smooth=True, tags="frame")

        # ── Snout ridge ──
        ridge_pts = [*hp(32, 0), *hp(20, -4), *hp(5, -5), *hp(-3, -5)]
        c.create_line(*ridge_pts, fill="#7a9c55", width=2, smooth=True, tags="frame")

        # ── Nostrils ──
        nose_l_x, nose_l_y = hp(24, -5)
        nose_r_x, nose_r_y = hp(24, 5)
        c.create_oval(nose_l_x-3, nose_l_y-2, nose_l_x+3, nose_l_y+2, fill="#1a2a08", outline="", tags="frame")
        c.create_oval(nose_r_x-3, nose_r_y-2, nose_r_x+3, nose_r_y+2, fill="#1a2a08", outline="", tags="frame")

        # ── Mouth line ──
        mouth_pts = [*hp(32, 0), *hp(18, -3), *hp(0, -3), *hp(-10, -3)]
        c.create_line(*mouth_pts, fill="#1a2a08", width=2, smooth=True, tags="frame")

        # ── Eye socket ──
        eye_x, eye_y = hp(8, -12)
        c.create_oval(eye_x-9, eye_y-8, eye_x+9, eye_y+8, fill="#1e3010", outline="#0a1808", width=1, tags="frame")

        # ── Iris ──
        c.create_oval(eye_x-7, eye_y-7, eye_x+7, eye_y+7, fill="#8B4513", outline="", tags="frame")

        # ── Iris pattern (concentric) ──
        c.create_oval(eye_x-5, eye_y-5, eye_x+5, eye_y+5, fill="#c8820a", outline="", tags="frame")
        c.create_oval(eye_x-3, eye_y-3, eye_x+3, eye_y+3, fill="#a06010", outline="", tags="frame")

        # ── Pupil (vertical slit!) ──
        blink_scale = 1.0 - liz.blink * 0.95
        pupil_h = 6 * blink_scale
        c.create_oval(
            eye_x - 2, eye_y - pupil_h,
            eye_x + 2, eye_y + pupil_h,
            fill="#050200", outline="", tags="frame"
        )

        # ── Eye shine ──
        if blink_scale > 0.3:
            shine_x, shine_y = hp(10, -14)
            c.create_oval(shine_x, shine_y, shine_x+3, shine_y+2, fill="#ffffff", outline="", tags="frame")

        # ── Eyelid (blink) ──
        if liz.blink > 0.05:
            lid_h = int(8 * liz.blink)
            c.create_rectangle(
                eye_x - 9, eye_y - 8,
                eye_x + 9, eye_y - 8 + lid_h,
                fill="#5a7a3a", outline="", tags="frame"
            )

        # ── Ear hole ──
        ear_x, ear_y = hp(-2, -11)
        c.create_oval(ear_x-4, ear_y-4, ear_x+4, ear_y+4, fill="#1a2a08", outline="#0a1808", tags="frame")

        # ── Dewlap (throat) ──
        dewlap_pts = [*hp(-5, 5), *hp(-10, 18), *hp(-18, 16), *hp(-16, 6)]
        c.create_polygon(*dewlap_pts, fill="#c86432", outline="", smooth=True, tags="frame")

        # ── Tongue ──
        if liz.tongue_out > 0.05:
            t_len = liz.tongue_out * 28
            tongue_base_x, tongue_base_y = hp(30, 0)
            tongue_tip_x, tongue_tip_y = hp(30 + t_len, 0)

            # Tongue body
            c.create_line(
                tongue_base_x, tongue_base_y,
                tongue_tip_x, tongue_tip_y,
                fill="#cc2222", width=3,
                capstyle=tk.ROUND, tags="frame"
            )

            # Forked tips
            if t_len > 10:
                fork_len = 9 * (t_len / 28)
                # Left fork
                fl1x, fl1y = hp(30 + t_len + fork_len, -fork_len * 0.6)
                # Right fork
                fr1x, fr1y = hp(30 + t_len + fork_len, fork_len * 0.6)

                c.create_line(
                    tongue_tip_x, tongue_tip_y, fl1x, fl1y,
                    fill="#dd1111", width=2, capstyle=tk.ROUND, tags="frame"
                )
                c.create_line(
                    tongue_tip_x, tongue_tip_y, fr1x, fr1y,
                    fill="#dd1111", width=2, capstyle=tk.ROUND, tags="frame"
                )

    # ── Spots / Pattern ───────────────────────
    def draw_spots(self):
        liz = self.liz
        c = self.canvas

        spot_indices = [12, 16, 20, 25, 30, 18]
        for i, si in enumerate(spot_indices):
            if si >= SEGS:
                continue
            ax, ay = liz.spine[si]
            nx, ny = liz.get_normals(si)
            w = body_width(si)
            offset = (i % 3 - 1) * w * 0.5

            sx = ax + nx * offset
            sy = ay + ny * offset

            spot_r = w * 1.1

            # Dark outer ring
            c.create_oval(
                sx - spot_r, sy - spot_r * 0.7,
                sx + spot_r, sy + spot_r * 0.7,
                fill=darken(get_skin_color(si), 0.15),
                outline="", tags="frame"
            )
            # Bright center
            c.create_oval(
                sx - spot_r * 0.5, sy - spot_r * 0.35,
                sx + spot_r * 0.5, sy + spot_r * 0.35,
                fill=lighten(get_skin_color(si), 0.2),
                outline="", tags="frame"
            )

# ─────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────

class App:
    def __init__(self):
        # Window
        self.root = tk.Tk()
        self.root.title("🦎 Realistic Lizard — Mouse Follow")
        self.root.configure(bg=BG_COLOR)

        # Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=WIDTH, height=HEIGHT,
            bg=BG_COLOR,
            highlightthickness=0,
            cursor="none"   # Mouse cursor hide
        )
        self.canvas.pack()

        # Mouse tracking
        self.mouse_x = WIDTH // 2
        self.mouse_y = HEIGHT // 2
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        # Lizard
        self.lizard = Lizard(WIDTH // 2, HEIGHT // 2)
        self.renderer = LizardRenderer(self.canvas, self.lizard)

        # FPS tracking
        self.last_time = time.time()
        self.frame_count = 0
        self.fps_display = 0

        # Start loop
        self.loop()
        self.root.mainloop()

    def on_mouse_move(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

    def draw_background(self):
        """Beautiful dark ground texture"""
        c = self.canvas

        # Base background
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill=BG_COLOR, outline="", tags="frame")

        # Grid pattern (rock surface feel)
        for row in range(0, HEIGHT, 60):
            for col in range(0, WIDTH, 80):
                offset_x = (row // 60 % 2) * 40
                shade = random.choice(["#141008", "#111006", "#131007"])
                c.create_rectangle(
                    col + offset_x, row,
                    col + offset_x + 78, row + 58,
                    fill=shade, outline="#0d0c06", width=1, tags="frame"
                )

        # Vignette (edges dark)
        for i in range(8):
            alpha = 0.08 * (8 - i) / 8
            c.create_rectangle(
                i * 10, i * 10,
                WIDTH - i * 10, HEIGHT - i * 10,
                fill="", outline="#050400",
                width=12, tags="frame"
            )

    def draw_cursor(self):
        """Custom cursor (small red dot)"""
        cx, cy = self.mouse_x, self.mouse_y
        self.canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill="#cc3322", outline="#ff5544", width=1, tags="frame")
        self.canvas.create_line(cx-8, cy, cx+8, cy, fill="#cc3322", width=1, tags="frame")
        self.canvas.create_line(cx, cy-8, cx, cy+8, fill="#cc3322", width=1, tags="frame")

    def draw_ui(self):
        """FPS + info text"""
        self.canvas.create_text(
            20, 20,
            text=f"FPS: {self.fps_display}",
            fill="#3a5020", font=("Courier", 14, "bold"),
            anchor="nw", tags="frame"
        )
        self.canvas.create_text(
            WIDTH // 2, HEIGHT - 30,
            text="MOUSE HILAO — LIZARD PEECHE AAYEGA  •  ESC = BAND KARO",
            fill="#2a3a15", font=("Courier", 11),
            tags="frame"
        )

    def loop(self):
        """Main game loop"""
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        # FPS
        self.frame_count += 1
        if self.frame_count % 30 == 0:
            self.fps_display = round(1.0 / dt) if dt > 0 else 999

        # Update physics
        self.lizard.update(self.mouse_x, self.mouse_y, dt)

        # Clear old frame
        self.canvas.delete("frame")

        # Draw new frame
        self.draw_background()
        self.renderer.render()
        self.draw_cursor()
        self.draw_ui()

        # Schedule next frame
        delay = max(1, int(1000 / FPS))
        self.root.after(delay, self.loop)


# ─────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🦎 Realistic Lizard starting...")
    print("   Mouse hilao — lizard peeche aayega!")
    print("   ESC dabao band karne ke liye.\n")
    App()
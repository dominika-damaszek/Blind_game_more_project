"""
Hand Puzzle – A Pygame + MediaPipe camera puzzle game.
Controls entirely through hand gestures tracked by a webcam.
"""

import pygame
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks_python
from mediapipe.tasks.python import vision as mp_tasks_vision
import numpy as np
import threading
import random
import math
import sys
import time
import os
import urllib.request

# ──────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────
WIN_W, WIN_H   = 1100, 700
PUZZLE_RECT    = pygame.Rect(400, 60, 640, 580)
CAMERA_RECT    = pygame.Rect(20, 60, 360, 270)
PINCH_THRESH   = 0.08    # normalised distance to trigger a pinch
SNAP_FRACTION  = 0.65    # snap distance ratio

PALETTE = {
    "bg":       (12,  16, 20),
    "panel":    (25,  35, 45),
    "panel_a":  (25,  35, 45, 230),
    "accent":   (20, 220, 160),
    "dim":      (40,  70,  90),
    "white":    (240, 245, 250),
    "gold":     (255, 200,  50),
    "danger":   (230,  80,  80)
}

# ──────────────────────────────────────────────
#  PROCEDURAL AUDIO (Numpy -> Pygame Mixer)
# ──────────────────────────────────────────────
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

def synth_sound(freq_start, freq_end, duration, wave_type='sine', vol=0.5):
    sr = 44100
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    freqs = np.linspace(freq_start, freq_end, len(t))
    phase = np.cumsum(freqs * 2 * np.pi / sr)
    
    if wave_type == 'sine':
        wave = np.sin(phase)
    elif wave_type == 'square':
        wave = np.sign(np.sin(phase))
    else: # saw
        wave = 2 * (phase / (2 * np.pi) - np.floor(phase / (2 * np.pi) + 0.5))
        
    env = np.exp(-t * (5/duration)) # quick exponential decay
    audio = np.int16(wave * env * vol * 32767)
    stereo = np.empty((audio.shape[0], 2), dtype=np.int16)
    stereo[:, 0] = audio; stereo[:, 1] = audio
    return pygame.sndarray.make_sound(stereo)

class Audio:
    hover   = synth_sound(800, 800, 0.05, 'sine', 0.1)
    click   = synth_sound(1200, 400, 0.1, 'sine', 0.3)
    shutter = synth_sound(800, 200, 0.15, 'square', 0.2)
    grab    = synth_sound(300, 600, 0.1, 'sine', 0.2)
    snap    = synth_sound(800, 1200, 0.15, 'sine', 0.4)
    error   = synth_sound(200, 100, 0.2, 'saw', 0.3)
    
    @classmethod
    def play_win(cls):
        def _play():
            synth_sound(400, 400, 0.15, 'sine', 0.4).play()
            time.sleep(0.15)
            synth_sound(500, 500, 0.15, 'sine', 0.4).play()
            time.sleep(0.15)
            synth_sound(600, 800, 0.4, 'sine', 0.5).play()
        threading.Thread(target=_play, daemon=True).start()

# ──────────────────────────────────────────────
#  THREAD-SAFE CAMERA + MEDIAPIPE (Tasks API)
# ──────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")
MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

def ensure_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading hand_landmarker.task model (~3 MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Model downloaded.")

class HandCamera:
    """Runs OpenCV + MediaPipe Tasks in a background thread."""
    INDEX_TIP = 8
    THUMB_TIP = 4

    def __init__(self):
        ensure_model()
        self._cap  = cv2.VideoCapture(0)
        self._lock = threading.Lock()
        self._frame      = None
        self._hands_data = [] # e.g. [{"ix":0.5, "iy":0.5, "tx":0.5, "ty":0.5, "pinch":False}]
        self._running    = True
        self._ts         = 0

        base_options = mp_tasks_python.BaseOptions(model_asset_path=MODEL_PATH)
        options = mp_tasks_vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=mp_tasks_vision.RunningMode.VIDEO,
        )
        self._landmarker = mp_tasks_vision.HandLandmarker.create_from_options(options)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            ok, frame = self._cap.read()
            if not ok: continue
            
            frame = cv2.flip(frame, 1)
            self._ts += 33

            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,
                                data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            result = self._landmarker.detect_for_video(mp_image, self._ts)

            hands_list = []
            if result.hand_landmarks:
                for landmarks in result.hand_landmarks:
                    ix, iy = landmarks[self.INDEX_TIP].x, landmarks[self.INDEX_TIP].y
                    tx, ty = landmarks[self.THUMB_TIP].x, landmarks[self.THUMB_TIP].y
                    dist = math.hypot(ix - tx, iy - ty)
                    hands_list.append({"ix": ix, "iy": iy, "tx": tx, "ty": ty, "pinch": (dist < PINCH_THRESH)})
            
            with self._lock:
                self._frame = frame
                self._hands_data = hands_list

    def read(self):
        with self._lock:
            return (self._frame.copy() if self._frame is not None else None), list(self._hands_data)

    def stop(self):
        self._running = False
        if hasattr(self, '_thread'):
            self._thread.join()
        self._cap.release()
        self._landmarker.close()

# ──────────────────────────────────────────────
#  SMOOTHED HAND STATE (Cursor Controller)
# ──────────────────────────────────────────────
class HandCursorFilter:
    """Applies Exponential Moving Average for jitter reduction."""
    def __init__(self, ema_alpha=0.4):
        self.alpha = ema_alpha
        self.active_cursors = {} # keyed by rough screen position heuristic to track hands reliably

    def filter(self, hands_data):
        # Very naive tracking: assign matched hands by nearest distance
        new_cursors = []
        unassigned_keys = list(self.active_cursors.keys())
        
        for hd in hands_data:
            px = int(hd["ix"] * WIN_W)
            py = int(hd["iy"] * WIN_H)
            pinch = hd["pinch"]
            
            best_k = None; best_dist = 9999
            for k in unassigned_keys:
                last_px, last_py = self.active_cursors[k]["pos"]
                d = math.hypot(px - last_px, py - last_py)
                if d < 150 and d < best_dist: # if hand moved less than 150px
                    best_k = k; best_dist = d
                    
            if best_k is not None:
                unassigned_keys.remove(best_k)
                last_px, last_py = self.active_cursors[best_k]["pos"]
                sm_px = last_px * (1 - self.alpha) + px * self.alpha
                sm_py = last_py * (1 - self.alpha) + py * self.alpha
                self.active_cursors[best_k]["pos"] = (sm_px, sm_py)
                self.active_cursors[best_k]["pinch"] = pinch
                new_cursors.append(self.active_cursors[best_k])
            else:
                # new hand
                key = id(hd)
                self.active_cursors[key] = {"pos": (px, py), "pinch": pinch, "key": key, "smooth_pinch": 0.0}
                new_cursors.append(self.active_cursors[key])
                
        # Clean up lost hands
        self.active_cursors = {c["key"]: c for c in new_cursors}
        
        # Smooth pinch animation logic
        for c in self.active_cursors.values():
            target = 1.0 if c["pinch"] else 0.0
            c["smooth_pinch"] += (target - c["smooth_pinch"]) * 0.3
            
        return list(self.active_cursors.values())


def cv_to_pygame_surface(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))

# ──────────────────────────────────────────────
#  PUZZLE STATE & VISUALS
# ──────────────────────────────────────────────
class Tile:
    def __init__(self, correct_rect, image_crop):
        self.correct_rect = correct_rect
        self.surf         = image_crop
        self.rect         = pygame.Rect(correct_rect)
        self.locked       = False
        self.being_held   = False
        self.hold_offset  = (0, 0)
        self.scale        = 1.0 # for pop animation
        self.rot          = random.uniform(-5, 5) # slight initial tilt

class PuzzleState:
    def __init__(self, image_surf, grid_n, area):
        self.grid_n = grid_n
        self.area   = area
        self.tiles  = []
        self.particles = []
        
        tw = area.w // grid_n
        th = area.h // grid_n
        scaled = pygame.transform.smoothscale(image_surf, (tw * grid_n, th * grid_n))

        positions = []
        for row in range(grid_n):
            for col in range(grid_n):
                c_rect = pygame.Rect(area.x + col * tw, area.y + row * th, tw, th)
                crop = scaled.subsurface(pygame.Rect(col * tw, row * th, tw, th)).copy()
                self.tiles.append(Tile(c_rect, crop))
                positions.append(pygame.Rect(c_rect))

        random.shuffle(positions)
        for tile, pos in zip(self.tiles, positions):
            tile.rect = pos

        self.held_tile = None

    @property
    def solved(self):
        return all(t.locked for t in self.tiles)
        
    def add_particles(self, x, y, col=PALETTE["accent"], count=15):
        for _ in range(count):
            self.particles.append({
                "x": x, "y": y,
                "vx": random.uniform(-4, 4), "vy": random.uniform(-4, 0),
                "r": random.randint(3, 8),
                "col": col,
                "life": 1.0
            })

    def try_snap(self, tile):
        if tile.locked: return
        dx = abs(tile.rect.centerx - tile.correct_rect.centerx)
        dy = abs(tile.rect.centery - tile.correct_rect.centery)
        th = tile.rect.h * SNAP_FRACTION
        tw = tile.rect.w * SNAP_FRACTION
        if dx < tw and dy < th:
            tile.rect = pygame.Rect(tile.correct_rect)
            tile.locked = True
            tile.rot = 0
            Audio.snap.play()
            self.add_particles(tile.rect.centerx, tile.rect.centery)
        else:
            Audio.error.play()

    def grab(self, px, py):
        if self.held_tile: return False
        for tile in reversed(self.tiles): # top first
            if not tile.locked and tile.rect.collidepoint(px, py):
                self.held_tile = tile
                tile.being_held = True
                tile.hold_offset = (tile.rect.x - px, tile.rect.y - py)
                tile.rot = 0
                Audio.grab.play()
                return True
        return False
        
    def move(self, px, py):
        if self.held_tile:
            ox, oy = self.held_tile.hold_offset
            self.held_tile.rect.x = px + ox
            self.held_tile.rect.y = py + oy

    def release(self):
        if self.held_tile:
            self.try_snap(self.held_tile)
            self.held_tile.being_held = False
            self.held_tile = None

    def check_snap_preview(self):
        """Returns the rect of the Correct Cell if the held tile is close to snapping."""
        if not self.held_tile: return None
        dx = abs(self.held_tile.rect.centerx - self.held_tile.correct_rect.centerx)
        dy = abs(self.held_tile.rect.centery - self.held_tile.correct_rect.centery)
        th = self.held_tile.rect.h * SNAP_FRACTION
        tw = self.held_tile.rect.w * SNAP_FRACTION
        if dx < tw and dy < th:
            return self.held_tile.correct_rect
        return None

    def draw(self, screen):
        # Draw background slots
        tw = self.area.w // self.grid_n
        th = self.area.h // self.grid_n
        for row in range(self.grid_n):
            for col in range(self.grid_n):
                r = pygame.Rect(self.area.x + col * tw, self.area.y + row * th, tw, th)
                pygame.draw.rect(screen, PALETTE["panel"], r)
                pygame.draw.rect(screen, PALETTE["bg"], r, 2)
                
        # Draw target snap highlight
        snap_rect = self.check_snap_preview()
        if snap_rect:
            pygame.draw.rect(screen, PALETTE["accent"], snap_rect, 4)
            s = pygame.Surface(snap_rect.size, pygame.SRCALPHA)
            s.fill((*PALETTE["accent"], 60))
            screen.blit(s, snap_rect)

        # Draw idle / locked tiles
        for t in self.tiles:
            if t.being_held: continue
            
            # Idle tilt logic
            if not t.locked and abs(t.rot) > 0.1:
                t.rot *= 0.95 # settle to 0 slowly if dropped
                
            surf = t.surf
            if not t.locked and abs(t.rot) > 0.5:
                surf = pygame.transform.rotate(t.surf, t.rot)
                
            r = surf.get_rect(center=t.rect.center)
            
            if not t.locked:
                pygame.draw.rect(screen, (0,0,0), r.move(3,3), border_radius=4) # shadow
                screen.blit(surf, r)
                pygame.draw.rect(screen, PALETTE["dim"], r, 2)
            else:
                screen.blit(t.surf, t.rect) # Locked tiles sit flush

        # Draw held tile on top
        if self.held_tile:
            t = self.held_tile
            t.scale += (1.1 - t.scale) * 0.2
            
            w, h = int(t.rect.w * t.scale), int(t.rect.h * t.scale)
            scaled = pygame.transform.smoothscale(t.surf, (w, h))
            cx, cy = t.rect.centerx, t.rect.centery
            sr = scaled.get_rect(center=(cx, cy))
            
            # Big hovering shadow
            pygame.draw.rect(screen, (0,0,0), sr.move(8, 12), border_radius=4)
            screen.blit(scaled, sr)
            pygame.draw.rect(screen, PALETTE["gold"], sr, 4)

        # Draw particles
        for p in reversed(self.particles):
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.2 # gravity
            p["life"] -= 0.03
            if p["life"] <= 0:
                self.particles.remove(p)
                continue
            r = int(p["r"] * p["life"])
            if r > 0:
                pygame.draw.circle(screen, p["col"], (int(p["x"]), int(p["y"])), r)


# ──────────────────────────────────────────────
#  UI HELPERS
# ──────────────────────────────────────────────
def draw_btn_ui(screen, rect, text, font, active=False, hovered=False):
    col = PALETTE["accent"] if active else (PALETTE["dim"] if not hovered else (60, 100, 120))
    # Panel
    pygame.draw.rect(screen, (0,0,0), rect.move(0,4), border_radius=10) # drop shadow
    pygame.draw.rect(screen, col, rect, border_radius=10)
    pygame.draw.rect(screen, PALETTE["white"] if active else PALETTE["dim"], rect, 2, border_radius=10)
    
    txt_col = PALETTE["bg"] if active else PALETTE["white"]
    txt_surf = font.render(text, True, txt_col)
    screen.blit(txt_surf, txt_surf.get_rect(center=rect.center))

def render_hand_cursors(screen, cursors):
    for c in cursors:
        px, py = int(c["pos"][0]), int(c["pos"][1])
        sp = c["smooth_pinch"] # 0.0 to 1.0
        
        # Color interpolation (White -> Gold)
        r = int(255)
        g = int(255 - sp * (255 - 200))
        b = int(255 - sp * (255 - 50))
        col = (r, g, b)
        
        radius = 16 - (sp * 6) # Shrinks when pinching
        
        # Pulse ring
        if sp > 0.8:
            pulse = (math.sin(time.time() * 10) + 1) * 3
            pygame.draw.circle(screen, PALETTE["gold"], (px, py), int(radius + 8 + pulse), 2)
            
        pygame.draw.circle(screen, col, (px, py), int(radius))
        pygame.draw.circle(screen, PALETTE["bg"], (px, py), int(radius), 2)


# ──────────────────────────────────────────────
#  MAIN GAME LOOP
# ──────────────────────────────────────────────
def main():
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Hand Puzzle: Camera Tracking Edition")
    clock  = pygame.time.Clock()

    font_xl = pygame.font.SysFont("Courier", 56, bold=True)
    font_lg = pygame.font.SysFont("Courier", 32, bold=True)
    font_md = pygame.font.SysFont("Courier", 22, bold=True)
    font_sm = pygame.font.SysFont("Courier", 16)

    cam = HandCamera()
    cursor_filter = HandCursorFilter()

    state = "menu"
    difficulty = 5
    puzzle = None
    captured_surf = None
    
    # Capture Mode variables
    capture_start_time = 0
    capture_duration   = 1.5 # seconds to hold pinch before snapping
    is_capturing       = False
    screen_flash       = 0.0

    # Layouts
    menu_btns = {
        5:  pygame.Rect(WIN_W//2 - 160, 280, 320, 60),
        10: pygame.Rect(WIN_W//2 - 160, 360, 320, 60),
        15: pygame.Rect(WIN_W//2 - 160, 440, 320, 60),
    }
    start_btn = pygame.Rect(WIN_W//2 - 160, 540, 320, 60)
    win_menu_btn = pygame.Rect(WIN_W//2 - 200, 460, 400, 60)
    
    hovered_memory = None # tracking hover for sfx

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        frame, raw_hands = cam.read()
        cursors = cursor_filter.filter(raw_hands) if raw_hands else []

        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state = "menu"; puzzle = None
                is_capturing = False

            # Mouse fallback
            if event.type == pygame.MOUSEBUTTONDOWN:
                if state == "menu":
                    for n, r in menu_btns.items():
                        if r.collidepoint(mouse_pos):
                            difficulty = n; Audio.click.play()
                    if start_btn.collidepoint(mouse_pos):
                        state = "capture"; Audio.click.play()
                elif state == "puzzle" and puzzle:
                    puzzle.grab(*mouse_pos)
                elif state == "win":
                    if win_menu_btn.collidepoint(mouse_pos):
                        state = "menu"; puzzle = None; Audio.click.play()

            if event.type == pygame.MOUSEBUTTONUP and state == "puzzle" and puzzle:
                puzzle.release()
            if event.type == pygame.MOUSEMOTION and state == "puzzle" and puzzle:
                puzzle.move(*mouse_pos)

        # ──────────────
        #  MENU
        # ──────────────
        if state == "menu":
            screen.fill(PALETTE["bg"])

            # Animated bg grid
            offset = (time.time() * 20) % 40
            for x in range(int(offset)-40, WIN_W, 40): pygame.draw.line(screen, (20, 30, 20), (x, 0), (x, WIN_H))
            for y in range(int(offset/2)-40, WIN_H, 40): pygame.draw.line(screen, (20, 30, 20), (0, y), (WIN_W, y))

            title = font_xl.render("HAND PUZZLE", True, PALETTE["accent"])
            screen.blit(title, title.get_rect(center=(WIN_W//2, 120)))
            sub = font_md.render("Interactive Gesture Jigsaw", True, PALETTE["dim"])
            screen.blit(sub, sub.get_rect(center=(WIN_W//2, 185)))

            label = font_md.render("Select Grid Size:", True, PALETTE["white"])
            screen.blit(label, label.get_rect(center=(WIN_W//2, 245)))

            any_hovered = None
            for n, r in menu_btns.items():
                is_hov = False
                for c in cursors:
                    if r.collidepoint(*c["pos"]):
                        is_hov = True; any_hovered = n
                        if c["smooth_pinch"] > 0.8:
                            difficulty = n; Audio.click.play()
                draw_btn_ui(screen, r, f"{n} × {n}  Tiles", font_md, (difficulty == n), is_hov or r.collidepoint(mouse_pos))

            start_hov = False
            for c in cursors:
                if start_btn.collidepoint(*c["pos"]):
                    start_hov = True; any_hovered = "start"
                    if c["smooth_pinch"] > 0.8:
                        state = "capture"; Audio.click.play()
                        last_pinch_time = time.time()
            draw_btn_ui(screen, start_btn, "▶  START CAMERA", font_lg, False, start_hov or start_btn.collidepoint(mouse_pos))
            
            if any_hovered != hovered_memory:
                if any_hovered is not None: Audio.hover.play()
                hovered_memory = any_hovered

            render_hand_cursors(screen, cursors)

        # ──────────────
        #  CAPTURE
        # ──────────────
        elif state == "capture":
            screen.fill(PALETTE["bg"])

            if frame is not None:
                cam_surf = cv_to_pygame_surface(frame)
                cam_surf = pygame.transform.scale(cam_surf, (WIN_W, WIN_H))
                screen.blit(cam_surf, (0, 0))

            overlay = pygame.Surface((WIN_W, 90), pygame.SRCALPHA)
            overlay.fill((10, 15, 20, 200))
            screen.blit(overlay, (0, 0))

            instr1 = font_md.render("Point BOTH index fingers to frame your photo.", True, PALETTE["accent"])
            instr2 = font_sm.render("PINCH & HOLD to start the capture timer!", True, PALETTE["white"])
            screen.blit(instr1, instr1.get_rect(center=(WIN_W//2, 30)))
            screen.blit(instr2, instr2.get_rect(center=(WIN_W//2, 65)))

            any_pinch = any(c["pinch"] for c in cursors)

            if len(cursors) >= 2:
                p1 = cursors[0]["pos"]
                p2 = cursors[1]["pos"]
                rx = min(p1[0], p2[0])
                ry = min(p1[1], p2[1])
                rw = abs(p2[0] - p1[0])
                rh = abs(p2[1] - p1[1])
                
                sel_rect = pygame.Rect(rx, ry, max(rw, 10), max(rh, 10))
                
                if any_pinch:
                    if not is_capturing:
                        is_capturing = True
                        capture_start_time = time.time()
                        
                    progress = (time.time() - capture_start_time) / capture_duration
                    
                    # Draw pulsing orange rectangle
                    pulse_h = abs(math.sin(time.time() * 20)) * 50
                    col = (255, 100+int(pulse_h), 50)
                    pygame.draw.rect(screen, col, sel_rect, 4, border_radius=4)
                    
                    # Central timer ring
                    cx2, cy2 = sel_rect.center
                    pygame.draw.arc(screen, col, pygame.Rect(cx2-40, cy2-40, 80, 80), 
                                    math.pi/2, math.pi/2 + (progress * 2 * math.pi), 8)
                    
                    countdown = font_lg.render(str(math.ceil(capture_duration - progress * capture_duration)), True, col)
                    screen.blit(countdown, countdown.get_rect(center=(cx2, cy2)))
                    
                    if progress >= 1.0 and rw > 40 and rh > 40:
                        # SNAP!
                        Audio.shutter.play()
                        screen_flash = 1.0
                        fx1, fy1 = int(rx * frame.shape[1] / WIN_W), int(ry * frame.shape[0] / WIN_H)
                        fx2, fy2 = int((rx+rw) * frame.shape[1] / WIN_W), int((ry+rh) * frame.shape[0] / WIN_H)
                        crop = frame[max(0, fy1):min(frame.shape[0], fy2), max(0, fx1):min(frame.shape[1], fx2)]
                        if crop.size > 0:
                            captured_surf = cv_to_pygame_surface(crop)
                            puzzle = PuzzleState(captured_surf, difficulty, pygame.Rect(PUZZLE_RECT))
                            state = "puzzle"
                            is_capturing = False
                else:
                    is_capturing = False
                    pygame.draw.rect(screen, PALETTE["accent"], sel_rect, 3, border_radius=4)
                    
                # Crosshairs
                for cx2, cy2 in [p1, p2]:
                    pygame.draw.circle(screen, PALETTE["white"], (int(cx2), int(cy2)), 5)
            else:
                is_capturing = False
                tip = font_md.render("Show BOTH hands!" if len(cursors)==0 else "Waiting for OTHER hand...", True, PALETTE["danger"])
                screen.blit(tip, tip.get_rect(center=(WIN_W//2, WIN_H - 100)))

            render_hand_cursors(screen, cursors)

            if screen_flash > 0:
                s = pygame.Surface((WIN_W, WIN_H))
                s.fill((255,255,255))
                s.set_alpha(int(screen_flash * 255))
                screen.blit(s, (0,0))
                screen_flash -= 0.1

        # ──────────────
        #  PUZZLE
        # ──────────────
        elif state == "puzzle":
            screen.fill(PALETTE["bg"])

            # Left panel
            if frame is not None:
                screen.blit(pygame.transform.scale(cv_to_pygame_surface(frame), CAMERA_RECT.size), CAMERA_RECT)
                pygame.draw.rect(screen, PALETTE["dim"], CAMERA_RECT, 2, border_radius=4)

            info_rect = pygame.Rect(20, 360, 360, 180)
            pygame.draw.rect(screen, PALETTE["panel"], info_rect, border_radius=8)
            pygame.draw.rect(screen, PALETTE["dim"], info_rect, 2, border_radius=8)
            
            solved_c = sum(1 for t in puzzle.tiles if t.locked)
            tot_c  = len(puzzle.tiles)
            pct    = int(solved_c / tot_c * 100)
            
            title = font_md.render(f"Progress: {solved_c}/{tot_c}", True, PALETTE["white"])
            screen.blit(title, (info_rect.x + 20, info_rect.y + 20))
            
            bar_bg = pygame.Rect(info_rect.x+20, info_rect.y+55, 320, 12)
            pygame.draw.rect(screen, PALETTE["bg"], bar_bg, border_radius=6)
            pygame.draw.rect(screen, PALETTE["accent"], pygame.Rect(bar_bg.x, bar_bg.y, int(bar_bg.w*pct/100), bar_bg.h), border_radius=6)
            
            tips = ["PINCH & HOLD to grab tiles", "Snap them into the glowing slots", "ESC → Return to Menu"]
            for i, t in enumerate(tips):
                lbl = font_sm.render(t, True, PALETTE["dim"])
                screen.blit(lbl, (info_rect.x + 20, info_rect.y + 95 + i*22))

            # Render Puzzle
            puzzle.draw(screen)

            # Hand Interactions
            for c in cursors:
                px, py = c["pos"]
                sp = c["smooth_pinch"]
                
                # Grab attempt
                if sp > 0.8:
                    if puzzle.held_tile is None:
                        puzzle.grab(px, py)
                else: # Release attempt
                    if puzzle.held_tile:
                        puzzle.release()

            if puzzle.held_tile and cursors:
                # Find the cursor that is pinching and nearest to the held offset
                # (Simple heuristic: just take the most "pinching" cursor)
                best_c = max(cursors, key=lambda cx: cx["smooth_pinch"])
                puzzle.move(*best_c["pos"])

            render_hand_cursors(screen, cursors)

            if puzzle.solved:
                state = "win"
                Audio.play_win()
                puzzle.held_tile = None
                
            if screen_flash > 0:
                s = pygame.Surface((WIN_W, WIN_H))
                s.fill((255,255,255))
                s.set_alpha(int(screen_flash * 255))
                screen.blit(s, (0,0))
                screen_flash -= 0.1

        # ──────────────
        #  WIN
        # ──────────────
        elif state == "win":
            screen.fill((10, 20, 15))

            if puzzle:
                dim = pygame.Surface((WIN_W, WIN_H))
                dim.fill((10, 20, 15))
                dim.set_alpha(100)
                puzzle.draw(screen)
                screen.blit(dim, (0, 0))

            # Firework particles
            if random.random() < 0.2:
                for _ in range(10): puzzle.add_particles(random.randint(0, WIN_W), WIN_H, random.choice([PALETTE["gold"], PALETTE["accent"]]), 10)
            
            for p in reversed(puzzle.particles):
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vy"] += 0.1
                p["life"] -= 0.015
                if p["life"] <= 0: puzzle.particles.remove(p)
                else: pygame.draw.circle(screen, p["col"], (int(p["x"]), int(p["y"])), int(p["r"]*p["life"]))

            panel = pygame.Rect(0, 0, 640, 360)
            panel.center = (WIN_W//2, WIN_H//2)
            
            s = pygame.Surface(panel.size, pygame.SRCALPHA)
            pygame.draw.rect(s, PALETTE["panel_a"], s.get_rect(), border_radius=15)
            pygame.draw.rect(s, PALETTE["accent"], s.get_rect(), 3, border_radius=15)
            screen.blit(s, panel)

            win_txt = font_xl.render("PUZZLE SOLVED!", True, PALETTE["gold"])
            screen.blit(win_txt, win_txt.get_rect(center=(WIN_W//2, WIN_H//2 - 90)))
            sub_txt = font_md.render("You fixed the image perfectly 🎉", True, PALETTE["white"])
            screen.blit(sub_txt, sub_txt.get_rect(center=(WIN_W//2, WIN_H//2 - 20)))

            any_hov = False
            for c in cursors:
                if win_menu_btn.collidepoint(*c["pos"]):
                    any_hov = True
                    if c["smooth_pinch"] > 0.8:
                        state = "menu"; puzzle = None; Audio.click.play()
            draw_btn_ui(screen, win_menu_btn, "↩ PLAY AGAIN", font_lg, False, any_hov or win_menu_btn.collidepoint(mouse_pos))

            render_hand_cursors(screen, cursors)

        pygame.display.flip()

    cam.stop()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

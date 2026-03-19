import pygame
import numpy as np
import math
import os
import subprocess
import time
import sys
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
import urllib.parse
import webbrowser

VOICE_COMMAND = None

class VoiceServerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        import os
        directory = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format, *args):
        pass
    def do_GET(self):
        global VOICE_COMMAND
        if self.path.startswith('/api/command'):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            if 'c' in params:
                VOICE_COMMAND = params['c'][0].lower()
            
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            super().do_GET()

def start_voice_server():
    try:
        HTTPServer.allow_reuse_address = True
        server = HTTPServer(('127.0.0.1', 8080), VoiceServerHandler)
        print("Voice server started at http://127.0.0.1:8080")
        server.serve_forever()
    except Exception as e:
        print(f"Failed to start voice server: {e}")

# ------ CONFIGURATION ------
import random

LEVEL_CONFIGS = {
    0: {"width": 11, "height": 11, "loop_prob": 0.05},
    1: {"width": 15, "height": 15, "loop_prob": 0.10},
    2: {"width": 21, "height": 21, "loop_prob": 0.15}
}

def generate_random_maze(width, height, loop_prob=0.0):
    """
    Generates a procedural maze using Randomized Depth-First Search (Recursive Backtracking).
    Adds 'fake paths' and loops by breaking walls randomly based on loop_prob.
    Start (0) is placed at (1,1); Goal (2) is placed at the farthest carved connected cell.
    """
    # Ensure dimensions are odd
    if width % 2 == 0: width += 1
    if height % 2 == 0: height += 1
        
    maze = [[1 for _ in range(width)] for _ in range(height)]
    
    # Directions: (dx, dy)
    dirs = [(0, -2), (0, 2), (-2, 0), (2, 0)]
    
    def in_bounds(x, y):
        return 0 < x < width - 1 and 0 < y < height - 1
        
    stack = [(1, 1)]
    maze[1][1] = 0
    distances = {(1, 1): 0}
    
    # DFS Carving
    while stack:
        ux, uy = stack[-1]
        random.shuffle(dirs)
        carved = False
        
        for dx, dy in dirs:
            nx, ny = ux + dx, uy + dy
            if in_bounds(nx, ny) and maze[ny][nx] == 1:
                # Carve through internal wall and destination
                maze[uy + dy//2][ux + dx//2] = 0
                maze[ny][nx] = 0
                stack.append((nx, ny))
                distances[(nx, ny)] = distances[(ux, uy)] + 1
                carved = True
                break
                
        if not carved:
            stack.pop()
            
    # Add fake paths/loops to prevent it being a perfectly linear maze
    if loop_prob > 0:
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if maze[y][x] == 1:
                    # Check if wall separates two passages
                    horiz = maze[y][x-1] == 0 and maze[y][x+1] == 0
                    vert = maze[y-1][x] == 0 and maze[y+1][x] == 0
                    if (horiz or vert) and random.random() < loop_prob:
                        maze[y][x] = 0
                        
    # Find the node farthest from the start to place the goal
    farthest_node = max(distances, key=distances.get)
    maze[farthest_node[1]][farthest_node[0]] = 2
    
    return maze

DIFFICULTIES = {
    "Easy": {"max_noticeable_dist": 6.0, "move_speed": 4.0},
    "Medium": {"max_noticeable_dist": 4.5, "move_speed": 3.0},
    "Hard": {"max_noticeable_dist": 3.0, "move_speed": 2.0}
}

# ------ AUDIO & SYS LOGIC ------
def generate_thump_sound(frequency=80, duration=0.15, sample_rate=44100):
    """
    Generates a low-frequency procedural thump sound for when the player hits a wall.
    Uses a sine wave with a rapid exponential decay envelope for a percussive effect.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    waveform = np.sin(2 * np.pi * frequency * t)
    envelope = np.exp(-t * 30)
    waveform = waveform * envelope * 0.8
    samples = np.int16(waveform * 32767)
    
    # Duplicate for stereo
    stereo = np.empty((samples.shape[0], 2), dtype=np.int16)
    stereo[:, 0] = samples
    stereo[:, 1] = samples
    sound = pygame.sndarray.make_sound(stereo)
    return sound

def generate_sonar_ping(frequency=700, duration=0.15, sample_rate=44100):
    """
    Generates a soft, higher-frequency 'ping' sound for the goal proximity indicator.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    waveform = np.sin(2 * np.pi * frequency * t)
    # Quick attack, exponential decay
    envelope = np.exp(-t * 20)
    waveform = waveform * envelope * 0.3
    samples = np.int16(waveform * 32767)
    
    stereo = np.empty((samples.shape[0], 2), dtype=np.int16)
    stereo[:, 0] = samples
    stereo[:, 1] = samples
    return pygame.sndarray.make_sound(stereo)

def generate_tone(frequency, duration=0.25, sample_rate=44100, volume=0.15, mod_rate=4.0):
    """
    Generates a short loopable sine tone with subtle amplitude modulation (tremolo).
    Used as the continuous drone sound that shifts frequency based on wall distance.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    waveform = np.sin(2 * np.pi * frequency * t)
    # Subtle amplitude modulation for a warm, modular feel
    modulation = 1.0 - 0.3 * np.sin(2 * np.pi * mod_rate * t)
    waveform = waveform * modulation * volume
    samples = np.int16(waveform * 32767)
    
    stereo = np.empty((samples.shape[0], 2), dtype=np.int16)
    stereo[:, 0] = samples
    stereo[:, 1] = samples
    return pygame.sndarray.make_sound(stereo)

def build_tone_table(num_steps=15, freq_low=50, freq_high=120):
    """
    Pre-generates an array of tones from low to high frequency.
    This array is used as a lookup table during gameplay to avoid generating tones on the fly.
    """
    tones = []
    for i in range(num_steps):
        ratio = i / (num_steps - 1)
        freq = freq_low + (freq_high - freq_low) * ratio
        tones.append(generate_tone(freq))
    return tones

def generate_ambient_noise(duration=0.5, sample_rate=44100, volume=0.2):
    """
    Generates a soft white noise/wind sound for spatial audio.
    Used to indicate openings to the left and right.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Generate white noise and apply a simple envelope
    noise = np.random.uniform(-1, 1, len(t))
    # Heavier low pass filter effect by smoothing with a large window for a dark "rumbling" sound
    smoothed = np.convolve(noise, np.ones(30)/30, mode='same')
    
    waveform = smoothed * volume
    samples = np.int16(waveform * 32767)
    
    stereo = np.empty((samples.shape[0], 2), dtype=np.int16)
    stereo[:, 0] = samples
    stereo[:, 1] = samples
    return pygame.sndarray.make_sound(stereo)

def angle_to_direction(angle):
    """Convert angle in degrees to cardinal direction name."""
    a = int(angle) % 360
    if a == 0:
        return "East"
    elif a == 90:
        return "South"
    elif a == 180:
        return "West"
    elif a == 270:
        return "North"
    return ""

def speak(text):
    subprocess.Popen(
        ['powershell', '-Command', f"Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Volume = 40; $synth.Speak('{text}');"],
        creationflags=subprocess.CREATE_NO_WINDOW
    )

class Player:
    """Stores the player's 2D grid position and facing angle."""
    def __init__(self, x, y, angle):
        self.x = float(x)
        self.y = float(y)
        self.angle = float(angle) # in degrees
        
        # Visual lerping properties for smooth camera
        self.visual_x = self.x
        self.visual_y = self.y
        self.visual_angle = self.angle

def cast_ray(maze, px, py, angle_deg):
    """
    Casts a 2D ray from (px, py) in the given direction.
    Steps forward incrementally until it hits a wall cell (1),
    returning the straight-line distance to that wall.
    """
    angle_rad = math.radians(angle_deg)
    dx = math.cos(angle_rad)
    dy = math.sin(angle_rad)
    
    step_size = 0.05
    distance = 0.0
    max_distance = 15.0
    
    while distance < max_distance:
        distance += step_size
        test_x = int(px + dx * distance)
        test_y = int(py + dy * distance)
        
        if test_y < 0 or test_y >= len(maze) or test_x < 0 or test_x >= len(maze[0]):
            return distance
        if maze[test_y][test_x] == 1:
            return distance
            
    return max_distance

# ------ UI SYSTEM ------
class ToggleButton:
    def __init__(self, x, y, w, h, text, font, val):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.val = val
        self.is_hovered = False
        self.is_selected = False

        self.color_base = (20, 40, 20)
        self.color_hover = (40, 80, 40)
        self.color_sel = (0, 255, 100)
        self.color_text = (0, 255, 100)

    def draw(self, screen):
        color = self.color_sel if self.is_selected else (self.color_hover if self.is_hovered else self.color_base)
        border_col = (0, 255, 100) if self.is_selected else self.color_hover
        
        if self.is_selected:
            pygame.draw.rect(screen, (0, 100, 40), self.rect.inflate(8, 8), border_radius=5)

        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        pygame.draw.rect(screen, border_col, self.rect, 2, border_radius=5)

        t_col = (0, 40, 10) if self.is_selected else self.color_text
        text_surf = self.font.render(self.text, True, t_col)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                return True
        return False

# ------ EFFECTS ------
def draw_radar_cone(screen, x, y, angle_deg, length, color):
    surf = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
    points = [(x, y)]
    spread = 30 
    
    for a in range(int(angle_deg - spread/2), int(angle_deg + spread/2) + 1, 5):
        rad = math.radians(a)
        ex = x + math.cos(rad) * length
        ey = y + math.sin(rad) * length
        points.append((ex, ey))
    
    pygame.draw.polygon(surf, (*color, 60), points)
    pygame.draw.polygon(surf, (*color, 150), points, 2)
    screen.blit(surf, (0, 0))

# ------ MAIN LOOPS ------
def menu_loop(screen, clock):
    font_large = pygame.font.SysFont("Courier", 48, bold=True)
    font_med = pygame.font.SysFont("Courier", 24, bold=True)
    
    lv_btns = [
        ToggleButton(100, 200, 140, 50, "Level 1", font_med, 0),
        ToggleButton(260, 200, 140, 50, "Level 2", font_med, 1),
        ToggleButton(420, 200, 140, 50, "Level 3", font_med, 2),
    ]
    lv_btns[0].is_selected = True
    selected_level = 0
    
    df_btns = [
        ToggleButton(100, 320, 140, 50, "Easy", font_med, "Easy"),
        ToggleButton(260, 320, 140, 50, "Medium", font_med, "Medium"),
        ToggleButton(420, 320, 140, 50, "Hard", font_med, "Hard"),
    ]
    df_btns[1].is_selected = True
    selected_diff = "Medium"
    
    start_btn = ToggleButton(260, 420, 140, 60, "START", font_large, None)
    
    running = True
    while running:
        clock.tick(60)
        pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            for btn in lv_btns:
                if btn.handle_event(event):
                    for b in lv_btns: b.is_selected = False
                    btn.is_selected = True
                    selected_level = btn.val
                    speak(f"Level {btn.val + 1}")
            
            for btn in df_btns:
                if btn.handle_event(event):
                    for b in df_btns: b.is_selected = False
                    btn.is_selected = True
                    selected_diff = btn.val
                    speak(btn.val)
                    
            if start_btn.handle_event(event):
                running = False
        
        for btn in lv_btns + df_btns + [start_btn]:
            btn.check_hover(pos)
            
        screen.fill((5, 15, 5))
        pygame.draw.circle(screen, (10, 30, 10), (330, 250), 250, 2)
        pygame.draw.circle(screen, (10, 30, 10), (330, 250), 150, 2)
        
        title_surf = font_large.render("AUDIO MAZE", True, (0, 255, 100))
        title_rect = title_surf.get_rect(center=(330, 70))
        screen.blit(title_surf, title_rect)
        
        pygame.draw.line(screen, (0, 255, 100), (80, 110), (580, 110), 3)
        
        lab1 = font_med.render("Select Level:", True, (0, 200, 80))
        screen.blit(lab1, (100, 150))
        
        lab2 = font_med.render("Select Difficulty:", True, (0, 200, 80))
        screen.blit(lab2, (100, 270))
        
        for btn in lv_btns + df_btns + [start_btn]:
            btn.draw(screen)
            
        pygame.display.flip()
        
    return selected_level, selected_diff

def game_loop(screen, clock, level_idx, diff_key):
    global VOICE_COMMAND
    config = LEVEL_CONFIGS[level_idx]
    maze = generate_random_maze(config["width"], config["height"], config["loop_prob"])
    diff = DIFFICULTIES[diff_key]
    
    thump_sound = generate_thump_sound()
    sonar_sound = generate_sonar_ping()
    tone_table = build_tone_table()
    
    tone_channel = pygame.mixer.Channel(1)
    sonar_channel = pygame.mixer.Channel(3)
    current_tone_idx = -1
    last_sonar_time = time.time()
    
    # Ambient sound for spatial left/right opening cues
    ambient_sound = generate_ambient_noise()
    ambient_channel = pygame.mixer.Channel(2)
    ambient_channel.play(ambient_sound, loops=-1)
    ambient_channel.set_volume(0.0) # Start muted
    
    # Find goal position (cell == 2). Start is always (1,1) by algorithm design.
    goal_x, goal_y = 0, 0
    start_r, start_c = 1, 1
    for r in range(len(maze)):
        for c in range(len(maze[0])):
            if maze[r][c] == 2:
                goal_x, goal_y = c + 0.5, r + 0.5
    
    player = Player(start_c + 0.5, start_r + 0.5, 0)
    
    # Calculate general goal direction based on start coordinates
    dx = goal_x - player.x
    dy = goal_y - player.y
    dir_str = ""
    if dy < -2: dir_str += "North "
    elif dy > 2: dir_str += "South "
    
    if dx > 2: dir_str += "East"
    elif dx < -2: dir_str += "West"
    dir_str = dir_str.strip() or "Nearby"
    
    speak(f"START LEVEL {level_idx + 1}. Facing East. The goal is generally to the {dir_str}.")
    
    move_speed = diff["move_speed"]
    rot_speed = 150.0
    max_noticeable_dist = diff["max_noticeable_dist"]
    
    cell_size = 40

    running = True
    won = False

    def handle_movement(key_code):
        nonlocal won
        if key_code == pygame.K_a:
            player.angle -= 90.0
            player.angle %= 360.0
            direction = angle_to_direction(player.angle)
            if direction:
                speak(direction)
        elif key_code == pygame.K_d:
            player.angle += 90.0
            player.angle %= 360.0
            direction = angle_to_direction(player.angle)
            if direction:
                speak(direction)
        # W key (Move Forward)
        elif key_code == pygame.K_w:
            rad = math.radians(player.angle)
            new_x = player.x + round(math.cos(rad))
            new_y = player.y + round(math.sin(rad))
            map_x, map_y = int(new_x), int(new_y)
            
            # Check bounds and collision
            if 0 <= map_y < len(maze) and 0 <= map_x < len(maze[0]):
                cell = maze[map_y][map_x]
                if cell != 1:  # Not a wall
                    player.x = new_x
                    player.y = new_y
                    if cell == 2:  # Reached the goal
                        won = True
                        speak("CONGRATULATIONS")
                else:  # Hit a wall
                    thump_sound.play()
                    
        # S key (Move Backward)
        elif key_code == pygame.K_s:
            rad = math.radians(player.angle)
            new_x = player.x - round(math.cos(rad))
            new_y = player.y - round(math.sin(rad))
            map_x, map_y = int(new_x), int(new_y)
            
            if 0 <= map_y < len(maze) and 0 <= map_x < len(maze[0]):
                cell = maze[map_y][map_x]
                if cell != 1:
                    player.x = new_x
                    player.y = new_y
                    if cell == 2:
                        won = True
                        speak("CONGRATULATIONS")
                else:
                    thump_sound.play()

    while running:
        dt = clock.tick(60) / 1000.0
        
        current_voice_cmd = VOICE_COMMAND
        VOICE_COMMAND = None
        
        voice_event = None
        if current_voice_cmd == "forward":
            voice_event = pygame.K_w
        elif current_voice_cmd == "backward":
            voice_event = pygame.K_s
        elif current_voice_cmd == "left":
            voice_event = pygame.K_a
        elif current_voice_cmd == "right":
            voice_event = pygame.K_d
            
        if not won and voice_event is not None:
            handle_movement(voice_event)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.KEYDOWN:
                if won:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
                        return 
                else:
                    handle_movement(event.key)
                
        if not won:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]:
                return
        
        if not won:
            # 1. Front distance sensing (Drone tone)
            dist_front = cast_ray(maze, player.x, player.y, player.angle)
            
            # Map distance to drone tone frequency: closer = higher index (higher freq)
            normalized_dist = min(dist_front, max_noticeable_dist) / max_noticeable_dist
            tone_idx = int((1.0 - normalized_dist) * (len(tone_table) - 1))
            tone_idx = max(0, min(tone_idx, len(tone_table) - 1))
            
            if tone_idx != current_tone_idx:
                current_tone_idx = tone_idx
                tone_channel.play(tone_table[tone_idx], loops=-1)
            
            # 2. Spatial Audio for openings (Left/Right)
            dist_left = cast_ray(maze, player.x, player.y, player.angle - 90)
            dist_right = cast_ray(maze, player.x, player.y, player.angle + 90)
            
            # Threshold for considering an opening "wide enough" to make sound
            opening_threshold = 1.5 
            
            vol_l = 0.0
            vol_r = 0.0
            
            # If left opening is deep, pan noise to left ear
            if dist_left > opening_threshold:
                # Closer openings are louder
                vol_l = min(1.0, dist_left / max_noticeable_dist) * 1.0 
                
            # If right opening is deep, pan noise to right ear
            if dist_right > opening_threshold:
                vol_r = min(1.0, dist_right / max_noticeable_dist) * 1.0
                
            ambient_channel.set_volume(vol_l, vol_r)
            
            # 3. Goal Proximity Sonar Ping
            goal_dist = math.sqrt((player.x - goal_x) ** 2 + (player.y - goal_y) ** 2)
            
            # Distance mapping to pulse interval: 15m away = 2.0s interval. 0m away = 0.2s interval.
            pulse_interval = max(0.2, min(2.0, (goal_dist / 15.0) * 1.8 + 0.2))
            
            if time.time() - last_sonar_time > pulse_interval:
                sonar_channel.play(sonar_sound)
                last_sonar_time = time.time()
                
        else:
            if tone_channel.get_busy():
                tone_channel.stop()
            if sonar_channel.get_busy():
                sonar_channel.stop()
        # --- UPDATE VISUAL LERPING ---
        lerp_speed = 12.0 * dt
        player.visual_x += (player.x - player.visual_x) * lerp_speed
        player.visual_y += (player.y - player.visual_y) * lerp_speed
        
        # Shortest path angle lerp
        diff_angle = (player.angle - player.visual_angle + 180) % 360 - 180
        player.visual_angle += diff_angle * lerp_speed
        
        # --- HUD & RENDERING ---
        screen.fill((5, 15, 5))
        
        # Screen center = permanent player screen position
        cx = screen.get_width() // 2
        cy = screen.get_height() // 2
        
        # Calculate world rotation so player visually always faces UP (-90 degrees in Pygame)
        world_angle_deg = -90 - player.visual_angle
        world_rad = math.radians(world_angle_deg)
        cos_a = math.cos(world_rad)
        sin_a = math.sin(world_rad)
        
        def world_to_screen(wx, wy):
            # Translate relative to player's visual position
            dx = wx - player.visual_x
            dy = wy - player.visual_y
            # 2D Rotation
            rx = dx * cos_a - dy * sin_a
            ry = dx * sin_a + dy * cos_a
            # Scale and translate to screen center
            return (cx + rx * cell_size, cy + ry * cell_size)

        for r in range(len(maze)):
            for c in range(len(maze[0])):
                cell = maze[r][c]
                if cell == 0: continue
                
                # Calculate the 4 corners of the cell in world coordinates -> screen coordinates
                pts = [
                    world_to_screen(c, r),
                    world_to_screen(c + 1, r),
                    world_to_screen(c + 1, r + 1),
                    world_to_screen(c, r + 1)
                ]
                
                if cell == 1:
                    pygame.draw.polygon(screen, (0, 40, 15), pts)
                    pygame.draw.polygon(screen, (0, 255, 100), pts, 1)
                elif cell == 2:
                    pulse = abs(math.sin(time.time() * 5)) * 155
                    pygame.draw.polygon(screen, (100, 100 + pulse, 100), pts)
        
        if not won:
            # We use logical player.angle/x/y for the text HUD so it responds instantly
            dist = cast_ray(maze, player.x, player.y, player.angle)
            
            # Radar cone visually tied to the HUD (points straight UP constantly)
            # The length is based on the logic raycast, but drawn from the center
            draw_radar_cone(screen, cx, cy, -90, dist * cell_size, (0, 255, 100))
            
            # Draw fixed player position
            pygame.draw.circle(screen, (150, 255, 150), (cx, cy), 6)
            pygame.draw.circle(screen, (0, 255, 100), (cx, cy), 10, 2)
            
            font_sm = pygame.font.SysFont("Courier", 18)
            goal_dist = math.sqrt((player.x - goal_x) ** 2 + (player.y - goal_y) ** 2)
            facing = angle_to_direction(player.angle)
            info = font_sm.render(f"Wall: {dist:.1f}m | Goal: {goal_dist:.1f}m | Facing: {facing}", True, (0, 200, 80))
            screen.blit(info, (10, 10))
            esc_info = font_sm.render("ESC to Menu", True, (0, 200, 80))
            screen.blit(esc_info, (screen.get_width() - 150, 10))
            
        else:
            overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
            overlay.fill((0, 255, 100, 128))
            screen.blit(overlay, (0, 0))
            
            font_win = pygame.font.SysFont("Courier", 64, bold=True)
            win_surf = font_win.render("EXIT REACHED!", True, (255, 255, 255))
            win_rect = win_surf.get_rect(center=(screen.get_width()//2, screen.get_height()//2 - 30))
            screen.blit(win_surf, win_rect)
            
            ret_surf = pygame.font.SysFont("Courier", 24).render("Press ENTER to return", True, (20, 80, 20))
            ret_rect = ret_surf.get_rect(center=(screen.get_width()//2, screen.get_height()//2 + 40))
            screen.blit(ret_surf, ret_rect)
            
        pygame.display.flip()

def main():
    server_thread = threading.Thread(target=start_voice_server, daemon=True)
    server_thread.start()
    webbrowser.open('http://127.0.0.1:8080/voice_controller.html')

    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.init()
    
    screen = pygame.display.set_mode((660, 500))
    pygame.display.set_caption("Audio Maze For the Blind")
    clock = pygame.time.Clock()
    
    while True:
        level_idx, diff_key = menu_loop(screen, clock)
        game_loop(screen, clock, level_idx, diff_key)

if __name__ == "__main__":
    main()

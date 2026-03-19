import pygame
import numpy as np
import math
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
MAZE_LEVELS = [
    # Level 1
    [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1, 0, 0, 0, 2, 1],
        [1, 0, 1, 0, 1, 0, 1, 1, 1, 1],
        [1, 0, 1, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 1, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 1, 0, 0, 1],
        [1, 1, 1, 1, 1, 0, 1, 0, 1, 1],
        [1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 1, 1, 0, 1, 1, 1, 1, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    ],
    # Level 2
    [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1],
        [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],
        [1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1],
        [1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 2, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    ],
    # Level 3
    [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 2, 1],
        [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1],
        [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    ]
]

DIFFICULTIES = {
    "Easy": {"max_noticeable_dist": 6.0, "move_speed": 4.0},
    "Medium": {"max_noticeable_dist": 4.5, "move_speed": 3.0},
    "Hard": {"max_noticeable_dist": 3.0, "move_speed": 2.0}
}

# ------ AUDIO & SYS LOGIC ------
def generate_tick_sound(frequency=880, duration=0.03, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    waveform = np.sin(2 * np.pi * frequency * t)
    envelope = np.exp(-t * 200)
    waveform = waveform * envelope
    samples = np.int16(waveform * 32767)
    stereo = np.empty((samples.shape[0], 2), dtype=np.int16)
    stereo[:, 0] = samples
    stereo[:, 1] = samples
    sound = pygame.sndarray.make_sound(stereo)
    return sound

def speak(text):
    subprocess.Popen(
        ['powershell', '-Command', f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{text}');"],
        creationflags=subprocess.CREATE_NO_WINDOW
    )

class Player:
    def __init__(self, x, y, angle):
        self.x = float(x)
        self.y = float(y)
        self.angle = float(angle) # in degrees

def cast_ray(maze, px, py, angle_deg):
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
    maze = MAZE_LEVELS[level_idx]
    diff = DIFFICULTIES[diff_key]
    
    tick_sound = generate_tick_sound()
    
    start_r, start_c = 1, 1
    for r in range(len(maze)):
        for c in range(len(maze[0])):
            if maze[r][c] == 0:
                start_r, start_c = r, c
                break
        else:
            continue
        break
        
    player = Player(start_c + 0.5, start_r + 0.5, 0)
    
    speak(f"START LEVEL {level_idx + 1}")
    
    last_tick_time = time.time()
    
    move_speed = diff["move_speed"]
    rot_speed = 150.0
    max_noticeable_dist = diff["max_noticeable_dist"]
    
    cell_size = 40
    map_w = len(maze[0]) * cell_size
    map_h = len(maze) * cell_size
    offset_x = (screen.get_width() - map_w) // 2
    offset_y = (screen.get_height() - map_h) // 2

    running = True
    won = False

    def handle_movement(key_code):
        nonlocal won
        if key_code == pygame.K_a:
            player.angle -= 90.0
            player.angle %= 360.0
        elif key_code == pygame.K_d:
            player.angle += 90.0
            player.angle %= 360.0
        elif key_code == pygame.K_w:
            rad = math.radians(player.angle)
            new_x = player.x + round(math.cos(rad))
            new_y = player.y + round(math.sin(rad))
            map_x, map_y = int(new_x), int(new_y)
            
            if 0 <= map_y < len(maze) and 0 <= map_x < len(maze[0]):
                cell = maze[map_y][map_x]
                if cell != 1:
                    player.x = new_x
                    player.y = new_y
                    if cell == 2:
                        won = True
                        speak("CONGRATULATIONS")
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
            dist = cast_ray(maze, player.x, player.y, player.angle)
            min_delay, max_delay = 0.05, 1.0
            
            normalized_dist = min(dist, max_noticeable_dist) / max_noticeable_dist
            tick_delay = min_delay + (max_delay - min_delay) * normalized_dist
            
            current_time = time.time()
            if current_time - last_tick_time >= tick_delay:
                tick_sound.play()
                last_tick_time = current_time
        
        screen.fill((5, 15, 5))
        
        for r in range(len(maze)):
            for c in range(len(maze[0])):
                x = offset_x + c * cell_size
                y = offset_y + r * cell_size
                if maze[r][c] == 1:
                    pygame.draw.rect(screen, (0, 255, 100), (x, y, cell_size, cell_size), 1)
                    pygame.draw.rect(screen, (0, 40, 15), (x+1, y+1, cell_size-2, cell_size-2))
                elif maze[r][c] == 2:
                    pulse = abs(math.sin(time.time() * 5)) * 155
                    pygame.draw.rect(screen, (100, 100 + pulse, 100), (x, y, cell_size, cell_size))
        
        px_screen = int(offset_x + player.x * cell_size)
        py_screen = int(offset_y + player.y * cell_size)
        
        if not won:
            dist = cast_ray(maze, player.x, player.y, player.angle)
            draw_radar_cone(screen, px_screen, py_screen, player.angle, dist * cell_size, (0, 255, 100))
            
            pygame.draw.circle(screen, (150, 255, 150), (px_screen, py_screen), 6)
            pygame.draw.circle(screen, (0, 255, 100), (px_screen, py_screen), 10, 2)
            
            font_sm = pygame.font.SysFont("Courier", 18)
            info = font_sm.render(f"Dist: {dist:.1f}m | Ticking at {dist/max_noticeable_dist:.1f}x", True, (0, 200, 80))
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

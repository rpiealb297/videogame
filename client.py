import pygame
import socket
import json
import threading
import os

# --- CONFIGURACIÓN ---
WIDTH, HEIGHT = 800, 600
ORIGINAL_SPRITE_SIZE = 16
SCALE_FACTOR = 2
PLAYER_SIZE = ORIGINAL_SPRITE_SIZE * SCALE_FACTOR
OBJ_SIZE = 50
ANIMATION_SPEED = 150

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Verdana", 14)
chat_font = pygame.font.SysFont("Verdana", 12)

class PlayerSprite:
    def __init__(self):
        self.animations = {
            'idle': self.load_spritesheet('images/character/Idle.png'),
            'walk': self.load_spritesheet('images/character/Walk.png')
        }
        self.state = 'idle'
        self.direction = 0
        self.frame_index = 0
        self.last_update = pygame.time.get_ticks()

    def load_spritesheet(self, filename):
        if not os.path.exists(filename):
            return None
        sheet = pygame.image.load(filename).convert_alpha()
        sheet_width, _ = sheet.get_size()
        cols = sheet_width // ORIGINAL_SPRITE_SIZE
        animation_database = []
        for row in range(4):
            row_frames = []
            for col in range(cols):
                rect = pygame.Rect(col * ORIGINAL_SPRITE_SIZE, row * ORIGINAL_SPRITE_SIZE, ORIGINAL_SPRITE_SIZE, ORIGINAL_SPRITE_SIZE)
                frame = pygame.Surface((ORIGINAL_SPRITE_SIZE, ORIGINAL_SPRITE_SIZE), pygame.SRCALPHA)
                frame.blit(sheet, (0, 0), rect)
                scaled_frame = pygame.transform.scale(frame, (PLAYER_SIZE, PLAYER_SIZE))
                row_frames.append(scaled_frame)
            animation_database.append(row_frames)
        return animation_database

class GameClient:
    def __init__(self):
        if os.environ.get('WSL_DISTRO_NAME'): os.environ['SDL_AUDIODRIVER'] = 'dummy'
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(('127.0.0.1', 5555))
        
        raw_init = self.client.recv(4096).decode().split('\n')[0]
        init_data = json.loads(raw_init)
        self.my_id = init_data["id"]
        self.map_data = init_data["map"]
        self.obstacles = [pygame.Rect(o["x"], o["y"], OBJ_SIZE, OBJ_SIZE) for o in self.map_data.get("objects", [])]
        
        self.pos = pygame.Vector2(100, 100)
        self.my_sprite_system = PlayerSprite()
        self.other_players = {}
        self.chat_log = []
        self.input_text = ""
        self.chatting = False
        self.running = True
        
        threading.Thread(target=self.receive_data, daemon=True).start()

    def receive_data(self):
        while self.running:
            try:
                data = self.client.recv(8192).decode()
                if not data: break
                for m in data.strip().split('\n'):
                    if not m: continue
                    msg = json.loads(m)
                    if msg["type"] == "sync":
                        self.other_players = msg["players"]
                    elif msg["type"] == "chat":
                        self.chat_log.append(f"{msg['user']}: {msg['text']}")
            except: break

    def update(self):
        new_state = 'idle'
        if not self.chatting:
            keys = pygame.key.get_pressed()
            new_pos = self.pos.copy()
            moving = False
            if keys[pygame.K_a]: new_pos.x -= 4; self.my_sprite_system.direction = 3; moving = True
            elif keys[pygame.K_d]: new_pos.x += 4; self.my_sprite_system.direction = 2; moving = True
            if keys[pygame.K_w]: new_pos.y -= 4; self.my_sprite_system.direction = 1; moving = True
            elif keys[pygame.K_s]: new_pos.y += 4; self.my_sprite_system.direction = 0; moving = True

            # Una forma más elegante de escribir los límites de pantalla:
            if 0 <= new_pos.x <= WIDTH - PLAYER_SIZE and 0 <= new_pos.y <= HEIGHT - PLAYER_SIZE:
                temp_rect = pygame.Rect(new_pos.x, new_pos.y, PLAYER_SIZE, PLAYER_SIZE)
                collision = False
                for obs in self.obstacles:
                    if temp_rect.colliderect(obs):
                        collision = True
                        break
                if not collision:
                    self.pos = new_pos
            if moving: new_state = 'walk'

        self.my_sprite_system.state = new_state
        # Temporizador de animación
        if pygame.time.get_ticks() - self.my_sprite_system.last_update > ANIMATION_SPEED:
            self.my_sprite_system.last_update = pygame.time.get_ticks()
            self.my_sprite_system.frame_index += 1

        try:
            payload = {"type": "update", "pos": {"x": self.pos.x, "y": self.pos.y}, 
                       "anim_state": self.my_sprite_system.state, "direction": self.my_sprite_system.direction}
            self.client.send((json.dumps(payload) + "\n").encode())
        except: pass

    def draw(self):
        screen.fill((50, 50, 50))
        for obj in self.map_data.get("objects", []):
            pygame.draw.rect(screen, obj["color"], (obj["x"], obj["y"], OBJ_SIZE, OBJ_SIZE))
            
        for pid, pdata in self.other_players.items():
            if "pos" not in pdata: continue
            ppos = pdata["pos"]
            p_state = pdata.get("anim_state", "idle")
            p_dir = pdata.get("direction", 0)
            
            try:
                anim_data = self.my_sprite_system.animations[p_state]
                if anim_data:
                    row = anim_data[p_dir]
                    f_idx = self.my_sprite_system.frame_index % len(row)
                    screen.blit(row[f_idx], (ppos["x"], ppos["y"]))
                else: raise ValueError
            except:
                pygame.draw.rect(screen, (200, 200, 200), (ppos["x"], ppos["y"], PLAYER_SIZE, PLAYER_SIZE))

            name_tag = font.render(pid, True, (255, 255, 255))
            screen.blit(name_tag, (ppos["x"] - 5, ppos["y"] - 20))

        # Chat
        chat_y = HEIGHT - 60
        if self.chat_log:
            bg = pygame.Surface((350, 100)); bg.set_alpha(150); bg.fill((20, 20, 20))
            screen.blit(bg, (10, chat_y - 110))
            for i, line in enumerate(reversed(self.chat_log[-5:])):
                screen.blit(chat_font.render(line, True, (255, 255, 255)), (15, chat_y - 30 - (i * 20)))
        
        if self.chatting:
            pygame.draw.rect(screen, (0,0,0), (10, chat_y, 350, 30))
            pygame.draw.rect(screen, (255,255,0), (10, chat_y, 350, 30), 1)
            screen.blit(chat_font.render(f"CHAT: {self.input_text}_", True, (255, 255, 0)), (15, chat_y + 7))
            
        pygame.display.flip()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.chatting and self.input_text.strip():
                            self.client.send((json.dumps({"type": "chat", "text": self.input_text}) + "\n").encode())
                            self.input_text = ""
                        self.chatting = not self.chatting
                    elif self.chatting:
                        if event.key == pygame.K_BACKSPACE: self.input_text = self.input_text[:-1]
                        else: self.input_text += event.unicode
            self.update()
            self.draw()
            clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    GameClient().run()
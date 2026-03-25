import pygame
import socket
import json
import threading
import os
from core import constants

# --- CONFIGURACIÓN DEL RECORTE DE OBJETOS (tileset) ---
# Define aquí qué región de 'House.png' es la casa real.
OBJECT_SPRITE_CONFIG = {
    "casa": {
        "path": "images/objects/House.png",
        # --- AJUSTAR AQUÍ --- Coordenadas del tileset
        "src_x": 150,       # Píxel X donde empieza la casa en el .png
        "src_y": 0,       # Píxel Y donde empieza la casa en el .png
        "src_w": 75,      # Ancho original de la casa en el .png
        "src_h": 100,      # Alto original de la casa en el .png
        # ---------------------
        # Tamaño final en el juego (escalado)
        "display_w": 64 * 1.5, # Ejemplo: escalado un poco
        "display_h": 64 * 1.5
    },

    "valla": {
        "path": "images/objects/valla.png",
        # --- AJUSTAR AQUÍ --- Coordenadas del tileset
        "src_x": 0,       # Píxel X donde empieza la casa en el .png
        "src_y": 0,       # Píxel Y donde empieza la casa en el .png
        "src_w": 50,      # Ancho original de la casa en el .png
        "src_h": 50,      # Alto original de la casa en el .png
        # ---------------------
        # Tamaño final en el juego (escalado)
        "display_w": 32 * 1.5, # Ejemplo: escalado un poco
        "display_h": 32 * 1.5
    }
}

pygame.init()
screen = pygame.display.set_mode((constants.WIDTH, constants.HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Verdana", 14)
chat_font = pygame.font.SysFont("Verdana", 12)

# --- GESTOR DE IMÁGENES DE OBJETOS ACTUALIZADO (con recorte) ---
class ObjectManager:
    def __init__(self):
        self.images = {}
        # Diccionario para guardar los Rects de colisión escalados
        self.collision_rects = {} 
        self.load_assets()

    def load_assets(self):
        for obj_type, config in OBJECT_SPRITE_CONFIG.items():
            path = config["path"]
            if not os.path.exists(path):
                print(f"Aviso Senior: No se encontró tileset para '{obj_type}' en {path}")
                continue

            try:
                # 1. Cargar el tileset completo
                tileset = pygame.image.load(path).convert_alpha()
                
                # 2. Definir la región de recorte (src_rect)
                src_rect = pygame.Rect(config["src_x"], config["src_y"], config["src_w"], config["src_h"])
                
                # 3. RECORTE SENIOR: Crear una superficie vacía y pegar solo el recorte
                cropped_img = pygame.Surface((config["src_w"], config["src_h"]), pygame.SRCALPHA)
                cropped_img.blit(tileset, (0, 0), src_rect)
                
                # 4. Escalar la imagen final
                final_w = int(config["display_w"])
                final_h = int(config["display_h"])
                final_img = pygame.transform.scale(cropped_img, (final_w, final_h))
                
                self.images[obj_type] = final_img
                
                # Guardamos el tamaño escalado para las colisiones dinámicas
                self.collision_rects[obj_type] = pygame.Rect(0, 0, final_w, final_h)
                
            except Exception as e:
                print(f"Error cargando objeto '{obj_type}': {e}")

    def get_image(self, obj_type):
        return self.images.get(obj_type)
        
    def get_collision_size(self, obj_type):
        """Devuelve (ancho, alto) escalado para las colisiones."""
        if obj_type in self.collision_rects:
            r = self.collision_rects[obj_type]
            return r.width, r.height
        return 50, 50 # Tamaño por defecto si no es sprite

class PlayerSprite:
    def __init__(self):
        self.animations = {
            'idle': self.load_spritesheet('images/character/Idle.png'),
            'walk': self.load_spritesheet('images/character/Walk.png')
        }
        self.state = 'idle'
        self.direction = 0 # 0: Abajo, 1: Arriba, 2: Derecha, 3: Izquierda
        self.frame_index = 0
        self.last_update = pygame.time.get_ticks()

    def load_spritesheet(self, filename):
        if not os.path.exists(filename):
            print(f"Advertencia: No se encontró {filename}")
            return None
            
        sheet = pygame.image.load(filename).convert_alpha()
        sheet_width, sheet_height = sheet.get_size()
        cols = sheet_width // constants.ORIGINAL_SPRITE_SIZE
        rows_in_file = sheet_height // constants.ORIGINAL_SPRITE_SIZE
        
        animation_database = []
        
        for row in range(min(rows_in_file, 4)):
            row_frames = []
            for col in range(cols):
                rect = pygame.Rect(col * constants.ORIGINAL_SPRITE_SIZE, row * constants.ORIGINAL_SPRITE_SIZE, constants.ORIGINAL_SPRITE_SIZE, constants.ORIGINAL_SPRITE_SIZE)
                frame = pygame.Surface((constants.ORIGINAL_SPRITE_SIZE, constants.ORIGINAL_SPRITE_SIZE), pygame.SRCALPHA)
                frame.blit(sheet, (0, 0), rect)
                scaled_frame = pygame.transform.scale(frame, (constants.PLAYER_SIZE, constants.PLAYER_SIZE))
                row_frames.append(scaled_frame)
            animation_database.append(row_frames)
        
        if len(animation_database) == 3:
            right_frames = animation_database[2]
            left_frames = [pygame.transform.flip(f, True, False) for f in right_frames]
            animation_database.append(left_frames)
            
        return animation_database

class GameClient:
    def __init__(self):
        if os.environ.get('WSL_DISTRO_NAME'): os.environ['SDL_AUDIODRIVER'] = 'dummy'
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.client.connect(('127.0.0.1', 5555))
        except:
            print("No se pudo conectar al servidor.")
            os._exit(1)
        
        raw_init = self.client.recv(4096).decode().split('\n')[0]
        init_data = json.loads(raw_init)
        self.my_id = init_data["id"]
        self.map_data = init_data["map"]
        
        # Gestor de objetos debe inicializarse ANTES que los obstáculos
        self.obj_manager = ObjectManager() 
        
        # --- GENERACIÓN DE OBSTÁCULOS DINÁMICOS ---
        # Ahora el tamaño de la colisión depende de si el objeto tiene sprite o no
        self.obstacles = []
        for o in self.map_data.get("objects", []):
            obj_type = o.get("tipo", "").lower()
            img = self.obj_manager.get_image(obj_type)
            
            if img:
                w, h = self.obj_manager.get_collision_size(obj_type)
                # La colisión coincide con el sprite
                self.obstacles.append(pygame.Rect(o["x"], o["y"], w, h))
            else:
                # Colisión genérica (50x50) para rectángulos de color
                self.obstacles.append(pygame.Rect(o["x"], o["y"], 50, 50))
        
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
            
            if keys[pygame.K_a]: 
                new_pos.x -= 4
                self.my_sprite_system.direction = 3
                moving = True
            elif keys[pygame.K_d]: 
                new_pos.x += 4
                self.my_sprite_system.direction = 2
                moving = True
            
            if keys[pygame.K_w]: 
                new_pos.y -= 4
                if not moving: self.my_sprite_system.direction = 1
                moving = True
            elif keys[pygame.K_s]: 
                new_pos.y += 4
                if not moving: self.my_sprite_system.direction = 0
                moving = True

            if 0 <= new_pos.x <= constants.WIDTH - constants.PLAYER_SIZE and 0 <= new_pos.y <= constants.HEIGHT - constants.PLAYER_SIZE:
                temp_rect = pygame.Rect(new_pos.x, new_pos.y, constants.PLAYER_SIZE, constants.PLAYER_SIZE)
                collision = any(temp_rect.colliderect(obs) for obs in self.obstacles)
                if not collision:
                    self.pos = new_pos
            
            if moving: new_state = 'walk'

        self.my_sprite_system.state = new_state
        
        if pygame.time.get_ticks() - self.my_sprite_system.last_update > constants.ANIMATION_SPEED:
            self.my_sprite_system.last_update = pygame.time.get_ticks()
            self.my_sprite_system.frame_index += 1

        try:
            payload = {
                "type": "update", 
                "pos": {"x": self.pos.x, "y": self.pos.y}, 
                "anim_state": self.my_sprite_system.state, 
                "direction": self.my_sprite_system.direction
            }
            self.client.send((json.dumps(payload) + "\n").encode())
        except: pass

    def draw(self):
        screen.fill((50, 50, 50))
        
        # --- DIBUJAR OBJETOS (Con recorte e info de debug) ---
        for obj in self.map_data.get("objects", []):
            obj_type = obj.get("tipo", "").lower()
            obj_img = self.obj_manager.get_image(obj_type)
            
            if obj_img:
                # Dibujamos el sprite recortado de la casa
                screen.blit(obj_img, (obj["x"], obj["y"]))
                
                # --- OPCIONAL SENIOR: Debug de Colisiones ---
                # Si quieres ver la caja de colisión, descomenta la siguiente línea:
                w, h = self.obj_manager.get_collision_size(obj_type)
                pygame.draw.rect(screen, (255, 0, 0), (obj["x"], obj["y"], w, h), 1)
            else:
                # Si no hay imagen, dibujamos el rect de color (50x50 por defecto)
                pygame.draw.rect(screen, obj["color"], (obj["x"], obj["y"], 50, 50))
            
        # Dibujar Jugadores
        for pid, pdata in self.other_players.items():
            if "pos" not in pdata: continue
            ppos = pdata["pos"]
            p_state = pdata.get("anim_state", "idle")
            p_dir = pdata.get("direction", 0)
            
            try:
                anim_data = self.my_sprite_system.animations.get(p_state)
                if anim_data and p_dir < len(anim_data):
                    row = anim_data[p_dir]
                    f_idx = self.my_sprite_system.frame_index % len(row)
                    screen.blit(row[f_idx], (ppos["x"], ppos["y"]))
                else:
                    pygame.draw.rect(screen, (200, 200, 200), (ppos["x"], ppos["y"], constants.PLAYER_SIZE, constants.PLAYER_SIZE))
            except:
                pygame.draw.rect(screen, (200, 200, 200), (ppos["x"], ppos["y"], constants.PLAYER_SIZE, constants.PLAYER_SIZE))

            name_tag = font.render(pid, True, (255, 255, 255))
            screen.blit(name_tag, (ppos["x"] - 5, ppos["y"] - 20))

        # Dibujar Chat
        chat_y = constants.HEIGHT - 60
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
                            try:
                                self.client.send((json.dumps({"type": "chat", "text": self.input_text}) + "\n").encode())
                            except: pass
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
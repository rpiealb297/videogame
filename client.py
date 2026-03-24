import pygame
import socket
import json
import threading

WIDTH, HEIGHT = 800, 600
PLAYER_SIZE = 32
OBJ_SIZE = 50

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Verdana", 14)
chat_font = pygame.font.SysFont("Verdana", 12)

class GameClient:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(('127.0.0.1', 5555))
        
        # Recibir datos iniciales
        raw_init = self.client.recv(4096).decode().split('\n')[0]
        init_data = json.loads(raw_init)
        
        self.my_id = init_data["id"]
        self.map_data = init_data["map"]
        # Crear objetos de colisión (Rects de Pygame)
        self.obstacles = [pygame.Rect(o["x"], o["y"], OBJ_SIZE, OBJ_SIZE) for o in self.map_data["objects"]]
        
        self.pos = pygame.Vector2(100, 100)
        self.other_players = {}
        self.chat_log = []
        self.input_text = ""
        self.chatting = False
        self.running = True
        
        threading.Thread(target=self.receive_data, daemon=True).start()

    def receive_data(self):
        while self.running:
            try:
                data = self.client.recv(4096).decode()
                if data:
                    messages = data.strip().split('\n')
                    for m in messages:
                        if not m: continue
                        msg = json.loads(m)
                        if msg["type"] == "sync":
                            self.other_players = msg["players"]
                        elif msg["type"] == "chat":
                            self.chat_log.append(f"{msg['user']}: {msg['text']}")
            except: break

    def check_collision(self, next_rect):
        """Verifica si el siguiente movimiento choca con obstáculos o límites."""
        # Límites de la pantalla
        if next_rect.left < 0 or next_rect.right > WIDTH or next_rect.top < 0 or next_rect.bottom > HEIGHT:
            return True
        # Obstáculos del JSON
        for obs in self.obstacles:
            if next_rect.colliderect(obs):
                return True
        return False

    def update(self):
        if not self.chatting:
            keys = pygame.key.get_pressed()
            new_pos = self.pos.copy()
            speed = 4
            
            if keys[pygame.K_a]: new_pos.x -= speed
            if keys[pygame.K_d]: new_pos.x += speed
            if keys[pygame.K_w]: new_pos.y -= speed
            if keys[pygame.K_s]: new_pos.y += speed

            # Crear un Rect temporal para la colisión
            temp_rect = pygame.Rect(new_pos.x, new_pos.y, PLAYER_SIZE, PLAYER_SIZE)
            
            if not self.check_collision(temp_rect):
                self.pos = new_pos

        try:
            self.client.send((json.dumps({"type": "update", "pos": {"x": self.pos.x, "y": self.pos.y}}) + "\n").encode())
        except: pass

    def draw(self):
        screen.fill((50, 50, 50))
        
        # Dibujar Objetos
        for obj in self.map_data["objects"]:
            pygame.draw.rect(screen, obj["color"], (obj["x"], obj["y"], OBJ_SIZE, OBJ_SIZE))
            
        # Dibujar Jugadores
        for pid, ppos in self.other_players.items():
            color = (0, 255, 150) if pid == self.my_id else (255, 80, 80)
            pygame.draw.rect(screen, color, (ppos["x"], ppos["y"], PLAYER_SIZE, PLAYER_SIZE))
            name_tag = font.render(pid, True, (255, 255, 255))
            screen.blit(name_tag, (ppos["x"] - 5, ppos["y"] - 20))

        # --- SISTEMA DE CHAT (REESTRUCTURADO) ---
        # El chat ahora está en la parte inferior izquierda
        chat_x, chat_y = 10, HEIGHT - 60
        
        # Fondo del historial de chat
        if self.chat_log:
            history_surface = pygame.Surface((350, 100))
            history_surface.set_alpha(150)
            history_surface.fill((20, 20, 20))
            screen.blit(history_surface, (10, chat_y - 110))

            # Dibujar mensajes de abajo hacia arriba
            for i, line in enumerate(reversed(self.chat_log[-5:])):
                msg_img = chat_font.render(line, True, (255, 255, 255))
                screen.blit(msg_img, (15, chat_y - 30 - (i * 20)))

        # Caja de entrada
        if self.chatting:
            input_bg = pygame.Rect(10, chat_y, 350, 30)
            pygame.draw.rect(screen, (0, 0, 0), input_bg)
            pygame.draw.rect(screen, (255, 255, 0), input_bg, 1)
            txt = chat_font.render(f"CHAT: {self.input_text}_", True, (255, 255, 0))
            screen.blit(txt, (15, chat_y + 7))
        else:
            hint = chat_font.render("Presiona [ENTER] para hablar", True, (150, 150, 150))
            screen.blit(hint, (10, HEIGHT - 20))

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
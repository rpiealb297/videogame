import pygame
import socket
import json
import threading

WIDTH, HEIGHT = 800, 600
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Verdana", 16)

class GameClient:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(('127.0.0.1', 5555))
        
        init_data = json.loads(self.client.recv(2048).decode())
        self.my_id = init_data["id"]
        self.map_objects = init_data["map"]["objects"]
        
        self.pos = {"x": 100, "y": 100}
        self.other_players = {}
        self.chat_log = []
        self.input_text = ""
        self.chatting = False
        
        self.running = True
        # Hilo para escuchar mensajes entrantes (sync y chat)
        threading.Thread(target=self.receive_data, daemon=True).start()

    def receive_data(self):
        while self.running:
            try:
                data = self.client.recv(4096).decode()
                if data:
                    # Los sockets pueden recibir varios JSON pegados, esto es un fix rápido
                    messages = data.replace('}{', '}\n{').split('\n')
                    for m in messages:
                        msg = json.loads(m)
                        if msg["type"] == "sync":
                            self.other_players = msg["players"]
                        elif msg["type"] == "chat":
                            self.chat_log.append(f"{msg['user']}: {msg['text']}")
            except: break

    def update(self):
        if not self.chatting:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.pos["x"] -= 4
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.pos["x"] += 4
            if keys[pygame.K_UP] or keys[pygame.K_w]: self.pos["y"] -= 4
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.pos["y"] += 4

        try:
            self.client.send(json.dumps({"type": "update", "pos": self.pos}).encode())
        except: pass

    def draw(self):
        screen.fill((40, 45, 52)) # Gris oscuro estilo RPG
        
        # 1. Dibujar Objetos del Mapa
        for obj in self.map_objects:
            pygame.draw.rect(screen, obj["color"], (obj["x"], obj["y"], 50, 50))
            label = font.render(obj["tipo"], True, (255, 255, 255))
            screen.blit(label, (obj["x"], obj["y"] - 20))
            
        # 2. Dibujar Jugadores (incluyéndome)
        for pid, ppos in self.other_players.items():
            color = (0, 255, 100) if pid == self.my_id else (255, 100, 100)
            rect = pygame.Rect(ppos["x"], ppos["y"], 32, 32)
            pygame.draw.rect(screen, color, rect)
            # Nombre sobre el jugador
            name_tag = font.render(pid, True, (255, 255, 255))
            screen.blit(name_tag, (ppos["x"] - 10, ppos["y"] - 25))

        # 3. Interfaz de Chat
        # Fondo del chat
        chat_bg = pygame.Surface((300, 130))
        chat_bg.set_alpha(128)
        chat_bg.fill((0, 0, 0))
        screen.blit(chat_bg, (10, 10))

        y = 15
        for line in self.chat_log[-6:]:
            msg_img = font.render(line, True, (255, 255, 255))
            screen.blit(msg_img, (15, y))
            y += 20
            
        if self.chatting:
            txt = font.render(f"> {self.input_text}_", True, (255, 255, 0))
            screen.blit(txt, (10, HEIGHT - 30))

        pygame.display.flip()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.running = False
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.chatting and self.input_text.strip():
                            msg = {"type": "chat", "text": self.input_text}
                            self.client.send(json.dumps(msg).encode())
                            self.input_text = ""
                        self.chatting = not self.chatting
                    
                    elif self.chatting:
                        if event.key == pygame.K_BACKSPACE:
                            self.input_text = self.input_text[:-1]
                        else:
                            if len(self.input_text) < 30: # Límite de caracteres
                                self.input_text += event.unicode
                    
                    elif event.key == pygame.K_e:
                        # Lógica de interacción (se mantiene igual que antes)
                        pass

            self.update()
            self.draw()
            clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    GameClient().run()
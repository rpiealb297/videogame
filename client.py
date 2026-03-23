import pygame
import socket
import json
import threading

# Configuración básica
WIDTH, HEIGHT = 800, 600
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 18)

class GameClient:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(('127.0.0.1', 5555))
        
        # Datos iniciales
        init_data = json.loads(self.client.recv(2048).decode())
        self.my_id = init_data["id"]
        self.map_objects = init_data["map"]["objects"]
        
        self.pos = {"x": 100, "y": 100}
        self.other_players = {}
        self.chat_log = []
        self.input_text = ""
        self.chatting = False
        
        self.running = True
        threading.Thread(target=self.receive_data, daemon=True).start()

    def receive_data(self):
        while self.running:
            try:
                data = self.client.recv(2048).decode()
                if data:
                    msg = json.loads(data)
                    if msg["type"] == "sync":
                        self.other_players = msg["players"]
                    elif msg["type"] == "chat":
                        self.chat_log.append(f"{msg['user']}: {msg['text']}")
            except: break

    def update(self):
        keys = pygame.key.get_pressed()
        if not self.chatting:
            if keys[pygame.K_w]: self.pos["y"] -= 5
            if keys[pygame.K_s]: self.pos["y"] += 5
            if keys[pygame.K_a]: self.pos["x"] -= 5
            if keys[pygame.K_d]: self.pos["x"] += 5

        # Enviar posición al servidor
        try:
            self.client.send(json.dumps({"type": "update", "pos": self.pos}).encode())
        except: pass

    def interact(self):
        for obj in self.map_objects:
            dist = ((self.pos["x"] - obj["x"])**2 + (self.pos["y"] - obj["y"])**2)**0.5
            if dist < 50:
                print(f"INTERACCIÓN: Has tocado la {obj['tipo']}")
                self.chat_log.append(f"Sistema: Interactuaste con {obj['tipo']}")

    def draw(self):
        screen.fill((30, 30, 30))
        
        # Dibujar objetos del mapa
        for obj in self.map_objects:
            pygame.draw.rect(screen, obj["color"], (obj["x"], obj["y"], 40, 40))
            
        # Dibujar otros jugadores
        for pid, ppos in self.other_players.items():
            color = (200, 0, 0) if pid != self.my_id else (0, 200, 0)
            pygame.draw.rect(screen, color, (ppos["x"], ppos["y"], 32, 32))

        # UI Chat
        y_offset = 10
        for text in self.chat_log[-5:]:
            img = font.render(text, True, (255, 255, 255))
            screen.blit(img, (10, y_offset))
            y_offset += 20
            
        if self.chatting:
            input_img = font.render(f"Escribiendo: {self.input_text}", True, (255, 255, 0))
            screen.blit(input_img, (10, HEIGHT - 30))

        pygame.display.flip()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.chatting and self.input_text:
                            self.client.send(json.dumps({"type": "chat", "text": self.input_text}).encode())
                            self.input_text = ""
                        self.chatting = not self.chatting
                    elif event.key == pygame.K_e and not self.chatting:
                        self.interact()
                    elif self.chatting:
                        if event.key == pygame.K_BACKSPACE: self.input_text = self.input_text[:-1]
                        else: self.input_text += event.unicode

            self.update()
            self.draw()
            clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    client = GameClient()
    client.run()
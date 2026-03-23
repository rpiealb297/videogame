import socket
import threading
import json

class GameServer:
    def __init__(self, host='127.0.0.1', port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen()
        
        # Cargar mapa
        with open('mapa.json', 'r') as f:
            self.map_data = json.load(f)
            
        self.clients = {} # id: socket
        self.players_data = {} # id: {x, y, chat_msg}
        print(f"[SERVER] Servidor iniciado en {host}:{port}")

    def handle_client(self, conn, addr):
        player_id = str(addr[1])
        print(f"[NUEVA CONEXIÓN] {player_id} conectado.")
        
        # Enviar mapa inicial al conectar
        conn.send(json.dumps({"type": "init", "map": self.map_data, "id": player_id}).encode())

        while True:
            try:
                data = conn.recv(1024).decode()
                if not data: break
                
                msg = json.loads(data)
                
                if msg["type"] == "update":
                    self.players_data[player_id] = msg["pos"]
                elif msg["type"] == "chat":
                    self.broadcast({"type": "chat", "user": player_id, "text": msg["text"]})

                # Enviar estado global a este cliente
                conn.send(json.dumps({"type": "sync", "players": self.players_data}).encode())
                
            except:
                break

        print(f"[DESCONECTADO] {player_id} se fue.")
        del self.clients[player_id]
        if player_id in self.players_data: del self.players_data[player_id]
        conn.close()

    def broadcast(self, data):
        # En una arquitectura real, esto se manejaría en un loop separado para optimizar
        pass 

    def start(self):
        while True:
            conn, addr = self.server.accept()
            player_id = str(addr[1])
            self.clients[player_id] = conn
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()

if __name__ == "__main__":
    server = GameServer()
    server.start()
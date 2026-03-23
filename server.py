import socket
import threading
import json

class GameServer:
    def __init__(self, host='127.0.0.1', port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen()
        
        with open('mapa.json', 'r') as f:
            self.map_data = json.load(f)
            
        self.clients = {} # Guardamos socket: id_jugador
        self.players_data = {} # Guardamos id_jugador: {datos}
        print(f"[SERVER] Corriendo en {host}:{port}")

    def broadcast(self, message_dict):
        """Envía un mensaje a TODOS los clientes conectados."""
        payload = json.dumps(message_dict).encode()
        # Hacemos una copia de los items para evitar errores de iteración si alguien se desconecta
        for client_socket in list(self.clients.keys()):
            try:
                client_socket.send(payload)
            except:
                self.remove_client(client_socket)

    def remove_client(self, conn):
        if conn in self.clients:
            pid = self.clients[conn]
            print(f"[DESCONECTADO] Jugador {pid} salio.")
            del self.players_data[pid]
            del self.clients[conn]
            conn.close()

    def handle_client(self, conn, addr):
        player_id = f"Player_{addr[1]}" # Nombre único basado en su puerto
        self.clients[conn] = player_id
        self.players_data[player_id] = {"x": 100, "y": 100}
        
        # Enviar configuración inicial
        conn.send(json.dumps({"type": "init", "map": self.map_data, "id": player_id}).encode())

        while True:
            try:
                data = conn.recv(1024).decode()
                if not data: break
                
                msg = json.loads(data)
                
                if msg["type"] == "update":
                    self.players_data[player_id] = msg["pos"]
                    # Enviamos el estado de todos los jugadores a este cliente
                    conn.send(json.dumps({"type": "sync", "players": self.players_data}).encode())
                
                elif msg["type"] == "chat":
                    # AQUÍ está el cambio: El servidor reparte el mensaje a todos
                    print(f"[CHAT] {player_id}: {msg['text']}")
                    self.broadcast({"type": "chat", "user": player_id, "text": msg["text"]})
            except:
                break
        
        self.remove_client(conn)

    def start(self):
        while True:
            conn, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()

if __name__ == "__main__":
    GameServer().start()
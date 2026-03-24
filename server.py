import socket
import threading
import json

class GameServer:
    def __init__(self, host='127.0.0.1', port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen()
        
        try:
            with open('mapa.json', 'r') as f:
                self.map_data = json.load(f)
        except:
            self.map_data = {"width": 800, "height": 600, "objects": []}
            
        self.clients = {} 
        self.players_data = {} 
        print(f"[SERVER] Corriendo en {host}:{port}")

    def broadcast(self, message_dict):
        payload = (json.dumps(message_dict) + "\n").encode()
        for client_socket in list(self.clients.keys()):
            try:
                client_socket.send(payload)
            except:
                self.remove_client(client_socket)

    def remove_client(self, conn):
        if conn in self.clients:
            pid = self.clients[conn]
            print(f"[DESCONECTADO] {pid} salió.")
            if pid in self.players_data: del self.players_data[pid]
            del self.clients[conn]
            conn.close()

    def handle_client(self, conn, addr):
        player_id = f"User_{addr[1]}"
        self.clients[conn] = player_id
        
        # INICIALIZACIÓN COMPLETA
        self.players_data[player_id] = {
            "pos": {"x": 100, "y": 100}, 
            "anim_state": "idle", 
            "direction": 0
        }
        
        conn.send((json.dumps({"type": "init", "map": self.map_data, "id": player_id}) + "\n").encode())

        while True:
            try:
                data = conn.recv(2048).decode()
                if not data: break
                
                messages = data.strip().split('\n')
                for m in messages:
                    if not m: continue
                    msg = json.loads(m)
                    
                    if msg["type"] == "update":
                        # ¡CORRECCIÓN AQUÍ! Usamos update para no borrar las otras llaves
                        if player_id in self.players_data:
                            self.players_data[player_id].update({
                                "pos": msg["pos"],
                                "anim_state": msg.get("anim_state", "idle"),
                                "direction": msg.get("direction", 0)
                            })
                        # Responder con el estado de TODOS
                        conn.send((json.dumps({"type": "sync", "players": self.players_data}) + "\n").encode())
                    
                    elif msg["type"] == "chat":
                        self.broadcast({"type": "chat", "user": player_id, "text": msg["text"]})
            except: break
        self.remove_client(conn)

    def start(self):
        while True:
            conn, addr = self.server.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    GameServer().start()
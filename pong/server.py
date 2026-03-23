from fastapi import FastAPI, WebSocket
import asyncio
import json
import random

app = FastAPI()

players = []
game_state = {
    "ball_x": 400,
    "ball_y": 250,
    "ball_vx": 4,
    "ball_vy": 4,
    "p1_y": 200,
    "p2_y": 200,
    "score1": 0,
    "score2": 0
}

WIDTH = 800
HEIGHT = 500
PADDLE_HEIGHT = 80

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    if len(players) >= 2:
        await ws.send_json({"error": "Game full"})
        return

    player_id = len(players)
    players.append(ws)

    # enviar estado inicial
    await ws.send_json(game_state)

    try:
        while True:
            data = await ws.receive_text()
            if player_id == 0:
                if data == "UP":
                    game_state["p1_y"] = max(0, game_state["p1_y"] - 10)
                elif data == "DOWN":
                    game_state["p1_y"] = min(HEIGHT-PADDLE_HEIGHT, game_state["p1_y"] + 10)
            else:
                if data == "UP":
                    game_state["p2_y"] = max(0, game_state["p2_y"] - 10)
                elif data == "DOWN":
                    game_state["p2_y"] = min(HEIGHT-PADDLE_HEIGHT, game_state["p2_y"] + 10)

    except:
        players.remove(ws)

async def game_loop():
    while True:
        # mover pelota
        game_state["ball_x"] += game_state["ball_vx"]
        game_state["ball_y"] += game_state["ball_vy"]

        # rebote paredes
        if game_state["ball_y"] <= 0 or game_state["ball_y"] >= HEIGHT:
            game_state["ball_vy"] *= -1

        # rebote palas
        if game_state["ball_x"] <= 40 and abs(game_state["ball_y"] - game_state["p1_y"]-40) <= 40:
            game_state["ball_vx"] *= -1
        if game_state["ball_x"] >= WIDTH-40 and abs(game_state["ball_y"] - game_state["p2_y"]-40) <= 40:
            game_state["ball_vx"] *= -1

        # puntuación
        if game_state["ball_x"] < 0:
            game_state["score2"] += 1
            game_state["ball_x"], game_state["ball_y"] = WIDTH//2, HEIGHT//2
            game_state["ball_vx"] = 4 * random.choice((1,-1))
            game_state["ball_vy"] = 4 * random.choice((1,-1))

        if game_state["ball_x"] > WIDTH:
            game_state["score1"] += 1
            game_state["ball_x"], game_state["ball_y"] = WIDTH//2, HEIGHT//2
            game_state["ball_vx"] = 4 * random.choice((1,-1))
            game_state["ball_vy"] = 4 * random.choice((1,-1))

        # enviar estado a todos los jugadores
        for ws in players:
            try:
                await ws.send_json(game_state)
            except:
                players.remove(ws)

        await asyncio.sleep(0.016)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(game_loop())

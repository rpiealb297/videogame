import pygame
import asyncio
import websockets
import json
import threading

WIDTH, HEIGHT = 800, 500
PADDLE_HEIGHT = 80

game_state = {
    "ball_x": 400,
    "ball_y": 250,
    "p1_y": 200,
    "p2_y": 200,
    "score1": 0,
    "score2": 0
}

async def network():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as ws:

        async def receive():
            global game_state
            while True:
                data = await ws.recv()
                game_state = json.loads(data)

        async def send():
            while True:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_UP]:
                    await ws.send("UP")
                elif keys[pygame.K_DOWN]:
                    await ws.send("DOWN")
                await asyncio.sleep(0.03)

        await asyncio.gather(receive(), send())

def start_network():
    asyncio.run(network())

threading.Thread(target=start_network, daemon=True).start()

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.Font(None, 50)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0,0,0))

    # dibujar palas
    pygame.draw.rect(screen,(255,255,255),(20,game_state["p1_y"],10,PADDLE_HEIGHT))
    pygame.draw.rect(screen,(255,255,255),(WIDTH-30,game_state["p2_y"],10,PADDLE_HEIGHT))

    # dibujar pelota
    pygame.draw.circle(screen,(255,255,255),(int(game_state["ball_x"]),int(game_state["ball_y"])),10)

    # dibujar marcador
    score_text = font.render(f"{game_state['score1']} - {game_state['score2']}", True, (255,255,255))
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 20))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()

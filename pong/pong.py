import pygame
import random

# Inicializar pygame
pygame.init()

# Tamaño de ventana
WIDTH, HEIGHT = 800, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pong")

# Colores
WHITE = (255,255,255)
BLACK = (0,0,0)

# Palas
paddle_width = 10
paddle_height = 80

player = pygame.Rect(20, HEIGHT//2 - paddle_height//2, paddle_width, paddle_height)
ai = pygame.Rect(WIDTH-30, HEIGHT//2 - paddle_height//2, paddle_width, paddle_height)

# Pelota
ball = pygame.Rect(WIDTH//2, HEIGHT//2, 15, 15)
ball_speed_x = random.choice((4,-4))
ball_speed_y = random.choice((4,-4))

# Puntuación
player_score = 0
ai_score = 0
font = pygame.font.Font(None, 40)

clock = pygame.time.Clock()

running = True
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Controles jugador
    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP] and player.top > 0:
        player.y -= 6
    if keys[pygame.K_DOWN] and player.bottom < HEIGHT:
        player.y += 6

    # IA sencilla
    if ai.centery < ball.centery:
        ai.y += 4
    elif ai.centery > ball.centery:
        ai.y -= 4

    # Movimiento pelota
    ball.x += ball_speed_x
    ball.y += ball_speed_y

    # Rebote paredes
    if ball.top <= 0 or ball.bottom >= HEIGHT:
        ball_speed_y *= -1

    # Rebote palas
    if ball.colliderect(player) or ball.colliderect(ai):
        ball_speed_x *= -1

    # Puntuación
    if ball.left <= 0:
        ai_score += 1
        ball.center = (WIDTH//2, HEIGHT//2)
        ball_speed_x *= -1

    if ball.right >= WIDTH:
        player_score += 1
        ball.center = (WIDTH//2, HEIGHT//2)
        ball_speed_x *= -1

    # Dibujar
    screen.fill(BLACK)

    pygame.draw.rect(screen, WHITE, player)
    pygame.draw.rect(screen, WHITE, ai)
    pygame.draw.ellipse(screen, WHITE, ball)
    pygame.draw.aaline(screen, WHITE, (WIDTH//2,0), (WIDTH//2,HEIGHT))

    score_text = font.render(f"{player_score}   {ai_score}", True, WHITE)
    screen.blit(score_text, (WIDTH//2 - 40, 20))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()

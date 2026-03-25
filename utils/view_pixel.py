import pygame

def inspeccionar_imagen(ruta):
    pygame.init()
    img = pygame.image.load(ruta)
    screen = pygame.display.set_mode(img.get_size())
    
    running = True
    while running:
        screen.blit(img, (0, 0))
        x, y = pygame.mouse.get_pos()
        # Muestra las coordenadas en el título de la ventana
        pygame.display.set_caption(f"Posición del ratón: X={x}, Y={y}")
        print(f"Posición del ratón: X={x}, Y={y}")

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        pygame.display.flip()
    pygame.quit()

inspeccionar_imagen('images/objects/valla.png')
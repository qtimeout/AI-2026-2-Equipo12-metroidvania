"""Punto de entrada del juego (escritorio y navegador vía pygbag).

El bucle es async porque pygbag lo exige: `await asyncio.sleep(0)` cede el control al navegador
en cada frame. Cada escena avanza su simulación con paso fijo y la IA con presupuesto por frame,
así el framerate no depende de cuánto tarde un agente en decidir.
"""
import asyncio

import pygame

from game.agents import build_agents
from game.assets import Assets
from game.config import FPS, SCREEN_H, SCREEN_W, SEED
from game.menu import MenuScene
from game.world import MIX


class App:
    def __init__(self):
        self.assets = Assets()
        # opciones del menú: MIX (técnica al azar por enemigo) + cada técnica para todos los enemigos
        self.techniques = [MIX] + list(build_agents(SEED))
        self.technique = MIX
        self.running = True

    def cycle_technique(self, step):
        i = self.techniques.index(self.technique)
        self.technique = self.techniques[(i + step) % len(self.techniques)]


async def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("MetroidvaniaPython — Paso Olvidado")
    app = App()
    scene = MenuScene(app)
    clock = pygame.time.Clock()

    while app.running:
        frame_dt = clock.tick(FPS) / 1000.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                app.running = False
            else:
                scene.handle(ev)
        nxt = scene.update(frame_dt)
        if nxt is not None:
            scene = nxt
        scene.draw(screen)
        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())

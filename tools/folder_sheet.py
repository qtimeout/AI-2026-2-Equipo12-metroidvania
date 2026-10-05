"""Hoja de contacto de todos los PNG de una carpeta (para elegir assets). Uso: python tools/folder_sheet.py <carpeta> <salida.png> [celda]"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

def main(folder, out, cell=180, cols=8):
    pygame.init(); pygame.display.set_mode((1, 1))
    font = pygame.font.Font(None, 16)
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".png"))
    rows = (len(files) + cols - 1) // cols
    sheet = pygame.Surface((cols * cell, rows * cell)); sheet.fill((70, 72, 92))
    for k, name in enumerate(files):
        img = pygame.image.load(os.path.join(folder, name)).convert_alpha()
        w, h = img.get_size(); f = min((cell - 6) / w, (cell - 30) / h, 1.0)
        t = pygame.transform.smoothscale(img, (max(1, int(w * f)), max(1, int(h * f))))
        x, y = (k % cols) * cell, (k // cols) * cell
        pygame.draw.rect(sheet, (50, 52, 70), (x, y, cell, cell), 1)
        sheet.blit(t, (x + (cell - t.get_width()) // 2, y + 28))
        sheet.blit(font.render(f"{k} {w}x{h}", True, (255, 230, 120)), (x + 3, y + 2))
        sheet.blit(font.render(name[:30], True, (200, 200, 220)), (x + 3, y + 14))
    pygame.image.save(sheet, out)
    print(len(files))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], *(int(a) for a in sys.argv[3:]))

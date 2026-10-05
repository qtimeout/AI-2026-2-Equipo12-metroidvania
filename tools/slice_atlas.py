"""Recorta un atlas de Unity (sin metadatos) en sprites sueltos y genera hojas de contacto numeradas.

Uso: python tools/slice_atlas.py "<atlas.png>" <carpeta_salida> [--gap 2] [--min 400] [--alpha 100]

1. Máscara "fuerte" (alfa >= --alpha) dilatada --gap píxeles: separa sprites vecinos sin que
   los brillos tenues los fusionen.
2. Cada componente conexo de esa máscara es un sprite; se recorta con la máscara "suave"
   (alfa >= 1) limitada al componente, para conservar los bordes antialiasados sin
   incluir píxeles del sprite vecino.
3. Guarda NNNN.png, index.json (rectángulo de origen) y sheet_XX.png numeradas para
   elegir a mano los fotogramas de cada animación.
"""
import argparse
import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame


def dilate(mask, g):
    if g <= 0:
        return mask
    k = pygame.mask.Mask((2 * g + 1, 2 * g + 1), fill=True)
    return mask.convolve(k, pygame.mask.Mask(mask.get_size()), (g, g))


def crop_mask(mask, rect):
    sub = pygame.mask.Mask(rect.size)
    sub.draw(mask, (-rect.x, -rect.y))
    return sub


def slice_atlas(atlas, alpha, gap, min_area):
    strong = dilate(pygame.mask.from_surface(atlas, alpha), gap)
    soft = pygame.mask.from_surface(atlas, 1)
    sprites = []
    for r in strong.get_bounding_rects():
        if r.w * r.h < min_area:
            continue
        comp = crop_mask(strong, r).connected_component()
        keep = comp.overlap_mask(crop_mask(soft, r), (0, 0))
        if keep.count() < min_area // 4:
            continue
        img = atlas.subsurface(r).copy()
        img.blit(keep.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)),
                 (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        bb = keep.get_bounding_rects()
        tight = bb[0].unionall(bb[1:]) if bb else img.get_rect()
        sprites.append((pygame.Rect(r.x + tight.x, r.y + tight.y, tight.w, tight.h), img.subsurface(tight).copy()))
    sprites.sort(key=lambda s: (s[0].y // 64, s[0].x))
    return sprites


def contact_sheets(crops, out_dir, cell=96, cols=16, rows=10):
    font = pygame.font.Font(None, 18)
    per = cols * rows
    for s in range(0, len(crops), per):
        sheet = pygame.Surface((cols * cell, rows * cell))
        sheet.fill((70, 72, 92))
        for k, (idx, img) in enumerate(crops[s:s + per]):
            w, h = img.get_size()
            f = min((cell - 6) / w, (cell - 18) / h, 1.0)
            thumb = pygame.transform.smoothscale(img, (max(1, int(w * f)), max(1, int(h * f))))
            x, y = (k % cols) * cell, (k // cols) * cell
            pygame.draw.rect(sheet, (50, 52, 70), (x, y, cell, cell), 1)
            sheet.blit(thumb, (x + (cell - thumb.get_width()) // 2, y + 16))
            sheet.blit(font.render(f"{idx} {w}x{h}", True, (255, 230, 120)), (x + 3, y + 2))
        pygame.image.save(sheet, os.path.join(out_dir, f"sheet_{s // per:02d}.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("atlas")
    ap.add_argument("out")
    ap.add_argument("--gap", type=int, default=2)
    ap.add_argument("--min", type=int, default=400, help="área mínima del recorte en px")
    ap.add_argument("--alpha", type=int, default=100, help="alfa mínimo de la máscara de separación")
    args = ap.parse_args()

    pygame.init()
    pygame.display.set_mode((1, 1))
    atlas = pygame.image.load(args.atlas).convert_alpha()
    sprites = slice_atlas(atlas, args.alpha, args.gap, args.min)

    os.makedirs(args.out, exist_ok=True)
    index, crops = {}, []
    for i, (rect, img) in enumerate(sprites):
        pygame.image.save(img, os.path.join(args.out, f"{i:04d}.png"))
        index[f"{i:04d}"] = [rect.x, rect.y, rect.w, rect.h]
        crops.append((i, img))
    with open(os.path.join(args.out, "index.json"), "w") as f:
        json.dump({"atlas": args.atlas, "rects": index}, f)
    contact_sheets(crops, args.out)
    print(f"{len(sprites)} sprites -> {args.out}")


if __name__ == "__main__":
    main()

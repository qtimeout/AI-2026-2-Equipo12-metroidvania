"""Genera app/assets/ a partir de Sprites/ (solo lo que el juego usa, ya recortado y escalado).

Uso (desde la raíz del proyecto): python tools/build_assets.py

- Los atlas se recortan con slice_atlas.slice_atlas (determinista: mismos índices que
  las hojas de contacto de work/).
- Los fotogramas que Unity empaquetó acostados (ancho > alto) se enderezan rotando 90°.
- Escribe app/assets/manifest.json con las animaciones (lista de archivos + fps).
"""
import json
import os
import shutil

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

from slice_atlas import slice_atlas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Sprites")
OUT = os.path.join(ROOT, "app", "assets")
KP = os.path.join(SRC, "Architecture & Environment", "Area specfic architecture", "King_s Pass")

ATLASES = {
    "knight": (os.path.join(SRC, "The Knight", "The Knight main sprites - atlas0 #00000357.png"), 0.62),
    "husk": (os.path.join(SRC, "Enemies & Corpses", "Leaping Husk - atlas0 #058005.png"), 0.5),
    "hud": (os.path.join(SRC, "Inventory & UI", "HUD main - atlas0.png"), 0.8),
    "whusk": (os.path.join(SRC, "Enemies & Corpses", "Wandering Husk - atlas0 #038017.png"), 0.6),
    "horn": (os.path.join(SRC, "Enemies & Corpses", "Husk Hornhead - atlas0 #041020.png"), 0.5),
}

# hacia dónde mira cada atlas en los sprites originales (-1 izquierda, 1 derecha)
FACES = {"knight": -1, "husk": -1, "whusk": 1, "horn": 1, "hud": -1}

# animación -> (atlas, índices, fps, loop, rotación)
#   rotación: True = enderezar si el recorte es apaisado (Unity lo empaquetó acostado),
#             False = tal cual, "force" = rotar siempre 90°
ANIMS = {
    "knight_idle": ("knight", [399, 400, 401, 402, 403], 6, True, True),
    "knight_run": ("knight", [308, 309, 310, 349, 350, 351], 12, True, True),
    "knight_jump": ("knight", [260, 261], 8, False, True),
    "knight_fall": ("knight", [272, 82, 201], 8, True, True),
    "knight_attack": ("knight", [385, 375], 14, False, True),
    "knight_hurt": ("knight", [372], 1, False, True),
    "slash": ("knight", [41], 1, False, False),
    "husk_walk": ("husk", [17, 20, 26, 28, 30, 10], 10, True, True),
    "husk_idle": ("husk", [17], 1, True, True),
    "husk_leap": ("husk", [8, 18, 21, 33], 8, False, True),
    "husk_hurt": ("husk", [15], 1, False, True),
    "husk_death": ("husk", [11, 4], 4, False, True),
    "whusk_walk": ("whusk", [19, 20, 21, 22, 25, 26], 9, True, True),
    "whusk_idle": ("whusk", [21], 1, True, True),
    "whusk_leap": ("whusk", [6, 9, 11, 16], 8, False, True),
    "whusk_hurt": ("whusk", [18], 1, False, False),
    "whusk_death": ("whusk", [24], 1, False, "force"),
    "horn_walk": ("horn", [21, 22, 23, 27, 24, 20], 10, True, True),
    "horn_idle": ("horn", [22], 1, True, True),
    "horn_leap": ("horn", [6, 7, 25, 32], 8, False, True),
    "horn_hurt": ("horn", [0], 1, False, True),
    "horn_death": ("horn", [14], 1, False, True),
    "mask_full": ("hud", [30], 1, False, False),
    "mask_empty": ("hud", [39], 1, False, True),
    "soul_orb": ("hud", [157], 1, False, False),
    "hit_fx": ("hud", [42], 1, False, False),
}

# archivo suelto -> (ruta de origen, escala)
SINGLES = {
    "menu_bg": (os.path.join(SRC, "Menu", "Voidheart_menu_BG.png"), 0.625),
    "title": (os.path.join(SRC, "Menu", "vheart_title_spanish.png"), 0.55),
    "beam": (os.path.join(SRC, "Menu", "vheart_beam.png"), 1.0),
    "fog": (os.path.join(SRC, "Particles & Effects", "Fog.png"), 1.0),
    "soft": (os.path.join(SRC, "Particles & Effects", "Soft.png"), 1.0),
}
for i in range(11):
    SINGLES[f"pointer_{i:02d}"] = (os.path.join(SRC, "Inventory & UI", "Pointers", f"main_menu_pointer_anim{i:04d}.png"), 0.6)

# piezas de King's Pass agrupadas por uso en el escenario
ENV = {
    "floor": ["tut_land_floor_0001_03", "tut_land_floor_0002_02", "tut_land_floor_0003_01"],
    "rock": ["tut_rocks_0004_05", "tut_rocks_0007_02", "tut_edge_02_0000_04", "tut_edge_02_0001_03",
             "tut_wall_r_0000_06", "tut_wall_r_0001_05", "tut_wall_r_0002_04", "tut_wall_r_0004_02",
             "tut_wall_r_0005_01", "tut_wall_l_0000s_0003_Color-Balance-1", "tut_wall_l_0000s_0004_Color-Balance-1"],
    "bg": ["tut_BG_set_01_0000_05", "tut_BG_set_01_0001_04", "tut_BG_set_01_0002_03", "tut_BG_set_01_0003_02",
           "tut_BG_set_02_0000_06", "tut_BG_set_02_0001_05", "tut_BG_set_02_0003_03", "tut_BG_set_02_0004_02",
           "tut_BG_set_02_0005_01"],
    "deco": ["tutorial_poles_0002_b2", "tutorial_poles_0003_b1", "tutorial_poles_0007_a2", "tutorial_poles_0008_a",
             "Hallownest_Gate_0000_20", "tut_door_large_0008_03"],
}
ENV_SCALE = 0.5


def scaled(img, k):
    if k == 1.0:
        return img
    w, h = img.get_size()
    return pygame.transform.smoothscale(img, (max(1, round(w * k)), max(1, round(h * k))))


def find_kp(stem):
    for name in os.listdir(KP):
        if name.startswith(stem) and name.lower().endswith(".png"):
            return os.path.join(KP, name)
    raise FileNotFoundError(stem)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    manifest = {"anims": {}, "images": {}, "env": {}}

    sliced = {}
    for key, (path, _) in ATLASES.items():
        sliced[key] = slice_atlas(pygame.image.load(path).convert_alpha(), 100, 2, 400)

    for name, (atlas, ids, fps, loop, upright) in ANIMS.items():
        files = []
        for n, i in enumerate(ids):
            img = sliced[atlas][i][1]
            if upright == "force" or (upright and img.get_width() > img.get_height()):
                img = pygame.transform.rotate(img, 90)
            img = scaled(img, ATLASES[atlas][1])
            fname = f"{name}_{n}.png"
            pygame.image.save(img, os.path.join(OUT, fname))
            files.append(fname)
        manifest["anims"][name] = {"frames": files, "fps": fps, "loop": loop, "faces": FACES[atlas]}

    for name, (path, k) in SINGLES.items():
        img = scaled(pygame.image.load(path).convert_alpha(), k)
        pygame.image.save(img, os.path.join(OUT, f"{name}.png"))
        manifest["images"][name] = f"{name}.png"

    for group, stems in ENV.items():
        files = []
        for stem in stems:
            img = scaled(pygame.image.load(find_kp(stem)).convert_alpha(), ENV_SCALE)
            fname = f"env_{group}_{len(files)}.png"
            pygame.image.save(img, os.path.join(OUT, fname))
            files.append(fname)
        manifest["env"][group] = files

    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    size = sum(os.path.getsize(os.path.join(OUT, n)) for n in os.listdir(OUT))
    print(f"{len(os.listdir(OUT))} archivos, {size / 1e6:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()

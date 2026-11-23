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
    "moss": (os.path.join(SRC, "Enemies & Corpses", "Mosskin, Volatile Mosskin - atlas0 #03709.png"), 0.55),
}

# hacia dónde mira cada atlas en los sprites originales (-1 izquierda, 1 derecha)
FACES = {"knight": -1, "husk": -1, "whusk": 1, "horn": 1, "hud": -1, "moss": -1, "hornet": -1, "thread": -1}

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
    "moss_walk": ("moss", [7, 8, 11, 13, 18, 21], 9, True, True),
    "moss_idle": ("moss", [7], 1, True, True),
    "moss_leap": ("moss", [22, 24, 25, 28], 8, False, True),
    "moss_hurt": ("moss", [38], 1, False, True),
    "moss_death": ("moss", [1, 47], 3, False, True),
    "mossv_walk": ("moss", [34, 37, 39, 41, 44, 48], 10, True, True),
    "mossv_idle": ("moss", [34], 1, True, True),
    "mossv_leap": ("moss", [36, 43, 45, 54], 8, False, True),
    "mossv_hurt": ("moss", [38], 1, False, True),
    "mossv_death": ("moss", [0, 3, 5], 5, False, True),
    "mask_full": ("hud", [30], 1, False, False),
    "mask_empty": ("hud", [39], 1, False, True),
    "soul_orb": ("hud", [157], 1, False, False),
    "hit_fx": ("hud", [42], 1, False, False),
}

# Animaciones a partir de archivos sueltos que comparten lienzo (Hornet): se recortan TODAS con el mismo
# rectángulo (unión de sus siluetas) para que los fotogramas no salten al animar.
# grupo -> (escala, {animación: (prefijo de archivo, índices, fps, loop)})
HORNET_DIR = os.path.join(SRC, "Bosses", "Hornet")
FILE_ANIMS = {
    "hornet": (0.55, {
        "hornet_idle": ("Hornet - idle", [0, 1], 4, True),
        "hornet_jump": ("Hornet - jump", list(range(10)), 16, False),
        "hornet_throw": ("Hornet - throw_side", list(range(8)), 14, False),
        "hornet_land": ("Hornet - hard_land", list(range(6)), 12, False),
        "hornet_dash": ("Hornet - harpoon_side", [0, 1], 10, True),
    }),
    "thread": (0.7, {
        "hornet_thread": ("Hornet weapon - harpoon_thread_v02", list(range(2, 9)), 16, False),
    }),
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

CR = os.path.join(SRC, "Architecture & Environment", "Area specfic architecture", "Forgotten Crossroads")
GP = os.path.join(SRC, "Architecture & Environment", "Area specfic architecture", "Greenpath")

# Piezas de escenario por tema (una zona de HK por nivel), agrupadas por uso:
#   floor = borde superior de las plataformas, rock = contorno de las rocas, bg = capas de fondo,
#   deco = capa cercana, exit = puerta de salida, lamp = faroles con luz (opcional)
# Una entrada puede ser (carpeta, prefijo) para tomar la pieza de otra zona.
THEMES = {
    "kingspass": (KP, {
        "floor": ["tut_land_floor_0001_03", "tut_land_floor_0002_02", "tut_land_floor_0003_01"],
        "rock": ["tut_rocks_0004_05", "tut_rocks_0007_02", "tut_edge_02_0000_04", "tut_edge_02_0001_03",
                 "tut_wall_r_0000_06", "tut_wall_r_0001_05", "tut_wall_r_0002_04", "tut_wall_r_0004_02",
                 "tut_wall_r_0005_01", "tut_wall_l_0000s_0003_Color-Balance-1", "tut_wall_l_0000s_0004_Color-Balance-1"],
        "bg": ["tut_BG_set_01_0000_05", "tut_BG_set_01_0001_04", "tut_BG_set_01_0002_03", "tut_BG_set_01_0003_02",
               "tut_BG_set_02_0000_06", "tut_BG_set_02_0001_05", "tut_BG_set_02_0003_03", "tut_BG_set_02_0004_02",
               "tut_BG_set_02_0005_01"],
        "deco": ["tutorial_poles_0002_b2", "tutorial_poles_0003_b1", "tutorial_poles_0007_a2", "tutorial_poles_0008_a",
                 "Hallownest_Gate_0000_20", "tut_door_large_0008_03"],
        "exit": [(CR, "cd_arch_01")],
    }),
    "crossroads": (CR, {
        "floor": ["cd_floor_02", "cd_floor_highway_05", "fg_ground_faces"],
        "rock": ["rocks_BG_01", "rocks_BG_02", "rocks_right_left_BG_01", "rocks_right_left_BG_02",
                 "rocks_right_left_BG_03", "floor_FG_rock_02_0000", "highway_01_layered_0003"],
        "bg": ["cd_mid_wall_detail_01", "cd_mid_wall_detail_02", "cd_mid_wall_detail_03", "statue_01", "statue_03",
               "cd_pillar_01", "cd_wall_01", "cd_wall_04", "cd_archway_01"],
        "deco": ["cd_pillar_01", "cd_wall_04", "statue_03", "cd_archway_02", "cd_pillar_03"],
        "exit": ["cd_arch_01"],
        "lamp": ["lamp_01", "lamp_02"],
    }),
    "greenpath": (GP, {
        "floor": ["floor_layered_0000_04_green", "floor_layered_0001_03_green", "floor_layered_0002_02_green",
                  "floor_layered_0003_01_green", "slug_floor"],
        "rock": ["fungd_rock_01_0000", "fungd_rock_01_0001", "fungd_rock_01_0002", "fung_new_0085_c",
                 "fung_new_0127_02", "fung_new_0128_01", "fungd_rock_03_0001"],
        "bg": ["fung_new_0083_c", "fung_new_0084_c", "fung_new_0089_a", "fung_new_0091_d", "fung_pillar_wall_0000",
               "fung_pillar_wall_0001", "thorn_mid_back.png", "thorn_mid_back_02", "hunter_scenery_0003"],
        "deco": ["hunter_scenery_0000", "hunter_scenery_0001", "fung_new_0092_d", "vine_platform_01", "thorn_plinth"],
        "exit": [(CR, "cd_arch_01")],
        "lamp": ["fung_pod_01", "fung_pod_02.png"],
    }),
}
ENV_SCALE = 0.5


def scaled(img, k):
    if k == 1.0:
        return img
    w, h = img.get_size()
    return pygame.transform.smoothscale(img, (max(1, round(w * k)), max(1, round(h * k))))


def find(folder, stem):
    for name in sorted(os.listdir(folder)):
        if name.startswith(stem) and name.lower().endswith(".png"):
            return os.path.join(folder, name)
    raise FileNotFoundError(f"{stem} en {folder}")


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

    for group, (k, anims) in FILE_ANIMS.items():
        frames = {name: [pygame.image.load(os.path.join(HORNET_DIR, f"{prefix}{i:04d}.png")).convert_alpha()
                         for i in ids] for name, (prefix, ids, _, _) in anims.items()}
        rects = [pygame.mask.from_surface(img, 8).get_bounding_rects() for imgs in frames.values() for img in imgs]
        union = [r for rs in rects for r in rs]
        box = union[0].unionall(union[1:]).inflate(4, 4)
        for name, (_, _, fps, loop) in anims.items():
            files = []
            for n, img in enumerate(frames[name]):
                crop = scaled(img.subsurface(box.clip(img.get_rect())).copy(), k)
                fname = f"{name}_{n}.png"
                pygame.image.save(crop, os.path.join(OUT, fname))
                files.append(fname)
            manifest["anims"][name] = {"frames": files, "fps": fps, "loop": loop, "faces": FACES[group]}

    for name, (path, k) in SINGLES.items():
        img = scaled(pygame.image.load(path).convert_alpha(), k)
        pygame.image.save(img, os.path.join(OUT, f"{name}.png"))
        manifest["images"][name] = f"{name}.png"

    for theme, (folder, groups) in THEMES.items():
        manifest["env"][theme] = {}
        for group, stems in groups.items():
            files = []
            for stem in stems:
                src_dir, stem = stem if isinstance(stem, tuple) else (folder, stem)
                img = scaled(pygame.image.load(find(src_dir, stem)).convert_alpha(), ENV_SCALE)
                fname = f"env_{theme}_{group}_{len(files)}.png"
                pygame.image.save(img, os.path.join(OUT, fname))
                files.append(fname)
            manifest["env"][theme][group] = files

    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    size = sum(os.path.getsize(os.path.join(OUT, n)) for n in os.listdir(OUT))
    print(f"{len(os.listdir(OUT))} archivos, {size / 1e6:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()

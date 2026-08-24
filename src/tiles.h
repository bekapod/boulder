#ifndef TILES_H
#define TILES_H

// which VRAM tile slots hold which art
// slot 0 stays blank b/c empty tilemap cells point at it
#define TILE_MARKER 1
#define TILE_BAR_FIRST 2
#define TILE_BAR_DARK_FIRST (TILE_BAR_FIRST + 9)
#define TILE_DIGIT_FIRST (TILE_BAR_DARK_FIRST + 3)
#define TILE_FONT_FIRST (TILE_DIGIT_FIRST + 10)
#define TILE_EXCLAIM (TILE_FONT_FIRST + 26)
#define TILE_BOULDER_FIRST (TILE_EXCLAIM + 1)
#define TILE_SISYPHUS_FIRST (TILE_BOULDER_FIRST + 16)
#define TILE_SCENE_FIRST (TILE_SISYPHUS_FIRST + 16)
#define TILE_FULLSCREEN_FIRST (TILE_SCENE_FIRST + 34)

#endif

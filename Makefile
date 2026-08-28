ROM_NAME := $(notdir $(CURDIR))
BUILD := build

GBDK_HOME ?= $(HOME)/gbdk/
LCC := $(GBDK_HOME)bin/lcc
LCCFLAGS := -debug -Wm-yS
CSRCS := $(wildcard src/*.c)
PNG2ASSET := $(GBDK_HOME)bin/png2asset
RESSRCS := res/title.c res/gameover.c res/marker_obj.c res/bar_bg.c res/tileset.c res/scene_map.c res/digits_bg.c res/boulder_obj.c res/sisyphus_obj.c

MAP_PNGS := $(wildcard art/*_map.png)
FULLSCREEN_PNGS := art/title.png art/gameover.png
SHEET_PNGS := $(filter-out $(MAP_PNGS) $(FULLSCREEN_PNGS),$(wildcard art/*.png))

.PHONY: all
all: $(BUILD)/$(ROM_NAME).gb

$(BUILD)/$(ROM_NAME).gb: $(CSRCS) $(RESSRCS) $(wildcard src/*.h) | $(BUILD)
	$(LCC) $(LCCFLAGS) -o $@ $(CSRCS) $(RESSRCS)

$(patsubst art/%.png,res/%.c,$(MAP_PNGS)): res/%.c: art/%.png art/tileset.png | res
	$(PNG2ASSET) $< -o $@ -map -source_tileset art/tileset.png -noflip -keep_palette_order -no_palettes > $@.log 2>&1 || { cat $@.log; false; }
	! grep -q "not in the source tileset" $@.log || { cat $@.log; false; }

$(patsubst art/%.png,res/%.c,$(SHEET_PNGS)): res/%.c: art/%.png | res
	$(PNG2ASSET) $< -o $@ -map -tiles_only -keep_duplicate_tiles -noflip -keep_palette_order -no_palettes

$(patsubst art/%.png,res/%.c,$(FULLSCREEN_PNGS)): res/%.c: art/%.png | res
	$(PNG2ASSET) $< -o $@ -map -noflip -keep_palette_order -no_palettes

res:
	mkdir -p res

$(BUILD):
	mkdir -p $(BUILD)

.DELETE_ON_ERROR:

.PHONY: test
test: all
	uv run --project tests pytest tests

.PHONY: sweep
sweep: $(BUILD)/$(ROM_NAME).gb
	uv run --project tests python tests/sweep.py

.PHONY: clean
clean:
	rm -rf $(BUILD) res

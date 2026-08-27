ROM_NAME := $(notdir $(CURDIR))
BUILD := build

GBDK_HOME ?= $(HOME)/gbdk/
LCC := $(GBDK_HOME)bin/lcc
LCCFLAGS := -debug -Wm-yS
CSRCS := $(wildcard src/*.c)
PNG2ASSET := $(GBDK_HOME)bin/png2asset
RESSRCS := res/title.c res/marker_obj.c res/bar_bg.c res/tileset.c res/scene_map.c res/digits_bg.c res/boulder_obj.c res/sisyphus_obj.c

MAP_PNGS := $(wildcard art/*_map.png)
FULLSCREEN_PNGS := art/title.png art/gameover.png
SHEET_PNGS := $(filter-out $(MAP_PNGS) $(FULLSCREEN_PNGS),$(wildcard art/*.png))
OBJS := $(patsubst %.rgbasm,$(BUILD)/%.o,$(wildcard *.rgbasm))
CHRS := $(patsubst art/%.png,$(BUILD)/%.chr,$(SHEET_PNGS))
TLMS := $(patsubst art/%_map.png,$(BUILD)/%_map.tlm,$(MAP_PNGS))

CHRS += $(patsubst art/%.png,$(BUILD)/%.chr,$(FULLSCREEN_PNGS))
TLMS += $(patsubst art/%.png,$(BUILD)/%.tlm,$(FULLSCREEN_PNGS))

.PHONY: all
all: $(BUILD)/$(ROM_NAME).gb $(BUILD)/$(ROM_NAME)-c.gb

$(BUILD)/$(ROM_NAME).gb: $(OBJS)
	rgblink --dmg --tiny --map $(BUILD)/$(ROM_NAME).map --sym $(BUILD)/$(ROM_NAME).sym -o $@ $^
	rgbfix --title game --pad-value 0 --validate $@

# -I $(BUILD) lets incbin/include find the generated .chr files
$(BUILD)/%.o: %.rgbasm $(CHRS) $(TLMS) $(wildcard *.rgbinc) | $(BUILD)
	rgbasm -Werror -Weverything -I $(BUILD) -o $@ $<

$(BUILD)/$(ROM_NAME)-c.gb: $(CSRCS) $(RESSRCS) $(wildcard src/*.h) | $(BUILD)
	$(LCC) $(LCCFLAGS) -o $@ $(CSRCS) $(RESSRCS)

$(BUILD)/%_map.tlm: art/%_map.png $(BUILD)/tileset.chr | $(BUILD)
	rgbgfx --unique-tiles --input-tileset $(BUILD)/tileset.chr --tilemap $@ $<

# don't use --unique-tiles here b/c play.rgbasm writes sequential tile
# indices for the bar, so duplicate tiles must keep their slots
$(BUILD)/%.chr: art/%.png | $(BUILD)
	rgbgfx --colors '#9bbc0f,#8bac0f,#306230,#0f380f' --output $@ $<

$(patsubst art/%.png,$(BUILD)/%.tlm,$(FULLSCREEN_PNGS)): $(BUILD)/%.tlm: art/%.png | $(BUILD)
	rgbgfx --colors '#9bbc0f,#8bac0f,#306230,#0f380f' --unique-tiles --tilemap $@ --output $(BUILD)/$*.chr $<

$(patsubst art/%.png,$(BUILD)/%.chr,$(FULLSCREEN_PNGS)): $(BUILD)/%.chr: $(BUILD)/%.tlm ;

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

.SECONDARY: $(CHRS) $(TLMS)

.DELETE_ON_ERROR:

.PHONY: test
test: all
	BOULDER_ROM=$(ROM) uv run --project tests pytest tests $(if $(filter c,$(ROM)),-m c_ready)

.PHONY: sweep
sweep: $(BUILD)/$(ROM_NAME).gb
	uv run --project tests python tests/sweep.py

.PHONY: clean
clean:
	rm -rf $(BUILD) res

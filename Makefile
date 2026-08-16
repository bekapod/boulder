ROM_NAME := $(notdir $(CURDIR))
BUILD := build
MAP_PNGS := $(wildcard art/*_map.png)
SHEET_PNGS := $(filter-out $(MAP_PNGS),$(wildcard art/*.png))
OBJS := $(patsubst %.rgbasm,$(BUILD)/%.o,$(wildcard *.rgbasm))
CHRS := $(patsubst art/%.png,$(BUILD)/%.chr,$(SHEET_PNGS))
TLMS := $(patsubst art/%_map.png,$(BUILD)/%_map.tlm,$(MAP_PNGS))

$(BUILD)/$(ROM_NAME).gb: $(OBJS)
	rgblink --dmg --tiny --map $(BUILD)/$(ROM_NAME).map --sym $(BUILD)/$(ROM_NAME).sym -o $@ $^
	rgbfix --title game --pad-value 0 --validate $@

# -I $(BUILD) lets incbin/include find the generated .chr files
$(BUILD)/%.o: %.rgbasm $(CHRS) $(TLMS) $(wildcard *.rgbinc) | $(BUILD)
	rgbasm -Werror -Weverything -I $(BUILD) -o $@ $<

$(BUILD)/%_map.tlm: art/%_map.png $(BUILD)/tileset.chr | $(BUILD)
	rgbgfx --unique-tiles --input-tileset $(BUILD)/tileset.chr --tilemap $@ $<

# don't use --unique-tiles here b/c play.rgbasm writes sequential tile
# indices for the bar, so duplicate tiles must keep their slots
$(BUILD)/%.chr: art/%.png | $(BUILD)
	rgbgfx --colors '#9bbc0f,#8bac0f,#306230,#0f380f' --output $@ $<

$(BUILD):
	mkdir -p $(BUILD)

.SECONDARY: $(CHRS) $(TLMS)

.PHONY: test
test: $(BUILD)/$(ROM_NAME).gb
	uv run --project tests pytest tests

.PHONY: sweep
sweep: $(BUILD)/$(ROM_NAME).gb
	uv run --project tests python tests/sweep.py

.PHONY: clean
clean:
	rm -rf $(BUILD)

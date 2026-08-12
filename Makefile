ROM_NAME := $(notdir $(CURDIR))
MAP_PNGS := $(wildcard *_map.png)
SHEET_PNGS := $(filter-out $(MAP_PNGS),$(wildcard *.png))
OBJS := $(patsubst %.rgbasm,%.o,$(wildcard *.rgbasm))
CHRS := $(patsubst %.png,%.chr,$(SHEET_PNGS))
TLMS := $(patsubst %.png,%.tlm,$(MAP_PNGS))

$(ROM_NAME).gb: $(OBJS)
	rgblink --dmg --tiny --map $(ROM_NAME).map --sym $(ROM_NAME).sym -o $@ $^
	rgbfix --title game --pad-value 0 --validate $@

%.o: %.rgbasm $(CHRS) $(TLMS) $(wildcard *.rgbinc)
	rgbasm -Werror -Weverything -o $@ $<

%_map.tlm: %_map.png tileset.chr
	rgbgfx --unique-tiles --input-tileset tileset.chr --tilemap $@ $<

%_obj.chr: %_obj.png
	rgbgfx --colors '#9bbc0f,#8bac0f,#306230,#0f380f' --output $@ $<

%.chr: %.png
	rgbgfx --unique-tiles --output $@ $<

.SECONDARY: $(CHRS) $(TLMS)

.PHONY: test
test: $(ROM_NAME).gb
	uv run --project tests pytest tests

.PHONY: clean
clean:
	rm -f *.o *.chr *.tlm $(ROM_NAME).gb $(ROM_NAME).map $(ROM_NAME).sym

.PHONY: all clean

F = _FeatureCounter
C = _ScoreCalculator

BINARIES = $(C) $(C).so $(C).dll $(F)

all: $(BINARIES)

clean:
	rm -f $(BINARIES) $(C).exe $(F).exe


$(F): $(F).c
	gcc -lm -o $@ $<	

$(C): $(C).c
	gcc -lm -DCSCORE -o $@ $<

$(C).so: $(C).c
	gcc -lm -shared -o $@ $<

$(C).dll: $(C).c
	gcc -lm -mno-cygwin -shared -o $@ $<


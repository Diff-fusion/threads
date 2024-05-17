MINIM_AS=./assembler.py

all: threads

threads: main.c trampoline.S minim_disable.bin encrypt.bin enc_key.h
	$(CC) -std=gnu99 -mdsp -Wl,-z,noexecstack -O2 $< -o $@

clean:
	rm minim_disable.bin encrypt.bin threads

#enc_key.h: gen_key.py
#	./gen_key.py > $@

minim_disable.bin: minim_disable.s
	$(MINIM_AS) $< -o $@

encrypt.bin: encrypt.s
	$(MINIM_AS) $< -o $@

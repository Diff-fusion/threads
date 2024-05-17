#!/usr/bin/env python3
import random

random.seed(4) # make deterministic

def gen():
    return random.choice(range(1, 256, 2))

print("static const uint32_t enc_key[N_WORDS] __attribute__ ((aligned(N_BYTES))) = {")

for i in range(1024):
      n = gen() | gen() << 8 | gen() << 16 | gen() << 24
      print(f"\t0x{n:08x},")

print("};")

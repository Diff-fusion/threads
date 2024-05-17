#!/usr/bin/env python3

import argparse
import logging
from assembler import Assembler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(args):
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    assembly = open(args.input).read()
    asm = Assembler()
    asm.assemble(assembly)
    asm.print_instructions()
    if args.output:
        open(args.output, "wb").write(asm.encoded)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("input", help="Input file")
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Enable debug output")
    args = parser.parse_args()
    main(args)

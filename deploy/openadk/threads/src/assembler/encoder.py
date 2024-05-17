import logging
from .arguments import Argument, ArgumentType
from .instructions import INSTRUCTIONS
from .instruction_encodings import EncodingType
from .modifiers import parse_modifiers

logger = logging.getLogger(__name__)

class Encoder:
    address: int
    op: str
    modifiers: list[str]
    args: list[Argument]
    encoded: int
    size: int
    label: int

    def __init__(self, address: int, op: str):
        self.address = address
        self.op = op
        self.args = []
        self.label = None

    def resolve_label(self, labels: dict[str, int]):
        self.args[self.label].resolve_label(labels, self.address)

    def parse_args(self, args: list[str]):
        self.args = []
        for i, arg in enumerate(args):
            arg = Argument.from_str(arg.strip(","))
            self.args.append(arg)
            if arg.type == ArgumentType.Label:
                self.label = i

    def encode(self):
        for instruction in INSTRUCTIONS:
            if not self.op.startswith(instruction.name):
                continue
            self.modifiers = parse_modifiers(self.op[len(instruction.name):])
            i_args = self.args[::-1] if instruction.swap_args else self.args
            for encoding in instruction.encodings:
                if encoding.match(i_args, self.modifiers):
                    break
            else:
                logger.debug("Found no encoding for %s in %s, trying other instructions", self.op, instruction)
                continue
            break
        else:
            logger.critical(f"Found no encoding for {self.op} with args {self.args}")
            exit()

        #print("Choose encoding", encoding)
        self.encoded = encoding.encode(i_args, self.modifiers)
        if encoding.type == EncodingType.Core:
            logger.debug("Encoding Core: 0x%x", self.encoded)
            self.size = 2
        else:
            logger.debug("Encoding Extended: 0x%x 0x%x", self.encoded & 0xFFFF, self.encoded >> 16)
            self.size = 4

    def __repr__(self):
        if self.size == 2:
            data = f"0x{self.encoded:04x}"
        else:
            data = f"0x{self.encoded & 0xFFFF:04x} 0x{self.encoded >> 16:04x}"
        return f"0x{self.address:04x}: {data:13} {self.op} {self.modifiers} {self.args}"

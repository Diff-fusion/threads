import logging
from .arguments import Argument
from .encoder import Encoder
from .instructions import BRANCH_RELATIVE_INSTRUCTIONS
from .modifiers import parse_modifiers

logger = logging.getLogger(__name__)

class Assembler:
    cursor: int
    labels: dict[str, int]
    instructions: list[Encoder]
    encoded: bytes

    def __init__(self):
        pass

    def align(self):
        assert self.cursor & 1 == 0
        if self.cursor & 2 != 0:
            # align all labels to 4 bytes to make jumps easyer
            self.process_line("NOP")


    def process_label(self, label: str):
        if label in self.labels:
            logger.critical("Label %s already defined at 0x%x", label, self.labels[label])
            exit()
        self.labels[label] = self.cursor

    def process_command(self, command: str, args: list[str]):
        match command:
            case "align4":
                self.align()
            case _:
                logger.warning("Undefined command %s", command)

    def process_line(self, line: str):
        line = line.split("!", 1)[0].strip()
        if not line:
            return

        if line.endswith(":"):
            self.process_label(line[:-1])
            return

        if line.startswith("."):
            command, *args = line[1:].split()
            self.process_command(command, args)
            return

        op, *args = line.split()
        logger.info("Op: %s, Args: %s", op, args)

        encoder = Encoder(self.cursor, op)
        self.instructions.append(encoder)
        encoder.parse_args(args)

        if encoder.label is None:
            # no labels
            encoder.encode()
            self.cursor += encoder.size
        else:
            # label, reserve 4 bytes
            self.cursor += 4

    def fill_labels(self):
        fillers = []
        for instruction in self.instructions:
            if instruction.label is not None:
                instruction.resolve_label(self.labels)
                instruction.encode()
                if instruction.size == 2:
                    # pad with nop
                    filler = Encoder(instruction.address + 2, "NOP")
                    filler.encode()
                    fillers.append(filler)
        self.instructions += fillers
        self.instructions.sort(key=lambda x: x.address)

    def create_encoded(self):
        self.encoded = b""
        for instruction in self.instructions:
            self.encoded += instruction.encoded.to_bytes(instruction.size, "little")


    def assemble(self, assembly: str):
        self.cursor = 0
        self.labels = {}
        self.instructions = []
        for line in assembly.splitlines():
            self.process_line(line)
        self.fill_labels()
        self.create_encoded()

    def print_instructions(self):
        for instruction in self.instructions:
            print(instruction)

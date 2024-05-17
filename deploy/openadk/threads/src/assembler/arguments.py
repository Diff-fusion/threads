import logging
from enum import Enum, auto
from .registers import Register, REGISTERS

logger = logging.getLogger(__name__)

class ArgumentType(Enum):
    Register = 1
    Constant = auto()
    Memory = auto()
    Label = auto()

class ExtractBits(Enum):
    All = 1
    Bottom = auto()
    Top = auto()

    def extract(self, val):
        match self:
            case self.All:
                return val
            case self.Bottom:
                return val & 0xFFFF
            case self.Top:
                return val >> 16
            case _:
                assert False

class Argument:
    type: ArgumentType
    register: Register
    constant: int
    offset: "Argument"
    #pre_increment: bool
    post_increment: bool
    name: str
    extract_bits: ExtractBits = ExtractBits.All

    def as_register(self, register: Register):
        self.type = ArgumentType.Register
        self.register = register

    def as_constant(self, constant: int):
        self.type = ArgumentType.Constant
        self.constant = constant

    def as_memory(self, base: Register, offset: "Argument"):
        self.type = ArgumentType.Memory
        self.register = base
        self.offset = offset

    def as_label(self, name: str):
        self.type = ArgumentType.Label
        self.name = name

    def resolve_label(self, labels: dict[str, int], address: int):
        val = labels.get(self.name)
        if val is None:
            logger.critical("Label %s is not defined", self.name)
            exit()
        val -= address # take values pc relative
        self.as_constant(self.extract_bits.extract(val))

    @classmethod
    def from_str(cls, arg: str):
        self = cls()

        match arg[0]:
            case "#":
                match arg[1:3]:
                    case "HI":
                        self.extract_bits = ExtractBits.Top
                        val = arg[4:-1]
                    case "LO":
                        self.extract_bits = ExtractBits.Bottom
                        val = arg[4:-1]
                    case _:
                        val = arg[1:]
                base = 10
                if val.startswith("0x"):
                    base = 16
                try:
                    # try decode immediate value
                    const = int(val, base)
                    const = self.extract_bits.extract(const)
                    self.as_constant(const)
                except ValueError:
                    # must be a lable
                    logger.debug("Can't decode %s as int, must be label", val)
                    self.as_label(val)
            case "[": # ]
                # memory reference
                arg = arg.strip("[]")
                fallback_offset = 0
                if arg.endswith("++"):
                    self.post_increment = True
                    fallback_offset = 1
                elif arg.endswith("--"):
                    self.post_increment = True
                    fallback_offset = -1
                else:
                    self.post_increment = False
                arg = arg.strip("+-")
                str_base, *str_offset = arg.split("+")
                assert len(str_offset) <= 1
                base = REGISTERS[str_base]
                if not str_offset:
                    str_offset = "#" + str(fallback_offset)
                else:
                    str_offset = str_offset[0]
                offset = cls.from_str(str_offset)
                self.as_memory(base, offset)
            case _ if arg in REGISTERS:
                # register
                self.as_register(REGISTERS[arg])
            case _:
                # must be a label
                self.as_label(arg)

        return self

    def __repr__(self):
        match self.type:
            case ArgumentType.Register:
                return f"Argument(type=Register, value={self.register})"
            case ArgumentType.Constant:
                return f"Argument(type=Constant, value={self.constant})"
            case ArgumentType.Memory:
                return f"Argument(type=Memory, base={self.register}, offset={self.offset})"
            case ArgumentType.Label:
                return f"Argument(type=Label, name={self.name})"
            case _:
                return "Unknown argument type"

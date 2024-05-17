import logging
from enum import Enum, auto
from .argument_encodings import RegisterEncoding, ImmediateEncoding, MemoryEncoding, PieceImmediateEncoding
from .constraints import UnitConstraint
from .modifiers import CONDITION_MAP, TRANSFER_MAP, gen_conditional
from .registers import REGISTERS

logger = logging.getLogger(__name__)

class EncodingType(Enum):
    Core = 1
    Extended = auto()
    Long = auto()

class Encoding:
    const_bits: int
    args_encoding: list = []
    constraints: list
    modifiers: dict[str, int] = None
    main_reg: int = None
    conditional: bool = False
    condition_base: int = None
    L2: int = None
    type: EncodingType

    def __init__(self, const_bits: int, modifiers: list[str] = None, cc: bool = False):
        self.const_bits = const_bits
        if cc:
            assert self.condition_base is not None
            self.conditional = True

        if self.modifiers is None:
            self.modifiers = {}

        if modifiers is not None:
            self.gen_modifiers(modifiers)

    def gen_modifiers(self, modifiers: list[str]):
        new_modifiers = {}
        # remove modifiers not wanted by instruction
        for modifier in modifiers:
            if modifier in CONDITION_MAP or modifier in TRANSFER_MAP:
                continue
            assert modifier in self.modifiers
            new_modifiers[modifier] = self.modifiers[modifier]
        self.modifiers = new_modifiers


    @classmethod
    def gen_constraints(cls):
        cls.constraints = []
        main_reg = cls.args_encoding[cls.main_reg] if cls.main_reg is not None else None
        for encoding in cls.args_encoding:
            cls.constraints.append(encoding.constraint(main_reg))

    def match(self, args: list["Argument"], modifiers: list[str]):
        if len(self.constraints) != len(args):
            logger.debug("Match encoding failed, wrong arg num")
            return False
        main_reg = None
        if self.main_reg is not None:
            # check main reg first
            if not self.constraints[self.main_reg].match(args[self.main_reg], modifiers):
                return False
            main_reg = args[self.main_reg].register

        for i, (constraint, arg) in enumerate(zip(self.constraints, args)):
            if i == self.main_reg:
                continue
            if not constraint.match(arg, modifiers, main_reg):
                return False

        for modifier in modifiers:
            if not (modifier in self.modifiers or modifier in TRANSFER_MAP or (self.conditional and modifier in CONDITION_MAP)):
                logger.debug("Match encoding failed, non matching modifier: %s", modifier)
                return False

        return True

    def encode(self, args: list["Argument"], modifiers: list[str]):
        assert len(args) == len(self.args_encoding)
        encoded_val = self.const_bits
        main_reg = args[self.main_reg].register if self.main_reg is not None else None
        for arg, encoding in zip(args, self.args_encoding):
            encoded_val |= encoding.encode(arg, modifiers, main_reg)

        for modifier in modifiers:
            if modifier in TRANSFER_MAP:
                # For MUL instruction W and D are valid and encoded in 1 bit
                if self.L2 is not None and modifier == "D":
                    encoded_val |= 1 << self.L2
                continue
            if modifier in CONDITION_MAP:
                assert self.conditional
                encoded_val |= gen_conditional(modifier) << self.condition_base
                continue

            assert modifier in self.modifiers
            encoded_val |= 1 << self.modifiers[modifier]

        match self.type:
            case EncodingType.Extended:
                encoded_val |= 0xc000
            case EncodingType.Long:
                encoded_val |= 0xb000
        return encoded_val

RE = RegisterEncoding
IE = ImmediateEncoding
ME = MemoryEncoding

UCX = UnitConstraint.Any
UCS = UnitConstraint.Same
UCO = UnitConstraint.Other
UCA = UnitConstraint.Address
UCA0 = UnitConstraint.Address0
UCD = UnitConstraint.Data

# Control encodings
class Encoding1r16ictl(Encoding):
    type = EncodingType.Long
    args_encoding = [
        RE(UnitConstraint.Control, 5, 3),
        IE(19, 11, split_base=0, split_size=5, sign_extend=17)
        ]
    modifiers = {
        "T": 16,
        }

# Address encodings

## 3 register core
class Encoding3ra(Encoding):
    type = EncodingType.Core
    main_reg = 1
    args_encoding = [
        RE(UCS, 7, 2),
        RE(UCA, 4, 2, unit_base=9, unit_size=1, pc_bit=6),
        RE(UCS, 1, 2, pc_bit=3),
        ]

## 3 register extended
class Encoding3rae(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS, 23, 2, split_base=12, split_size=1),
        RE(UCA, 20, 2, unit_base=25, unit_size=1, pc_bit=22, split_base=10, split_size=2),
        RE(UCS, 17, 2, pc_bit=19, split_base=8, split_size=2),
        ]

## 2 register core
class Encoding2ra(Encoding):
    type = EncodingType.Core
    main_reg = 1
    args_encoding = [
        RE(UCS, 7, 2),
        RE(UCA, 1, 2, unit_base=9, unit_size=1, pc_bit=3),
        ]

## 2 register extended
class Encoding2rae(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS, 23, 2, split_base=12, split_size=1),
        RE(UCA, 17, 2, split_base=8, split_size=2, unit_base=25, unit_size=1, pc_bit=19),
        ]

## 2 register immediated core
class Encoding2ria(Encoding):
    type = EncodingType.Core
    main_reg = 1
    args_encoding = [
        RE(UCS),
        RE(UCA, 7, 2, unit_base=9, unit_size=1),
        IE(2, 5, sign_extend=0)
        ]

## 2 register immediated extended
class Encoding2riae(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS),
        RE(UCA, 23, 2, unit_base=25, unit_size=1, pc_bit=12),
        IE(18, 5, split_base=1, split_size=11, sign_extend=16)
        ]
    modifiers = {
        "T": 0,
        }

## 1 register immediated core
class Encoding1ria(Encoding):
    type = EncodingType.Core
    main_reg = 0
    args_encoding = [
        RE(UCA, 7, 2, unit_base=9, unit_size=1),
        IE(2, 5, sign_extend=0)
        ]

## 1 register immediated extended
class Encoding1riae(Encoding):
    type = EncodingType.Extended
    main_reg = 0
    args_encoding = [
        RE(UCA, 23, 2, unit_base=25, unit_size=1, pc_bit=12),
        IE(18, 5, split_base=1, split_size=11, sign_extend=16)
        ]
    modifiers = {
        "T": 0,
        }

# data encodings

## 3 register core
class Encoding3r(Encoding):
    type = EncodingType.Core
    main_reg = 1
    args_encoding = [
        RE(UCS, 7, 3),
        RE(UCD, 4, 3, unit_base=10, unit_size=1),
        RE(UCS, 1, 3),
        ]
    L2 = 0

## 3 register extended
class Encoding3re(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS, 23, 3),
        RE(UCD, 20, 3, unit_base=26, unit_size=1, split_base=10, split_size=2),
        RE(UCS, 17, 3, split_base=8, split_size=2),
        ]
    modifiers = {
        "S": 13,
        "P": 0,
        }
    L2 = 16

## 2 register core
class Encoding2r(Encoding):
    type = EncodingType.Core
    main_reg = 1
    args_encoding = [
        RE(UCS, 7, 3),
        RE(UCD, 1, 3, unit_base=10, unit_size=1),
        ]

## 2 register extended
class Encoding2re(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS, 23, 3),
        RE(UCD, 17, 3, unit_base=26, unit_size=1, split_base=8, split_size=2),
        ]
    modifiers = {
        "P": 7,
        "S": 13,
        }
    L2 = 3

## 2 register source core
class Encoding2rs(Encoding):
    type = EncodingType.Core
    main_reg = 0
    args_encoding = [
        RE(UCD, 6, 3, unit_base=9, unit_size=1),
        RE(UCS, 1, 5),
        ]

## 2 register source extended
class Encoding2rse(Encoding):
    type = EncodingType.Extended
    main_reg = 0
    args_encoding = [
        RE(UCD, 22, 3, unit_base=25, unit_size=1, split_base=8, split_size=2), # mismatch for split_base, should be 7 from manual but qemu expects 8
        RE(UCS, 17, 5),
        ]

## 2 register immediated core
class Encoding2ri(Encoding):
    type = EncodingType.Core
    main_reg = 1
    args_encoding = [
        RE(UCS),
        RE(UCD, 7, 3, unit_base=10, unit_size=1),
        IE(2, 5, sign_extend=0)
        ]
    modifiers = {
        "M": 1,
        }
    L2 = 1

## 2 register immediated extended
class Encoding2rie(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS),
        RE(UCD, 23, 3, unit_base=26, unit_size=1),
        IE(18, 5, split_base=1, split_size=11, sign_extend=16)
        ]
    modifiers = {
        "M": 17,
        "P": 0,
        "S": 13,
        "T": 0,
        }
    L2 = 17

## 1 register immediated core
class Encoding1ri(Encoding):
    type = EncodingType.Core
    args_encoding = [
        RE(UCD, 7, 3, unit_base=10, unit_size=1),
        IE(2, 5, sign_extend=0)
        ]

## 1 register immediated extended
class Encoding1rie(Encoding):
    type = EncodingType.Extended
    args_encoding = [
        RE(UCD, 23, 3, unit_base=26, unit_size=1),
        IE(18, 5, split_base=1, split_size=11, sign_extend=16)
        ]
    modifiers = {
        "S": 13,
        "T": 0,
        }

## 1 register immediated cmp core
class Encoding1ric(Encoding):
    type = EncodingType.Core
    args_encoding = [
        RE(UCD, 6, 3, unit_base=9, unit_size=1),
        IE(1, 5, sign_extend=0)
        ]

## 1 register immediated cmp extended
class Encoding1riec(Encoding):
    type = EncodingType.Extended
    args_encoding = [
        RE(UCD, 22, 3, unit_base=25, unit_size=1),
        IE(17, 5, split_base=2, split_size=11, sign_extend=16)
        ]
    modifiers = {
        "M": 1,
        "T": 0,
        }

# Data unit encodings

## 3 register extended
class Encoding3redu(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS, 10, 3),
        RE(UCD, 22, 3, unit_base=25, unit_size=1, split_base=8, split_size=2),
        RE(UCS, 17, 5),
        ]

## 2 register extended
class Encoding2redu(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS, 10, 3),
        RE(UCD, 22, 3, unit_base=25, unit_size=1, split_base=8, split_size=2),
        ]

# Address and Data

## 2 register cross unit extended
class Encoding2rcue(Encoding):
    type = EncodingType.Extended
    args_encoding = [
        RE(UCX, 16, 2, split_base=8, split_size=3, unit_base=0, unit_size=4),
        RE(UCX, 18, 2, split_base=11, split_size=3, unit_base=4, unit_size=4),
        ]

## 2 register address cross unit immediated extended
class Encoding2riacue(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCX, 23, 2, split_base=12, split_size=1, unit_base=0, unit_size=4),
        RE(UCA, 20, 2, split_base=10, split_size=2, unit_base=25, unit_size=1, pc_bit=22),
        IE(17, 3, split_base=5, split_size=5, sign_extend=0)
        ]

## Encodings with O2R (operand 2 replace)

## 3 register extended
class Encoding3reduo2r(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS, 10, 3),
        RE(UCD, 22, 3, unit_base=25, unit_size=1, split_base=8, split_size=2),
        RE(UnitConstraint.O2R, 17, 5),
        ]

## 2 register source core
class Encoding2rso2r(Encoding):
    type = EncodingType.Core
    main_reg = 0
    args_encoding = [
        RE(UCD, 6, 3, unit_base=9, unit_size=1),
        RE(UnitConstraint.O2R, 1, 5),
        ]

## 2 register source extended
class Encoding2rso2re(Encoding):
    type = EncodingType.Extended
    main_reg = 0
    args_encoding = [
        RE(UCD, 22, 3, unit_base=25, unit_size=1, split_base=8, split_size=2),
        RE(UnitConstraint.O2R, 17, 5),
        ]

## Shift encodings
class Encoding3rs(Encoding):
    type = EncodingType.Core
    main_reg = 1
    args_encoding = [
        RE(UCS, 7, 3),
        RE(UCD, 5, 2, unit_base=10, unit_size=1),
        RE(UCS, 2, 3),
        ]

class Encoding2ri5s(Encoding):
    type = EncodingType.Core
    main_reg = 1
    args_encoding = [
        RE(UCS),
        RE(UCD, 7, 3, unit_base=10, unit_size=1),
        IE(2, 5, sign_extend=False)
        ]

class Encoding3rse(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS, 23, 3),
        RE(UCD, 21, 2, split_base=9, split_size=3, unit_base=26, unit_size=1),
        RE(UCS, 18, 3, split_base=7, split_size=2),
        ]
    modifiers = {
        "P": 6,
        "S": 13,
        }
    L2 = 4

class Encoding2ri5se(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS, 23, 3),
        RE(UCD, 7, 5, unit_base=26, unit_size=1),
        IE(18, 5, sign_extend=False)
        ]
    modifiers = {
        "P": 6,
        "S": 13,
        }
    L2 = 4

# DSP encodings
class Encoding3rdspe(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS, 23, 3),
        RE(UCD, 20, 3, unit_base=26, unit_size=1, split_base=10, split_size=2),
        RE(UCS, 17, 3, split_base=8, split_size=2),
        ]
    modifiers = {
        "C": 3,
        "S": 13,
        "U": 16,
        "X": 6,
        }
    L2 = 4

class Encoding3rdsp8e(Encoding):
    type = EncodingType.Extended
    main_reg = 1
    args_encoding = [
        RE(UCS, 23, 3),
        RE(UCD, 20, 3, unit_base=26, unit_size=1, split_base=10, split_size=2),
        RE(UCS, 17, 3, split_base=8, split_size=2),
        ]
    modifiers = {
        "P": 7,
        "S": 13,
        "T": 16,
        "U": 5,
        "X": 6,
        }
    L2 = 3

# Branches
class Encoding10i(Encoding):
    type = EncodingType.Core
    args_encoding = [IE(0, 10, force_signed=True, shift=1)]

class Encoding19ie(Encoding):
    type = EncodingType.Extended
    args_encoding = [IE(21, 5, split_base=0, split_size=14, force_signed=True, shift=1)]
    modifiers = {
        "R": 16
        }
    condition_base = 17

class Encoding5i(Encoding):
    type = EncodingType.Core
    args_encoding = [IE(5, 5, force_signed=True, shift=1)]
    modifiers = {
        "R": 0
        }
    condition_base = 1

class Encoding1r5i(Encoding):
    type = EncodingType.Core
    args_encoding = [
        RE(UCX, reg=REGISTERS["D1RtP"]),
        IE(0, 10, force_signed=True, shift=1),
        ]

class Encoding1r19ie(Encoding):
    type = EncodingType.Extended
    args_encoding = [
        RE(UCX, 0, 3, unit_base=3, unit_size=2),
        IE(16, 10, split_base=5, split_size=9, force_signed=True, shift=1),
        ]

# Memory Access
class Encoding1r3im(Encoding):
    type = EncodingType.Core
    args_encoding = [
        RE(UCX, 7, 3, unit_base=0, unit_size=2),
        ME(
            RE(UCA0, 5, 2),
            IE(2, 3, force_signed=True),
            transfer_size=2,
            )
        ]

class Encoding1r6ime(Encoding):
    type = EncodingType.Extended
    args_encoding = [
        RE(UCX, 23, 3, split_base=10, split_size=1, unit_base=16, unit_size=2, split_unit_base=1, split_unit_size=2),
        ME(
            RE(UCX, 21, 2, split_base=9, split_size=1, unit_base=3, unit_size=2),
            IE(18, 3, split_base=6, split_size=3, force_signed=True),
            transfer_bits=[11, 13],
            increment = [5, 0],
            )
        ]

class Encoding2r6ime(Encoding):
    type = EncodingType.Extended
    main_reg = 0
    args_encoding = [
        RE(UCX, 23, 3, split_base=10, split_size=1, unit_base=16, unit_size=2, split_unit_base=1, split_unit_size=2),
        RE(UCO),
        ME(
            RE(UCX, 21, 2, split_base=9, split_size=1, unit_base=3, unit_size=2),
            IE(18, 3, split_base=6, split_size=3, force_signed=True),
            transfer_bits=[11, 13],
            increment = [5, 0],
            )
        ]

class Encoding1rmoe(Encoding):
    type = EncodingType.Extended
    args_encoding = [
        RE(UCX, 23, 3, split_base=10, split_size=1, unit_base=16, unit_size=2, split_unit_base=1, split_unit_size=2),
        ME(
            RE(UCX, 21, 2, split_base=9, split_size=1, unit_base=18, unit_size=2),
            RE(UCS, 4, 5),
            transfer_bits=[11, 13],
            increment = [3, 0],
            )
        ]

class Encoding2rmoe(Encoding):
    type = EncodingType.Extended
    main_reg = 0
    args_encoding = [
        RE(UCX, 23, 3, split_base=10, split_size=1, unit_base=16, unit_size=2, split_unit_base=1, split_unit_size=2),
        RE(UCO),
        ME(
            RE(UCX, 21, 2, split_base=9, split_size=1, unit_base=18, unit_size=2),
            RE(UCS, 4, 5),
            transfer_bits=[11, 13],
            increment = [3, 0],
            )
        ]

# Switch
class EncodingSwitch(Encoding):
    type = EncodingType.Core
    args_encoding = [
        PieceImmediateEncoding([
            (1, 0, 3),
            (9, 3, 1),
            (16, 4, 2),
            (22, 6, 2),
            ],
            extra_map=[0xffffff, 0xc3020e]
            )
        ]

class EncodingSwitche(Encoding):
    type = EncodingType.Extended
    args_encoding = [
        PieceImmediateEncoding([
            (0, 0, 1),
            (1, 16, 3),
            (4, 1, 4),
            (8, 5, 1),
            (9, 19, 1),
            (10, 6, 4),
            (16, 20, 2),
            (18, 10, 4),
            (22, 22, 2),
            ])
        ]

# No Arguments
class EncodingN(Encoding):
    type = EncodingType.Core
class EncodingNe(Encoding):
    type = EncodingType.Extended

classes = []
k = v = None
for k, v in locals().items():
    if k.startswith("Encoding") and k not in ["Encoding", "EncodingType"]:
        v.gen_constraints()

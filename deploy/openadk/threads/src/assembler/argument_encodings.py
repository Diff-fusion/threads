import logging
from dataclasses import dataclass
from .arguments import Argument, ArgumentType
from .constraints import RegConstraint, ImmConstraint, UnitConstraint, MemoryConstraint, PieceImmConstraint
from .modifiers import gen_transfer_size
from .registers import RegUnits, Register

logger = logging.getLogger(__name__)

# Base Unit encoding table
BU_encoding = {
    RegUnits.Address1: 0,
    RegUnits.Data0: 1,
    RegUnits.Data1: 2,
    RegUnits.Address0: 3,
    }

O2R_encoding = {
    RegUnits.Data0: {
        RegUnits.Address1: 0,
        RegUnits.Data1: 1,
        RegUnits.Address0: 3,
        },
    RegUnits.Data1: {
        RegUnits.Address1: 0,
        RegUnits.Data0: 1,
        RegUnits.Address0: 3,
        },
    RegUnits.Address0: {
        RegUnits.Address1: 0,
        RegUnits.Data0: 1,
        RegUnits.Data1: 3,
        },
    RegUnits.Address1: {
        RegUnits.Data1: 0,
        RegUnits.Data0: 1,
        RegUnits.Address0: 3,
        },
    }

@dataclass
class RegisterEncoding:
    unit_constraint: UnitConstraint
    base: int = None
    size: int = None
    unit_base: int = None
    unit_size: int = None
    split_base: int = None
    split_size: int = None
    split_unit_base: int = None
    split_unit_size: int = None
    pc_bit: int = None
    reg: Register = None

    def encode(self, arg: Argument, modifiers: list[str], main_reg: Register = None):
        if self.base is None:
            # already given by other argument
            return 0
        unit = arg.register.unit
        num = arg.register.number
        if unit == RegUnits.PC and self.pc_bit is not None:
            return 1 << self.pc_bit
        ret = 0
        if self.unit_base is not None:
            if self.split_unit_base is not None:
                unit_num = unit.value
                num_base = unit_num & ((1<<self.unit_size) - 1)
                ret |= num_base << self.unit_base

                num_base = (unit_num >> self.unit_size) & ((1<<self.split_unit_size) - 1)
                ret |= num_base << self.split_unit_base
            elif self.unit_size == 1:
                if (unit == RegUnits.Data1 or unit == RegUnits.Address1):
                    ret |= 1 << self.unit_base
            elif self.unit_size == 2:
                ret |= BU_encoding[unit] << self.unit_base
            else:
                ret |= unit.value << self.unit_base
        if self.unit_constraint == UnitConstraint.O2R:
            assert self.size == 5
            assert main_reg is not None
            size = 3
            replacement_unit = O2R_encoding[main_reg.unit][unit]
        else:
            size = self.size

        num_base = num & ((1<<size) - 1)
        if self.unit_constraint == UnitConstraint.O2R:
            num_base |= replacement_unit << 3
        ret |= num_base << self.base

        if self.split_base is not None:
            num_base = (num >> size) & ((1<<self.split_size) - 1)
            ret |= num_base << self.split_base
        return ret

    def constraint(self, main_reg: "RegisterEncoding" = None) -> RegConstraint:
        if self.reg:
            return RegConstraint(self.reg.unit, range(self.reg.number, self.reg.number + 1))
        unit = self.unit_constraint
        if self.size is None:
            assert main_reg.size is not None
            size = main_reg.size + (main_reg.split_size or 0)
        else:
            size = self.size + (self.split_size or 0)
        if unit == UnitConstraint.O2R:
            # top two bits are for unit specification
            assert size == 5
            size = 3
        num = range(2**size)
        same_num = self.base is None
        pc = self.pc_bit is not None
        return RegConstraint(unit, num, same_num, pc)

@dataclass
class ImmediateEncoding:
    base: int
    size: int
    sign_extend: int = None
    force_signed: bool = False
    split_base: int = None
    split_size: int = None
    shift: int = 0

    def encode(self, arg: Argument, modifiers: list[str], *args):
        value = arg.constant >> self.shift
        ret = 0
        value_base = value & ((1<<self.size) - 1)
        ret |= value_base << self.base

        if self.split_base is not None:
            value_base = (value >> self.size) & ((1<<self.split_size) - 1)
            ret |= value_base << self.split_base

        if value < 0 and not self.force_signed:
            ret |= 1 << self.sign_extend

        return ret

    def constraint(self, main_reg: "RegisterEncoding" = None) -> RegConstraint:
        size = self.size + (self.split_size or 0)
        min = -2**(size-1) if self.sign_extend is not None or self.force_signed else 0
        max = 2**size if not self.force_signed else 2**(size-1)
        return ImmConstraint(min, max, self.shift)

@dataclass
class PieceImmediateEncoding:
    mapping: list[tuple[int, int, int]] # src (meta bits), dst (minim bits), size
    extra_map: tuple[int, int] = None # map specific number from src (meta) to dst (minim) before encoding

    def encode(self, arg: Argument, modifiers: list[str], *args):
        constant = arg.constant
        if self.extra_map is not None and constant == self.extra_map[0]:
            constant = self.extra_map[1]
        ret = 0
        for src, dst, size in self.mapping:
            # extract bits from source
            val = (arg.constant >> src) & ((1<<size) - 1)
            # set in destination
            ret |= val << dst
        return ret

    def constraint(self, main_reg: "RegisterEncoding" = None) -> RegConstraint:
        mask = 0
        for src, dst, size in self.mapping:
            # create mask that contains all representable bits
            mask |= ((1<<size) - 1) << src
        return PieceImmConstraint(mask, self.extra_map)

@dataclass
class MemoryEncoding:
    base: RegisterEncoding
    offset: RegisterEncoding | ImmediateEncoding
    transfer_bits: tuple[int, int] = None # L1, L2
    transfer_size: int = None
    increment: tuple[int, int] = None # UA, PP

    def encode(self, arg: Argument, modifiers: list[str], main_reg: Register = None):
        ret = 0
        transfer_size = gen_transfer_size(self.transfer_size, modifiers)

        if self.transfer_bits is not None:
            ret |= (transfer_size & 1) << self.transfer_bits[0]
            ret |= (transfer_size >> 1) << self.transfer_bits[1]

        ret |= self.base.encode(arg, modifiers, main_reg)
        if arg.offset.type == ArgumentType.Constant:
            val = arg.offset.constant
            if arg.post_increment and (val == 1 or val == -1):
                # adjust transfer size in case of short hand notation
                val = (1 << transfer_size) * val
            val >>= transfer_size
            arg.offset.constant = val
        ret |= self.offset.encode(arg.offset, modifiers, main_reg)

        if arg.post_increment:
            assert self.increment is not None
            ret |= 1 << self.increment[0] # update address
            ret |= 1 << self.increment[1] # post increment

        return ret

    def constraint(self, main_reg: "RegisterEncoding" = None):
        return MemoryConstraint(self.base.constraint(main_reg), self.offset.constraint(main_reg), self.transfer_size, post_increment=self.increment is not None)

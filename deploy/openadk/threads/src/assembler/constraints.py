import logging
from enum import Enum, auto
from dataclasses import dataclass
from .arguments import Argument, ArgumentType
from .modifiers import gen_transfer_size
from .registers import RegUnits, Register, CONTROL_REGS, ADDRESS_UNITS, DATA_UNITS

logger = logging.getLogger(__name__)

class UnitConstraint(Enum):
    Any = 1
    Same = auto()
    Other = auto()
    Control = auto()
    Address = auto()
    Data = auto()
    O2R = auto()
    Address0 = auto()

    def match(self, unit: RegUnits, main_unit: RegUnits = None):
        match self:
            case UnitConstraint.Any:
                return True
            case UnitConstraint.Same:
                assert main_unit is not None
                if unit == main_unit:
                    return True
            case UnitConstraint.Other:
                if unit in ADDRESS_UNITS and main_unit in ADDRESS_UNITS and unit != main_unit:
                    return True
                if unit in DATA_UNITS and main_unit in DATA_UNITS and unit != main_unit:
                    return True
            case UnitConstraint.Control:
                if unit == RegUnits.Control:
                    return True
            case UnitConstraint.O2R:
                assert main_unit is not None
                if unit != main_unit:
                    return True
            case UnitConstraint.Address:
                if unit in ADDRESS_UNITS:
                    return True
            case UnitConstraint.Data:
                if unit in DATA_UNITS:
                    return True
            case UnitConstraint.Address0:
                if unit == RegUnits.Address0:
                    return True

        logger.debug("Match unit failed, arg unit: %s, main unit: %s, constraint: %s", unit, main_unit, self)
        return False

@dataclass
class RegConstraint:
    unit: UnitConstraint | RegUnits
    num: range
    same_num: bool = False
    pc: bool = False

    def match(self, arg: Argument, modifiers: list[str], main_reg: Register = None):
        if arg.type != ArgumentType.Register:
            logger.debug("Match register failed, wrong argument type: %s", arg.type)
            return False
        return self.match_reg(arg.register, main_reg)

    def match_reg(self, register: Register, main_reg: Register = None):
        if type(self.unit) == RegUnits:
            # Concrete unit
            if self.unit != register.unit:
                logger.debug("Match register failed, given unit %s doesn't match required %s", register.unit, self.unit)
                return False
        else:
            if self.pc and register.unit == RegUnits.PC:
                return True
            if not self.unit.match(register.unit, main_reg.unit if main_reg else None):
                return False
        if self.same_num:
            if main_reg and register.number == main_reg.number:
                return True
            else:
                logger.debug("Match register failed, must be same numb but arg num %d != main_reg num %d", register.number, main_reg.number)
                return False
        if register.number in self.num:
            return True
        logger.debug("Match register failed, arg num %d not in range %s", register.number, self.num)
        return False


@dataclass
class ImmConstraint:
    min: int
    max: int
    shift: int = 0

    def match(self, arg: Argument, modifiers: list[str], *args):
        if arg.type != ArgumentType.Constant:
            logger.debug("Match constant failed, wrong argument type: %s", arg.type)
            return False
        return self.match_val(arg.constant)

    def match_val(self, val: int):
        if val & ((1 << self.shift) - 1) != 0:
            logger.debug("Match constant failed, value %d is shifted by %d but has lower bits set", val, self.shift)
            return False
        val >>= self.shift
        if val not in range(self.min, self.max):
            logger.debug("Match constant failed, argument: %d not in range %d %d", val, self.min, self.max)
            return False
        return True

@dataclass
class PieceImmConstraint:
    mask: int
    extra_map: tuple[int, int]

    def match(self, arg: Argument, modifiers: list[str], *args):
        if arg.type != ArgumentType.Constant:
            logger.debug("Match piece constant failed, wrong argument type: %s", arg.type)
            return False
        if self.extra_map is not None and arg.constant == self.extra_map[0]:
            return True
        if arg.constant & (~self.mask) != 0:
            logger.debug("Match piece constant failed, val 0x%x has bits ouf of mask 0x%x", arg.constant, self.mask)
            return False
        if self.extra_map is not None and arg.constant == self.extra_map[1]:
            logger.debug("Match piece constatn failed, val 0x%x is in extra map", arg.constant)
            return False
        return True


@dataclass
class MemoryConstraint:
    base: RegConstraint
    offset: RegConstraint | ImmConstraint
    transfer_size: int
    #pre_increment: bool = False
    post_increment: bool = False

    def match(self, arg: Argument, modifiers: list[str], *args):
        if arg.type != ArgumentType.Memory:
            logger.debug("Match memory failed, wrong argument type: %s", arg.type)
            return False
        if not self.base.match_reg(arg.register):
            logger.debug("Match memory failed, base reg doesn't match")
            return False

        transfer_size = gen_transfer_size(self.transfer_size, modifiers)
        if arg.offset.type == ArgumentType.Constant:
            val = arg.offset.constant
            if arg.post_increment and (val == 1 or val == -1):
                # adjust transfer size in case of short hand notation
                val = (1 << transfer_size) * val
            if val % (1 << transfer_size) != 0:
                logger.critical("Offset (%d) must be multiple of transfer size %d", val, 1 << transfer_size)
                exit()
            val >>= transfer_size
            if not self.offset.match_val(val):
                logger.debug("Match memory failed, offset doesn't match")
                return False
        elif not self.offset.match(arg.offset, modifiers, arg.register):
            logger.debug("Match memory failed, offset doesn't match")
            return False

        if arg.post_increment and not self.post_increment:
            logger.debug("Match memory failed, post increment not supported")
            return False

        return True

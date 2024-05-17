from enum import Enum, auto


class RegUnits(Enum):
    Control = 0
    Data0 = auto()
    Data1 = auto()
    Address0 = auto()
    Address1 = auto()
    PC = auto()
    Ports = auto()
    TR = auto()
    TT = auto()


ADDRESS_UNITS = set((RegUnits.Address0, RegUnits.Address1))
DATA_UNITS = set((RegUnits.Data0, RegUnits.Data1))


class Register:
    unit: RegUnits
    number: int

    def __init__(self, unit: RegUnits, number: int):
        self.unit = unit
        self.number = number

    def __repr__(self):
        return f"Register(unit={self.unit}, number={self.number})"


CONTROL_REGS = {
    "TXENABLE": Register(RegUnits.Control, 0),
    "TXMODE": Register(RegUnits.Control, 1),
    "TXSTATUS": Register(RegUnits.Control, 2),
    "TXRPT": Register(RegUnits.Control, 3),
    "TXTIMER": Register(RegUnits.Control, 4),
    "TXL1START": Register(RegUnits.Control, 5),
    "TXL1END": Register(RegUnits.Control, 6),
    "TXL1COUNT": Register(RegUnits.Control, 7),
    "TXL2START": Register(RegUnits.Control, 8),
    "TXL2END": Register(RegUnits.Control, 9),
    "TXL2COUNT": Register(RegUnits.Control, 10),
    "TXBPOBITS": Register(RegUnits.Control, 11),
    "TXMRSIZE": Register(RegUnits.Control, 12),
    "TXTIMERI": Register(RegUnits.Control, 13),
    "TXDRCTRL": Register(RegUnits.Control, 14),
    "TXDRSIZE": Register(RegUnits.Control, 15),
    "TXCATCH0": Register(RegUnits.Control, 16),
    "TXCATCH1": Register(RegUnits.Control, 17),
    "TXCATCH2": Register(RegUnits.Control, 18),
    "TXCATCH3": Register(RegUnits.Control, 19),
    "TXDEFR": Register(RegUnits.Control, 20),
    "CT.21": Register(RegUnits.Control, 21),
    "TXCLKCTRL": Register(RegUnits.Control, 22),
    "TXINTERN0": Register(RegUnits.Control, 23),
    "TXAMAREG0": Register(RegUnits.Control, 24),
    "TXAMAREG1": Register(RegUnits.Control, 25),
    "TXAMAREG2": Register(RegUnits.Control, 26),
    "TXAMAREG3": Register(RegUnits.Control, 27),
    "TXDIVTIME": Register(RegUnits.Control, 28),
    "TXPRIVEXT": Register(RegUnits.Control, 29),
    "TXTACTCYC": Register(RegUnits.Control, 30),
    "TXIDLECYC": Register(RegUnits.Control, 31),
}

ADDRESS_REGS = {
    "A0StP": Register(RegUnits.Address0, 0),
    "A0.0": Register(RegUnits.Address0, 0),
    "A0FrP": Register(RegUnits.Address0, 1),
    "A0.1": Register(RegUnits.Address0, 1),
    "A0.2": Register(RegUnits.Address0, 2),
    "A0.3": Register(RegUnits.Address0, 3),
    "A0.4": Register(RegUnits.Address0, 4),
    "A0.5": Register(RegUnits.Address0, 5),
    "A0.6": Register(RegUnits.Address0, 6),
    "A0.7": Register(RegUnits.Address0, 7),
    "A0.8": Register(RegUnits.Address0, 8),
    "A0.9": Register(RegUnits.Address0, 9),
    "A0.10": Register(RegUnits.Address0, 10),
    "A0.11": Register(RegUnits.Address0, 11),
    "A0.12": Register(RegUnits.Address0, 12),
    "A0.13": Register(RegUnits.Address0, 13),
    "A0.14": Register(RegUnits.Address0, 14),
    "A0.15": Register(RegUnits.Address0, 15),
    "A1GbP": Register(RegUnits.Address1, 0),
    "A1.0": Register(RegUnits.Address1, 0),
    "A1LbP": Register(RegUnits.Address1, 1),
    "A1.1": Register(RegUnits.Address1, 1),
    "A1.2": Register(RegUnits.Address1, 2),
    "A1.3": Register(RegUnits.Address1, 3),
    "A1.4": Register(RegUnits.Address1, 4),
    "A1.5": Register(RegUnits.Address1, 5),
    "A1.6": Register(RegUnits.Address1, 6),
    "A1.7": Register(RegUnits.Address1, 7),
    "A1.8": Register(RegUnits.Address1, 8),
    "A1.9": Register(RegUnits.Address1, 9),
    "A1.10": Register(RegUnits.Address1, 10),
    "A1.11": Register(RegUnits.Address1, 11),
    "A1.12": Register(RegUnits.Address1, 12),
    "A1.13": Register(RegUnits.Address1, 13),
    "A1.14": Register(RegUnits.Address1, 14),
    "A1.15": Register(RegUnits.Address1, 15),
}

DATA_REGS = {
    "D0Re0": Register(RegUnits.Data0, 0),
    "D0.0": Register(RegUnits.Data0, 0),
    "D0Ar6": Register(RegUnits.Data0, 1),
    "D0.1": Register(RegUnits.Data0, 1),
    "D0Ar4": Register(RegUnits.Data0, 2),
    "D0.2": Register(RegUnits.Data0, 2),
    "D0Ar2": Register(RegUnits.Data0, 3),
    "D0.3": Register(RegUnits.Data0, 3),
    "D0FrT": Register(RegUnits.Data0, 4),
    "D0.4": Register(RegUnits.Data0, 4),
    "D0.5": Register(RegUnits.Data0, 5),
    "D0.6": Register(RegUnits.Data0, 6),
    "D0.7": Register(RegUnits.Data0, 7),
    "D0.8": Register(RegUnits.Data0, 8),
    "D0.9": Register(RegUnits.Data0, 9),
    "D0.10": Register(RegUnits.Data0, 10),
    "D0.11": Register(RegUnits.Data0, 11),
    "D0.12": Register(RegUnits.Data0, 12),
    "D0.13": Register(RegUnits.Data0, 13),
    "D0.14": Register(RegUnits.Data0, 14),
    "D0.15": Register(RegUnits.Data0, 15),
    "D0.16": Register(RegUnits.Data0, 16),
    "D0.17": Register(RegUnits.Data0, 17),
    "D0.18": Register(RegUnits.Data0, 18),
    "D0.19": Register(RegUnits.Data0, 19),
    "D0.20": Register(RegUnits.Data0, 20),
    "D0.21": Register(RegUnits.Data0, 21),
    "D0.22": Register(RegUnits.Data0, 22),
    "D0.23": Register(RegUnits.Data0, 23),
    "D0.24": Register(RegUnits.Data0, 24),
    "D0.25": Register(RegUnits.Data0, 25),
    "D0.26": Register(RegUnits.Data0, 26),
    "D0.27": Register(RegUnits.Data0, 27),
    "D0.28": Register(RegUnits.Data0, 28),
    "D0.29": Register(RegUnits.Data0, 29),
    "D0.30": Register(RegUnits.Data0, 30),
    "D0.31": Register(RegUnits.Data0, 31),
    "D1Re0": Register(RegUnits.Data1, 0),
    "D1.0": Register(RegUnits.Data1, 0),
    "D1Ar5": Register(RegUnits.Data1, 1),
    "D1.1": Register(RegUnits.Data1, 1),
    "D1Ar3": Register(RegUnits.Data1, 2),
    "D1.2": Register(RegUnits.Data1, 2),
    "D1Ar1": Register(RegUnits.Data1, 3),
    "D1.3": Register(RegUnits.Data1, 3),
    "D1RtP": Register(RegUnits.Data1, 4),
    "D1.4": Register(RegUnits.Data1, 4),
    "D1.5": Register(RegUnits.Data1, 5),
    "D1.6": Register(RegUnits.Data1, 6),
    "D1.7": Register(RegUnits.Data1, 7),
    "D1.8": Register(RegUnits.Data1, 8),
    "D1.9": Register(RegUnits.Data1, 9),
    "D1.10": Register(RegUnits.Data1, 10),
    "D1.11": Register(RegUnits.Data1, 11),
    "D1.12": Register(RegUnits.Data1, 12),
    "D1.13": Register(RegUnits.Data1, 13),
    "D1.14": Register(RegUnits.Data1, 14),
    "D1.15": Register(RegUnits.Data1, 15),
    "D1.16": Register(RegUnits.Data1, 16),
    "D1.17": Register(RegUnits.Data1, 17),
    "D1.18": Register(RegUnits.Data1, 18),
    "D1.19": Register(RegUnits.Data1, 19),
    "D1.20": Register(RegUnits.Data1, 20),
    "D1.21": Register(RegUnits.Data1, 21),
    "D1.22": Register(RegUnits.Data1, 22),
    "D1.23": Register(RegUnits.Data1, 23),
    "D1.24": Register(RegUnits.Data1, 24),
    "D1.25": Register(RegUnits.Data1, 25),
    "D1.26": Register(RegUnits.Data1, 26),
    "D1.27": Register(RegUnits.Data1, 27),
    "D1.28": Register(RegUnits.Data1, 28),
    "D1.29": Register(RegUnits.Data1, 29),
    "D1.30": Register(RegUnits.Data1, 30),
    "D1.31": Register(RegUnits.Data1, 31),
}

PC_REGS = {
    "PC": Register(RegUnits.PC, 0),
    "PCX": Register(RegUnits.PC, 1),
}

REGISTERS = {**CONTROL_REGS, **ADDRESS_REGS, **DATA_REGS, **PC_REGS}

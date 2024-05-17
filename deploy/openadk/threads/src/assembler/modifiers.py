MODIFIERS = [
    "S",  # set condition flags
    "B", "W", "D", "L", # size of transfer
    "EQ", "NE", "NZ", "CS", "LO", "CC", "HS", "MI", "PL", "NC", "VS", "VC", "HI", "LS", "GE", "LT", "GT", "LE", # conditions
    "NV", # never condition, not really part of modifiers
    "Z", "N", # parse single letter conditions last
    "T", # move top value
    "MT", # mask top value
    "MB", # mask bottom value
    "R", # repeat
    # custom flags
    "P", # DSP
    "C", # modified for complex numbers
    "X", # split 8 multi for source 1
    "U", # unsigned
    ]

TRANSFER_MAP = {"B": 0, "W": 1, "D": 2, "L": 3}

CONDITION_MAP = {
    "A": 0,
    "EQ": 1,
    "Z": 1,
    "NE": 2,
    "NZ": 2,
    "CS": 3,
    "LO": 3,
    "CC": 4,
    "HS": 4,
    "MI": 5,
    "N": 5,
    "PL": 6,
    "NC": 6,
    "VS": 7,
    "VC": 8,
    "HI": 9,
    "LS": 10,
    "GE": 11,
    "LT": 12,
    "GT": 13,
    "LE": 14,
    "NV": 15,
    }


def parse_modifiers(raw: str):
    modifiers = []
    for modifier in MODIFIERS:
        if not raw.startswith(modifier):
            continue
        raw = raw[len(modifier):]
        if modifier == "MB":
            modifiers.append("M")
        elif modifier == "MT":
            modifiers.extend(["M", "T"])
        else:
            modifiers.append(modifier)
    return modifiers

def gen_conditional(condition: str) -> int:
    return CONDITION_MAP[condition]

def gen_transfer_size(transfer_size: int | None, modifiers: list[str]):
    for modifier in modifiers:
        if modifier in TRANSFER_MAP:
            break
    else:
        assert transfer_size is not None
        return transfer_size
    assert transfer_size is None
    transfer_size = TRANSFER_MAP[modifier]
    return transfer_size

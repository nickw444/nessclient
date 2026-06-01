import enum
import random
from typing import Iterable
from nessclient.event import (
    ZoneUpdate_1_16,
    MiscellaneousAlarmsUpdate,
    ArmingUpdate,
    OutputsUpdate,
    AuxiliaryOutputsUpdate,
)


def or_list(vals: list[int]) -> int:
    output = 0
    for val in vals:
        output |= val
    return output


def select_bitfield(bitfield: Iterable[enum.Enum]) -> list[int]:
    all_elems = [elem.value for elem in bitfield]

    # Begin with the 'no bits' case
    val_list = [0]
    for k in range(1, len(all_elems)):
        # Take a random subset of 16 values with k zones active
        for _ in range(0, len(all_elems)):
            while True:
                elem_subset = random.sample(all_elems, k)
                val = or_list(elem_subset)
                if val not in val_list:
                    val_list.append(val)
                    break
    # Add the 'all bits' case
    val_list.append(or_list(all_elems))
    return val_list


# Run this file stand-alone to generate new lists
if __name__ == "__main__":
    print(
        "\nzones_list:"
        + str([f"0x{val:04x}" for val in select_bitfield(ZoneUpdate_1_16.Zone)])
    )
    print(
        "\nmisc_alarm_list:"
        + str(
            [
                f"0x{val:04x}"
                for val in select_bitfield(MiscellaneousAlarmsUpdate.AlarmType)
            ]
        )
    )
    print(
        "\narming_list:"
        + str([f"0x{val:04x}" for val in select_bitfield(ArmingUpdate.ArmingStatus)])
    )
    print(
        "\noutput_list:"
        + str([f"0x{val:04x}" for val in select_bitfield(OutputsUpdate.OutputType)])
    )
    print(
        "\nauxoutput_list:"
        + str(
            [f"0x{val:04x}" for val in select_bitfield(AuxiliaryOutputsUpdate.OutputType)]
        )
    )

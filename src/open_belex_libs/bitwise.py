r"""
By Dylon Edwards and Brian Beckman
"""

from open_belex.literal import INV_RL, RL, VR, belex_apl


@belex_apl
def or_16(Belex, result: VR, src1: VR, src2: VR) -> None:
    RL[:] <= src1()
    RL[:] |= src2()
    result[:] <= RL()


@belex_apl
def xor_16(Belex, res: VR, src1: VR, src2: VR) -> None:
    RL[:] <= src1()
    RL[:] ^= src2()
    res[:] <= RL()


@belex_apl
def and_16(Belex, res: VR, x: VR, y: VR) -> None:
    RL[:] <= x() & y()
    res[:] <= RL()


@belex_apl
def not_16(Belex, res: VR, x: VR) -> None:
    RL[:] <= x()
    res[:] <= INV_RL()

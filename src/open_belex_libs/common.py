r"""
By Dylon Edwards and Brian Beckman
"""

from open_belex.kernel_libs.common import (cpy_16, cpy_imm_16,
                                           cpy_imm_16_to_rl, cpy_vr)
from open_belex.literal import (INV_RSP16, NOOP, RL, RN_REG_FLAGS, RSP2K,
                                RSP16, RSP32K, RSP256, RSP_END, RSP_START_RET,
                                SM_0XFFFF, VR, Mask, belex_apl)


@belex_apl
def reset_16(Belex, tgt: VR):
    tgt[::] <= RSP16()


@belex_apl
def set_16(Belex, tgt: VR):
    tgt[::] <= INV_RSP16()


@belex_apl
def rsp_out_in(Belex, mask: Mask) -> None:
    RSP16[mask] <= RL()
    RSP256()    <= RSP16()
    RSP2K()     <= RSP256()
    RSP_START_RET()
    RSP256()    <= RSP2K()
    RSP16()     <= RSP256()


@belex_apl
def rsp_out(Belex, mask: Mask) -> None:
    RSP16[mask] <= RL()
    RSP256()    <= RSP16()
    RSP2K()     <= RSP256()
    RSP32K()    <= RSP2K()
    NOOP()
    NOOP()
    RSP_END()


@belex_apl
def set_m(Belex, mdst: Mask) -> None:
    vreg = RN_REG_FLAGS
    vreg[mdst] <= INV_RSP16()


@belex_apl
def rl_from_sb(Belex, vr: VR) -> None:
    RL[SM_0XFFFF] <= vr()


@belex_apl
def rl_xor_equals_sb(Belex, vr: VR) -> None:
    RL[SM_0XFFFF] ^= vr()


@belex_apl
def sb_from_rl(Belex, vr: VR) -> None:
    vr[SM_0XFFFF] <= RL()


@belex_apl
def src_vr_to_dst_vr(Belex, dst: VR, src: VR) -> None:
    rl_from_sb(src)
    sb_from_rl(dst)

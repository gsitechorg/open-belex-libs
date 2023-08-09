r"""
 By Dylon Edwards and Brian Beckman

 Copyright 2023 GSI Technology, Inc.

 Permission is hereby granted, free of charge, to any person obtaining a copy of
 this software and associated documentation files (the “Software”), to deal in
 the Software without restriction, including without limitation the rights to
 use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
 the Software, and to permit persons to whom the Software is furnished to do so,
 subject to the following conditions:

 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
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

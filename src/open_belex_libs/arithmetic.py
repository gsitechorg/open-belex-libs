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

from open_belex.literal import (GGL, GL, INV_GL, INV_RL, INV_RSP16, NRL, RL,
                                RN_REG_FLAGS, RN_REG_G0, RN_REG_G1, RN_REG_G2,
                                RN_REG_G3, RN_REG_T0, RN_REG_T1, RN_REG_T2,
                                RN_REG_T3, RN_REG_T4, RN_REG_T5, RN_REG_T6,
                                RSP16, SM_0X000F, SM_0X0001, SM_0X1111,
                                SM_0X3333, SM_0XFFFF, SM_REG0, SM_REG1, SRL,
                                VR, Mask, apl_commands, apl_set_rn_reg,
                                apl_set_sm_reg, belex_apl)

#   ___                         ___       _   _       _           _
#  / __|_  _ _ __  ___ _ _ ___ / _ \ _ __| |_(_)_ __ (_)______ __| |
#  \__ \ || | '_ \/ -_) '_|___| (_) | '_ \  _| | '  \| |_ / -_) _` |
#  |___/\_,_| .__/\___|_|      \___/| .__/\__|_|_|_|_|_/__\___\__,_|
#    _____  |_|__  __ _        _    |_|    _
#   / __\ \ / /  \/  | |      /_\  __| |__| |___ _ _
#  | (_ |\ V /| |\/| | |__   / _ \/ _` / _` / -_) '_|
#   \___| \_/ |_|  |_|____| /_/ \_\__,_\__,_\___|_|


@belex_apl
def add_u16_lifted_rn_regs(
        Belex,
        res: VR, x: VR, y: VR,  # original parameters of the interface
        x_xor_y: VR, cout1: VR, flags: VR  # lifted RN_REG parameters
        ) -> None:
    r"""Moshe's 12-clock carry-prediction adder with RN_REGs lifted
    from local constants to parameters; tested in belex-tests/tests/
    test_belex_libs_arithmetic.py::test"""

    os = SM_0X0001
    fs = SM_0XFFFF
    threes = SM_0X3333
    ones = SM_0X1111
    one_f = SM_0X000F

    # "Lifting" means lift these local variables with constant
    # values into parameter position.

    # x_xor_y = RN_REG_T0
    # cout1 = RN_REG_T1
    # flags = RN_REG_FLAGS

    # OBSERVED FACT: The lifted register may be anything EXCEPT 15, which is
    # its original value!

    # Carry in/out flag
    C_FLAG = 0

    with apl_commands("instruction 1"):
        RL[fs] <= x()
    with apl_commands("instruction 2"):
        RL[fs] ^= y()
        GGL[threes] <= RL()
    with apl_commands("instruction 3"):
        x_xor_y[fs] <= RL()
    with apl_commands("instruction 4"):
        cout1[ones] <= RL()
        cout1[ones<<1] <= GGL()
        RL[ones<<2] <= x_xor_y() & GGL()
        RL[threes] <= x() & y()
    with apl_commands("instruction 5"):
        cout1[ones<<2] <= RL()
        RL[ones<<3] <= x_xor_y() & NRL()
        RL[ones<<1] |= x_xor_y() & NRL()
        RL[ones<<2] <= x() & y()
    with apl_commands("instruction 6"):
        cout1[ones<<3] <= RL()
        RL[ones<<3] <= x() & y()
        RL[ones<<2] |= x_xor_y() & NRL()
        GGL[os] <= RL()
    with apl_commands("instruction 7"):
        RL[ones<<3] |= x_xor_y() & NRL()
        GL[os<<3] <= RL()
        RL[os] <= cout1()
    with apl_commands("instruction 8"):
        RL[one_f<<4] |= cout1() & GL()
        GL[os<<7] <= RL()
        res[os] <= RL()
    with apl_commands("instruction 9"):
        RL[one_f<<8] |= cout1() & GL()
        GL[os<<11] <= RL()
        RL[os] <= GGL()
    with apl_commands("instruction 10"):
        RL[one_f<<12] |= cout1() & GL()
        GL[os<<15] <= RL()
    with apl_commands("instruction 11"):
        flags[os<<C_FLAG] <= GL()
        RL[~os] <= x_xor_y() ^ NRL()
    with apl_commands("instruction 12"):
        res[~os] <= RL()


@belex_apl
def add_u16_lifted_rn_regs_one_lifted_sm_reg(
        Belex,
        res: VR, x: VR, y: VR,  # original parameters of the interface
        x_xor_y: VR, cout1: VR, flags: VR,  # lifted RN_REG parameters
        sm_just_one: Mask
        ) -> None:
    r"""Moshe's 12-clock carry-prediction adder with RN_REGs lifted
    from local constants to parameters; tested in belex-tests/tests/
    test_belex_libs_arithmetic.py::test"""

    os = sm_just_one

    # The rest of these are lowered in from the environment of
    # gvml pseudo-constants.

    fs = SM_0XFFFF
    threes = SM_0X3333
    ones = SM_0X1111
    one_f = SM_0X000F

    # "Lifting" means lift these local variables with constant
    # values into parameter position.

    # x_xor_y = RN_REG_T0
    # cout1 = RN_REG_T1
    # flags = RN_REG_FLAGS

    # OBSERVED FACT: The lifted register may be anything EXCEPT 15, which is
    # its original value!

    # Carry in/out flag
    C_FLAG = 0

    with apl_commands("instruction 1"):
        RL[fs] <= x()
    with apl_commands("instruction 2"):
        RL[fs] ^= y()
        GGL[threes] <= RL()
    with apl_commands("instruction 3"):
        x_xor_y[fs] <= RL()
    with apl_commands("instruction 4"):
        cout1[ones] <= RL()
        cout1[ones<<1] <= GGL()
        RL[ones<<2] <= x_xor_y() & GGL()
        RL[threes] <= x() & y()
    with apl_commands("instruction 5"):
        cout1[ones<<2] <= RL()
        RL[ones<<3] <= x_xor_y() & NRL()
        RL[ones<<1] |= x_xor_y() & NRL()
        RL[ones<<2] <= x() & y()
    with apl_commands("instruction 6"):
        cout1[ones<<3] <= RL()
        RL[ones<<3] <= x() & y()
        RL[ones<<2] |= x_xor_y() & NRL()
        GGL[os] <= RL()
    with apl_commands("instruction 7"):
        RL[ones<<3] |= x_xor_y() & NRL()
        GL[os<<3] <= RL()
        RL[os] <= cout1()
    with apl_commands("instruction 8"):
        RL[one_f<<4] |= cout1() & GL()
        GL[os<<7] <= RL()
        res[os] <= RL()
    with apl_commands("instruction 9"):
        RL[one_f<<8] |= cout1() & GL()
        GL[os<<11] <= RL()
        RL[os] <= GGL()
    with apl_commands("instruction 10"):
        RL[one_f<<12] |= cout1() & GL()
        GL[os<<15] <= RL()
    with apl_commands("instruction 11"):
        flags[os<<C_FLAG] <= GL()
        RL[~os] <= x_xor_y() ^ NRL()
    with apl_commands("instruction 12"):
        res[~os] <= RL()


@belex_apl
def add_u16_lifted_rn_regs_all_lifted_sm_regs(
        Belex,
        res: VR, x: VR, y: VR,  # original parameters of the interface
        x_xor_y: VR, cout1: VR, flags: VR,  # lifted RN_REG parameters
        sm_just_one: Mask, sm_all: Mask,
        sm_threes: Mask, sm_ones: Mask,
        sm_one_f: Mask
        ) -> None:
    r"""Moshe's 12-clock carry-prediction adder with RN_REGs lifted
    from local constants to parameters; tested in belex-tests/tests/
    test_belex_libs_arithmetic.py::test"""

    os = sm_just_one
    fs = sm_all
    threes = sm_threes
    ones = sm_ones
    one_f = sm_one_f

    # The rest of these are lowered in from the environment of
    # gvml pseudo-constants.

    # fs = SM_0XFFFF
    # threes = SM_0X3333
    # ones = SM_0X1111
    # one_f = SM_0X000F

    # "Lifting" means lift these local variables with constant
    # values into parameter position.

    # x_xor_y = RN_REG_T0
    # cout1 = RN_REG_T1
    # flags = RN_REG_FLAGS

    # OBSERVED FACT: The lifted register may be anything EXCEPT 15, which is
    # its original value!

    # Carry in/out flag
    C_FLAG = 0

    with apl_commands("instruction 1"):
        RL[fs] <= x()
    with apl_commands("instruction 2"):
        RL[fs] ^= y()
        GGL[threes] <= RL()
    with apl_commands("instruction 3"):
        x_xor_y[fs] <= RL()
    with apl_commands("instruction 4"):
        cout1[ones] <= RL()
        cout1[ones<<1] <= GGL()
        RL[ones<<2] <= x_xor_y() & GGL()
        RL[threes] <= x() & y()
    with apl_commands("instruction 5"):
        cout1[ones<<2] <= RL()
        RL[ones<<3] <= x_xor_y() & NRL()
        RL[ones<<1] |= x_xor_y() & NRL()
        RL[ones<<2] <= x() & y()
    with apl_commands("instruction 6"):
        cout1[ones<<3] <= RL()
        RL[ones<<3] <= x() & y()
        RL[ones<<2] |= x_xor_y() & NRL()
        GGL[os] <= RL()
    with apl_commands("instruction 7"):
        RL[ones<<3] |= x_xor_y() & NRL()
        GL[os<<3] <= RL()
        RL[os] <= cout1()
    with apl_commands("instruction 8"):
        RL[one_f<<4] |= cout1() & GL()
        GL[os<<7] <= RL()
        res[os] <= RL()
    with apl_commands("instruction 9"):
        RL[one_f<<8] |= cout1() & GL()
        GL[os<<11] <= RL()
        RL[os] <= GGL()
    with apl_commands("instruction 10"):
        RL[one_f<<12] |= cout1() & GL()
        GL[os<<15] <= RL()
    with apl_commands("instruction 11"):
        flags[os<<C_FLAG] <= GL()
        RL[~os] <= x_xor_y() ^ NRL()
    with apl_commands("instruction 12"):
        res[~os] <= RL()


@belex_apl
def add_u16(Belex, res: VR, x: VR, y: VR) -> None:
    r"""Moshe's 12-clock carry-prediction adder, verbatim in BELEX."""
    os = SM_0X0001
    fs = SM_0XFFFF
    threes = SM_0X3333
    ones = SM_0X1111
    one_f = SM_0X000F

    x_xor_y = RN_REG_T0
    cout1 = RN_REG_T1
    flags = RN_REG_FLAGS

    # Carry in/out flag
    C_FLAG = 0

    with apl_commands("instruction 1"):
        RL[fs] <= x()
    with apl_commands("instruction 2"):
        RL[fs] ^= y()
        GGL[threes] <= RL()
    with apl_commands("instruction 3"):
        x_xor_y[fs] <= RL()
    with apl_commands("instruction 4"):
        cout1[ones] <= RL()
        cout1[ones<<1] <= GGL()
        RL[ones<<2] <= x_xor_y() & GGL()
        RL[threes] <= x() & y()
    with apl_commands("instruction 5"):
        cout1[ones<<2] <= RL()
        RL[ones<<3] <= x_xor_y() & NRL()
        RL[ones<<1] |= x_xor_y() & NRL()
        RL[ones<<2] <= x() & y()
    with apl_commands("instruction 6"):
        cout1[ones<<3] <= RL()
        RL[ones<<3] <= x() & y()
        RL[ones<<2] |= x_xor_y() & NRL()
        GGL[os] <= RL()
    with apl_commands("instruction 7"):
        RL[ones<<3] |= x_xor_y() & NRL()
        GL[os<<3] <= RL()
        RL[os] <= cout1()
    with apl_commands("instruction 8"):
        RL[one_f<<4] |= cout1() & GL()
        GL[os<<7] <= RL()
        res[os] <= RL()
    with apl_commands("instruction 9"):
        RL[one_f<<8] |= cout1() & GL()
        GL[os<<11] <= RL()
        RL[os] <= GGL()
    with apl_commands("instruction 10"):
        RL[one_f<<12] |= cout1() & GL()
        GL[os<<15] <= RL()
    with apl_commands("instruction 11"):
        flags[os<<C_FLAG] <= GL()
        RL[~os] <= x_xor_y() ^ NRL()
    with apl_commands("instruction 12"):
        res[~os] <= RL()


@belex_apl
def add_u16_literal_sections(Belex, res: VR, x: VR, y: VR) -> None:
    r"""Moshe's 12-clock carry-prediction adder,
    with literal section notation instead of with symbolic masks.
    Test in test_belex_library that the generated code is
    identical to the verbatim version 'add_u16'."""
    x_xor_y = RN_REG_T0
    cout1 = RN_REG_T1
    flags = RN_REG_FLAGS

    C_FLAG = 0

    with apl_commands("instruction 1"):
        RL["0xFFFF"] <= x()
    with apl_commands("instruction 2"):
        RL["0xFFFF"] ^= y()
        GGL["014589CD"] <= RL()
    with apl_commands("instruction 3"):
        x_xor_y["0xFFFF"] <= RL()
    with apl_commands("instruction 4"):
        cout1["048C"] <= RL()
        cout1["159D"] <= GGL()
        RL["26AE"] <= x_xor_y() & GGL()
        RL["014589CD"] <= x() & y()
    with apl_commands("instruction 5"):
        cout1["26AE"] <= RL()
        RL["37BF"] <= x_xor_y() & NRL()
        RL["159D"] |= x_xor_y() & NRL()
        RL["26AE"] <= x() & y()
    with apl_commands("instruction 6"):
        cout1["37BF"] <= RL()
        RL["37BF"] <= x() & y()
        RL["26AE"] |= x_xor_y() & NRL()
        GGL["0"] <= RL()
    with apl_commands("instruction 7"):
        RL["37BF"] |= x_xor_y() & NRL()
        GL["3"] <= RL()
        RL["0"] <= cout1()
    with apl_commands("instruction 8"):
        RL["4567"] |= cout1() & GL()
        GL["7"] <= RL()
        res["0"] <= RL()
    with apl_commands("instruction 9"):
        RL["89AB"] |= cout1() & GL()
        GL["B"] <= RL()
        RL["0"] <= GGL()
    with apl_commands("instruction 10"):
        RL["CDEF"] |= cout1() & GL()
        GL["F"] <= RL()
    with apl_commands("instruction 11"):
        # flags[f"0<<{C_FLAG}"] <= GL()  # proposed new syntax
        flags["0"] <= GL()
        # RL["~0"] <= x_xor_y() ^ NRL()  # proposed new syntax
        RL["0xFFFE"] <= x_xor_y() ^ NRL()
    with apl_commands("instruction 12"):
        # res["~0"] <= RL()  # proposed new syntax
        res["0xFFFE"] <= RL()


#  ___                         ___       _   _       _           _
# / __|_  _ _ __  ___ _ _ ___ / _ \ _ __| |_(_)_ __ (_)______ __| |
# \__ \ || | '_ \/ -_) '_|___| (_) | '_ \  _| | '  \| |_ / -_) _` |
# |___/\_,_| .__/\___|_|      \___/| .__/\__|_|_|_|_|_/__\___\__,_|
#          |_|                     |_|
#   _____   ____  __ _      ___      _    _               _
#  / __\ \ / /  \/  | |    / __|_  _| |__| |_ _ _ __ _ __| |_ ___ _ _
# | (_ |\ V /| |\/| | |__  \__ \ || | '_ \  _| '_/ _` / _|  _/ _ \ '_|
#  \___| \_/ |_|  |_|____| |___/\_,_|_.__/\__|_| \__,_\__|\__\___/_|


@belex_apl
def sub_u16(Belex, res: VR, x: VR, y: VR) -> None:
    x_xor_noty = RN_REG_T0  # FIXME: Should this be "not__x_xor_y"?
    cout1 = RN_REG_T1
    noty = RN_REG_T2

    # Borrow in/out flag
    B_FLAG = 1

    with apl_commands("instruction 1"):
        RL[SM_0XFFFF] <= y()
    with apl_commands("instruction 2"):
        noty[SM_0XFFFF] <= INV_RL()
        RL[SM_0XFFFF] ^= x()
    with apl_commands("instruction 3"):
        x_xor_noty[SM_0XFFFF] <= INV_RL()
        RL[SM_0X3333] <= INV_RL()
        GGL[SM_0X3333] <= RL()
    with apl_commands("instruction 4"):
        cout1[SM_0X1111] <= RL()
        cout1[SM_0X1111<<1] <= GGL()
        RL[SM_0X1111<<2] <= x_xor_noty() & GGL()
        RL[SM_0X3333] <= x() & noty()
    with apl_commands("instruction 5"):
        cout1[SM_0X1111<<2] <= RL()
        RL[SM_0X1111<<3] <= x_xor_noty() & NRL()
        RL[SM_0X1111<<1] |= x_xor_noty() & NRL()
        RL[SM_0X1111<<2] <= x() & noty()
    with apl_commands("instruction 6"):
        cout1[SM_0X1111<<3] <= RL()
        RL[SM_0X1111<<3] <= x() & noty()
        RL[SM_0X1111<<2] |= x_xor_noty() & NRL()
    with apl_commands("instruction 7"):
        RL[SM_0X1111<<3] |= x_xor_noty() & NRL()
    with apl_commands("instruction 8"):
        RL[SM_0X000F] |= cout1()
        GGL[SM_0X0001<<1] <= RL()
        GL[SM_0X0001<<3] <= RL()
    with apl_commands("instruction 9"):
        RL[SM_0X0001] <= ~x_xor_noty() & INV_RSP16()
        RL[SM_0X0001<<1] <= x_xor_noty() ^ NRL()
        RL[SM_0X000F<<4] |= cout1() & GL()
        GL[SM_0X0001<<7] <= RL()
    with apl_commands("instruction 10"):
        res[~(SM_0XFFFF<<2)] <= RL()
        RL[SM_0X000F<<8] |= cout1() & GL()
        GL[SM_0X0001<<11] <= RL()
    with apl_commands("instruction 11"):
        RL[SM_0X0001<<1] <= GGL()
        RL[SM_0X000F<<12] |= cout1() & GL()
        GL[SM_0X0001<<11] <= RL()
    with apl_commands("instruction 12"):
        RL[SM_0XFFFF<<2] <= x_xor_noty() ^ NRL()
        RN_REG_FLAGS[SM_0X0001<<B_FLAG] <= INV_GL()
        RL[SM_0X0001<<B_FLAG] <= INV_GL()
        GL[SM_0X0001<<B_FLAG] <= RL()
    with apl_commands("instruction 13"):
        res[SM_0XFFFF<<2] <= RL()


@belex_apl
def init_mul_16_7tmp(Belex, x: VR, y: VR, s0: VR, s1: VR, _2x: VR, m0: VR,
                     m1: VR, t_y_res_lsb: VR):
    # input: x, y
    # output: s0 = y[0] ? x>>1 : 0
    #         _2x = rotate_left(x)
    #         m0 = y[2] ? 0xffff : 0
    #         t_y_res_lsb[0] = y[0] & x[0]
    #             [15..1] = y[15..1]
    #         RL = y[1] ? x : 0

    # Copy y to t_y_res_lsb (to allow y and res_msb use the same vreg)
    with apl_commands():
        RL[SM_0XFFFF] <= y()
        m1[SM_0XFFFF] <= RSP16()
    with apl_commands():
        t_y_res_lsb[SM_0XFFFF] <= RL()  # t_y_res_lsb = y
        GL[SM_0X0001 << 2] <= RL()  # GL = y[2]
    with apl_commands():
        m0[SM_0XFFFF] <= GL()  # m0 = y[2] ? 0xffff : 0
        RL[SM_0XFFFF] <= x()  # RL = x
        GGL[SM_0X0001 << 15] <= RL()  # GL = x[15]
    with apl_commands():
        # _2x[SM_0X0001] <= GL()
        _2x[~SM_0X0001] <= NRL()  # _2x = rotate_left(x)
        RL[SM_0X0001] <= t_y_res_lsb()
        GL[SM_0X0001] <= RL()  # GL = t_y_res_lsb[0] (= y[0])
    RL[SM_0XFFFF] <= x() & GL()  # RL = y[0] ? x ; 0
    with apl_commands():
        t_y_res_lsb[SM_0X0001] <= RL()  # t_y_res_lsb[0] = y[0] & x[0];
        (SM_0X0001 << 15)[s0, s1] <= GGL()
    with apl_commands():
        s0[~(SM_0X0001 << 15)] <= SRL()  # s0[15..0] = y[0] ? x>>1 : 0
        RL[SM_0X0001 << 1] <= t_y_res_lsb()
        GL[SM_0X0001 << 1] <= RL()  # GL[1] = t_y_res_lsb[1] (= y[1])
    RL[SM_0XFFFF] <= x() & GL()  # RL = y[1] ? x : 0


@belex_apl
def _3to2_mul_16_7tmp(Belex, c: VR, s0: VR, s1: VR, _2x: VR, m0: VR, m1: VR,
                      c_xor_s: VR, t_y_res_lsb: VR, iter_msk: Mask, sm_0x3fff: Mask):
    with apl_commands():
        c[SM_0XFFFF] <= RL()
        RL[~(SM_0X0001 << 15)] ^= s0()
        RL[SM_0X0001 << 15] ^= s0() & m1()
    with apl_commands():
        c_xor_s[SM_0XFFFF] <= RL()
        RL[~SM_0X0001] ^= _2x() & m0()
    with apl_commands():
        s1[~(SM_0X0001 << 15)] <= SRL()
        RL[iter_msk << 2] <= t_y_res_lsb()
        GL[iter_msk << 2] <= RL()
        RL[SM_0X0001 << 15] <= c() & s0() & m1()
    with apl_commands():
        m1[SM_0XFFFF] <= GL()
        RL[sm_0x3fff << 1] <= c() & s0()
        RL[SM_0X0001] <= c_xor_s()
        GL[SM_0X0001] <= RL()
    with apl_commands():
        t_y_res_lsb[iter_msk] <= GL()
        RL[SM_0X0001] <= c() & s0()
        RL[~SM_0X0001] |= _2x() & m0() & c_xor_s()


@belex_apl
def _3to2_mul_16_7tmp_iter_msk_13(Belex, c: VR, s0: VR, s1: VR, _2x: VR, m0: VR,
                                  m1: VR, c_xor_s: VR, t_y_res_lsb: VR,
                                  sm_0x3fff: Mask):
    with apl_commands():
        c[SM_0XFFFF] <= RL()
        RL[~(SM_0X0001 << 15)] ^= s0()
        RL[SM_0X0001 << 15] ^= s0() & m1()
    with apl_commands():
        c_xor_s[SM_0XFFFF] <= RL()
        RL[~SM_0X0001] ^= _2x() & m0()
    with apl_commands():
        s1[~(SM_0X0001 << 15)] <= SRL()
        RL[SM_0X0001 << 15] <= c() & s0() & m1()
        GGL[SM_0X0001 << 15] <= RL()
    with apl_commands():
        RL[SM_0X0001 << 15] <= t_y_res_lsb()  # iter
        GL[SM_0X0001 << 15] <= RL()  # iter
    with apl_commands():
        m1[SM_0XFFFF] <= GL()
        RL[sm_0x3fff << 1] <= c() & s0()
        RL[SM_0X0001] <= c_xor_s()
        GL[SM_0X0001] <= RL()
    with apl_commands():
        t_y_res_lsb[SM_0X0001 << 13] <= GL()  # iter
        RL[SM_0X0001] <= c() & s0()
        RL[sm_0x3fff << 1] |= _2x() & m0() & c_xor_s()
        RL[SM_0X0001 << 15] <= (_2x() & m0() & c_xor_s()) | GGL()


@belex_apl
def _3to2_mul_16_7tmp_last(Belex, c: VR, s0: VR, s1: VR, _2x: VR, m0: VR, m1: VR,
                           c_xor_s: VR, t_y_res_lsb: VR, sm_0x3fff: Mask):
    with apl_commands():
        c[SM_0XFFFF] <= RL()
        RL[~(SM_0X0001 << 15)] ^= s0()
        RL[SM_0X0001 << 15] ^= s0() & m1()
    with apl_commands():
        c_xor_s[SM_0XFFFF] <= RL()
        RL[~SM_0X0001] ^= _2x() & m0()
    with apl_commands():
        s1[~(SM_0X0001 << 15)] <= SRL()
        RL[SM_0X0001 << 15] <= c() & s0() & m1()
        RL[SM_0X0001] <= c_xor_s()
        GL[SM_0X0001] <= RL()
    RL[sm_0x3fff << 1] <= c() & s0()
    with apl_commands():
        t_y_res_lsb[SM_0X0001 << 14] <= GL()
        RL[SM_0X0001] <= c() & s0()
        RL[~SM_0X0001] |= _2x() & m0() & c_xor_s()


@belex_apl
def mul_u16_u16xu16_7t(Belex, t_y_z_lsb: VR, c: VR, z_lsb: VR, m0: VR, y: VR):
    C_FLAG = 0
    with apl_commands():
        c[SM_0XFFFF] <= RL()
        RL[~(SM_0X0001 << 15)] <= t_y_z_lsb()
        RL[SM_0X0001 << 15] <= y() & m0()
    with apl_commands():
        z_lsb[~(SM_0X0001 << 15)] <= RL()
        y[SM_0X0001 << 15] <= RL()
        RL[SM_0XFFFF] <= c()
    with apl_commands():
        RL[SM_0X0001] ^= y()
        RL[~SM_0X0001] |= y()
        GL[SM_0X0001] <= RL()
    with apl_commands():
        z_lsb[SM_0X0001 << 15] <= GL()
        RL[SM_0X0001] <= c() & y()
    with apl_commands():
        RL[SM_0XFFFF] <= INV_RL()
        GL[SM_0XFFFF] <= RL()
    RN_REG_FLAGS[SM_0X0001 << C_FLAG] <= INV_GL()


def mul_u16(res: int, x: int, y: int) -> None:
    apl_set_rn_reg(RN_REG_G0, x)
    apl_set_rn_reg(RN_REG_G1, y)
    init_mul_16_7tmp(x=RN_REG_G0, y=RN_REG_G1, s0=RN_REG_T4, s1=RN_REG_T0,
                     _2x=RN_REG_T1, m0=RN_REG_T2, m1=RN_REG_T5,
                     t_y_res_lsb=RN_REG_T6)

    apl_set_rn_reg(RN_REG_G3, res)
    apl_set_sm_reg(SM_REG1, 0x3fff)
    apl_set_sm_reg(SM_REG0, 1 << 1)
    for i in range(1, 13, 2):
        apl_set_sm_reg(SM_REG0, 1 << i)
        _3to2_mul_16_7tmp(c=RN_REG_T3, s0=RN_REG_T4, s1=RN_REG_T0, _2x=RN_REG_T1,
                          m0=RN_REG_T2, m1=RN_REG_T5, c_xor_s=RN_REG_G3,
                          t_y_res_lsb=RN_REG_T6, iter_msk=SM_REG0,
                          sm_0x3fff=SM_REG1)
        apl_set_sm_reg(SM_REG0, 2 << i)
        _3to2_mul_16_7tmp(c=RN_REG_T3, s0=RN_REG_T0, s1=RN_REG_T4, _2x=RN_REG_T1,
                          m0=RN_REG_T5, m1=RN_REG_T2, c_xor_s=RN_REG_G3,
                          t_y_res_lsb=RN_REG_T6, iter_msk=SM_REG0,
                          sm_0x3fff=SM_REG1)

    _3to2_mul_16_7tmp_iter_msk_13(c=RN_REG_T3, s0=RN_REG_T4, s1=RN_REG_T0,
                                  _2x=RN_REG_T1, m0=RN_REG_T2, m1=RN_REG_T5,
                                  c_xor_s=RN_REG_G3, t_y_res_lsb=RN_REG_T6,
                                  sm_0x3fff=SM_REG1)
    apl_set_sm_reg(SM_REG0, 2 << i)
    _3to2_mul_16_7tmp_last(c=RN_REG_T3, s0=RN_REG_T0, s1=RN_REG_T4,
                           _2x=RN_REG_T1, m0=RN_REG_T5, m1=RN_REG_T2,
                           c_xor_s=RN_REG_G3, t_y_res_lsb=RN_REG_T6,
                           sm_0x3fff=SM_REG1)

    apl_set_rn_reg(RN_REG_G2, res)
    mul_u16_u16xu16_7t(t_y_z_lsb=RN_REG_T6, c=RN_REG_T3, z_lsb=RN_REG_G2,
                       m0=RN_REG_T5, y=RN_REG_T4)

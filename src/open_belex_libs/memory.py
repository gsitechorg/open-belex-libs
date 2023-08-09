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

from open_belex.bleir.types import FragmentCallerCall
from open_belex.kernel_libs.memory import load_16_t0, store_16_t0
from open_belex.literal import (L1, RL, RN_REG_T0, SM_0XFFFF, VR, Mask,
                                apl_commands, belex_apl)

from open_belex_libs.constants import (APL_VM_ROWS_PER_U16, GSI_L1_VA_NUM_ROWS,
                                       GSI_L1_VA_SET_ADDR_ROWS)

# __   ____  __ ___     _    _
# \ \ / /  \/  | _ \   | |  / |
#  \ V /| |\/| |   /_  | |__| |
#   \_/ |_|  |_|_|_( ) |____|_|
#                  |/


def belex_gal_vm_reg_to_set_ext(vm_reg: int) -> int:
    parity_set = (vm_reg >> 1)
    parity_grp = (vm_reg & 1)  # 1 or 0 (True or False)
    row = parity_set * GSI_L1_VA_SET_ADDR_ROWS
    parity_row = row + (2 * APL_VM_ROWS_PER_U16)
    row += (APL_VM_ROWS_PER_U16 * parity_grp)
    assert row < GSI_L1_VA_NUM_ROWS
    return parity_grp, parity_row, row


def load_16_parity_mask(parity_grp: int) -> int:
    return 0x0808 << parity_grp


def load_16(dst: int, vm_reg: int) -> FragmentCallerCall:
    parity_grp, parity_src, src = \
        belex_gal_vm_reg_to_set_ext(vm_reg)
    parity_mask = load_16_parity_mask(parity_grp)
    return load_16_t0(dst, src, parity_src, parity_mask)


def store_16_parity_mask(parity_grp: int) -> int:
    return 0x0001 << (4 * parity_grp)


def store_16(vm_reg: int, src: int) -> FragmentCallerCall:
    parity_grp, parity_dst, dst = \
        belex_gal_vm_reg_to_set_ext(vm_reg)
    parity_mask = store_16_parity_mask(parity_grp)
    return store_16_t0(dst, parity_dst, parity_mask, src)


@belex_apl
def swap_vr_vmr_16_t1(
        Belex,
        vr: VR,
        vmr: L1,
        parity_row: L1,
        load_parity_msk: Mask,
        store_parity_msk: Mask
        ) -> None:
    load_16_t0(RN_REG_T0, vmr, parity_row, load_parity_msk)
    store_16_t0(vmr, parity_row, store_parity_msk, vr)

    # CSRC_CPY_16_MSK_INST
    RL[SM_0XFFFF] <= RN_REG_T0()
    # Workaround to add the previous instruction to the lane from the final
    # statement of store_16_t0, as is done in GVML through macros.
    instruction = Belex.instructions.pop()
    Belex.instructions[-1].instructions.append(instruction)
    with apl_commands("instruction 19"):
        vr[SM_0XFFFF] <= RL()


def swap_vr_vmr_16(vr: int, vmr: int) -> FragmentCallerCall:
    parity_grp, parity_row, vmr_row = \
        belex_gal_vm_reg_to_set_ext(vmr)
    load_parity_mask = load_16_parity_mask(parity_grp)
    store_parity_mask = store_16_parity_mask(parity_grp)
    return swap_vr_vmr_16_t1(vr, vmr_row, parity_row,
                             load_parity_mask,
                             store_parity_mask)

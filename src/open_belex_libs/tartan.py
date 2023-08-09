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

from open_belex.literal import (GL, NOOP, RL, VR, WRL, Mask, Section,
                                apl_commands, belex_apl, u16)

# __      __   _ _         _____      __  __          _          _
# \ \    / / _(_) |_ ___  |_   _|__  |  \/  |__ _ _ _| |_____ __| |
#  \ \/\/ / '_| |  _/ -_)   | |/ _ \ | |\/| / _` | '_| / / -_) _` |
#   \_/\_/|_| |_|\__\___|   |_|\___/ |_|  |_\__,_|_| |_\_\___\__,_|


@belex_apl
def _write_test_markers(
        Belex,
        tvrp: VR, msrp: Section, mvrp: VR):
    r"""Write 0001 0111 0000 ... to section msrp of VR mvrp.
    No attempt at performance optimization (no laning, e.g.).
    Tested in several places in test_belex_library.py."""
    RL[:]      <= 0               # Clear RL.
    mvrp[:]    <= RL()            # Clear MV (marker VR).
    tvrp[:]    <= RL()            # Clear TV (temporary VR)

    RL[msrp]   <= 1               # RL  = 1111 1111 1111 1111 ...

    mvrp[msrp] <= WRL()           # MVR = 0111 1111 1111 1111 ...
    RL[msrp]   <= ~mvrp() & RL()  # RL  = 1000 0000 0000 0000 ...

    mvrp[msrp] <= WRL()           # MVR = 0100 0000 0000 0000 ...
    RL[msrp]   <= mvrp() ^ RL()   # RL  = 1100 0000 0000 0000 ...
    mvrp[msrp] <= WRL()           # MVR = 0110 0000 0000 0000 ...
    RL[msrp]   |= mvrp()          # RL  = 1110 0000 0000 0000 ...

    mvrp[msrp] <= WRL()           # MVR = 0111 0000 0000 0000 ...
    RL[msrp]   <= mvrp()          # RL  = 0111 0000 0000 0000 ...
    mvrp[msrp] <= WRL()           # MVR = 0011 1000 0000 0000 ...
    RL[:]      <= 0               # Clear RL.

    RL[msrp]   <= 1               # Ones in section msec of RL
    tvrp[msrp] <= WRL()           # TVR = 0111 1111 1111 1111 ...
    RL[msrp]   <= tvrp() ^ RL()   # RL  = 1000 0000 0000 0000 ...
    RL[msrp]   |= mvrp()          # RL  = 1011 1000 0000 0000 ...

    mvrp[msrp] <= WRL()           # MVR = 0101 1100 0000 0000 ...
    RL[msrp]   <= mvrp()          # RL  = 0101 1100 0000 0000 ...
    mvrp[msrp] <= WRL()           # MVR = 0010 1110 0000 0000 ...
    RL[msrp]   <= mvrp()          # RL  = 0010 1110 0000 0000 ...

    mvrp[msrp] <= WRL()           # MVR = 0001 0111 0000 0000 ...


@belex_apl
def write_to_marked(Belex,
        dst: VR, mrk: VR, mrks: Section, val: u16) -> VR:
    r"""Famous algorithm for writing val to the marked plats
    of dst, where the markers are stored in the 2048 bits
    of section mrks of VR mrk."""
    RL[:] <= 0
    with apl_commands("Copy marks to GL.") as instruction_1:
        RL[mrks]  <= mrk()
        GL[mrks]  <= RL()
    with apl_commands("Copy original data to unmarked plats.") \
         as instruction_2:
        RL[val]   <= ~dst() & ~GL()
        RL[~val]  <=  dst() & ~GL()
    with apl_commands("Copy back to marked plats.") \
         as instruction_3:
        dst[val]  <= ~RL()
        dst[~val] <=  RL()
    return dst



#  _____         _
# |_   _|_ _ _ _| |_ __ _ _ _
#   | |/ _` | '_|  _/ _` | ' \
#   |_|\__,_|_|  \__\__,_|_||_|


# Tartan Cheat Sheet:
#
# The original tartan paper, called "tartan.pdf," is in the
# docs/Tartan folder. It is written in mathematical notation. This
# cheat-sheet is in programmer notation, for programmers who are
# writing belops or other code-generators. It has references back to
# the original paper when appropriate.
#
# All assignment or copy operations have the form
#
#     L' op= L ^ ( M & ( {L ^, nil}  {D, D {&, |} L} ) )
#
# where curly braces enclose options and with ^ bit-wise XOR, |
# bit-wise OR, and & bit-wise AND. In the original paper, simple
# assignment is equation 14, and L is called A:
#
#     A' = A + (M (.) (A + D))
#
# where (.) is a circle-dot operator meaning AND or Hadamard product,
# and + is XOR.
#
# L' is the new value of L after the op.
#
# The "op" copies data from the donor matrix D into the marked plats
# and masked sections of L. The op can also mix original data from L
# via Boolean XOR, AND, and OR. The mask matrix, M, specifies the
# marked plats and masked sections of L to receive the data from the
# corresponding marked plats and masked sections of D. The unmarked
# plats and unmasked sections of L are undisturbed.
#
# L is an lvalue VR. Its section mask, ls, is accounted for in
# mask-matrix M as described below. D is a Data or Donor matrix,
# constructed from rvalue and rvalue2 as shown below.
#
# We speak of "copying or mixing data from D into the marked plats and
# masked sections of L." The matrix M specifies the marked plats and
# masked sections of L as an outer product of a section mask and a
# plat mask. A section mask, as always, is a 16-bit integer. A plat
# mask has the shape of a wordline: a bit string of length 2048. Plat
# masks are also called "markers" or marks in the APL jargon. The
# marks come from a section or wordline in a marker VR. The ON bits in
# the marker wordline indicate the masked-on (columns) in both L and
# D. The sections come from the section-mask part of an lvalue
# parameter of a belops call.
#
# Spelled out, the logical mixing operations follow this scheme:

#     := :: L ^ ( M & ( L ^   D       ) )  # assignment
#     ^= :: L ^ ( M & (       D       ) )  # assignment with XOR
#     &= :: L ^ ( M & ( L ^ ( D & L ) ) )  # assignment with AND
#     |= :: L ^ ( M & ( L ^ ( D | L ) ) )  # assignment with OR
#
# The meanings, in pseudo-belex, are
#
#     L[ls, m[ms]] <= D()
#     L[ls, m[ms]] ^= D()
#     L[ls, m[ms]] &= D()
#     L[ls, m[ms]] |= D()
#
# where L is a VR containing data to be partially overwritten; ls is a
# section mask; m is a VR containing a plat mask --- a row or section,
# ms, of marker bits; and D is a donor matrix containing data to be
# moved or mixed into L.
#
# In belex, :=, for simple assignment, is written <=.
#
# Additional commands are required to permute, shift, or duplicate
# sections of D before assignment, if desired. We do not address such
# permutations, shifts, or duplications in this cheat sheet. We also
# do not address permutations, shifts, or duplications in the plat
# dimensions.
#
#  __  __          _               __  __         _
# |  \/  |__ _ _ _| |_____ _ _ ___|  \/  |__ _ __| |__
# | |\/| / _` | '_| / / -_) '_|___| |\/| / _` (_-< / /
# |_|  |_\__,_|_| |_\_\___|_|     |_|  |_\__,_/__/_\_\
#  __  __      _       _       __  __
# |  \/  |__ _| |_ _ _(_)_ __ |  \/  |
# | |\/| / _` |  _| '_| \ \ / | |\/| |
# |_|  |_\__,_|\__|_| |_/_\_\ |_|  |_|
#
#
# M is a plat-marker + section-mask matrix, also called a mask matrix
# or a marker matrix. It has ON bits where the plats of the Marker
# wordline cross the section Mask of the lvalue, namely lsections, and
# zeros elsewhere. M has the shape of a VR and is often stored in a
# temporary VR; though sometimes we don't need a temporary VR and can
# store M in RL.
#
# Every section in M that has any ON marker bits must have the same ON
# plat-marker bits. That is what the paper means in equation 10 by an
# "outer product" of a section mask \psi and a marker mask \mu. For
# example:
#
# M = [ ..11 .1.1 ...1 .1.. .1.1 ...1 .... .1.1,
#       .... .... .... .... .... .... .... ....,
#       ..11 .1.1 ...1 .1.. .1.1 ...1 .... .1.1,
#       .... .... .... .... .... .... .... ....,
#       ..11 .1.1 ...1 .1.. .1.1 ...1 .... .1.1,
#       .... .... .... .... .... .... .... ....,
#       etc. ]
#       (dots mean 0's for visual clarity)
#
# has marker bits ON in the prime-numbered plats (up to 31), of the
# even-numbered sections, and zero in all other plats and sections. M
# is the outer product (using bit-wise AND as multiplication) of a
# section mask "5555" (all the even sections / wordlines) and a marker
# string 0011 0101 0001 0100 0101 0001 0000 0101 == 0x_3514_5105.
#
# The "tartan" pattern in the mas matrix, the pattern that gives the
# Tartan theory its name, is obvious in the sketch above.
#
# One way to copy markers into the lsections of the M matrix is with
# code like the following:
#
# Let the markers be stored in a single wordline in section ms of SB
# number mvr. Let the section mask be stored in ls. Let the
# destination VR be tvr, a temporary in this case.
#
#     with apl_commands():
#       RL[ms] <= mvr()   # pull marker 1s out of section ms of mvr
#       GL[ms] <= RL()    # deposit those 1s in GL
#     NOOP()
#     RL[:] <= 0          # clear RL
#     with apl_commands():
#       tvr[~ls] <= RL()  # clear unmarked sections of tvr
#       tvr[ls]  <= GL()  # deposit marker 1s in sections ls of tvr
#
# The C-sim revealed that a noop is necessary at step 3. The reason
# comes from obscure details of the hardware, but the C-sim is a
# reliable guide as to when that "wait-state" is needed. In a later
# example, we will see a similar sequence of instructions that,
# empirically, does not require this noop.
#
# In the case of all-plat operations, a common case called "full
# markers," we must create something like the following:
#
# M = [ 1111 1111 1111 1111 1111 1111 1111 1111,
#       0000 0000 0000 0000 0000 0000 0000 0000,
#       1111 1111 1111 1111 1111 1111 1111 1111,
#       0000 0000 0000 0000 0000 0000 0000 0000,
#       1111 1111 1111 1111 1111 1111 1111 1111,
#       0000 0000 0000 0000 0000 0000 0000 0000,
#       ... ]
#
# We can do that without an mvr, as follows
#
#     with apl_commands():
#       RL[ms] <= 1       # put constant 1s in section ms of RL
#       GL[ms] <= RL()    # deposit those 1s in GL
#     NOOP()
#     RL[:] <= 0          # clear RL
#     with apl_commands():
#       tvr[~ls] <= RL()  # clear unmarked sections of tvr
#       tvr[ls]  <= GL()  # deposit marker 1s in sections ls of tvr
#
#  ___                     __  __      _       _       ___
# |   \ ___ _ _  ___ _ _  |  \/  |__ _| |_ _ _(_)_ __ |   \
# | |) / _ \ ' \/ _ \ '_| | |\/| / _` |  _| '_| \ \ / | |) |
# |___/\___/_||_\___/_|   |_|  |_\__,_|\__|_| |_/_\_\ |___/
#
#
#     # Set up D, in RL, donor matrix: the IV in all plats
#     with apl_commands():
#       RL[ds]  <= 1
#       RL[~ds] <= 0
#
# Notice we do not need a second temporary VR, here, for D because the
# caller gave us an explicit section mask for the immediate value. We
# can do all the rest of our work in RL, now.
#
#  ___                _   _            _ _ _
# | __|__ _ _  _ __ _| |_(_)___ _ _   / | | |
# | _|/ _` | || / _` |  _| / _ \ ' \  | |_  _|
# |___\__, |\_,_\__,_|\__|_\___/_||_| |_| |_|
#        |_|
#
#     # PRECONDITION: RL contains D, tvr contains M
#
#     RL[:]  ^= lvr()  # RL <- L ^ D
#     RL[:]  &= tvr()  # RL <- M & (L ^ D)
#     RL[:]  ^= lvr()  # RL <- L ^ (M & (L ^ D))
#     lvr[:] <= RL()   # L' <- L ^ (M & (L ^ D))
#
# What about the other Tartan operations? They differ only on the
# right-hand sides of M's & operator.
#
#     := :: L ^ ( M & ( L ^   D       ) )  # assignment
#     ^= :: L ^ ( M & (       D       ) )  # assignment with XOR
#     &= :: L ^ ( M & ( L ^ ( D & L ) ) )  # assignment with AND
#     |= :: L ^ ( M & ( L ^ ( D | L ) ) )  # assignment with OR
#
# The last one is Boolean, not in GF2, because GF2 doesn't have OR.
#
# The original Tartan expression for |= is
#
#     |= :: L ^ ( M & ( D ^ ( D & L ) ) )  # assignment with OR
#
# Entirely in GF2, with ^ for plus and & for times.
#
# This is undesirable because, in a right-associative encoding, the
# innermost sub-expression on the right will overwrite RL == D, the
# precondition, with D & L, and we will need a temporary register to
# hold a copy of the original D.
#
# However D|L = (D^L)^(D&L) in GF2, and the original Tartan
# sub-expression
#
#     D ^ (D & L) <=> L^D^L ^ (D & L) <=> L ^ (D^L)^(D&L) <=>
#     L ^ (D | L)
#
# which is right-associative Boolean, supported by the machine, and
# uses D = RL just once, bypassing the need for a temporary register.
# Here are all four tartan assignment sequences, for reference
#
#     # PRECONDITION for all: RL contains D, tvr contains M
#
#      := :: L ^ ( M & ( L ^   D       ) )  # assignment
#
#     RL[:]  ^= lvr()  # RL <- L ^ D
#     RL[:]  &= tvr()  # RL <- M & (L ^ D)
#     RL[:]  ^= lvr()  # RL <- L ^ (M & (L ^ D))
#     lvr[:] <= RL()   # L' <- L ^ (M & (L ^ D))
#
#      ^= :: L ^ ( M & (       D       ) )  # assignment with XOR
#
#     RL[:]  &= tvr()  # RL <- M & D
#     RL[:]  ^= lvr()  # RL <- L ^ (M & D)
#     lvr[:] <= RL()   # L' <- L ^ (M & D)
#
#      &= :: L ^ ( M & ( L ^ ( D & L ) ) )  # assignment with AND
#
#     RL[:]  &= lvr()  # RL <- D & L
#     RL[:]  ^= lvr()  # RL <- L ^ (D & L)
#     RL[:]  &= tvr()  # RL <- M & (L ^ (D & L))
#     RL[:]  ^= lvr()  # RL <- L ^ (M & (L ^ (D & L)))
#     lvr[:] <= RL()   # L' <- L ^ (M & (L ^ (D & L)))
#
#      |= :: L ^ ( M & ( L ^ ( D | L ) ) )  # assignment with OR
#
#     RL[:]  |= lvr()  # RL <- D | L
#     RL[:]  ^= lvr()  # RL <- L ^ (D | L)
#     RL[:]  &= tvr()  # RL <- M & (L ^ (D | L))
#     RL[:]  ^= lvr()  # RL <- L ^ (M & (L ^ (D | L)))
#     lvr[:] <= RL()   # L' <- L ^ (M & (L ^ (D | L)))
#
# That covers the case of writing immediate values to marked plats
# specified in mvr and ms. If the user specifies "all plats," we need
# only a small difference in the set-up of M. Instead of
#
#     RL[:] <= mvr()
#
# we write
#
#     RL[:] <= 1
#
# before pulling the markers into GL. All the rest is the same.


@belex_apl
def tartan_set_up_mask_matrix(
        Belex,
        dst: VR, ls: Mask, mvr: VR, ms: Section) -> None:
    r"""Effect an outer product of a 16-bit section mask with
    a 2048-bit plat mask of 'markers' stored in section 'ms'
    of marker VR 'mvr'."""
    with apl_commands():# "read before broadcast" safe case 9.2
      RL[ms] <= mvr()   # Pull marker ones out of section ms of mvr.
      GL[ms] <= RL()    # Deposit marker ones in GL.
    NOOP()              # C-sim empirically tells us we need this.
    RL[:] <= 0          # Clear RL.
    with apl_commands():# The two commands write disjoint sections.
      dst[~ls] <= RL()  # Clear unmarked sections of dst.
      dst[ls]  <= GL()  # Deposit marker ones in sections ls of dst.


@belex_apl
def tartan_imm_donor(
        Belex,
        dst: VR, val: u16) -> None:
    r"""Copy val to all plats of the dst VR.
    Leaves donor D in RL and optionally copies it to 'dst'."""
    with apl_commands():
        RL[val] <= 1
        RL[~val] <= 0
    if dst is not None:
        dst[:] <= RL()


@belex_apl
def tartan_assign(
        Belex,
        lvr: VR, ls: Mask,
        mvr: VR, ms: Section,
        donor: VR,
        tvr: VR  # user-supplied temporary
        ) -> None:
    r"""(pseudo-belex) L[ls, mvr[ms]] <= D, or
    L' = L ^ ( M & ( L ^   D       ) )"""
    tartan_set_up_mask_matrix(tvr, ls, mvr, ms)
    RL[:]  <= donor()
    RL[:]  ^= lvr()  # RL <- L ^ D
    RL[:]  &= tvr()  # RL <- M & (L ^ D)
    RL[:]  ^= lvr()  # RL <- L ^ (M & (L ^ D))
    lvr[:] <= RL()   # L' <- L ^ (M & (L ^ D))


@belex_apl
def tartan_xor_equals(
        Belex,
        lvr: VR, ls: Mask,
        mvr: VR, ms: Section,
        donor: VR,
        tvr: VR  # user-supplied temporary
        ) -> None:
    r"""(pseudo-belex) L[ls, mvr[ms]] ^= D, or
    L' = L ^ ( M & (       D       ) )"""
    tartan_set_up_mask_matrix(tvr, ls, mvr, ms)
    RL[:]  <= donor()
    RL[:]  &= tvr()  # RL <- M & D
    RL[:]  ^= lvr()  # RL <- L ^ (M & D)
    lvr[:] <= RL()   # L' <- L ^ (M & D)


@belex_apl
def tartan_and_equals(
        Belex,
        lvr: VR, ls: Mask,
        mvr: VR, ms: Section,
        donor: VR,
        tvr: VR  # user-supplied temporary
        ) -> None:
    r"""(pseudo-belex) L[ls, mvr[ms]] &= D, or
    L' = L ^ ( M & ( L ^ ( D & L ) ) )"""
    tartan_set_up_mask_matrix(tvr, ls, mvr, ms)
    RL[:]  <= donor()
    RL[:]  &= lvr()  # RL <- D & L
    RL[:]  ^= lvr()  # RL <- L ^ (D & L)
    RL[:]  &= tvr()  # RL <- M & (L ^ (D & L))
    RL[:]  ^= lvr()  # RL <- L ^ (M & (L ^ (D & L)))
    lvr[:] <= RL()   # L' <- L ^ (M & (L ^ (D & L)))


@belex_apl
def tartan_or_equals(
        Belex,
        lvr: VR, ls: Mask,
        mvr: VR, ms: Section,
        donor: VR,
        tvr: VR  # user-supplied temporary
        ) -> None:
    r"""(pseudo-belex) L[ls, mvr[ms]] |= D, or
    L' = L ^ ( M & ( L ^ ( D | L ) ) )"""
    tartan_set_up_mask_matrix(tvr, ls, mvr, ms)
    RL[:]  <= donor()
    RL[:]  |= lvr()  # RL <- D | L
    RL[:]  ^= lvr()  # RL <- L ^ (D | L)
    RL[:]  &= tvr()  # RL <- M & (L ^ (D | L))
    RL[:]  ^= lvr()  # RL <- L ^ (M & (L ^ (D | L)))
    lvr[:] <= RL()   # L' <- L ^ (M & (L ^ (D | L)))


#  ___                         _      __
# / __|_  _ _ __ _ __  ___ _ _| |_   / _|___ _ _
# \__ \ || | '_ \ '_ \/ _ \ '_|  _| |  _/ _ \ '_|
# |___/\_,_| .__/ .__/\___/_|  \__| |_| \___/_|
#          |_|  |_|
#  ___                _
# | __|_ _____ _ _ __(_)___ ___ ___
# | _|\ \ / -_) '_/ _| (_-</ -_|_-<
# |___/_\_\___|_| \__|_/__/\___/__/


@belex_apl
def walk_marks_eastward(Belex, mvr: VR, mrk_sec: Section):
    RL[mrk_sec] <= mvr()
    mvr[mrk_sec] <= WRL()


@belex_apl
def write_markers_in_plats_matching_value(
        Belex,
        srh_vr: VR,   val: u16,
        mrk_vr: VR,   mrk_sec: Section):
    with apl_commands():
        RL[~val] <= 0
        RL[ val] <= 1
    # The next two commands are read-before-broadcast, so they
    # can be laned:
    # with apl_commands():
    RL[:] <= srh_vr() ^ ~RL()
    # plats in srh that match RL will be 'all ones'
    GL[:] <= RL()
    # put the marker bits in the intended places
    mrk_vr[mrk_sec] <= GL()

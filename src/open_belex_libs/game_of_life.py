r"""
By Dylon Edwards and Brian Beckman
"""

from open_belex.literal import (ERL, GL, INV_RSP16, NRL, RL, SRL, VR, WRL, Belex,
                           Section, apl_commands, belex_apl, u16)

from open_belex_libs.arithmetic import add_u16
from open_belex_libs.common import reset_16
from open_belex_libs.tartan import walk_marks_eastward, write_to_marked

#    ___                       ___ _ _    _          ___
#   / __|___ ____ __  ___ _ _ / __| (_)__| |___ _ _ / __|_  _ _ _
#  | (_ / _ (_-< '_ \/ -_) '_| (_ | | / _` / -_) '_| (_ | || | ' \
#   \___\___/__/ .__/\___|_|  \___|_|_\__,_\___|_|  \___|\_,_|_||_|
#              |_|


# FIXED: unknown whether timeout problems are caused by GL;
#  a hack surrounding all GL usages with NOOP() calls did
#  not fix timeout. This times out on C-Sim.
#
# The fix is to comment out the timeout code in sim_apuc.c,
# which is in subprojects/gsi-sys-libs/gsi-device-libs/
# simulation/lib/src. The lines to comment out are near
# line 1700 and they are obvious. Then build, then run
# ./set_path.sh to redirect simulation references to the
# rebuilt C-Sim.

@belex_apl
def gosper_gun_write_initial_pattern(Belex,
        petri_dish: VR):

    # Ensure petri_dish is clear of old values
    reset_16(petri_dish)

    #  +-+-+-+ +-+-+ +-+-+-+-+-+-+-+
    #   S e t   U p   M a r k e r s
    #  +-+-+-+ +-+-+ +-+-+-+-+-+-+-+

    marker_vr = Belex.VR(0)
    marker_section = 2  # arbitrary
    RL[::] <= 1                          # 1111 1111 1111 1111 ...
    marker_vr[marker_section] <= ~WRL()  # 1000 0000 0000 0000 ...

    #  +-+-+-+-+-+ +-+-+-+ +-+-+-+ +-+-+-+-+-+-+-+
    #   W r i t e   t h e   G u n   P a t t e r n
    #  +-+-+-+-+-+ +-+-+-+ +-+-+-+ +-+-+-+-+-+-+-+

    y_shift = 0

    def write_column(col_val: int, walk_count: int = 1):
        nonlocal y_shift, petri_dish, marker_vr, marker_section
        for _ in range(walk_count):
            walk_marks_eastward(marker_vr, marker_section)
        col_mask = Belex.Mask(col_val) << y_shift
        write_to_marked(petri_dish, marker_vr, marker_section, col_mask)

    write_column("56")       # column  1: sections 5 and 6, optionally shifted down
    write_column("56")       # column  2: sections 5 and 6, ...
    write_column("567", 9)   # column 11: sections 5, 6, 7, skip 9 columns to right
    write_column("48")       # column 12: sections 4 and 8
    write_column("39")       # column 13
    write_column("39")       # column 14
    write_column("6")        # column 15
    write_column("48")       # column 16
    write_column("567")      # column 17
    write_column("6")        # column 18
    write_column("345", 3)   # column 21
    write_column("345")      # column 22
    write_column("26")       # column 23
    write_column("1267", 2)  # column 25
    write_column("34", 10)   # column 35
    write_column("34")       # column 36


@belex_apl
def gosper_gun_moore_counts(Belex,
        section: Section, petri_dish: VR, sum_vr: VR,
        temp_vr: VR, addend_1_vr: VR):
    r"""Work in Progress: exhausts allocated registers.
    Just for one section, count the eight neighbors (the Moore cell).
    Flat-Earth boundary conditions, not toroidal!"""

    def accumulate_temp_non_diagonal(section, shifted_RL):
        RL[::]           <= petri_dish()
        temp_vr[section] <= shifted_RL
        RL[section]      <= temp_vr()
        GL[section]      <= RL()
        addend_1_vr[0]   <= GL()
        add_u16(sum_vr, addend_1_vr, sum_vr)

    def accumulate_temp_diagonal(section, first_shifted_RL, second_shifted_RL):
        RL[::]           <= petri_dish()
        temp_vr[::]      <= first_shifted_RL
        RL[::]           <= temp_vr()
        temp_vr[section] <= second_shifted_RL
        RL[section]      <= temp_vr()
        GL[section]      <= RL()
        addend_1_vr[0]   <= GL()
        add_u16(sum_vr, addend_1_vr, sum_vr)

    reset_16(sum_vr)

    accumulate_temp_non_diagonal(section, WRL())
    accumulate_temp_non_diagonal(section, ERL())
    accumulate_temp_non_diagonal(section, NRL())
    accumulate_temp_non_diagonal(section, SRL())

    accumulate_temp_diagonal(section, WRL(), NRL())
    accumulate_temp_diagonal(section, ERL(), NRL())
    accumulate_temp_diagonal(section, WRL(), SRL())
    accumulate_temp_diagonal(section, ERL(), SRL())


@belex_apl
def gosper_gun_evolve(Belex,
        section: Section, petri_dish: VR, sum_vr: VR,
        new_generation: VR):

    # The following is not optimized, for clarity's sake.

    # RULE 1: If a dead cell's Moore neighbor-count is 3, turn it ON.
    # RULE 2: If a live cell's Moore neighbor-count is 2 or 3, leave it ON.
    # RULE 3: (REDUNDANT) All other live cells die; dead cells stay dead.

    # Rule 3 is redundant in our implementation because the
    # new_generation starts dead.

    def rule_1(section):
        r"""RULE 1: If a dead cell's Moore neighbor-count is 3, turn it ON."""

        # Strategy: use GL's implicit AND to find OFF cells with
        # exactly 3 neighbors.

        # The sum calculation uses only sections
        # 0, 1, 2, and 3 because the maximum neighbor count
        # is 8 = 2^3 = 2^[section-3]. Section 4 of RL is free to use

        # Put the OFF cells of "section" of the petri disk in section 4 of RL:

        RL[section] <= petri_dish()
        GL[section] <= RL()
        RL[4]       <= ~GL()

        # Get sum_vr sections 0 and 1; both ON if sum == 3
        # (but not ONLY if).

        RL["01"]    <= sum_vr()

        # AND-in the complement of sections 2 and 3 of sum,
        # which is ON only if sum < 4.
        # Command 16 (from belex-alpha doc, Figure 6)

        RL["23"]    <= 1
        RL["23"]    &= ~sum_vr()

        # GL's AND will be ON iff
        # A. RL[0] & RL[1] are ON,
        # B. RL[2] & RL[3] are OFF,
        # C. petri_dish[arbitrary_section] is OFF.

        GL["01234"] <= RL()

        # Those cells are going ON in the next round.

        new_generation[section] <= GL()

    def rule_2(section):
        r"""RULE 2: If a live cell's Moore neighbor-count is 2 or 3, leave it ON."""

        # Put "live now" into RL[4]:

        RL[section] <= petri_dish()
        GL[section] <= RL()
        RL[4]       <= GL()

        # Find counts in sum_vr that are 2 or 3. It suffices
        # to check sections 1, anti-2, and anti-3:

        RL["1"]     <= sum_vr()
        RL["23"]    <= 1
        RL["23"]    &= ~sum_vr()

        # AND them all up, excluding section 0!, otherwise as before.
        # GL's AND will be ON iff
        # A. RL[1] is ON,
        # B. RL[2] & RL[3] are OFF,
        # C. petri_dish[arbitrary_section] is ON.

        GL["1234"]  <= RL()

        new_generation[section] |= GL()

    def rules(section):
        rule_1(section)
        rule_2(section)
        # rule_3(section)  # REDUNDANT: because new_gen starts all dead

    rules(section)


@belex_apl
def gosper_gun_tick(Belex,
        petri_dish: VR, sum_vr: VR, temp_vr: VR,
        addend_1_vr: VR, new_generation: VR):

    for section in range(16):
        gosper_gun_moore_counts(section, petri_dish, sum_vr, temp_vr, addend_1_vr)
        gosper_gun_evolve(section, petri_dish, sum_vr, new_generation)
    #  Overwrite Petri Dish
    RL[::] <= new_generation()
    petri_dish[::] <= RL()


@belex_apl
def gosper_gun_one_period(Belex, petri_dish: VR):
    r"""function-under-test that demonstrates calling glass and
    stacking up the results."""
    gosper_gun_write_initial_pattern(petri_dish)

    print('\ngosper_gun_one_period GEN 0\n')
    def play():
        s = Belex.glass(petri_dish, plats=40, sections=16, fmt="bin",
                        order="lsb")
        if s:  # it's None in belex-test
            t = s.replace('0', '.')
            print (t)
            print ('\n')

    play()

    sum_vr = Belex.VR(0)
    temp_vr = Belex.VR(0)
    addend_1_vr = Belex.VR(0)
    new_generation = Belex.VR(0)

    for i in range(2):  # 30): 30 is ONE PERIOD, but takes MUCH TOO LONG
        gosper_gun_tick(petri_dish, sum_vr, temp_vr, addend_1_vr,
                        new_generation)
        print(f'gosper_gun_one_period GEN {1 + i}\n')
        play()


def pdisplay(string: str, message=""):
    belex = Belex.context()
    if (belex.debug):
        print("tutorial: ")
        print(message)
        print(string.replace("0", "."))


@belex_apl
def gosper_glider_gun_tutorial(Belex, petri_dish: VR):
    #  +-+-+-+ +-+-+ +-+-+-+-+-+-+-+
    #   S e t   U p   M a r k e r s
    #  +-+-+-+ +-+-+ +-+-+-+-+-+-+-+

    # ROUGH SCRIPT OF VIDEO:

    # Hi everyone! Today, I am going to show you a couple of ways
    # to program John Horton Conway's Game of Life (GoL) on the
    # APU. First, a few words about the game. It's a zero-player
    # game on a grid --- finite or infinite --- of 1-bit cells.
    # Cells with ON bits model live cells; cells with OFF bits
    # model dead cells. Over time, cells are born, or die, or
    # survive to the next round. The opening video shows a
    # particular pattern of cells we are going to implement.
    #
    #  https://www.dropbox.com/s/yy4eeg86xxdf2bq/GroundTruthGoL.mp4?dl=0
    #
    # To set expectations, I am only showing, today, the first
    # two generations of the game running in the APU.
    #
    # Dead cells with exactly two neighbors are "born" --- become
    # alive in the next round. Live cells with 2 or 3 neighbors
    # stay alive. All other cells die. These rules, on an infinite
    # grid, produce an infinite variety of patterns, some stable,
    # quiescently or periodically; some ever-changing; some
    # eventually dying out. In fact, the game is capable of
    # representing any computation that a Turing-machine can
    # represent:
    #
    #  https://en.wikipedia.org/wiki/General_recursive_function
    #
    # On spatially finite grids, the game produces a large variety
    # of interesting patterns, many of which live forever, some
    # useful for testing, as we show today. The web site
    # "playgameoflife.com" has much information and many patterns
    # to play with. The free program "golly" offers very
    # high-performance implementations for exploring billions of
    # generations and for exploring alternative rule sets beyond
    # GoL.
    #
    # GoL has fascinated programmers, engineers, and computer
    # scientists since around 1970. I used it around 1984 as an
    # ever-running stress test for the Time Warp Operating System,
    # an early distributed parallel computing platform for
    # optimistic discrete-even simulation. GoL proved its value by
    # exposing a bug after three weeks of continual operation. It
    # dropped a bit at midnight on Halloween (I'm not joking) and
    # the expected pattern changed. It took us another three weeks
    # to reproduce and pinpoint the bug. It turned out to be due
    # to garbage data's on the C stack "peeking" through holes in
    # unpacked structs. The operating system compared messages in
    # structs for semantic equality via "memcmp," cheaper than
    # hashes back then. Memcmp --- and, indeed, any credible hash
    # function --- produces false negatives in the rare case that
    # semantically identical messages differ by garbage in the
    # holes.
    #
    # The game is an instance of the larger class of "cellular
    # automata," CAs. Stephen Wolfram's book "A New Kind of
    # Science" is a comprehensive zoology of certain kinds of CAs.
    # As is often the case for scientific and mathematical topics,
    # the wikipedia article is excellent:
    #
    #  https://en.wikipedia.org/wiki/Cellular_automaton
    #
    # To get started on the MMB, we'll implement GoL on a 16x2048
    # grid of bits with "flat-Earth" boundary conditions. We'll
    # implement the "Gosper Glider Gun" shown in the opening
    # video. Under those boundary conditions, cells on the edges
    # have permanently dead neighbors off the grid. An
    # alternative, toroidal boundary conditions, wraps the bottom
    # edge to the top edge and the left edge to the bottom edge.
    # Other boundary conditions include Klein bottles and Mobius
    # strips.
    #
    # Some of the enhancements to GoL on the APU include:
    #
    # - stacking VRs, horizontally or vergically, for bigger
    #   fields
    #
    # - implementing the rules "in-section" or cross VRs,
    #   wherewith the fundamental chunk of grid will be 24x2048
    #   instead of the 16x2048 "cross-section" model shown here.
    #
    # - stacking multiple MMBs in an APU, up to 64, for even
    #   larger fields
    #
    # - stacking multiple APUs for even larger fields, perhaps
    #   employing MPI or other distributed-computing software
    #   architectures
    #
    # Let's do the Gosper Glider Gun! I will walk through the
    # exact steps I took to develop this code. You will see my
    # personal style of development: "prebugging." I don't like
    # debugging, even though I'm good at it, because it takes an
    # upredictable amount of time. I'd rather go slowly and
    # incrementally, in a linear process, because when things go
    # wrong I know right _where_. It feels slow, but it's really
    # just meticulous. In the long run, it's much faster because I
    # don't often search an exponentially large space of
    # possibilities for a bug that I wrote long ago. It took me
    # only two days to write the code for this working tutorial.
    #
    # Incidentally, my "prebugging" style is just a
    # non-fundamentalist variation of test-driven development
    # (TDD). In the fundamentalist variation, one writes
    # intentionally failing tests at first, then writes
    # test-target code until the tests pass. The tests are
    # permanently saved in a regression corpus that doubles as
    # semi-formal documentation for the tested feature.
    # Fundamentalist TDD is a very high discipline, justified for
    # difficult or mission-critical code. Prebugging is a
    # lighter-weight back-and-forth between testing and coding
    # that shares the goals of fundamentalist TDD without the
    # heavier discipline. It's a kind of surfer-dude TDD.

    #    ____     _ __  _      __  _____            ___       __  __
    #   /  _/__  (_) /_(_)__ _/ / / ___/_ _____    / _ \___ _/ /_/ /____ _______
    #  _/ // _ \/ / __/ / _ `/ / / (_ / // / _ \  / ___/ _ `/ __/ __/ -_) __/ _ \
    # /___/_//_/_/\__/_/\_,_/_/  \___/\_,_/_//_/ /_/   \_,_/\__/\__/\__/_/ /_//_/

    # STRATEGY: Write the initial pattern to columns (plats) of
    # the MMB via the library function "write_to_marked." This
    # function writes a 16-bit pattern, encoded as a section mask,
    # to indicated plats, leaving all other plats undisturbed.
    # "Indicated plats" are those corresponding to ON-bits in a
    # known section --- the marker section --- of a known VR ---
    # the marker VR. This strategy is analogous to
    #
    #   printf("hello, world");
    #
    # ALTERNATIVE STRATEGY: Read the initial pattern from
    # host-side data. This strategy is analogous to
    #
    #   char * foo = "hello, world";
    #   printf("%s", foo);
    #
    # or even to
    #
    #   char foo[BIG_ENOUGH];
    #   fscanf(some_file_stream, "%s", foo);  // careful!
    #   printf("%s", foo);
    #
    # We don't pursue the alternative strategy here.
    #
    # TERMINOLOGY: A VR (vector register) is a 16x2048 array of
    # bits. One half-bank (HB) has 24 VRs and several VR-shaped
    # special registers. RL and GL are two such we employ here.
    # The MMB (main-memory bank) has 64 HBs. The APU has one MMB
    # plus four levels of caches for I/O. Sometimes we're not
    # careful to distinguish the MMB from the APU. The _host_ is
    # an ordinary PC or server that drives the entire process.

    # Allocate a VR for the markers.
    # import ipdb; ipdb.set_trace()  # uncomment for debugging
    marker_vr = Belex.VR(0)

    # Pick an arbitrary section to store the markers.
    marker_section = 2

    # Put an ON-bit, 1, in plat zero of the marker VR:
    #
    # 1. Read a 1 into all sections of RL (a "read" is any BELEX
    #    command that has RL on the left-hand side of an
    #    assignment. BELEX assignment is normally denoted with the <=
    #    operator.)

    RL[::] <= 1                          # 1111 1111 1111 1111 ...

    # Set some convenience variables for debugging in "glass".

    number_of_plats_to_glass = 40
    glass_kwargs = {"plats": number_of_plats_to_glass,
                    "sections": 16, "fmt": "bin", "order": "lsb"}

    # Walk the rows of RL to the right (WRL), invert the result,
    # and copy the inverted result to the marker section:

    marker_vr[marker_section] <= ~WRL()  # 1000 0000 0000 0000 ...

    # Check the marker section in _glass_ (see line 31ff in
    # "test_belex_game_of_life.py" in belex_tests/tests).

    actual_rows = Belex.glass(marker_vr, ** glass_kwargs)
    expected_rows = "\n".join(s.replace(".", "0") for s in [
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[1 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
    ])
    pdisplay(actual_rows, "Expect ON in row 2, column 0; all others OFF.")
    Belex.assert_true(actual_rows == expected_rows)

    #  +-+-+-+-+-+ +-+-+-+ +-+-+-+ +-+-+-+-+-+-+-+
    #   W r i t e   t h e   G u n   P a t t e r n
    #  +-+-+-+-+-+ +-+-+-+ +-+-+-+ +-+-+-+-+-+-+-+

    # We can shift the pattern down a given number of cells, but
    # we want it as near the top as we can get.

    y_shift = 0

    def write_column(col_val: str, walk_count: int = 1):
        r"""Given a column value as a string containing section
        numbers and an Eastward, horizontal walk-count defaulting
        to 1, write ON bits into the sections specified. Note this
        is an ordinary Python function that calls BELEX functions
        in a loop. When this function is called, the loop will be
        unrolled.
        """
        nonlocal y_shift, petri_dish, marker_vr, marker_section
        for _ in range(walk_count):
            # Library routine; see line 463 in "tartan.py" in
            # belex-libs/src/belex-libs
            walk_marks_eastward(marker_vr, marker_section)
        col_mask = Belex.Mask(col_val) << y_shift
        # Library routine; see line 65 in "tartan.py" in
        # belex-libs/src/belex-libs
        write_to_marked(petri_dish, marker_vr, marker_section, col_mask)

    # Write the initial pattern of the Gosper glider gun to the
    # indicated sections of the columns, starting with column 1.

    write_column("56")       # column  1: sections 5 and 6, optionally shifted down
    write_column("56")       # column  2: sections 5 and 6, ...
    write_column("567", 9)   # column 11: sections 5, 6, 7, skip 9 columns to right
    write_column("48")       # column 12: sections 4 and 8
    write_column("39")       # column 13
    write_column("39")       # column 14
    write_column("6")        # column 15
    write_column("48")       # column 16
    write_column("567")      # column 17
    write_column("6")        # column 18
    write_column("345", 3)   # column 21
    write_column("345")      # column 22
    write_column("26")       # column 23
    write_column("1267", 2)  # column 25
    write_column("34", 10)   # column 35
    write_column("34")       # column 36

    # Check the initial generation in glass. Visually ensure that
    # it matches the initial generation in the opening video.

    actual_rows = Belex.glass(petri_dish, **glass_kwargs)
    expected_rows = "\n".join(s.replace(".", "0") for s in [
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . 1 . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . 1 . 1 . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . 1 1 . . . . . . 1 1 . . . . . . . . . . . . 1 1 . . .]",
        "[. . . . . . . . . . . . 1 . . . 1 . . . . 1 1 . . . . . . . . . . . . 1 1 . . .]",
        "[. 1 1 . . . . . . . . 1 . . . . . 1 . . . 1 1 . . . . . . . . . . . . . . . . .]",
        "[. 1 1 . . . . . . . . 1 . . . 1 . 1 1 . . . . 1 . 1 . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . 1 . . . . . 1 . . . . . . . 1 . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . 1 . . . 1 . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . 1 1 . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",])
    pdisplay(actual_rows, "Expect the initial generation shape of the Gosper glider gun.")
    Belex.assert_true(actual_rows == expected_rows)

    #  +-+-+-+-+-+-+-+-+-+-+-+ +-+-+-+-+-+ +-+-+-+-+-+
    #   P r e l i m i n a r y   S m o k e   T e s t s
    #  +-+-+-+-+-+-+-+-+-+-+-+ +-+-+-+-+-+ +-+-+-+-+-+

    # Test that we can load an "incrementing" register. This
    # register contains a single row of 1s in section 0. We will
    # add (the contents of) this register to (the contents of)
    # other registers to increment the values in the other
    # register.

    ones_vr = Belex.VR(0)
    RL["0"] <= 1
    ones_vr["0"] <= RL()
    actual_rows = Belex.glass(ones_vr, **glass_kwargs)
    expected_rows = "\n".join(s.replace(".", "0") for s in [
        "[1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",])
    pdisplay(actual_rows, "Expect all ones in section 0.")
    Belex.assert_true(actual_rows == expected_rows)

    # Allocate a register for sums and another to contain interim
    # values to increment. Later, take the interim values from the
    # life pattern under test.

    sum_vr = Belex.VR(0)
    addend_1_vr = Belex.VR(0)

    # Test that the adder works by incrementing the (values in) the
    # interim register three times.

    add_u16(sum_vr, ones_vr, addend_1_vr)
    add_u16(sum_vr, ones_vr, sum_vr)
    add_u16(sum_vr, ones_vr, sum_vr)
    actual_rows = Belex.glass(sum_vr, **glass_kwargs)
    expected_rows = "\n".join(s.replace(".", "0") for s in [
        "[1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1]",
        "[1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",])
    pdisplay(actual_rows, "Expect binary 3 in all plats.")
    Belex.assert_true(actual_rows == expected_rows)

    # Zero out the sum VR and test.

    reset_16(sum_vr)
    actual_rows = Belex.glass(sum_vr, **glass_kwargs)
    expected_rows = "\n".join(s.replace(".", "0") for s in [
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",
        "[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]",])
    pdisplay(actual_rows, "Expect all zero.")
    Belex.assert_true(actual_rows == expected_rows)

    # SMOKE TEST:
    # Count the number of ON bits in each plat of the petri_dish
    # and check.
    for section in range(16):
        RL[section]    <= petri_dish()
        GL[section]    <= RL()
        addend_1_vr[0] <= GL()
        add_u16(sum_vr, addend_1_vr, sum_vr)
    actual_rows = Belex.glass(sum_vr, plats=number_of_plats_to_glass,
                              sections=8, fmt="bin", order="lsb")
    if Belex.debug:
        actual_rows = "\n".join(actual_rows.split("\n")[:8])
    expected_rows = "\n".join(s.replace(".", "0") for s in [
        # . 2 2 . . . . . . . . 3 2 2 2 1 2 3 1 . . 3 3 2 . 4 . . . . . . . . . 2 2 . . .
        '[. . . . . . . . . . . 1 . . . 1 . 1 1 . . 1 1 . . . . . . . . . . . . . . . . .]',
        '[. 1 1 . . . . . . . . 1 1 1 1 . 1 1 . . . 1 1 1 . . . . . . . . . . . 1 1 . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . 1 . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]', ])
    print("SMOKE TEST: Expect the following counts in binary:")
    pdisplay(actual_rows,
        "___2_2_________________3_2_2_2_1_2_3_1_____3_3_2___4___________________2_2______")
    Belex.assert_true(actual_rows == expected_rows)

    # Allocate an additional temporary directory to store counts
    # from the West.
    temp_vr = Belex.VR(0)

    # SMOKE TEST:
    # Add in the number of ON bits in the West.
    for section in range(16):
        RL[section]      <= petri_dish()
        temp_vr[section] <= WRL()
        RL[section]      <= temp_vr()
        GL[section]      <= RL()  # WRL not allowed, here
        addend_1_vr[0]   <= GL()
        add_u16(sum_vr, addend_1_vr, sum_vr)
    actual_rows = Belex.glass(sum_vr, plats=number_of_plats_to_glass,
                              sections=8, fmt="bin", order="lsb")
    expected_rows = "\n".join(s.replace(".", "0") for s in [
        # . 2 4 2 . . . . . . . 3 5 4 4 3 3 5 5 1 . 3 6 5 2 4 4 . . . . . . . . 2 4 2 . .
        '[. . . . . . . . . . . 1 1 . . 1 1 1 . 1 . 1 . 1 . . . . . . . . . . . . . . . .]',
        '[. 1 . 1 . . . . . . . 1 . . . 1 1 . . . . 1 1 . 1 . . . . . . . . . . 1 . 1 . .]',
        '[. . 1 . . . . . . . . . 1 1 1 . . 1 1 . . . 1 1 . 1 1 . . . . . . . . . 1 . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]'])
    print("SMOKE TEST: Expect the following counts in binary:")
    pdisplay(actual_rows,
        "___2_4_2_______________3_5_4_4_3_3_5_5_1___3_6_5_2_4_4_________________2_4_2____")
    if Belex.debug:
        actual_rows = "\n".join(actual_rows.split("\n")[:8])
    Belex.assert_true(actual_rows == expected_rows)

    #  +-+-+-+-+-+-+-+-+-+-+ +-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    #   B i t - S e r i a l   ( S e c t i o n - W i s e )
    #  +-+-+-+-+-+-+-+-+-+-+ +-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    #   N e i g h b o r   C o u n t s
    #  +-+-+-+-+-+-+-+-+ +-+-+-+-+-+-+

    def accumulate_temp_non_diagonal(section, shifted_RL):
        r"""For a given section, accumulate the number of live
        neighbors in some non-diagonal direction specified by
        the 'shifted_RL,' which must be one of {WRL, ERL, NRL,
        SRL}.
        """
        RL[::]           <= petri_dish()
        temp_vr[section] <= shifted_RL
        RL[section]      <= temp_vr()
        GL[section]      <= RL()
        addend_1_vr[0]   <= GL()
        # Belex.glass(addend_1_vr, plats=number_of_plats_to_glass, sections=8, fmt="bin", order="lsb")
        add_u16(sum_vr, addend_1_vr, sum_vr)
        # Belex.glass(sum_vr, plats=number_of_plats_to_glass, sections=8, fmt="bin", order="lsb")

    def accumulate_temp_diagonal(section,
            first_shifted_RL, second_shifted_RL):
        r"""For a given section, accumulate the number of live
        neigbors in some diagonal direction specified by a pair
        of shifted RLs, one in the East-West direction and the
        other in the North-South direction."""
        RL[::]           <= petri_dish()
        temp_vr[::]      <= first_shifted_RL
        RL[::]           <= temp_vr()
        temp_vr[section] <= second_shifted_RL
        RL[section]      <= temp_vr()
        GL[section]      <= RL()
        addend_1_vr[0]   <= GL()
        add_u16(sum_vr, addend_1_vr, sum_vr)

    def moore_counts(section, debug=False):
        """Just for one section, count the eight neighbors (the Moore
        cell). Flat-Earth boundary conditions, not toroidal!
        """
        reset_16(sum_vr)
        # The following four lines accumulate the von-Neumann counts
        # (the non-diagonal neighbors)
        accumulate_temp_non_diagonal(section, WRL())
        accumulate_temp_non_diagonal(section, ERL())
        accumulate_temp_non_diagonal(section, NRL())
        accumulate_temp_non_diagonal(section, SRL())
        if (debug):
            actual_rows = Belex.glass(sum_vr, plats=number_of_plats_to_glass,
                                      sections=8, fmt="bin", order="lsb")
            expected_rows = "\n".join(s.replace(".", "0") for s in [
                # plat numbers:       1 1 1 1 1 1 1 1 1 1 2 2 2 2 2 2 2 2 2 2 3 3 3 3 3 3 3 3 3 3
                # 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9
                # expected von-Neumann counts (up + down + left + right): (from paper calculation)
                # . 1 1 . . . . . . . . 2 . 2 1 1 . 2 . . 1 3 3 1 . . . . . . . . . . 1 2 2 1 . .
                # little-endian bit patterns for expected von-Neumann counts:
                '[. 1 1 . . . . . . . . . . . 1 1 . . . . 1 1 1 1 . . . . . . . . . . 1 . . 1 . .]',
                '[. . . . . . . . . . . 1 . 1 . . . 1 . . . 1 1 . . . . . . . . . . . . 1 1 . . .]',
                '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
                '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
                '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
                '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
                '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
                '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]'])
            print("Expect von Neumann counts (non-diagonal neighbor live counts) in binary:")
            pdisplay(actual_rows,
                     "___1_1_________________2___2_1_1___2_____1_3_3_1_____________________1_2_2_1____")
            if Belex.debug:
                actual_rows = "\n".join(actual_rows.split("\n")[:8])
            Belex.assert_true(actual_rows == expected_rows)

        # To get the diagonal neighbors, we must do two shifts
        # upper-left, the NRL of the WRL.
        accumulate_temp_diagonal(section, WRL(), NRL())
        # Now, the other three corners:
        accumulate_temp_diagonal(section, ERL(), NRL())
        accumulate_temp_diagonal(section, WRL(), SRL())
        accumulate_temp_diagonal(section, ERL(), SRL())

    # For debugging and live-coding, arbitrarily choose section 4.

    unit_test_section = 4
    moore_counts(unit_test_section, debug=True)

    # Assert this result in the test code (check against hand
    # calculation).

    actual_rows = Belex.glass(sum_vr, plats=number_of_plats_to_glass,
                              sections=8, fmt="bin", order="lsb")
    expected_rows = "\n".join(s.replace(".", "0") for s in [
        # plat numbers:
        #                     1 1 1 1 1 1 1 1 1 1 2 2 2 2 2 2 2 2 2 2 3 3 3 3 3 3 3 3 3 3
        # 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9
        # expected Moore (eight neighbors): (from paper calculation)
        # 1 2 2 1 . . . . . . 1 2 2 3 2 2 1 2 1 . 3 5 5 3 . . . . . . . . . . 2 3 3 2 . .
        # little-endian bit patterns for expected Moore counts:
        '[1 . . 1 . . . . . . 1 . . 1 . . 1 . 1 . 1 1 1 1 . . . . . . . . . . . 1 1 . . .]',
        '[. 1 1 . . . . . . . . 1 1 1 1 1 . 1 . . 1 . . 1 . . . . . . . . . . 1 1 1 1 . .]',
        '[. . . . . . . . . . . . . . . . . . . . . 1 1 . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]'])
    print("Expect Moore counts (non-diagonal neighbor live counts) in binary:")
    pdisplay(actual_rows,
        "_1_2_2_1_____________1_2_2_3_2_2_1_2_1___3_5_5_3_____________________2_3_3_2____")
    if Belex.debug:
        actual_rows = "\n".join(actual_rows.split("\n")[:8])
    Belex.assert_true(actual_rows == expected_rows)

    #  +-+-+-+-+-+-+-+-+-+
    #   E v o l u t i o n
    #  +-+-+-+-+-+-+-+-+-+

    # The following is not optimized, for clarity's sake. We are sure
    # some clever optimizations can reduce the command-count and
    # instruction count.

    new_generation = Belex.VR(0)
    reset_16(new_generation)

    # RULE 1: If a dead cell's Moore neighbor-count is 3, turn it ON.
    # RULE 2: If a live cell's Moore neighbor-count is 2 or 3, leave it ON.
    # RULE 3: (REDUNDANT) All other live cells die; dead cells stay dead.

    # Rule 3 is redundant in our implementation because the new_generation starts dead.

    #  +-+-+-+-+-+-+
    #   R U L E   1
    #  +-+-+-+-+-+-+

    # RULE 1: If a dead cell's Moore neighbor-count is 3, turn it ON.

    def rule_1(section):

        # Note that the sum calculation uses only sections
        # 0, 1, 2, and 3 because the maximum neighbor count
        # is 8 = 2^3 = 2^[section-3].

        # Strategy: use GL's implicit AND to find OFF cells with
        # exactly 3 neighbors.

        # Put in section RL[4] (unused by moore_count) the OFF cells of
        # cells of 'section' of petri_dish:

        RL[section] <= petri_dish()
        GL[section] <= RL()
        RL[4] <= ~GL()

        # get sum_vr sections 0 and 1; both ON if sum == 3
        # (but not ONLY if).
        RL["01"] <= sum_vr()
        # Now, AND-in the complement of sections 2 and 3 of sum,
        # ON only if sum < 4.
        # We would like to say RL["23"] <= ~sum_vr(), but this
        # command is not allowed
        # (TODO: BELEX doesn't reject it!)
        # Instead, we can use command 16 (from belex-alpha doc,
        # Figure 6)
        #     16. RL["23"] &= ~<SB>
        # Set up some ones for the &= of command 16:
        RL["23"] <= 1
        RL["23"] &= ~sum_vr()

        # GL's AND will be ON iff
        # A. RL[0] & RL[1] are ON,
        # B. RL[2] & RL[3] are OFF,
        # C. petri_dish[arbitrary_section] is OFF.
        GL["01234"] <= RL()

        # Those cells are going ON in the next round.
        new_generation[section] <= GL()

    rule_1(unit_test_section)

    actual_rows = Belex.glass(new_generation, plats=number_of_plats_to_glass,
                              sections=8, fmt="bin", order="lsb")
    expected_rows = "\n".join(s.replace(".", "0") for s in [
        # plat numbers:       1 1 1 1 1 1 1 1 1 1 2 2 2 2 2 2 2 2 2 2 3 3 3 3 3 3 3 3 3 3
        # 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9
        # expected Moore (eight neighbors): (from paper calculation)
        # 1 2 2 1 . . . . . . 1 2 2 3 2 2 1 2 1 . 3 5 5 3 . . . . . . . . . . 2 3 3 2 . .
        # on bits where (and only where) Moore-count = exactly 3 and center is dead
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . 1 . . . . . . 1 . . 1 . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]', ])
    pdisplay(actual_rows, """In section 4, expect ON bits where (and only where)
    Moore-count == exactly 3 and center is dead.""")
    if Belex.debug:
        actual_rows = "\n".join(actual_rows.split("\n")[:8])
    Belex.assert_true(actual_rows == expected_rows)

    #  +-+-+-+-+-+-+
    #   R U L E   2
    #  +-+-+-+-+-+-+

    # RULE 2: If an ON cell's Moore neighbor-count is 2 or 3, leave it ON.

    def rule_2(section):

        # Put in RL[4] the ON bits of petri-dish:

        RL[section] <= petri_dish()
        GL[section] <= RL()
        RL[4] <= GL()

        # Find counts in sum_vr that are 2 or 3. It suffices to check sections
        # 1, anti-2, and anti-3:

        RL["1"]  <= sum_vr()
        RL["23"] <= 1
        RL["23"] &= ~sum_vr()

        # AND them all up, excluding section 0!, otherwise as before.
        # GL's AND will be ON iff
        # A. RL[1] is ON,
        # B. RL[2] & RL[3] are OFF,
        # C. petri_dish[arbitrary_section] is ON.
        GL["1234"] <= RL()
        new_generation[section] |= GL()

    rule_2(unit_test_section)

    actual_rows = Belex.glass(new_generation, plats=number_of_plats_to_glass,
                              sections=8, fmt="bin", order="lsb")
    expected_rows = "\n".join(s.replace(".", "0") for s in [
        # plat numbers:       1 1 1 1 1 1 1 1 1 1 2 2 2 2 2 2 2 2 2 2 3 3 3 3 3 3 3 3 3 3
        # 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9
        # expected Moore (eight neighbors): (from paper calculation)
        # 1 2 2 1 . . . . . . 1 2 2 3 2 2 1 2 1 . 3 5 5 3 . . . . . . . . . . 2 3 3 2 . .
        # on bits where (and only where) Moore-count == 2 or 3 and center is live
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . 1 1 . . . . . . 1 . . 1 . . . . . . . . . . . 1 1 . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]', ])
    pdisplay(actual_rows, """In section 4, expect ON bits where (and only where)
    Moore-count == 2 or 3 and center is live.""")
    if Belex.debug:
        actual_rows = "\n".join(actual_rows.split("\n")[:8])
    Belex.assert_true(actual_rows == expected_rows)

    def rules(section):
        rule_1(section)
        rule_2(section)

    # Check the second generation of the glider gun:
    reset_16(new_generation)
    for section in range(16):
        moore_counts(section)
        rules(section)

    actual_rows = Belex.glass(new_generation, **glass_kwargs)
    expected_rows = "\n".join(s.replace(".", "0") for s in [
        # plat numbers:       1 1 1 1 1 1 1 1 1 1 2 2 2 2 2 2 2 2 2 2 3 3 3 3 3 3 3 3 3 3
        # 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . 1 . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . 1 . 1 . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . 1 . . . . . . . 1 . 1 . . . . . . . . . . . 1 1 . . .]',
        '[. . . . . . . . . . . . 1 1 . . . . . . 1 . . 1 . . . . . . . . . . . 1 1 . . .]',
        '[. 1 1 . . . . . . . . 1 1 . . . . 1 1 . . 1 . 1 . . . . . . . . . . . . . . . .]',
        '[. 1 1 . . . . . . . 1 1 1 . . . . 1 1 . . . 1 . 1 . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . 1 1 . . . . 1 1 . . . . . 1 . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . 1 1 . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . 1 . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]',
        '[. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .]'])
    pdisplay(actual_rows, """In all sections, expect generation 2.""")
    Belex.assert_true(actual_rows == expected_rows)

    stop_here = 42


# ______________________________________________________________________
#  | |_ __ _| |__| |___ ___| |___  ___| |___  _ _ __   __| |_ _  _| |__
#  |  _/ _` | '_ \ / -_)___| / _ \/ _ \ / / || | '_ \ (_-<  _| || | '_ \
#   \__\__,_|_.__/_\___|   |_\___/\___/_\_\\_,_| .__/ /__/\__|\_,_|_.__/
#                                              |_|

# [8:37 AM] eli ehrman
# N.B. It is not a regular mask that must be passed here.
# It is the mask you want AND the INV of the imm val
# i.e. all the zero bits of the imm are set to one and
# none of the bits outside the mask


@belex_apl
def gvrc_eq_imm_16_msk(Belex,
        flags: VR,
        dest_mrk : u16,
        src : VR,
        imm_test : u16,  # the ones
        inv_mask : u16): # the zeros
    # don't cares are neither
    with apl_commands('AND all RLs for the mask to GL'):
        RL[imm_test] <= src()
        RL[inv_mask] <= ~src() & INV_RSP16()
        GL[imm_test] <= RL()
        GL[inv_mask] <= RL()
    # indent to here when you put apl_commands
    flags[dest_mrk] <= GL()


# __________________________________________________________________
#  (_)_ _ ___ ___ ___ __| |_(_)___ _ _   __ _____ _ _ __(_)___ _ _
#  | | ' \___(_-</ -_) _|  _| / _ \ ' \  \ V / -_) '_(_-< / _ \ ' \
#  |_|_||_|  /__/\___\__|\__|_\___/_||_|  \_/\___|_| /__/_\___/_||_|

#    ___      ___         __                  __
#   / _ \___ / _/__ _____/ /____  _______ ___/ /
#  / , _/ -_) _/ _ `/ __/ __/ _ \/ __/ -_) _  /
# /_/|_|\__/_/ \_,_/\__/\__/\___/_/  \__/\_,_/

@belex_apl
def ha(Belex,
       ssum: VR, cout: VR,  # outputs
       a: VR, b: VR         # inputs
       ):
    """half-adder"""
    RL[::] <= a()
    RL[::] ^= b()
    with apl_commands():
        ssum[::] <= RL()
        RL[::] <= a() & b()
    cout[::] <= RL()

@belex_apl
def qa(Belex,
       ssum: VR,     # outputs
       a: VR, b: VR  # inputs
       ):
    """quarter-adder"""
    RL[::] <= a()
    RL[::] ^= b()
    ssum[::] <= RL()


@belex_apl
def fa(Belex,
       ssum: VR, cout: VR,     # outputs
       a: VR, b: VR, cin: VR,  # inputs
       scratch: VR             # user-provided space
       ):
    """full adder"""
    # ssum = a ^ b ^ cin
    RL[::] <= a()
    RL[::] ^= b()
    RL[::] ^= cin()
    with apl_commands():
        ssum[::] <= RL()
        # cout = (a /\ b) ^ (c /\ (a ^ b))
        RL[::] <= a()
    RL[::] ^= b()
    RL[::] &= cin()
    with apl_commands():
        scratch[::] <= RL()
        RL[::] <= a()
    RL[::] &= b()
    RL[::] ^= scratch()
    cout[::] = RL()


@belex_apl
def ha1(Belex,
        s10: VR, s11: VR,  # 2 outputs
        petri_dish: VR):   # input

    RL[::] <= petri_dish()

    x1 = w = Belex.VR(0)
    w[::] <= WRL()

    x2 = e = Belex.VR(0)
    e[::] <= ERL()

    ha(s10, s11, x1, x2)


@belex_apl
def ha2(Belex,
        s20: VR, s21: VR,  # 2 outputs
        petri_dish: VR):   # input

    RL[::] <= petri_dish()

    x3 = n = Belex.VR(0)
    n[::] <= NRL()

    x4 = s = Belex.VR(0)
    s[::] <= SRL()

    ha(s20, s21, x3, x4)


@belex_apl
def ha5_fa1(Belex,
        t10: VR, t11: VR, t12: VR,  # 3 outputs
        petri_dish: VR):

    s10 = Belex.VR(0)
    s11 = Belex.VR(0)
    s20 = Belex.VR(0)
    s21 = Belex.VR(0)
    c1 = Belex.VR(0)
    scratch = Belex.VR(0)

    ha1(s10, s11, petri_dish)
    ha2(s20, s21, petri_dish)

    ha(t10, c1, s10, s20)
    fa(t11, t12, s11, s21, c1, scratch)


@belex_apl
def ha3(Belex,
        s30: VR, s31: VR,  # 2 outputs
        petri_dish: VR):   # input

    RL[::] <= petri_dish()
    w = Belex.VR(0)
    w[::] <= WRL()  # TODO: test read-after-write
    RL[::] <= w()

    x5 = nw = Belex.VR(0)
    nw[::] <= NRL()

    x6 = sw = Belex.VR(0)
    sw[::] <= SRL()

    ha(s30, s31, x5, x6)


@belex_apl
def ha4(Belex,
        s40: VR, s41: VR,  # 2 outputs
        petri_dish: VR):   # input

    RL[::] <= petri_dish()
    e = Belex.VR(0)
    e[::] <= ERL()
    RL[::] <= e()

    x7 = ne = Belex.VR(0)
    ne[::] <= NRL()

    x8 = se = Belex.VR(0)
    se[::] <= SRL()

    ha(s40, s41, x7, x8)


@belex_apl
def ha6_fa2(Belex,
        t20: VR, t21: VR, t22: VR,  # 3 outputs
        petri_dish: VR):

    s30 = Belex.VR(0)
    s31 = Belex.VR(0)
    s40 = Belex.VR(0)
    s41 = Belex.VR(0)
    c2 = Belex.VR(0)
    scratch = Belex.VR(0)

    ha3(s30, s31, petri_dish)
    ha4(s40, s41, petri_dish)

    ha(t20, c2, s30, s40)
    fa(t21, t22, s31, s41, c2, scratch)


@belex_apl
def ha7_fa3(Belex,
            u0: VR, u1: VR, d1: VR, t12: VR, t22: VR,  # 5 outputs
            petri_dish: VR):
    t10 = Belex.VR(0)
    t20 = Belex.VR(0)
    t11 = Belex.VR(0)
    t21 = Belex.VR(0)
    d0 = Belex.VR(0)
    scratch = Belex.VR(0)

    ha5_fa1(t10, t11, t12, petri_dish)
    ha6_fa2(t20, t21, t22, petri_dish)

    ha(u0, d0, t10, t20)
    fa(u1, d1, t11, t21, d0, scratch)


@belex_apl
def fa4(Belex,
        u0: VR, u1: VR, u2: VR, u3: VR,  # 4 outputs
        petri_dish: VR):
    scratch = Belex.VR(0)
    t12 = Belex.VR(0)
    t22 = Belex.VR(0)
    d1 = Belex.VR(0)
    ha7_fa3(u0, u1, d1, t12, t22, petri_dish)
    fa(u2, u3, t12, t22, d1, scratch)


@belex_apl
def gol_in_section_refactored(Belex, petri_dish: VR):

    RL[::] <= petri_dish()

    u0 = Belex.VR(0)
    u1 = Belex.VR(0)
    u2 = Belex.VR(0)
    u3 = Belex.VR(0)

    fa4(u0, u1, u2, u3, petri_dish)

    new_gen = Belex.VR(0)

    # If it's ON and has 2 or 3 neighbors, leave it ON.
    RL[::] <= petri_dish()  # it's ON
    RL[::] &= u1()          # bit one (coefficient of 2) is ON
    RL[::] &= ~u2()         # bit two (coefficient of 4) is OFF
    RL[::] &= ~u3()         # bit tre (coefficient of 8) is OFF

    new_gen[::] <= RL()

    # If it's OFF and has exactly 3 neighbors, turn it ON.
    RL[::] <= 1
    RL[::] &= ~petri_dish() # it's OFF
    RL[::] &= u0()          # bit zro (coefficient of 0) is ON
    RL[::] &= u1()          # bit one (coefficient of 2) is ON
    RL[::] &= ~u2()         # bit two (coefficient of 4) is OFF
    RL[::] &= ~u3()         # bit tre (coefficient of 8) is OFF

    # with apl_commands():  # does not work
    new_gen[::] |= RL()

    RL[::] <= new_gen()
    petri_dish[::] <= RL()


#    ___      ___         __                  __
#   / _ \___ / _/__ _____/ /____  _______ ___/ /
#  / // / -_) _/ _ `/ __/ __/ _ \/ __/ -_) _  /
# /____/\__/_/ \_,_/\__/\__/\___/_/  \__/\_,_/


@belex_apl
def gol_in_section_defactored(Belex, petri_dish: VR):

    RL[::] <= petri_dish()

    # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    #  V o n - N e u m a n n   b i t s   ( n o n - d i a g o n a l )
    # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    x1 = w = Belex.VR(0)  # x1 is an alias, helpful for correctly writing the adder
    w[::] <= WRL()

    x2 = e = Belex.VR(0)  # x2 is an alias for the adder
    e[::] <= ERL()

    x3 = n = Belex.VR(0)  # x3 is an alias for the adder
    n[::] <= NRL()

    x4 = s = Belex.VR(0)  # x4 is an alias for the adder
    s[::] <= SRL()

    # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    #  M o o r e   b i t s   ( i n c l u d i n g   d i a g o n a l s )
    # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    RL[::] <= w()

    x5 = nw = Belex.VR(0)  # x5 is an alias for the adder
    nw[::] <= NRL()

    x6 = sw = Belex.VR(0)  # x6 is an alias for the adder
    sw[::] <= SRL()

    RL[::] <= e()

    x7 = ne = Belex.VR(0)  # x7 is an alias for the adder
    ne[::] <= NRL()

    x8 = se = Belex.VR(0)  # x8 is an alias for the adder
    se[::] <= SRL()

    # +-+-+-+-+
    #  s u m s
    # +-+-+-+-+

    def ha(ssum, cout, a, b):
        """half-adder"""
        RL[::] <= a()
        RL[::] ^= b()
        with apl_commands():
            ssum[::] <= RL()
            RL[::] <= a()

        RL[::] &= b()
        cout[::] <= RL()

    def fa(ssum, cout, a, b, cin, temp):
        """full adder"""
        # ssum = a ^ b ^ cin
        RL[::] <= a()
        RL[::] ^= b()
        RL[::] ^= cin()
        with apl_commands():
            ssum[::] <= RL()
            # cout = (a /\ b) ^ (c /\ (a ^ b))
            RL[::] <= a()

        RL[::] ^= b()
        RL[::] &= cin()
        with apl_commands():
            temp[::] <= RL()
            RL[::] <= a()

        RL[::] &= b()
        RL[::] ^= temp()
        cout[::] = RL()

    def pair_count(s0, s1,  # outputs
                   x1, x2): # inputs
        r"""Count the number of ON-bits in x1 and x2.
        s0 is the coefficient of 2^0; s1 is the coefficient
        of 2^1; x1 is one input of the pair; x2 is the other
        input of the pair. The truth table of this function
        is just that of the half adder."""
        ha(s0, s1, x1, x2)

    def quad_count(t0, t1, t2,  # 3-bit output
                   sp10, sp20,  # inputs from prior call of pair_count
                   sp11, sp21,  # inputs from prior call of pair_count
                   c0,          # temp for rippled-carry
                   scratch):    #
        r"""Count the 3-bit number of ON-bits in four inputs
        aggregated in four prior calls of pair_count.
        t0, t1, t2 are little-endian outputs; sp10, sp20
        are the 0-bits of two prior pair counts; sp11, sp21
        are the 1-bits of two prior pair counts."""
        ha(t0, c0, sp10, sp20)               # ha5, ha6
        fa(t1, t2, sp11, sp21, c0, scratch)  # fa1, fa2

    def octo_count(u0, u1, u2, u3,  # 4-bit output
                   t10, t20,  # inputs from prior call of quad_count
                   t11, t21,  # inputs from prior call of quad_count
                   t12, t22,  # inputs from prior call of quad_count
                   d0, d1,  # temps for rippled carries
                   scratch):  #
        r"""Count the 4-bit number of ON-bits in eight inputs
        aggregated in two prior calls of quad_count.
        u0, ..., u3 are the little-endian outputs; t10, t20
        are the 0-bits of two prior quad counts; t11, t21
        are the 1-bits of two prior quad counts; t12, t22
        are the 2-bits of two prior quad counts."""
        ha(u0, d0, t10, t20)  # ha7 on the diagram
        fa(u1, d1, t11, t21, d0, scratch)  # fa3
        fa(u2, u3, t12, t22, d1, scratch)  # fa4

    s10 = Belex.VR(0)
    s11 = Belex.VR(0)

    s20 = Belex.VR(0)
    s21 = Belex.VR(0)

    s30 = Belex.VR(0)
    s31 = Belex.VR(0)

    s40 = Belex.VR(0)
    s41 = Belex.VR(0)

    pair_count(s10, s11, x1, x2)
    pair_count(s20, s21, x3, x4)
    pair_count(s30, s31, x5, x6)
    pair_count(s40, s41, x7, x8)

    t10 = Belex.VR(0)
    t11 = Belex.VR(0)
    t12 = Belex.VR(0)

    t20 = Belex.VR(0)
    t21 = Belex.VR(0)
    t22 = Belex.VR(0)

    c0 = Belex.VR(0)
    scratch = Belex.VR(0)

    quad_count(t10, t11, t12,
               s10, s20, s11, s21,
               c0, scratch)
    quad_count(t20, t21, t22,
               s30, s40, s31, s41,
               c0, scratch)

    c1 = Belex.VR(0)

    u0 = Belex.VR(0)
    u1 = Belex.VR(0)
    u2 = Belex.VR(0)
    u3 = Belex.VR(0)

    octo_count(u0, u1, u2, u3,
               t10, t20, t11, t21, t12, t22,
               c0, c1, scratch)

    new_gen = Belex.VR(0)

    # If it's ON and has 2 or 3 neighbors, leave it ON.
    RL[::] <= petri_dish()  # it's ON
    RL[::] &= u1()          # bit one (coefficient of 2) is ON
    RL[::] &= ~u2()         # bit two (coefficient of 4) is OFF
    RL[::] &= ~u3()         # bit tre (coefficient of 8) is OFF

    new_gen[::] <= RL()

    # If it's OFF and has exactly 3 neighbors, turn it ON.
    RL[::] <= 1
    RL[::] &= ~petri_dish() # it's OFF
    RL[::] &= u0()          # bit zro (coefficient of 0) is ON
    RL[::] &= u1()          # bit one (coefficient of 2) is ON
    RL[::] &= ~u2()         # bit two (coefficient of 4) is OFF
    RL[::] &= ~u3()         # bit tre (coefficient of 8) is OFF

    new_gen[::] |= RL()

    RL[::] <= new_gen()
    petri_dish[::] <= RL()


@belex_apl
def gol_in_section_danilan(Belex, petri_dish: VR):
    # Step 1
    sb0 = petri_dish  # alias
    sb1 = Belex.VR(); sb2 = Belex.VR(); sb3 = Belex.VR()
    sb4 = Belex.VR(); sb5 = Belex.VR(); sb6 = Belex.VR()
    sb7 = Belex.VR(); sb8 = Belex.VR(); sb9 = Belex.VR()
    sb10 = Belex.VR(); sb11 = Belex.VR(); sb12 = Belex.VR()
    scratch = Belex.VR()

    # Additional laning can be had by inlining fa and ha, or
    # by automated peephole laning.

    RL[::] <= petri_dish()

    sb1[::] <= ERL()
    sb2[::] <= WRL()
    fa(sb3, sb4, sb0, sb1, sb2, scratch)
    # sb3 has e + w + center sum bit; sb4 has e & w & center carry-out bit
    # rsp_out("0xFFFF")  # TODO: lane it!; for future stacked play field.

    # Step 2
    RL[::] <= sb3()  # e + w + center, bit 0 of sum
    # with apl_commands():
    sb1[::] <= NRL() # ne + nw + n
    sb2[::] <= SRL() # se + sw + s
    fa(sb5, sb6, sb1, sb2, sb3, scratch)
    # sb5 has 9-cell sum bit 0; sb6 has 9-cell carry-out of bit 0 sum

    RL[::] <= sb5()  # all nine cells, sum bit 0
    with apl_commands():
        sb9[::] <= ~RL()  # inverse of 9-cell sum bit 0

        # Step 3
        RL[::] <= sb4()  # e & w & center, carry bit
    # with apl_commands():  # NRL and SRL cannot be simultaneously laned
    sb1[::] <= NRL()  # ne & nw & n, carry bit
    sb2[::] <= SRL()  # se & sw & s, carry bit
    fa(sb7, sb8, sb1, sb2, sb4, scratch)
    # sb7 has bit 1 of 9-cell sum; sb8 has carry-out of 9-cell sum bit 1

    # Step 4
    ha(sb1, sb2, sb7, sb6)
    RL[::] <= sb1()
    sb10[::] <= ~RL()
    ha(sb6, sb7, sb8, sb2)

    RL[::] <= sb7()
    with apl_commands():
        sb12[::] <= ~RL()  # inverse of bit 3? of 9-cell sum
        RL[::] <= sb6()
    with apl_commands():
        sb11[::] <= ~RL()  # inverse of bit 2? of 9-cell sum

        # Step 5 without RE for now
        RL[::] <= 0  # redundant but zero-cost; necessary when we have RE.
    # bit 0 don't care
    RL[::] <= sb12() & sb11() & sb1()
    RL[::] &= sb5()

    scratch[::] <= RL()

    RL[::] <= sb0() & sb9()
    RL[::] &= sb12() & sb6() & sb10()
    RL[::] |= scratch()

    sb0[::] <= RL()



@belex_apl
def fa_2(Belex, sum_: VR, cout: VR, a: VR, b: VR, cin: VR):
    """TODO: Untested, optimal full adder. Will be tested when Belex
    has automatic laning. """
    RL[::] <= a()  # LANE this with last instruction before the call
    RL[::] ^= b()
    RL[::] ^= cin()
    with apl_commands():
        sum_[::] <= RL()  # underscore prevents collision with built-in "sum"
        RL[::] <= a() & b()
    RL[::] |= a() & cin()
    RL[::] |= b() & cin()
    cout[::] <= RL() # LANE this with first instruction after the call


@belex_apl
def ha_2(Belex, sum_: VR, cout: VR, a: VR, b: VR):
    """TODO: Untested, optimal half adder. Will be tested when Belex
    has automatic laning. """
    RL[::] <= a  # LANE this with last instruction before the call
    RL[::] ^= b
    with apl_commands():
        sum_[::] <= RL()  # underscore prevents collision with built-in "sum"
        RL[::] <= a() & b()
    cout[::] <= RL() # LANE this with first instruction after the call


@belex_apl
def gol_in_section_danilan_2_manually_inlined_and_laned(
        Belex, petri_dish: VR):

    r"""Version of Dan's fast GoL retained for performance
    regressions against the Belex compiler of May 2022, which can
    perform automatic laning across boundaries of inlined
    functions, as well as everywhere else."""

    # Aliases to make the code understandable mathematically.
    center = petri_dish
    RL_c = RL                 # original center data point
    RL_C_0 = RL               # bit 0 of central row C
    east = Belex.VR()         # original east data point
    west = Belex.VR()         # original west data point
    C_0 = Belex.VR()          # bit 0 of central row C
    C_0_cout = Belex.VR()     # carry-out of computation of bit 0 of C
    N_0 = Belex.VR()          # bit 0 of sum of North row
    S_0 = Belex.VR()          # bit 0 of sum of South row
    mOdd = Belex.VR()         # bit 0 of 9-cell sum
    NSC_0_cout = Belex.VR()   # carry-out of computation of NSC
    mEven = Belex.VR()        # inverse of bit 0 of 9-cell sum
    N_0_cout = Belex.VR()
    S_0_cout = Belex.VR()
    NSC_1 = Belex.VR()
    NSC_1_cout = Belex.VR()
    NSC_2 = Belex.VR()
    NSC_2_cout = Belex.VR()
    INV_NSC_2 = Belex.VR()
    NSC_3 = Belex.VR()
    INV_NSC_3 = Belex.VR()

    RL_c[::] <= center()

    #  ___ _____ ___ ___   _
    # / __|_   _| __| _ \ / |
    # \__ \ | | | _||  _/ | |
    # |___/ |_| |___|_|   |_|

    # Add east, west, and center to get C_0, sum of central row,
    # C, and its carry-out bit, C_0_cout, using the full adder,
    # fa_2.

    # The Belex compiler will inline the code for the full adder,
    # fa_2. However, versions of the Belex compiler before May
    # 2022 cannot, combine commands across function-call
    # boundaries into 'with apl_commands' blocks. All commands in
    # such a block, if mutually compatible, run in parallel.
    # Compatibility rules are not explained here.

    # The process of combining commands into 'with apl_commands'
    # blocks is called 'laning.' An improvement of the Belex
    # compiler, current in May 2022, both inlines and lanes
    # commands blocks automatically. In this regression test, we
    # manually inline and lane the code for both the full adder,
    # fa_2, and for the half adder, ha_2.

    # What we want to write:

    # east[::] <= ERL()
    # west[::] <= WRL()
    # fa_2(C_0, C_0_cout, center, east, west)

    # what we actually write, to lane manually:

    # At this point, RL == RL_c = c = center bit of game state.
    east[::] <= ERL()              # e = the bit east of c
    with apl_commands():
        # last command of the call site of fa_2, laned in
        west[::] <= WRL()          # w = the bit west of c

        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- #
        #  b e g i n   f u l l   a d d e r  #
        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- #

        # The next command is redundant but harmless, even to
        # speed, because it runs in parallel with the command
        # above; it's the result of blind inlining:

        # first command of fa_2 laned in; bit-wise PLUS is XOR.
        RL[::] <= center()      # RL*   = c
    RL[::] ^= east()            # RL**  = RL*  + e == e + c
    RL[::] ^= west()            # RL*** = RL** + w == e + c = w
    with apl_commands():
        C_0[::] <= RL()         # C_0 = RL** == = e + w + c;
        # Start carry-out bit of center-row sum C_0; re-use RL.
        RL[::] <= center() & east()     # RL'   = c & e
    RL[::] |= center() & west()         # RL''  = RL'  | c & w
    RL[::] |= east() & west()           # RL''' = RL'' | e & w
    with apl_commands():
        # last command of fa_2 laned out
        C_0_cout[::] <= RL()    # C_cout carry-out bit = RL'''

        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+- #
        #  e n d   f u l l   a d d e r  #
        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+- #

    #  ___ _____ ___ ___   ___
    # / __|_   _| __| _ \ |_  )
    # \__ \ | | | _||  _/  / /
    # |___/ |_| |___|_|   /___|

    # First command after the call of fa_2, laned in. RL was
    # overwritten by the carry-out computation, restore it:
        RL_C_0[::] <= C_0()     # e + w + c, bit 0 of sum

    N_0[::] <= NRL()            # N_0 = ne + nw + n
    with apl_commands():
        # last command of the call site of fa_2, laned in:
        S_0[::] <= SRL()        # S_0 = se + sw + s

        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- #
        #  b e g i n   f u l l   a d d e r  #
        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- #

        RL[::] <= N_0()         # RL*   = N_0
    RL[::] ^= S_0()             # RL**  = RL*  ^ S_0 == N_0 ^ S_0
    RL[::] ^= C_0()             # RL*** = RL** ^ C_0 == N_0 ^ S_0 ^ C_0
    with apl_commands():
        mOdd[::] <= RL()        # NSC_0 = N_0 ^ S_0 ^ C_0
        # Start carry-out computation of the full adder.
        RL[::] <= N_0() & S_0() # RL'   = N_0 & S_0
    RL[::] |= N_0() & C_0()     # RL''  = RL'  | N_0 & C_0
    RL[::] |= S_0() & C_0()     # RL''' = RL'' | S_0 & C_0
    with apl_commands():
        NSC_0_cout[::] <= RL()  # last command of fa_2 laned out

        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+- #
        #  e n d   f u l l   a d d e r  #
        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+- #

    # NSC_0 has 9-cell sum bit 0; NSC_0_cout has 9-cell carry-out
    # of bit 0 sum.

    # The first command after call of fa_2 above, laned in.

        RL[::] <= mOdd()  # all nine cells, sum bit 0

    with apl_commands():
        mEven[::] <= ~RL()

        #  ___ _____ ___ ___   ____
        # / __|_   _| __| _ \ |__ /
        # \__ \ | | | _||  _/  |_ \
        # |___/ |_| |___|_|   |___/

        RL[::] <= C_0_cout()

    N_0_cout[::] <= NRL()
    with apl_commands():
        S_0_cout[::] <= SRL()

        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- #
        #  b e g i n   f u l l   a d d e r  #
        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- #

        RL[::] <= N_0_cout()
    RL[::] ^= S_0_cout()
    RL[::] ^= C_0_cout()
    with apl_commands():
        NSC_1[::] <= RL()
        RL[::] <= N_0_cout() & S_0_cout()
    RL[::] |= N_0_cout() & C_0_cout()
    RL[::] |= S_0_cout() & C_0_cout()
    with apl_commands():
        NSC_1_cout[::] <= RL()

        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+- #
        #  e n d   f u l l   a d d e r  #
        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+- #

    #  ___ _____ ___ ___   _ _
    # / __|_   _| __| _ \ | | |
    # \__ \ | | | _||  _/ |_  _|
    # |___/ |_| |___|_|     |_|

    # ha(NSC_2, NSC_2_cout, NSC_1, NSC_0_cout)

    # NSC_2 makes no implication about NSC:0, bit 0 of NSC.
    # NSC_2 <=> NSC:1
    # NSC_2 makes no implication about NSC:2.
    # NSC_2 => ~NSC:3; Converse is not true.

        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- #
        #  b e g i n   h a l f   a d d e r  #
        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- #

        RL[::] <= NSC_1()
    RL[::] ^= NSC_0_cout()
    with apl_commands():
        NSC_2[::] <= RL()
        RL[::] <= NSC_1() & NSC_0_cout()
    with apl_commands():
        NSC_2_cout[::] <= RL()

        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+- #
        #  e n d   h a l f   a d d e r  #
        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+- #

        RL[::] <= NSC_2()

    # Save the inverse of bit 2, NSC_2, of the 9-cell sum to
    # distinguish c == 3 from c == 4.

    with apl_commands():
        INV_NSC_2[::] <= ~RL()

    #  ___ _____ ___ ___   ___
    # / __|_   _| __| _ \ | __|
    # \__ \ | | | _||  _/ |__ \
    # |___/ |_| |___|_|   |___/

    # ha(NSC_3, NSC_3_cout, NSC_1_cout, NSC_2_cout)

    # NSC_3 makes no implication about NSC:0, bit 0 of NSC.
    # NSC_3 makes no implication about NSC:1.
    # NSC_3 <=> NSC:2
    # NSC_3 => ~NSC:3; Converse is not true.

        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- #
        #  b e g i n   h a l f   a d d e r  #
        # -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- #

        RL[::] <= NSC_1_cout()
    RL[::] ^= NSC_2_cout()
    with apl_commands():
        NSC_3[::] = RL()
        # RL[::] <= NSC_1_cout() & NSC_2_cout()  # unused

    # NSC_3_cout[::] <= RL()  # unused

    # -+-+-+-+-+-+-+-+-+-+-+-+-+-+- #
    #  e n d   h a l f   a d d e r  #
    # -+-+-+-+-+-+-+-+-+-+-+-+-+-+- #

    # read-after-write peephole will eliminate this
    # RL[::] <= NSC_3_cout()

    with apl_commands():
        RL[::] <= NSC_3()
    with apl_commands():
        INV_NSC_3[::] <= ~RL()  # inverse of bit 3 of 9-cell sum

        RL[::] <= center()

    # c & (mEven & ~NSC:1 & NSC:2 & ~NSC:3)
    # (c & m==4)
    RL[::] &= mEven() & INV_NSC_2() & NSC_3()

    # (NSC:1 & ~NSC:2 & ~NSC:3)
    # | m==3
    RL[::] |= mOdd() & NSC_2() & INV_NSC_3()

    center[::] <= RL()



@belex_apl
def gol_in_section_danilan_2(Belex, petri_dish: VR):
    r"""Algorithm:

    One /generation/ in the Game of Life (GOL) is a transition
    from an initial state, c, to a final state c'. The symbols "c"
    stand for "cells."

    In this implementation on the APU, each state is a pattern of
    ON bits and OFF bits in a VR (vector register). A VR is a 16 x
    32,768 matrix of mutable bits, in 16 rows or /sections/ and
    32,768 columns or /plats/.

    Mathematically, state c is a matrix of immutable bits, the
    contents of a VR before a transition, and state c' is a matrix
    of immutable bits, the contents of the same VR after the
    transition. Thinking in terms of immutable matrices c and c'
    lets us reason mathematically about the algorithm for the
    transition. The contents of a VR change (mutate) by
    side-effect, but the values of the mathematical quantities c
    and c' are immutable.

    Interpret the ON bits as "live" and the OFF bits as "dead."
    That interpretation gives the Game of Life its picturesque
    name, which we can see in the following example, the Gosper
    Glider Gun, the first 30 plats of which look like this:

        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . 1 . . .
        . . . . . . . . . . . . . . . . . . . . . . . . 1 . 1 . . .
        . . . . . . . . . . . . . . 1 1 . . . . . . 1 1 . . . . . .
        . . . . . . . . . . . . . 1 . . . 1 . . . . 1 1 . . . . . .
        . . 1 1 . . . . . . . . 1 . . . . . 1 . . . 1 1 . . . . . .
        . . 1 1 . . . . . . . . 1 . . . 1 . 1 1 . . . . 1 . 1 . . .
        . . . . . . . . . . . . 1 . . . . . 1 . . . . . . . 1 . . .
        . . . . . . . . . . . . . 1 . . . 1 . . . . . . . . . . . .
        . . . . . . . . . . . . . . 1 1 . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

    Dots represent 0 or OFF, for clear visualization. After one
    generation, the first 30 plats of the final state c' look like
    this:

        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . 1 . . . . .
        . . . . . . . . . . . . . . . . . . . . . . 1 . 1 . . . . .
        . . . . . . . . . . . . . 1 . . . . . . . 1 . 1 . . . . . .
        . . . . . . . . . . . . 1 1 . . . . . . 1 . . 1 . . . . . .
        . 1 1 . . . . . . . . 1 1 . . . . 1 1 . . 1 . 1 . . . . . .
        . 1 1 . . . . . . . 1 1 1 . . . . 1 1 . . . 1 . 1 . . . . .
        . . . . . . . . . . . 1 1 . . . . 1 1 . . . . . 1 . . . . .
        . . . . . . . . . . . . 1 1 . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . 1 . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

    After 30 generations, the first 30 plats of the final state
    look like this:

        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . 1 . . . .
        . . . . . . . . . . . . . . . . . . . . . . . 1 . 1 . . . .
        . . . . . . . . . . . . . 1 1 . . . . . . 1 1 . . . . . . .
        . . . . . . . . . . . . 1 . . . 1 . . . . 1 1 . . . . . . .
        . 1 1 . . . . . . . . 1 . . . . . 1 . . . 1 1 . . . . . . .
        . 1 1 . . . . . . . . 1 . . . 1 . 1 1 . . . . 1 . 1 . . . .
        . . . . . . . . . . . 1 . . . . . 1 . . . . . . . 1 . . . .
        . . . . . . . . . . . . 1 . . . 1 . . . . . . . . . . . . .
        . . . . . . . . . . . . . 1 1 . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . 1 . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . 1 1 . . .
        . . . . . . . . . . . . . . . . . . . . . . . . 1 1 . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
        . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

    One might define an immutable mathematical variable c^30 or c
    with 30 tick marks to name this state.

    The small sub-pattern to the southeast of the main
    superstructure is a /glider/. This sub-pattern crawls further
    to the southeast as generations proceed. It appears first at
    generation 15 and has a sub-period of four, shifting one cell
    south and one cell east every sub-period. That shifting
    activity gives the name "glider" to that small sub-pattern.
    However, the main superstructure above the glider has returned
    to its original shape, as in initial state c. Every 30
    generations, the main superstructure emits a new glider, which
    chases the prior glider. In this implementation, with dead
    cells over the boundaries, the gliders annihilate against
    stable, 4x4 "block" patterns at the bottom right of the
    visualization.

    The upper superstructure is thus a "glider gun."

    To effect the transition, interpret ON bits as the integer 1
    and OFF bits as the integer 0. That interpretation lets us
    count the number of live and dead cells in a Moore
    neighborhood of every cell. A Moore neighborhood includes the
    diagonal neighbors, and thus has 8 elements. The standard
    rules for one generation of the GOL are often stated as
    follows:

    for each cell c:
        Compute Moore counts
            (count the number of live neighbors of c).
        If c is live:
            If there are 2 or 3 live neighbors:
                c' is live
            else:
                c' is dead due to overcrowding or loneliness
        else, if c is dead:
            If there are exactly 3 live neighbors:
                c' is live
            else:
                c' is dead

    The APU hardware does not have tests or jumps of any kind. APU
    microcode consists entirely of basic blocks called /frags/.
    Ordinary CPU code on the coprocessor or /ARC/ invokes frags
    within conditional logic and loops. Thus, we say the ARC
    implements /business logic/.

    In a straight-but-naive implementation of the code above, we
    would compute the Moore counts in the APU, pull the counts
    into the ARC, do the business logic there, then push the
    values of c' back into the APU for the next generation. The
    ARC code would have an outer loop over generations.

    In such a naive implementation, the I/O to pull the counts out
    and to push the new generation bits in would dominate
    execution time. That implementation would be I/O-bound.
    However, we can modify the business logic to keep all of it in
    the APU. First, modify the Moore counts to include the value
    of the center cell. We now remove the conditionals from the
    microcode. Denoting assignment with a single equals sign and a
    test with a double equals sign:

    for each cell c:
        Compute modified Moore counts m: number of live neighbors
            plus the value of c.
        If c == 1:
            If m == 3 or 4:
                c' = 1
            else:
                c' = 0
        else, if c == 0:
            If m == 3:
                c' = 1
            else:
                c' = 0

    A moment's thought or a truth table demonstrates that the
    above is equivalent to

    for each cell c:
        Compute modified Moore counts m: number of live neighbors
            plus the value of c.
        c' = ((m == 3) or (c & (m == 4)))
    """
    # Aliases to make the code understandable mathematically. The
    # Belex compiler will automatically allocate and recycle
    # (coalesce) physical VRs.
    c = petri_dish
    RL_c = RL                 # original center data point
    RL_C_0 = RL               # bit 0 of central row C
    e = Belex.VR()            # original east data point
    w = Belex.VR()            # original west data point
    C_0 = Belex.VR()          # bit 0 of central row C
    C_0_cout = Belex.VR()     # carry-out of computation of bit 0 of C
    N_0 = Belex.VR()          # bit 0 of sum of North row
    S_0 = Belex.VR()          # bit 0 of sum of South row
    mOdd = Belex.VR()        # bit 0 of 9-cell sum
    NSC_0_cout = Belex.VR()   # carry-out of computation of NSC
    mEven = Belex.VR()         # inverse of bit 0 of 9-cell sum
    N_0_cout = Belex.VR()
    S_0_cout = Belex.VR()
    NSC_1 = Belex.VR()
    NSC_1_cout = Belex.VR()
    NSC_2 = Belex.VR()
    NSC_2_cout = Belex.VR()
    INV_NSC_2 = Belex.VR()
    NSC_3 = Belex.VR()
    INV_NSC_3 = Belex.VR()

    # At this point, RL_c = c == center bit of the original game
    # state.
    RL_c[::] <= c()

    #  ___ _____ ___ ___   _
    # / __|_   _| __| _ \ / |
    # \__ \ | | | _||  _/ | |
    # |___/ |_| |___|_|   |_|

    e[::] <= ERL()
    w[::] <= WRL()
    fa_2(C_0, C_0_cout, c, e, w)

    # C_0 = e + w + c sum bit
    # C_0_cout = c&e | c&w | e&w

    #  ___ _____ ___ ___   ___
    # / __|_   _| __| _ \ |_  )
    # \__ \ | | | _||  _/  / /
    # |___/ |_| |___|_|   /___|

    RL_C_0[::] <= C_0()  # e + w + c, bit 0 of sum

    N_0[::] <= NRL() # N = ne + nw + n
    S_0[::] <= SRL() # S = se + sw + s
    fa_2(mOdd, NSC_0_cout, N_0, S_0, C_0)

    # NSC_0 has 9-cell sum bit 0; NSC_0_cout has 9-cell carry-out
    # of bit 0 sum.

    RL[::] <= mOdd()  # all nine cells, sum bit 0

    mEven[::] <= ~RL()  # The inverse of the 9-cell sum
    # bit 0 will determine whether NSC_0 is an odd number.

    #  ___ _____ ___ ___   ____
    # / __|_   _| __| _ \ |__ /
    # \__ \ | | | _||  _/  |_ \
    # |___/ |_| |___|_|   |___/

    RL[::] <= C_0_cout()  # e & w & c, carry bit

    N_0_cout[::] <= NRL()  # ne & nw & n, carry bit
    S_0_cout[::] <= SRL()  # se & sw & s, carry bit
    fa_2(NSC_1, NSC_1_cout, N_0_cout, S_0_cout, C_0_cout)

    #  ___ _____ ___ ___   _ _
    # / __|_   _| __| _ \ | | |
    # \__ \ | | | _||  _/ |_  _|
    # |___/ |_| |___|_|     |_|

    ha(NSC_2, NSC_2_cout, NSC_1, NSC_0_cout)

    # NSC_2 makes no implication about NSC:0, bit 0 of NSC.
    # NSC_2 <=> NSC:1
    # NSC_2 makes no implication about NSC:2.
    # NSC_2 => ~NSC:3; Converse is not true.

    RL[::] <= NSC_2()

    # Save the inverse of bit 2, NSC_2, of the 9-cell sum to
    # distinguish c == 3 from c == 4.

    INV_NSC_2[::] <= ~RL()

    #  ___ _____ ___ ___   ___
    # / __|_   _| __| _ \ | __|
    # \__ \ | | | _||  _/ |__ \
    # |___/ |_| |___|_|   |___/

    # qa == "quarter adder" because two of the statements are unused.
    # ---------------------------------------------------------------
    # TODO: Once the delete-dead-writes peephole is ported to
    # BLEIR, replace this with its half-adder relative:
    # ----------------------------------------
    # ha(NSC_2, NSC_2_cout, NSC_1, NSC_0_cout)
    # ----------------------------------------
    qa(NSC_3, NSC_1_cout, NSC_2_cout)

    # NSC_3 makes no implication about NSC:0, bit 0 of NSC.
    # NSC_3 makes no implication about NSC:1.
    # NSC_3 <=> NSC:2
    # NSC_3 => ~NSC:3; Converse is not true.

    RL[::] <= NSC_3()

    INV_NSC_3[::] <= ~RL()

    RL[::] <= c()
    # c & (mEven & ~NSC:1 & NSC:2 & ~NSC:3)
    # (c & m==4)
    RL[::] &= mEven() & INV_NSC_2() & NSC_3()

    # (NSC:1 & ~NSC:2 & ~NSC:3)
    # | m==3
    RL[::] |= mOdd() & NSC_2() & INV_NSC_3()

    # Overwrite the VR containing the game state.
    c[::] <= RL()


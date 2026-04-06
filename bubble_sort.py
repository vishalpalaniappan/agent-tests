"""
Bubble Sort implementation derived from bubble_sort_design.dal.

The design describes nine behaviors that form the algorithm's state machine:
  Initialize Sort -> BeginPass -> SelectAdjacentPair -> CompareAdjacentPair
    -> (Swap Adjacent Pair ->) AdvanceComparison
    -> (Complete Pass ->) Check Early Completion
    -> (Terminate Sort | BeginPass)

Participants (state variables) from the design:
  sequence       - the list being sorted
  pass_boundary  - upper exclusive bound of the unsorted region (shrinks each pass)
  current_index  - position of the left element of the current adjacent pair
  adjacent_pair  - the two elements currently under consideration
  swap_flag      - True if at least one swap occurred in the current pass
  ordering_rel   - comparison function that defines the desired order
"""


def bubble_sort(sequence, ordering_rel=lambda a, b: a > b):
    """Sort *sequence* in-place using the optimised bubble sort algorithm.

    Parameters
    ----------
    sequence:     list  - the list to sort (modified in-place).
    ordering_rel: callable(a, b) -> bool
                        - returns True when *a* should be swapped with *b*
                          (i.e. *a* is "out of order" relative to *b*).
                          Defaults to ascending order (swap when a > b).
    """

    # ── Behavior: Initialize Sort ─────────────────────────────────────────────
    # Participants: Sequence, Pass Boundary, Current Index, Swap Flag,
    #               Ordering Relation
    # Set up every participant before the first pass begins.
    pass_boundary = len(sequence)   # unsorted region is sequence[0:pass_boundary]
    current_index = 0
    swap_flag = False
    # ordering_rel is already bound via the function parameter
    # ─────────────────────────────────────────────────────────────────────────

    # A sequence of length 0 or 1 is already sorted; go straight to Terminate Sort.
    if pass_boundary <= 1:
        return sequence

    while True:
        # ── Behavior: BeginPass ───────────────────────────────────────────────
        # Participants: Current Index, Swap Flag, Pass Boundary
        # Reset the index and swap flag at the start of each left-to-right sweep.
        current_index = 0
        swap_flag = False
        # ─────────────────────────────────────────────────────────────────────

        while True:
            # ── Behavior: SelectAdjacentPair ──────────────────────────────────
            # Participants: Sequence, Current Index, Adjacent Pair, Pass Boundary
            # Identify the pair of elements at positions current_index and
            # current_index + 1 within the unsorted region.
            adjacent_pair = (sequence[current_index], sequence[current_index + 1])
            # ─────────────────────────────────────────────────────────────────

            # ── Behavior: CompareAdjacentPair ─────────────────────────────────
            # Participants: Adjacent Pair, Ordering Relation
            # Apply the ordering relation to decide whether a swap is needed.
            if ordering_rel(adjacent_pair[0], adjacent_pair[1]):
                # ── Behavior: Swap Adjacent Pair ──────────────────────────────
                # Participants: Adjacent Pair, Sequence, Swap Flag
                # The pair is out of order: exchange the elements and set the
                # swap flag so the pass is recorded as productive.
                sequence[current_index], sequence[current_index + 1] = (
                    adjacent_pair[1], adjacent_pair[0]
                )
                swap_flag = True
                # ─────────────────────────────────────────────────────────────

            # ── Behavior: AdvanceComparison ───────────────────────────────────
            # Participants: Current Index, Pass Boundary
            # Move one position to the right.  When we reach the pass boundary
            # the inner sweep is done; otherwise select the next adjacent pair.
            current_index += 1
            if current_index >= pass_boundary - 1:
                break           # -> Complete Pass
            # else -> SelectAdjacentPair (continue inner loop)
            # ─────────────────────────────────────────────────────────────────

        # ── Behavior: Complete Pass ───────────────────────────────────────────
        # Participants: Pass Boundary, Sequence
        # The largest unsorted element has bubbled to sequence[pass_boundary-1].
        # Shrink the boundary so subsequent passes skip that position.
        pass_boundary -= 1
        # ─────────────────────────────────────────────────────────────────────

        # ── Behavior: Check Early Completion ─────────────────────────────────
        # Participants: Swap Flag, Pass Boundary
        # If no swaps occurred the sequence is already sorted; we can stop.
        # If the unsorted region has collapsed to one element we are also done.
        if not swap_flag or pass_boundary <= 1:
            break               # -> Terminate Sort
        # else -> BeginPass (continue outer loop)
        # ─────────────────────────────────────────────────────────────────────

    # ── Behavior: Terminate Sort ──────────────────────────────────────────────
    # Participant: Sequence
    # The sequence is fully sorted; return it to the caller.
    return sequence
    # ─────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    examples = [
        [5, 3, 8, 1, 2],
        [1],
        [],
        [4, 4, 4],
        [9, 8, 7, 6, 5],
        [1, 2, 3, 4, 5],
    ]

    for lst in examples:
        result = bubble_sort(lst[:])   # pass a copy to leave the original intact for display
        print(f"sorted: {result}")

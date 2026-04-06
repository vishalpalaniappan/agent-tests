"""
Bubble Sort — state-machine implementation driven solely by bubble_sort_design.dal.

The design defines 9 behaviors (graph nodes) and a set of participants (state
variables).  This module implements each behavior as its own function and a
lightweight driver that walks the graph by following _goToBehaviorIds transitions.

Points where the design does not provide enough information to write the code are
marked DESIGN_AMBIGUITY.  Those points are called out in the PR for clarification;
the assumptions made here are the minimal ones needed to produce runnable code.

Participants extracted from the design:
  sequence        - the list being sorted           (Sequence)
  pass_boundary   - upper bound of the unsorted region (Pass Boundary)
  current_index   - left position of the active pair  (Current Index)
  adjacent_pair   - the two elements under comparison  (Adjacent Pair)
  swap_flag       - whether a swap occurred this pass  (Swap Flag)
  ordering_rel    - decides when two elements are out of order (Ordering Relation)
"""

from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# State object — one field per design participant
# ---------------------------------------------------------------------------

class _SortState:
    """Holds every participant declared in the design."""

    def __init__(self, sequence: list, ordering_rel: Callable[[Any, Any], bool]) -> None:
        self.sequence: list = sequence
        self.ordering_rel: Callable[[Any, Any], bool] = ordering_rel
        # These are deliberately left uninitialised here; Initialize Sort sets them.
        self.pass_boundary: Optional[int] = None
        self.current_index: Optional[int] = None
        self.adjacent_pair: Optional[tuple] = None
        self.swap_flag: Optional[bool] = None


# ---------------------------------------------------------------------------
# Behavior functions — one per design node
# ---------------------------------------------------------------------------

def _initialize_sort(s: _SortState) -> str:
    """
    Behavior: Initialize Sort  (atomic=true)
    Participants: Sequence, Pass Boundary, Current Index, Swap Flag, Ordering Relation
    Description:  (none provided in the design)
    Transitions to: BeginPass

    DESIGN_AMBIGUITY: The design lists five participants but provides no description,
    so the initial values of Pass Boundary, Current Index, and Swap Flag are not
    specified.  Assumption: pass_boundary = len(sequence) — the entire sequence
    is unsorted at the start.  Current Index and Swap Flag are left for BeginPass
    to initialise (as that behavior's description explicitly states their starting
    values).
    """
    s.pass_boundary = len(s.sequence)  # DESIGN_AMBIGUITY: value not stated in design
    return "BeginPass"


def _begin_pass(s: _SortState) -> str:
    """
    Behavior: BeginPass
    Participants: Current Index, Swap Flag, Pass Boundary
    Description:  "Start processing an unsorted portion, swap is false, index is 0."
    Transitions to: SelectAdjacentPair
    """
    s.current_index = 0
    s.swap_flag = False
    return "SelectAdjacentPair"


def _select_adjacent_pair(s: _SortState) -> str:
    """
    Behavior: SelectAdjacentPair
    Participants: Sequence, Current Index, Adjacent Pair, Pass Boundary
    Description:  "Select the pair to compare."
    Transitions to: CompareAdjacentPair
    """
    i = s.current_index
    s.adjacent_pair = (s.sequence[i], s.sequence[i + 1])
    return "CompareAdjacentPair"


def _compare_adjacent_pair(s: _SortState) -> str:
    """
    Behavior: CompareAdjacentPair
    Participants: Adjacent Pair, Ordering Relation
    Description:  "Compare the selected pair."
    Transitions to: SwapAdjacentPair  OR  AdvanceComparison
    """
    if s.ordering_rel(s.adjacent_pair[0], s.adjacent_pair[1]):
        return "SwapAdjacentPair"
    return "AdvanceComparison"


def _swap_adjacent_pair(s: _SortState) -> str:
    """
    Behavior: Swap Adjacent Pair
    Participants: Adjacent Pair, Sequence, Swap Flag
    Description:  "Swap the unordered elements. Swap flag becomes true."
    Transitions to: AdvanceComparison
    """
    i = s.current_index
    s.sequence[i], s.sequence[i + 1] = s.adjacent_pair[1], s.adjacent_pair[0]
    s.swap_flag = True
    return "AdvanceComparison"


def _advance_comparison(s: _SortState) -> str:
    """
    Behavior: AdvanceComparison
    Participants: Current Index, Pass Boundary
    Description:  "Move to the next adjacent pair in the current pass."
    Transitions to: CompletePass  OR  SelectAdjacentPair

    DESIGN_AMBIGUITY: The design says to move to the next adjacent pair and that
    the participants are Current Index and Pass Boundary, but the exact condition
    that triggers the transition to CompletePass (vs continuing) is not stated.
    Assumption: increment current_index; if there is no room for another adjacent
    pair before pass_boundary, the pass is complete.
    """
    s.current_index += 1
    # DESIGN_AMBIGUITY: exact boundary condition not specified in design
    if s.current_index >= s.pass_boundary - 1:
        return "CompletePass"
    return "SelectAdjacentPair"


def _complete_pass(s: _SortState) -> str:
    """
    Behavior: Complete Pass
    Participants: Pass Boundary, Sequence
    Description:  "Conclude one full left-to-right sweep."
    Transitions to: CheckEarlyCompletion

    DESIGN_AMBIGUITY: The design lists Pass Boundary as a participant and says the
    sweep is concluded, but does not specify how Pass Boundary changes.  Assumption:
    pass_boundary decrements by 1 — one more position at the end of the sequence
    is now in its final sorted place.
    """
    s.pass_boundary -= 1  # DESIGN_AMBIGUITY: change amount not specified in design
    return "CheckEarlyCompletion"


def _check_early_completion(s: _SortState) -> str:
    """
    Behavior: Check Early Completion
    Participants: Swap Flag, Pass Boundary
    Description:  "Determine whether sorting can stop early."
    Transitions to: TerminateSort  OR  BeginPass
    """
    if not s.swap_flag or s.pass_boundary <= 1:
        return "TerminateSort"
    return "BeginPass"


def _terminate_sort(s: _SortState) -> Optional[str]:
    """
    Behavior: Terminate Sort
    Participants: Sequence
    Description:  "Finish Process"
    Transitions to: (terminal — no outgoing edges in design)
    """
    return None  # signals the driver to stop


# ---------------------------------------------------------------------------
# State-machine driver — mirrors the _goToBehaviorIds graph in the design
# ---------------------------------------------------------------------------

_BEHAVIORS: dict[str, Callable[[_SortState], Optional[str]]] = {
    "InitializeSort":       _initialize_sort,
    "BeginPass":            _begin_pass,
    "SelectAdjacentPair":   _select_adjacent_pair,
    "CompareAdjacentPair":  _compare_adjacent_pair,
    "SwapAdjacentPair":     _swap_adjacent_pair,
    "AdvanceComparison":    _advance_comparison,
    "CompletePass":         _complete_pass,
    "CheckEarlyCompletion": _check_early_completion,
    "TerminateSort":        _terminate_sort,
}


def bubble_sort(
    sequence: list,
    ordering_rel: Callable[[Any, Any], bool] = lambda a, b: a > b,
) -> list:
    """Sort *sequence* in-place by executing the state machine from bubble_sort_design.dal.

    Parameters
    ----------
    sequence:     The list to sort (modified in-place).
    ordering_rel: Returns True when the first argument should be swapped with the second.
                  Defaults to ascending order (swap when a > b).
    """
    # Edge case: a sequence of 0 or 1 elements needs no sorting.
    # The design does not model this explicitly; Initialize Sort would set
    # pass_boundary = 0 or 1, and BeginPass would immediately attempt to read
    # sequence[0] and sequence[1] in SelectAdjacentPair — which would be out of
    # bounds.  We short-circuit here and go straight to Terminate Sort.
    if len(sequence) <= 1:
        return sequence

    state = _SortState(sequence, ordering_rel)
    current_behavior: Optional[str] = "InitializeSort"

    while current_behavior is not None:
        current_behavior = _BEHAVIORS[current_behavior](state)

    return state.sequence


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------

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
        original = lst[:]
        result = bubble_sort(lst)
        print(f"input: {original} → sorted: {result}")

#!/usr/bin/env python3
# Requires Python 3.8+
"""
Library Manager

Implemented from library_manager_design.dal, which defines three atomic graphs:

  1. AcceptBook        - User adds a book (name + genre) to the basket.
  2. PlaceBookOnShelf  - Librarian shelves every basket book, grouped by first letter.
  3. AuditLibrary      - Librarian generates and hands an audit report to the user.

Each graph is entered through an *atomic* behavior (a menu choice) and proceeds
through its subsequent behaviors in sequence.  Invariants declared in the design
are enforced at the point they are introduced (e.g. Book Name Length >= 1).
"""
from __future__ import annotations

from typing import Dict
from typing import List
from typing import Optional


# ---------------------------------------------------------------------------
# State shared across graphs (in-memory for the session)
# ---------------------------------------------------------------------------

basket: List[Dict] = []
shelf: Dict[str, List[Dict]] = {}


# ---------------------------------------------------------------------------
# Graph 1 - AcceptBook
# Behaviors: AcceptChoiceToAddBookToBasket -> AcceptBookFromUser -> AddBookToBasket
# ---------------------------------------------------------------------------


def accept_choice_to_add_book_to_basket() -> bool:
    """Atomic entry behavior.

    Participants: Choice, User, Librarian.
    The user expresses the choice to add a book; the librarian accepts it.
    Returns True when the user confirms, False to cancel.
    """
    print("\n=== Add a Book to the Basket ===")
    raw_answer = input("Proceed? (y/n): ")
    stripped_answer = raw_answer.strip()
    lowered_answer = stripped_answer.lower()
    confirmed = lowered_answer == "y"
    return confirmed


def accept_book_from_user() -> Dict:
    """Accept book details from the user.

    Participant - Book with invariant:
        Book Name Length: name must have minimum length of 1.
    """
    name_is_valid = False
    name = ""
    while not name_is_valid:
        raw_name = input("Book name: ")
        name = raw_name.strip()
        name_length = len(name)
        # Invariant: Book Name Length - min_length = 1
        if name_length < 1:
            print("  [!] Book name must be at least 1 character. Please try again.")
        else:
            name_is_valid = True
    raw_genre = input("Book genre: ")
    genre = raw_genre.strip()
    book = {"name": name, "genre": genre}
    return book


def add_book_to_basket(book: Dict) -> None:
    """Place the accepted book in the basket."""
    basket.append(book)
    book_name = book["name"]
    print(f"  '{book_name}' added to the basket.")


def run_accept_book() -> None:
    """Execute the AcceptBook graph."""
    confirmed = accept_choice_to_add_book_to_basket()
    if confirmed:
        book = accept_book_from_user()
        add_book_to_basket(book)


# ---------------------------------------------------------------------------
# Graph 2 - PlaceBookOnShelf
# Behaviors: AcceptChoiceToPlaceBooksOnShelf -> GetBookFromBasket ->
#            GetFirstLetterOfBookName -> [CreateSlotOnBookShelf ->] AddBookToShelf
#            (loops back to GetBookFromBasket until basket is empty)
# ---------------------------------------------------------------------------


def accept_choice_to_place_books_on_shelf() -> bool:
    """Atomic entry behavior.

    The librarian accepts the choice to place all basket books on the shelf.
    """
    print("\n=== Place Books on the Shelf ===")
    basket_is_empty = len(basket) == 0
    if basket_is_empty:
        print("  The basket is empty - nothing to shelve.")
        return False
    basket_count = len(basket)
    print(f"  {basket_count} book(s) in basket.")
    raw_answer = input("Proceed? (y/n): ")
    stripped_answer = raw_answer.strip()
    lowered_answer = stripped_answer.lower()
    confirmed = lowered_answer == "y"
    return confirmed


def get_book_from_basket() -> Optional[Dict]:
    """Retrieve the next book from the basket; returns None when empty."""
    basket_is_empty = len(basket) == 0
    if basket_is_empty:
        return None
    book = basket.pop(0)
    return book


def get_first_letter_of_book_name(book: Dict) -> str:
    """Read the first letter of the book's name."""
    book_name = book.get("name")
    if not book_name:
        error_message = f"Book has an empty name: {book!r}"
        raise ValueError(error_message)
    first_letter = book_name[0]
    first_letter_upper = first_letter.upper()
    return first_letter_upper


def create_slot_on_book_shelf(letter: str) -> None:
    """Create a shelf slot for *letter* if one does not already exist."""
    slot_already_exists = letter in shelf
    if not slot_already_exists:
        shelf[letter] = []
        print(f"  Created shelf slot '{letter}'.")


def add_book_to_shelf(book: Dict, letter: str) -> None:
    """Add the book to the shelf slot identified by *letter*."""
    shelf[letter].append(book)
    book_name = book["name"]
    print(f"  '{book_name}' shelved under '{letter}'.")


def run_place_book_on_shelf() -> None:
    """Execute the PlaceBookOnShelf graph."""
    confirmed = accept_choice_to_place_books_on_shelf()
    if not confirmed:
        return

    all_shelved = False
    while not all_shelved:
        # GetBookFromBasket
        book = get_book_from_basket()
        basket_is_now_empty = book is None
        if basket_is_now_empty:
            print("  All books have been shelved.")
            all_shelved = True
        else:
            # GetFirstLetterOfBookName
            letter = get_first_letter_of_book_name(book)
            # CreateSlotOnBookShelf (only when slot is missing)
            create_slot_on_book_shelf(letter)
            # AddBookToShelf
            add_book_to_shelf(book, letter)
            # loop back to GetBookFromBasket


# ---------------------------------------------------------------------------
# Graph 3 - AuditLibrary
# Behaviors: AcceptChoiceToAuditLibrary -> GenerateAuditReport -> HandAuditToUser
# ---------------------------------------------------------------------------


def accept_choice_to_audit_library() -> bool:
    """Atomic entry behavior.

    The librarian accepts the choice to audit the library.
    """
    print("\n=== Audit the Library ===")
    raw_answer = input("Proceed? (y/n): ")
    stripped_answer = raw_answer.strip()
    lowered_answer = stripped_answer.lower()
    confirmed = lowered_answer == "y"
    return confirmed


def generate_audit_report() -> Dict:
    """Generate the audit report from the current shelf state."""
    sorted_shelf_letters = sorted(shelf.keys())
    sorted_shelf: Dict[str, List[Dict]] = {}
    for letter in sorted_shelf_letters:
        books_on_letter_slot = shelf[letter]
        sorted_shelf[letter] = books_on_letter_slot
    basket_count = len(basket)
    report = {"shelf": sorted_shelf, "basket_count": basket_count}
    return report


def hand_audit_to_user(report: Dict) -> None:
    """Display the audit report to the user."""
    print("\n--- Audit Report ---")
    shelf_data = report["shelf"]
    shelf_is_empty = len(shelf_data) == 0
    if shelf_is_empty:
        print("  The shelf is empty.")
    else:
        for letter in shelf_data:
            print(f"  [{letter}]")
            books_in_slot = shelf_data[letter]
            for book in books_in_slot:
                book_name = book["name"]
                book_genre = book["genre"]
                print(f"    - {book_name}  ({book_genre})")
    basket_count = report["basket_count"]
    print(f"\n  Basket: {basket_count} book(s) awaiting shelving.")
    print("--------------------")


def run_audit_library() -> None:
    """Execute the AuditLibrary graph."""
    confirmed = accept_choice_to_audit_library()
    if confirmed:
        report = generate_audit_report()
        hand_audit_to_user(report)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print("Library Manager")

    running = True
    while running:
        print("\n--- Menu ---")
        print("  1. Add a book to the basket  (AcceptBook)")
        print("  2. Place books on the shelf  (PlaceBookOnShelf)")
        print("  3. Audit the library         (AuditLibrary)")
        print("  4. Exit")
        raw_choice = input("Choice: ")
        choice = raw_choice.strip()

        if choice == "1":
            run_accept_book()
        elif choice == "2":
            run_place_book_on_shelf()
        elif choice == "3":
            run_audit_library()
        elif choice == "4":
            print("Goodbye!")
            running = False
        else:
            print("  Invalid choice. Please enter 1-4.")


if __name__ == "__main__":
    main()

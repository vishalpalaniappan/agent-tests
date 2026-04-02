#!/usr/bin/env python3
"""
Library Manager

Implemented from library_manager_design.dal, which defines three atomic graphs:

  1. AcceptBook        — User adds a book (name + genre) to the basket.
  2. PlaceBookOnShelf  — Librarian shelves every basket book, grouped by first letter.
  3. AuditLibrary      — Librarian generates and hands an audit report to the user.

Each graph is entered through an *atomic* behavior (a menu choice) and proceeds
through its subsequent behaviors in sequence.  Invariants declared in the design
are enforced at the point they are introduced (e.g. Book Name Length ≥ 1).
"""


# ---------------------------------------------------------------------------
# State shared across graphs (in-memory for the session)
# ---------------------------------------------------------------------------
basket: list[dict] = []   # books waiting to be shelved
shelf: dict[str, list[dict]] = {}   # first-letter → [books]


# ---------------------------------------------------------------------------
# Graph 1 – AcceptBook
# Behaviors: AcceptChoiceToAddBookToBasket → AcceptBookFromUser → AddBookToBasket
# ---------------------------------------------------------------------------

def accept_choice_to_add_book_to_basket() -> bool:
    """Atomic entry behavior.

    Participants: Choice, User, Librarian.
    The user expresses the choice to add a book; the librarian accepts it.
    Returns True when the user confirms, False to cancel.
    """
    print("\n=== Add a Book to the Basket ===")
    answer = input("Proceed? (y/n): ").strip().lower()
    return answer == "y"


def accept_book_from_user() -> dict:
    """Accept book details from the user.

    Participant – Book with invariant:
        Book Name Length: name must have minimum length of 1.
    """
    while True:
        name = input("Book name: ").strip()
        # Invariant: Book Name Length – min_length = 1
        if len(name) < 1:
            print("  [!] Book name must be at least 1 character. Please try again.")
            continue
        break
    genre = input("Book genre: ").strip()
    return {"name": name, "genre": genre}


def add_book_to_basket(book: dict) -> None:
    """Place the accepted book in the basket."""
    basket.append(book)
    print(f"  ✓ '{book['name']}' added to the basket.")


def run_accept_book() -> None:
    """Execute the AcceptBook graph."""
    if not accept_choice_to_add_book_to_basket():
        return
    book = accept_book_from_user()
    add_book_to_basket(book)


# ---------------------------------------------------------------------------
# Graph 2 – PlaceBookOnShelf
# Behaviors: AcceptChoiceToPlaceBooksOnShelf → GetBookFromBasket →
#            GetFirstLetterOfBookName → [CreateSlotOnBookShelf →] AddBookToShelf
#            (loops back to GetBookFromBasket until basket is empty)
# ---------------------------------------------------------------------------

def accept_choice_to_place_books_on_shelf() -> bool:
    """Atomic entry behavior.

    The librarian accepts the choice to place all basket books on the shelf.
    """
    print("\n=== Place Books on the Shelf ===")
    if not basket:
        print("  The basket is empty — nothing to shelve.")
        return False
    print(f"  {len(basket)} book(s) in basket.")
    answer = input("Proceed? (y/n): ").strip().lower()
    return answer == "y"


def get_book_from_basket() -> dict | None:
    """Retrieve the next book from the basket; returns None when empty."""
    if not basket:
        return None
    return basket.pop(0)


def get_first_letter_of_book_name(book: dict) -> str:
    """Read the first letter of the book's name."""
    if not book.get("name"):
        raise ValueError(f"Book has an empty name: {book!r}")
    return book["name"][0].upper()


def create_slot_on_book_shelf(letter: str) -> None:
    """Create a shelf slot for *letter* if one does not already exist."""
    if letter not in shelf:
        shelf[letter] = []
        print(f"  Created shelf slot '{letter}'.")


def add_book_to_shelf(book: dict, letter: str) -> None:
    """Add the book to the shelf slot identified by *letter*."""
    shelf[letter].append(book)
    print(f"  ✓ '{book['name']}' shelved under '{letter}'.")


def run_place_book_on_shelf() -> None:
    """Execute the PlaceBookOnShelf graph."""
    if not accept_choice_to_place_books_on_shelf():
        return

    # GetBookFromBasket → loop
    while True:
        book = get_book_from_basket()
        if book is None:
            print("  All books have been shelved.")
            break

        # GetFirstLetterOfBookName
        letter = get_first_letter_of_book_name(book)

        # CreateSlotOnBookShelf (only when slot is missing) → AddBookToShelf
        create_slot_on_book_shelf(letter)
        add_book_to_shelf(book, letter)
        # → back to GetBookFromBasket


# ---------------------------------------------------------------------------
# Graph 3 – AuditLibrary
# Behaviors: AcceptChoiceToAuditLibrary → GenerateAuditReport → HandAuditToUser
# ---------------------------------------------------------------------------

def accept_choice_to_audit_library() -> bool:
    """Atomic entry behavior.

    The librarian accepts the choice to audit the library.
    """
    print("\n=== Audit the Library ===")
    answer = input("Proceed? (y/n): ").strip().lower()
    return answer == "y"


def generate_audit_report() -> dict:
    """Generate the audit report from the current shelf state."""
    return {
        "shelf": {letter: books for letter, books in sorted(shelf.items())},
        "basket_count": len(basket),
    }


def hand_audit_to_user(report: dict) -> None:
    """Display the audit report to the user."""
    print("\n--- Audit Report ---")
    if not report["shelf"]:
        print("  The shelf is empty.")
    else:
        for letter, books in report["shelf"].items():
            print(f"  [{letter}]")
            for book in books:
                print(f"    • {book['name']}  ({book['genre']})")
    print(f"\n  Basket: {report['basket_count']} book(s) awaiting shelving.")
    print("--------------------")


def run_audit_library() -> None:
    """Execute the AuditLibrary graph."""
    if not accept_choice_to_audit_library():
        return
    report = generate_audit_report()
    hand_audit_to_user(report)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("╔══════════════════════════╗")
    print("║    Library Manager       ║")
    print("╚══════════════════════════╝")

    menu = {
        "1": ("Add a book to the basket  (AcceptBook)", run_accept_book),
        "2": ("Place books on the shelf  (PlaceBookOnShelf)", run_place_book_on_shelf),
        "3": ("Audit the library         (AuditLibrary)", run_audit_library),
        "4": ("Exit", None),
    }

    while True:
        print("\n--- Menu ---")
        for key, (label, _) in menu.items():
            print(f"  {key}. {label}")
        choice = input("Choice: ").strip()

        if choice == "4":
            print("Goodbye!")
            break
        if choice in menu:
            _, action = menu[choice]
            if action:
                action()
        else:
            print("  Invalid choice. Please enter 1–4.")


if __name__ == "__main__":
    main()

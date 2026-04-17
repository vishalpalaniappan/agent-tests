import sys


def log_transition(behavior_name, participants):
    """Log a behavior transition with participant variable values."""
    parts = ", ".join(f"{k}={repr(v)}" for k, v in participants.items())
    print(f"[{behavior_name}] {parts}" if parts else f"[{behavior_name}]")


def AcceptString():
    """AcceptString (atomic): String to check to see if it is a palindrome."""
    stringToCheck = input("Enter a string to check: ")
    log_transition("AcceptString", {"stringToCheck": stringToCheck})
    return stringToCheck


def InitLeftPosition(stringToCheck):
    """InitLeftPosition: Sets the left position to 0."""
    leftPosition = 0
    log_transition("InitLeftPosition", {"stringToCheck": stringToCheck, "leftPosition": leftPosition})
    return leftPosition


def InitRightPosition(stringToCheck):
    """InitRightPosition: Initializes the right position to be the right most character in the string."""
    rightPosition = len(stringToCheck) - 1
    log_transition("InitRightPosition", {"stringToCheck": stringToCheck, "rightPosition": rightPosition})
    return rightPosition


def CheckIfLeftCrossedRight(leftPosition, rightPosition):
    """CheckIfLeftCrossedRight: Checks if the left position is equal to or greater than the right position."""
    crossed = leftPosition >= rightPosition
    log_transition("CheckIfLeftCrossedRight", {"leftPosition": leftPosition, "rightPosition": rightPosition})
    return crossed


def _GetLeftValue(stringToCheck, leftPosition):
    """_GetLeftValue: Gets the character at the left position in the string."""
    leftValue = stringToCheck[leftPosition]
    log_transition("_GetLeftValue", {"stringToCheck": stringToCheck, "leftPosition": leftPosition, "leftValue": leftValue})
    return leftValue


def _GetRightValue(stringToCheck, rightPosition):
    """_GetRightValue: Gets the character at the right position in the string."""
    rightValue = stringToCheck[rightPosition]
    log_transition("_GetRightValue", {"stringToCheck": stringToCheck, "rightPosition": rightPosition, "rightValue": rightValue})
    return rightValue


def _CheckIfEqual(leftValue, rightValue):
    """_CheckIfEqual: Checks if the left value and the right value are equal."""
    equal = leftValue == rightValue
    log_transition("_CheckIfEqual", {"leftValue": leftValue, "rightValue": rightValue, "equal": equal})
    return equal


def _IncrementLeftPosition(leftPosition):
    """_IncrementLeftPosition: Increments the left position since characters at the previous left and right position were both equal."""
    leftPosition += 1
    log_transition("_IncrementLeftPosition", {"leftPosition": leftPosition})
    return leftPosition


def _DecrementRightPosition(rightPosition):
    """_DecrementRightPosition: Decrements the right position since characters at the previous left and right position were both equal."""
    rightPosition -= 1
    log_transition("_DecrementRightPosition", {"rightPosition": rightPosition})
    return rightPosition


def _MarkAsPalindrome():
    """_MarkAsPalindrome: Marks the string as palindrome because left has crossed right and all the characters were equal."""
    isPalindrome = True
    log_transition("_MarkAsPalindrome", {})
    return isPalindrome


def _MarkAsNotAPalindrome():
    """_MarkAsNotAPalindrome: Mark the string as not a palindrome because left and right were not equal."""
    isPalindrome = False
    log_transition("_MarkAsNotAPalindrome", {})
    return isPalindrome


def _ShowResults(isPalindrome):
    """_ShowResults: Print the results (if it is a palindrome) to the screen."""
    log_transition("_ShowResults", {"isPalindrome": isPalindrome})
    if isPalindrome:
        print("Result: The string IS a palindrome.")
    else:
        print("Result: The string is NOT a palindrome.")


def main():
    # AcceptString (atomic): get the string to check
    stringToCheck = AcceptString()

    # InitLeftPosition: set left pointer to start of string
    leftPosition = InitLeftPosition(stringToCheck)

    # InitRightPosition: set right pointer to end of string
    rightPosition = InitRightPosition(stringToCheck)

    # Main loop: CheckIfLeftCrossedRight → either MarkAsPalindrome or continue comparing
    while True:
        if CheckIfLeftCrossedRight(leftPosition, rightPosition):
            # left has reached or crossed right with all chars equal → palindrome
            isPalindrome = _MarkAsPalindrome()
            break

        # GetLeftValue and GetRightValue
        leftValue = _GetLeftValue(stringToCheck, leftPosition)
        rightValue = _GetRightValue(stringToCheck, rightPosition)

        # CheckIfEqual → either continue or mark not palindrome
        if _CheckIfEqual(leftValue, rightValue):
            leftPosition = _IncrementLeftPosition(leftPosition)
            rightPosition = _DecrementRightPosition(rightPosition)
        else:
            isPalindrome = _MarkAsNotAPalindrome()
            break

    # ShowResults: print the result
    _ShowResults(isPalindrome)


if __name__ == "__main__":
    main()

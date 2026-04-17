def b_AcceptString(stringToCheck):
    """AcceptString (atomic): String to check to see if it is a palindrome."""
    return str(stringToCheck)


def b_InitLeftPosition(stringToCheck):
    """InitLeftPosition: Sets the left position to 0."""
    leftPosition = 0
    return leftPosition


def b_InitRightPosition(stringToCheck):
    """InitRightPosition: Initializes the right position to be the right most character in the string."""
    rightPosition = len(stringToCheck) - 1
    return rightPosition


def b_CheckIfLeftCrossedRight(leftPosition, rightPosition):
    """CheckIfLeftCrossedRight: Checks if the left position is equal to or greater than the right position."""
    crossed = leftPosition >= rightPosition
    return crossed


def b__GetLeftValue(stringToCheck, leftPosition):
    """_GetLeftValue: Gets the character at the left position in the string."""
    leftValue = stringToCheck[leftPosition]
    return leftValue


def b__GetRightValue(stringToCheck, rightPosition):
    """_GetRightValue: Gets the character at the right position in the string."""
    rightValue = stringToCheck[rightPosition]
    return rightValue


def b__CheckIfEqual(leftValue, rightValue):
    """_CheckIfEqual: Checks if the left value and the right value are equal."""
    equal = leftValue == rightValue
    return equal


def b__IncrementLeftPosition(leftPosition):
    """_IncrementLeftPosition: Increments the left position since characters at the previous left and right position were both equal."""
    leftPosition += 1
    return leftPosition


def b__DecrementRightPosition(rightPosition):
    """_DecrementRightPosition: Decrements the right position since characters at the previous left and right position were both equal."""
    rightPosition -= 1
    return rightPosition


def b__MarkAsPalindrome():
    """_MarkAsPalindrome: Marks the string as palindrome because left has crossed right and all the characters were equal."""
    isPalindrome = True
    return isPalindrome


def b__MarkAsNotAPalindrome():
    """_MarkAsNotAPalindrome: Mark the string as not a palindrome because left and right were not equal."""
    isPalindrome = False
    return isPalindrome


def b__ShowResults(isPalindrome):
    """_ShowResults: Print the results (if it is a palindrome) to the screen."""
    if isPalindrome:
        print("Result: The string IS a palindrome.")
    else:
        print("Result: The string is NOT a palindrome.")


def main(stringToCheck):
    # AcceptString (atomic): get the string to check
    stringToCheck = b_AcceptString(stringToCheck)

    # InitLeftPosition: set left pointer to start of string
    leftPosition = b_InitLeftPosition(stringToCheck)

    # InitRightPosition: set right pointer to end of string
    rightPosition = b_InitRightPosition(stringToCheck)

    # Main loop: CheckIfLeftCrossedRight → either MarkAsPalindrome or continue comparing
    while True:
        if b_CheckIfLeftCrossedRight(leftPosition, rightPosition):
            # left has reached or crossed right with all chars equal → palindrome
            isPalindrome = b__MarkAsPalindrome()
            break

        # GetLeftValue and GetRightValue
        leftValue = b__GetLeftValue(stringToCheck, leftPosition)
        rightValue = b__GetRightValue(stringToCheck, rightPosition)

        # CheckIfEqual → either continue or mark not palindrome
        if b__CheckIfEqual(leftValue, rightValue):
            leftPosition = b__IncrementLeftPosition(leftPosition)
            rightPosition = b__DecrementRightPosition(rightPosition)
        else:
            isPalindrome = b__MarkAsNotAPalindrome()
            break

    # ShowResults: print the result
    b__ShowResults(isPalindrome)


if __name__ == "__main__":
    stringToCheck = input("Enter a string to check: ")
    main(stringToCheck)

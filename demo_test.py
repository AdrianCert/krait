def longest_ones_sequence_start(input):
    """
    Finds the starting index of the maximum sequence of consecutive 1's in the given list.

    Parameters
    ----------
    input : list of int
        A list of integers containing 0's and 1's.

    Returns
    -------
    int
        The starting index of the maximum sequence of consecutive 1's.
        If there are multiple sequences of the same length, returns the starting index of the last one.
        Returns -1 if there are no 1's in the list.
    """
    n = len(input)
    i = n - 1
    result = -1
    maximal = 0
    k = 0
    while i > 0:
        if input[i] == 1:
            k = k + 1
            if k >= maximal:
                maximal = k
                result = i
        else:
            k = 0
        i = i - 1
    if input[i] == 1 and k + 1 >= maximal:
        result = 0
    return result


if __name__ == "__main__":
    print(longest_ones_sequence_start([1, 1, 1, 0, 1, 1, 1]))

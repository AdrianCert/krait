# you can write to stdout for debugging purposes, e.g.
# print("this is a debug message")


def solution2(S):
    encoded = [ord(c) - ord("A") for c in S]
    # res
    n = len(S)
    ne_r = list(range(1, n))
    ne_l = list(range(n - 1))
    ne_r.append(-1)
    i = 0
    start = 0
    while i < n:
        curr_r = ne_r[i]
        if curr_r == -1:
            break
        print("*", *ne_l)
        print(*("-" * i), "|")
        print(*ne_r, "*")
        print(":" * 3 * n)
        near = encoded[curr_r]
        curr = encoded[i]
        if near + curr in [1, 5]:
            near_r = ne_r[curr_r]
            ne_r[i] = near_r
            if start == i:
                start = i = near_r
                continue
            else:
                i = near_l = ne_l[i - 1]
                ne_r[near_l] = near_r
                ne_l[near_r] = near_l
                continue
            # # res.pop(neb[n])
            # if start == i:
            #     pass

            # ne_r[near_l] = near_r
            # ne_l[near_l] = near_l
            # # go back
            # i = ne_l[near_l]
            # continue

        i = curr_r

    return len(ne_r)


def print_state(x):
    print("".join([chr(c + ord("A")) for c in x]))


def solution(S):
    encoded = [ord(c) - ord("A") for c in S]
    n = len(S)
    i = n - 1
    while i > 1:
        curr = encoded[i]
        near = encoded[i - 1]
        if near + curr in [1, 5]:
            encoded.pop(i)
            encoded.pop(i - 1)
            n -= 2
            i -= 2
            i = max(i, n - 1)
        else:
            i -= 1

    return "".join([chr(c + ord("A")) for c in encoded])


print(solution("CBACD"))
print(solution("CABACDB"))

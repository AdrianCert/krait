"""
showcase of hashing with krait.hashing.hash_extended.

RUN: python packages/lib/examples/hashing.py

"""

from krait.introspect import hash_extended

if __name__ == "__main__":
    from dataclasses import dataclass

    @dataclass
    class Point:
        """Represent a point in 2D space."""

        x: int
        y: int

        # def __init__(self, x, y):
        #     self.x = x
        #     self.y = y

    dict3 = {
        "name": "George",
        "age": 30,
        "details": {
            "city": "New York",
            "hobbies": ["reading", "traveling"],
            "scores": {"math": 95, "science": 90},
        },
        "friends": [],
    }

    dict1 = {
        "name": "Alice",
        "age": 30,
        "details": {
            "city": "New York",
            "hobbies": ["reading", "traveling"],
            "scores": {"math": 95, "science": 90},
        },
        "friends": [dict3],
        "location": Point(10, 20),
        "tags": ["python", "developer"],
    }

    dict2 = {
        "tags": ["python", "developer"],
        "age": 30,
        "details": {
            "scores": {"science": 90, "math": 95},  # Order changed
            "hobbies": ["traveling", "reading"],
            "city": "New York",
        },
        "friends": [dict3],
        "location": Point(10, 20),
        "name": "Alice",
    }

    dict3["friends"].append(dict1)
    dict3["friends"].append(dict2)

    # class Point2:
    #     x: int
    #     y: int

    #     def __init__(self, x, y):
    #         self.x = x
    #         self.y = y

    import timeit

    x1 = Point(10, 20)
    x2 = Point(10, 20)
    print(
        "Hashing x1 and x2:",
        hash_extended(x1),
        hash_extended(x2),
        hash_extended(x1) == hash_extended(x2),
    )

    print("Hashing dict1 and dict2:", hash_extended(dict1), hash_extended(dict2))

    print(
        "Hashing dict1 and dict2:",
        hash_extended(dict1),
        hash_extended(dict2),
        hash_extended(dict1) == hash_extended(dict2),
    )

    cache = {}

    print(
        timeit.timeit(
            lambda: hash_extended(10, _cache=cache)
            == hash_extended(dict2, _cache=cache),
            number=1_000,
        )
    )

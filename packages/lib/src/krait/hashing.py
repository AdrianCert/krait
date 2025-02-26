"""
Module providing a hash related utility functions.

This module provides a function to compute the hash of an object, including nested
structures such as dictionaries and iterables.
Functions
---------
extended_hash(obj)
    Compute the hash of an object, handling nested dictionaries and iterables.

Examples
--------
>>> dict1 = {
...     "name": "Alice",
...     "age": 30,
...     "details": {
...         "city": "New York",
...         "hobbies": ["reading", "traveling"],
...         "scores": {"math": 95, "science": 90},
...     },
...     "tags": ["python", "developer"],
... }
>>> dict2 = {
...     "tags": ["python", "developer"],
...     "age": 30,
...     "details": {
...         "scores": {"science": 90, "math": 95},
...         "hobbies": ["traveling", "reading"],
...         "city": "New York",
...     },
...     "name": "Alice",
... }
>>> extended_hash(dict1) == extended_hash(dict2)
True
"""

import typing


def hash4class_instance(obj, **kw) -> int:
    """
    Generate a hash for a class instance.

    Parameters
    ----------
    obj : object
        The class instance to hash.

    Returns
    -------
    int
        The hash value of the class instance.
    """
    _hash = 0
    if hasattr(obj, "__dict__"):
        _hash = hash_extended(obj.__dict__, **kw)
    if hasattr(obj, "__slots__"):
        _hash = hash_extended(obj.__slots__, **kw)
    _hash ^= hash_extended(type(obj), **kw)
    return _hash


def _compute_hash(obj, **kw) -> int:
    ds = frozenset if kw.get("order_independent") else tuple
    try:
        _hash = hash(obj)
    except Exception:
        _hash = None
    if _hash and _hash != id(obj) >> 4:
        # ignore the default hash implementation for custom classes
        # as it is not stable across different runs
        pass
    elif isinstance(obj, typing.Mapping):
        _hash = hash(
            ds(
                (
                    hash_extended(k, **kw),
                    hash_extended(v, **kw),
                )
                for k, v in obj.items()
            )
        )
    elif isinstance(obj, typing.Iterable):
        _hash = hash(ds(hash_extended(x, **kw) for x in obj))
    elif isinstance(obj, typing.Callable):
        try:
            _hash = hash(obj.__code__)
        except AttributeError:
            _hash = hash(repr(obj))
    elif isinstance(type(obj), type):
        # is a instance of a class
        _hash = hash4class_instance(obj, **kw)
    else:
        _hash = hash(repr(obj))
    return _hash


def hash_extended(obj, order_independent: bool = True, _cache=None, _seen=None) -> int:
    """
    Compute the hash of an object.

    Python's built-in `hash` function is not suitable for hashing nested structures.
    This function computes the hash of an object, including nested dictionaries and
    iterables.

    Parameters
    ----------
    obj : Any
        The object to compute the hash for.
    order_independent : bool
        Whether to compute the hash in an order-independent
        way for dictionaries and iterables.

    Returns
    -------
    int
        The hash value of the object.
    """
    if _cache is None:
        _cache = {}
    if _seen is None:
        _seen = set()
    _id = id(obj)
    if _id in _seen:
        return hash(f"circular-structure:{_id}")
    _seen.add(_id)
    _hash = _cache.get(_id) or _compute_hash(
        obj, order_independent=order_independent, _cache=_cache, _seen=_seen
    )
    _cache[_id] = _hash
    return _hash

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

import inspect
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
        _hash = hash4any(obj.__dict__, **kw)
    if hasattr(obj, "__slots__"):
        _hash = hash4any(obj.__slots__, **kw)
    _hash ^= hash4any(type(obj), **kw)
    return _hash


def _hash4any(obj, **kw) -> int:
    ds = frozenset if kw.get("order_independent") else tuple
    try:
        _hash = hash(obj)

    except Exception:
        _hash = None
    if _hash and _hash != id(obj) >> 4:
        # ignore the default hash implementation for custom classes
        # as it is not stable across different runs
        pass
    elif _hash and type(obj) is type:
        # Use the original hash for classes
        pass
    elif isinstance(obj, typing.Mapping):
        _hash = hash(
            ds(
                (
                    hash4any(k, **kw),
                    hash4any(v, **kw),
                )
                for k, v in obj.items()
            )
        )
    elif isinstance(obj, typing.Iterable):
        _hash = hash(ds(hash4any(x, **kw) for x in obj))
    elif callable(obj):
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


def hash4any(obj, order_independent: bool = True, _cache=None, _seen=None) -> int:
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
    _hash = _cache.get(_id) or _hash4any(
        obj, order_independent=order_independent, _cache=_cache, _seen=_seen
    )
    _cache[_id] = _hash
    return _hash


def kind4function(function):
    """
    Determine the type of a function.

    Parameters
    ----------
    function : callable
        The function to inspect.

    Returns
    -------
    str
        A string indicating the type of the function. Possible values are:
        - "staticmethod": if the function does not take any parameters.
        - "method": if the first parameter is named "self".
        - "classmethod": if the first parameter is named "cls".
        - "staticmethod": if none of the above conditions are met.
    """
    signature = inspect.signature(function)
    parameters = list(signature.parameters.values())

    if not parameters:
        return "staticmethod"
    elif parameters[0].name == "self":
        return "method"
    elif parameters[0].name == "cls":
        return "classmethod"
    else:
        return "staticmethod"


def repr4cls(cls):
    return f"{cls.__module__}.{cls.__qualname__}"


def lookup4mro(cls, name, default):
    for base in cls.__mro__:
        _vars = vars(base)
        if name in _vars:
            return _vars[name]
    return default


def lookup4descriptor(*_, relative_frame=1, attr=None):
    import ast

    caller_frame = inspect.stack()[relative_frame]

    caller_code_line = caller_frame.code_context[0][
        caller_frame.positions.col_offset : caller_frame.positions.end_col_offset
    ]

    tree = ast.parse(caller_code_line)
    stmt = tree.body[0]

    if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
        return None
    call_stmt = stmt.value
    if not call_stmt.args:
        return None
    caller_arg = call_stmt.args[0]
    if not isinstance(caller_arg, ast.Attribute):
        return None

    var_owner = caller_arg.value.id

    if not var_owner:
        return None

    owner = caller_frame.frame.f_locals.get(var_owner, None)
    var_attribute = attr or caller_arg.attr
    descriptor = lookup4mro(type(owner), var_attribute, None)
    if not descriptor:
        return None

    return descriptor

import typing
from contextlib import contextmanager

_VSTACK_VAR = "__virtual_stack"


@contextmanager
def virtual_stack(instance: typing.Any, item: typing.Any):
    if not hasattr(instance, _VSTACK_VAR):
        setattr(instance, _VSTACK_VAR, [])
    stack: typing.List[typing.Any] = getattr(instance, _VSTACK_VAR)
    stack.append(item)
    yield
    stack.pop()
    if not stack:
        delattr(instance, _VSTACK_VAR)


class SignaledProperty:
    class _Kinds:
        primitive = "primitive"
        dynamic = "callable"

    def __init__(self, target) -> None:
        self.target = target
        self.target_kind = self._Kinds.primitive
        self.target_name = ""
        self.truncated = False
        self.deps: typing.Dict[int, "SignaledProperty"] = {}
        if callable(self.target):
            self.truncated = True
            self.target_kind = self._Kinds.dynamic
            self.target_name = self.target.__name__

    def __set_name__(self, owner, name):
        self.target_name = name

    def __repr__(self) -> str:
        return f"signal::<{self.target.__class__.__name__}>({repr(self.target)})"

    def __get__(self, instance, owner):
        if instance is None:
            return self

        self.add_deps(instance)

        if self.target_kind == self._Kinds.primitive:
            return self.target

        if self.target_name in instance.__dict__:
            if not self.truncated:
                return instance.__dict__[self.target_name]
            instance.__dict__[self.target_name] = value = self.target(instance)
            self.truncated = False
            return value

        with virtual_stack(instance, self):
            instance.__dict__[self.target_name] = value = self.target(instance)
            self.truncated = False
            return value

    def __set__(self, instance, value):
        if self.target_kind == self._Kinds.dynamic:
            raise AttributeError("Can't set dynamic signaled attribute")
        self.target = value
        self.truncate()

    def add_deps(self, instance):
        if not hasattr(instance, _VSTACK_VAR):
            return
        prev_stack = getattr(instance, _VSTACK_VAR)[-1]
        self.deps[id(prev_stack)] = prev_stack

    def truncate(self):
        self.truncated = True
        for _, dep_obj in self.deps.items():
            dep_obj.truncate()


class signal(SignaledProperty):  # noqa: N801
    """
    The signal class is a decorator and descriptor used to define reactive properties in a class. It allows
    for automatic recalculation and caching of dependent properties when the base properties change. This
    is particularly useful for scenarios where properties depend on each other and need to be recalculated
    when their dependencies change.
    """

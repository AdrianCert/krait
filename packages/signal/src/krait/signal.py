"""
Module implements a reactive property system inspired by modern web frameworks.

Module implements a reactive property system inspired by modern web frameworks
such as SolidJS and ReactJS. It allows for the creation of properties that can react
to changes in their dependencies, enabling automatic recalculation and caching of
derived values. This is particularly useful for building dynamic, dependency-aware
systems in Python.

Features:
---------
- **Signal Handlers**: Manage the behavior and lifecycle of signal-enabled properties.
  Handlers ensure that the origin value remains consistent with the property they are managing.
- **Dynamic Signals**: Support for dynamic, callable properties with caching and
  expiration capabilities.
- **Dependency Tracking**: Automatically tracks relationships between properties to
  propagate changes efficiently, similar to state management in ReactJS.


Modules and Classes:
--------------------
- BaseSignalHandler: A base class for managing signal behaviors, ensuring that handler
  origin values remain consistent with the property.
- SignaledProperty: A descriptor that enables reactive properties, tracking dependencies,
  and handling updates automatically.
- DynamicSignaledType: A specialized handler for callable properties, supporting caching
  and controlled expiration of values.
- signal: A decorator and subclass of `SignaledProperty` for defining reactive properties
  within classes.

Notes
-----
- Limitations: This module have not yet support for handling mutable objects as signals.
    In case that a mutable object is used as a signal, the signal will not be triggered when
    the object is modified. This is a known limitation and will be addressed in future updates.

    As a workaround, you can trigger the signal by setting the signal to itself, like this:
    ```python
    class ExampleClass:
        @signal
        def signal_instance(self):
            return [1, 2, 3]

    instance = ExampleClass()
    instance.signal_instance = instance.signal_instance
    # This will trigger the signal and update the downstream properties.
    # or u can do: instance.signal_instance = signal
    ```


This module is suitable for scenarios requiring state management, derived computations,
or reactive programming principles in Python.
"""

import abc
import contextlib
import datetime
import typing
import weakref

from krait import introspect

__sentinel__ = object()


class SignalContext(typing.NamedTuple):
    instance: typing.Any = None
    owner: typing.Optional[typing.Type] = None


class BaseSignalHandler(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def accept(cls, value: typing.Any) -> bool: ...

    @abc.abstractmethod
    def get(self) -> typing.Any: ...

    @abc.abstractmethod
    def set(self, value) -> bool: ...

    @abc.abstractmethod
    def alter(self, **kwargs) -> None: ...

    def __init__(
        self,
        /,
        owner: "SignaledProperty",
        context: typing.Optional[SignalContext] = None,
        **kwargs,
    ) -> None:
        """
        Initialize a BaseSignalHandler instance.

        Parameters
        ----------
        owner : SignaledProperty
            The signaled property witch own this
        context: typing.Optional[SignalContext]
            The context in where signal were called
        """
        self.context = context
        self.owner: SignaledProperty = owner

    def get_value(self):
        """
        Retrieve the value from the signal property.

        Returns
        -------
        Any
            The value of the signal property.
        """
        return self.get()

    def set_value(self, value):
        """
        Set the value for the given instance and triggers alteration if the value is changed.

        Parameters
        ----------
        value : any
            The new value to set.

        Returns
        -------
        None

        """
        altered = self.set(value)
        if altered:
            self.notice_alter()

    def notice_alter(self, **kw):
        context = kw.pop("context", self.context)
        self.owner.alter(context=context, **kw)


class PrimitiveSignalHandler(BaseSignalHandler):
    """
    Base class for signal handlers.

    Attributes
    ----------
    original_value : Any
        The original value of the signal that the handler manages.
    """

    original_value: typing.Any

    def __init__(
        self,
        origin,
        use_hashing: typing.Union[bool, typing.Callable[..., bool]] = True,
        **kwargs,
    ) -> None:
        """
        Initialize a BaseSignalHandler instance.

        Parameters
        ----------
        origin : Any
            The original value of the signal.
        """
        super().__init__(**kwargs)
        self.original_value = origin
        self.hashing = (
            use_hashing
            and (use_hashing if callable(use_hashing) else introspect.hash4any)
            or None
        )
        self.use_hashing = use_hashing and True or False
        self.original_hash = self.hashing and self.hashing(origin) or None

    @classmethod
    def accept(cls, value: typing.Any) -> bool:
        """
        Determine whether this handler can process the given value.

        Parameters
        ----------
        value : Any
            The value to be checked.

        Returns
        -------
        bool
            True if the value is accepted by this handler, False otherwise.
        """
        return True

    def get(self) -> typing.Any:
        """
        Retrieve the value managed by this signal handler.

        Parameters
        ----------
        instance : Any
            The instance of the class where the signal is defined.
        owner : type
            The owner class where the signal is defined.

        Returns
        -------
        Any
            The value managed by this signal handler.
        """
        return self.original_value

    def set(self, value) -> bool:
        """
        Set the value managed by this signal handler.

        If the value is different from the original value, the handler will update the
        original value and return True. Otherwise, it will return False.

        Parameters
        ----------
        instance : Any
            The instance of the class where the signal is defined.
        value : Any
            The new value to set.
        """
        self.original_value = value
        if self.hashing:
            new_hash = self.hashing(value)
            diff_hash = new_hash != self.original_hash
            self.original_hash = new_hash
            return diff_hash
        return True

    def alter(self, **kwargs): ...


class DynamicSignalHandler(BaseSignalHandler):
    def __init__(self, origin, expire: int = 0, **kwargs) -> None:
        super().__init__(**kwargs)
        self._function = origin
        self._cache_expire = expire
        self._cache_reset()

    def _cache_reset(self):
        self._cache_value = __sentinel__
        self._cache_expire_at = (
            datetime.datetime.min if self._cache_expire else datetime.datetime.max
        )

    def _cache_get(self) -> typing.Any:
        if self._cache_expire_at <= datetime.datetime.now():
            self._cache_reset()
        return self._cache_value

    def _cache_set(self, value):
        self._cache_value = value
        if self._cache_expire:
            self._cache_expire_at = datetime.datetime.now() + datetime.timedelta(
                seconds=self._cache_expire
            )
            self.notice_alter(at=self._cache_expire_at)

    @classmethod
    def accept(cls, value: typing.Any) -> bool:
        return callable(value)

    def get(self) -> typing.Any:
        cached_value = self._cache_get()
        if cached_value is not __sentinel__:
            return cached_value
        computed_value = (
            self.context
            and self._function.__get__(self.context.instance, self.context.owner)
            or self._function
        )()

        self._cache_set(computed_value)
        return computed_value

    def alter(self, at: typing.Optional[datetime.datetime] = None, **kwargs):
        if not at:
            return self._cache_reset()
        if at < self._cache_expire_at:
            self._cache_expire_at = at
            self.notice_alter(at=at)

    def set(self, value) -> bool:
        raise AttributeError("Can't set dynamic signaled attribute")


SIGNAL_HANDLER_TYPES = (
    DynamicSignalHandler,
    PrimitiveSignalHandler,
)


class SignalLinkPicker:
    from contextvars import ContextVar

    signals_stack: ContextVar[typing.List["SignaledProperty"]] = ContextVar(
        "signals_stack", default=[]
    )

    def push(self, item: "SignaledProperty"):
        self.signals_stack.set(self.signals_stack.get() + [item])

    def pop(self, /, default=__sentinel__):
        stack = self.signals_stack.get()
        if not stack:  # pragma: no cover
            if default is __sentinel__:
                raise KeyError("stack::signal empty in current context")
            return default
        *stack, value = stack
        self.signals_stack.set(stack)
        return stack

    def get(self, /, default=None):
        stack = self.signals_stack.get()
        return stack[-1] if stack else None

    def __call__(self, signal: "SignaledProperty"):
        with contextlib.suppress(Exception):
            other: SignaledProperty = self.get()
            other.link_signal_used(signal)
        self.push(signal)


class SignaledProperty:
    """
    Signal Property.

    Descriptor for signal-enabled properties that support dependency tracking and
    automatic updates.

    """

    __slots__ = (
        "handler",
        "name",
        "shared",
        "owner",
        "_handler_refs",
        "_upstream_signals",
        "_downstream_signals",
        "_hkw",
    )

    handler: typing.Type[BaseSignalHandler]
    shared: bool
    name: str

    @classmethod
    def __peek_handler(cls, target) -> typing.Type[BaseSignalHandler]:
        """
        Determine the appropriate signal handler for a given target.

        Parameters
        ----------
        target : Any
            The target value to be handled.

        Returns
        -------
        typing.Type[BaseSignalHandler]
            The signal handler that can handle the target.

        Raises
        ------
        ValueError
            If no appropriate signal handler is found.
        """
        for signaled_type in SIGNAL_HANDLER_TYPES:
            if signaled_type.accept(target):
                return typing.cast(typing.Type[BaseSignalHandler], signaled_type)
        raise ValueError(f"Unsupported signal type: {type(target)}")  # pragma: no cover

    def __init__(self, origin=__sentinel__, shared: bool = False, **kwargs) -> None:
        """
        Initialize a SignaledProperty instance.

        Parameters
        ----------
        target : Any
            The initial value of the property.
        args : tuple
            Positional arguments for the signal handler.
        kwargs : dict
            Keyword arguments for the signal handler.
        """
        self._upstream_signals: weakref.WeakSet["SignaledProperty"] = weakref.WeakSet()
        self._downstream_signals: weakref.WeakSet["SignaledProperty"] = (
            weakref.WeakSet()
        )
        self._handler_refs: weakref.WeakKeyDictionary[typing.Any, BaseSignalHandler] = (
            weakref.WeakKeyDictionary()
        )
        self.shared = shared
        self._hkw = {"origin": origin, "owner": self, **kwargs}

    def __call__(self, target) -> "SignaledProperty":
        """
        Call the SignaledProperty instance with a new target value.

        Parameters
        ----------
        target : Any
            The new target value.

        Returns
        -------
        SignaledProperty
            A new instance of the SignaledProperty with the updated target value.
        """
        self._hkw["origin"] = target
        return self

    def __hash__(self):
        return id(self) >> 5

    def __repr__(self) -> str:
        """
        Return a string representation of the SignaledProperty instance.

        Returns
        -------
        str
            String representation of the property.
        """
        return "signal:{name} {{ {fields} }}".format(
            name=self.name,
            fields=", ".join(
                f"{k}: {v}"
                for k, v in {
                    "shared": self.shared,
                    "owner": introspect.repr4cls(self.owner),
                    "handler": introspect.repr4cls(self.handler),
                }.items()
            ),
        )

    def resolve_signal_handler(self, instance, owner=None):
        ref = owner if self.shared or not instance else instance

        handler = self._handler_refs.get(ref)
        if handler:
            return handler
        self._handler_refs[ref] = handler = self.handler(
            context=SignalContext(instance, owner), **self._hkw
        )
        return handler

    @contextlib.contextmanager
    def visit_on_setup(self, instance, owner):
        self.handler = self.__peek_handler(self._hkw["origin"])
        with self.visit_on_linking(instance, owner) as handler:
            yield handler
        self.visit = self.visit_on_linking

    @contextlib.contextmanager
    def visit_on_linking(self, instance, owner):
        picker = SignalLinkPicker()
        picker(self)
        with self.visit_on_call(instance, owner) as handler:
            yield handler
        picker.pop()
        # need to find a way to optimize the linking signals
        # given A, B, C signals A -> B, C -> B
        # when any link done we disable with line bellow
        # but next time A/C call B and B does not report
        # It's need to come up with a solution to reactivate B
        # self.visit = self.visit_on_call

    visit = visit_on_setup

    @contextlib.contextmanager
    def visit_on_call(self, instance, owner):
        """
        Context manager for visiting the signal.

        Parameters
        ----------
        instance : Any
            The instance of the class where the signal is defined.
        owner : type
            The owner class where the signal is defined.

        """
        try:
            yield self.resolve_signal_handler(instance, owner)
        except Exception as exc:
            # TODO: obfuscate the traceback to the user in order to avoid confusion
            exc.with_traceback(None)
            raise

    def __set_name__(self, owner, name):
        self.name = name
        self.owner = owner

    def __get__(self, instance, owner):
        with self.visit(instance, owner) as handler:
            return handler.get_value()

    def get(self):
        return self.__get__(None, SignaledProperty)

    def set(self, value):
        return self.__set__(SignaledProperty, value)

    def __set__(self, instance, value) -> None:
        # if issubclass(type(value), SignaledProperty):
        #     # the behavior for setting a signal to another signal it's to trigger a change
        #     # in that way, the chain of signals will be updated correctly, this operation
        #     # might be useful for triggering a change in a signal that is not directly related
        #     # like the signal it's a mutable object and it's downstream attributes are not signals.
        #     # One example of this is a list or a dict, where the signal is the container
        #     return self.alter()
        with self.visit(instance, type(instance)) as handler:
            handler.set_value(value)

    def link_signal_used(self, other: "SignaledProperty", reflexive: bool = True):
        self._downstream_signals.add(other)
        if reflexive:
            other.link_signal_used_by(self, False)

    def link_signal_used_by(self, other: "SignaledProperty", reflexive: bool = True):
        self._upstream_signals.add(other)
        if reflexive:
            other.link_signal_used(self, False)

    def alter(
        self,
        context: typing.Optional[SignalContext] = None,
        src: typing.Optional["SignaledProperty"] = None,
        **kwargs,
    ):
        if src and src.shared:
            for handler in self._handler_refs.values():
                handler.alter(
                    **kwargs,
                )
        elif context:
            handler = self.resolve_signal_handler(*context)
            handler.alter(**kwargs)
        else:
            # check when context will be none
            pass

        for ref_signal in self._upstream_signals:
            ref_signal.alter(**kwargs, src=self, context=context)


# TODO: Add support for mutable objects as signals
# One possible approach is to create a custom signal handler for mutable objects
# that handler will return a proxy object that will trigger the signal when the object is modified
# the proxy object will be a subclass of the original object and will override the __setattr__ method
# to trigger the signal when the object is modified.

# As example if the signal is a dict, the proxy object
# will be a subclass of UserDict and will override methods to trigger the signal when the dict is modified by
# returning items as signals as well and triggering the signal when the dict is modified. Methods containing
# __setitem__, __delitem__, update, clear, pop, popitem, setdefault

# For custom classes we can monkey patch the class to return a proxy object that will trigger the signal when the


class signal(SignaledProperty):  # noqa: N801
    """
    The signal property.

    The signal class is a decorator and descriptor used to define reactive properties in a class. It allows
    for automatic recalculation and caching of dependent properties when the base properties change. This
    is particularly useful for scenarios where properties depend on each other and need to be recalculated
    when their dependencies change.

    """

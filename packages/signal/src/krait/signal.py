"""
This module implements a reactive property system inspired by modern web frameworks 
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

Notes:
------
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
import datetime
import inspect
import typing
from contextlib import contextmanager

__sentinel__ = object()


def equal_objects(obj1, obj2) -> bool:
    """
    Compare two objects for equality.

    Parameters
    ----------
    obj1 : Any
        The first object to compare.
    obj2 : Any
        The second object to compare.

    Returns
    -------
    bool
        True if the objects are equal, False otherwise.
    """
    # this is a simple comparison, we can improve this by adding support for
    # handling mutable objects and other types of objects
    return obj1 == obj2


class BaseSignalHandler:
    """
    Base class for signal handlers.

    Attributes
    ----------
    original_value : Any
        The original value of the signal that the handler manages.
    """

    original_value: typing.Any
    property: "SignaledProperty"

    def __init__(self, original_value, *args, **kwargs) -> None:
        """
        Initialize a BaseSignalHandler instance.

        Parameters
        ----------
        original_value : Any
            The original value of the signal.
        """
        self.original_value = original_value
        self.property = None

    @contextmanager
    def with_property(
        self,
        prop: "SignaledProperty",
    ) -> typing.Generator[None, None, None]:
        """
        Context manager for setting the property instance.

        Parameters
        ----------
        prop : SignaledProperty
            The signal property instance.

        Yields
        ------
        None
        """
        self.property = prop
        yield
        self.property = None

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

    def alter(self) -> None:
        """
        Trigger an alteration in the signal handler.
        """
        pass

    def get_value(self, instance, owner) -> typing.Any:
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

    def set_value(self, instance, value) -> bool:
        """
        Set the value managed by this signal handler.

        Parameters
        ----------
        instance : Any
            The instance of the class where the signal is defined.
        value : Any
            The new value to set.
        """
        # TODO: Implement a proper comparison to avoid unnecessary updates
        # changed = not equal_objects(self.original_value, value)
        self.original_value = value
        return True

    def get(self, prop, instance, owner):
        """
        Retrieve the value from the signal property.

        Parameters
        ----------
        prop : SignaledProperty
            The signal property instance.
        instance : Any
            The instance of the class where the signal is defined.
        owner : type
            The owner class where the signal is defined.

        Returns
        -------
        Any
            The value of the signal property.
        """
        with self.with_property(prop):
            return self.get_value(instance, owner)


class SignaledProperty:
    """
    Descriptor for signal-enabled properties that support dependency tracking and
    automatic updates.

    Attributes
    ----------
    __original_value__ : Any
        The original value of the property.
    __altered__ : bool
        Indicates whether the property value has been altered.
    __handler__ : BaseSignalHandler
        The signal handler managing this property.
    __ref_name__ : str
        The name of the property as defined in the owner class.
    __upstream_signals__ : dict
        Dictionary mapping upstream signal IDs to SignaledProperty instances.
    __skip_mem_upstream_signals__ : bool
        Indicates whether upstream signal tracking should be skipped.
    """

    __original_value__: typing.Any = __sentinel__
    __altered__: bool = False
    __handler__: typing.Union[
        BaseSignalHandler, typing.Tuple[typing.Tuple, typing.Dict]
    ] = None
    __ref_name__: str = ""
    __upstream_signals__: typing.Dict[int, "SignaledProperty"] = {}
    __skip_mem_upstream_signals__: bool = False

    @classmethod
    def __iter_signals_types(cls) -> typing.Iterable[BaseSignalHandler]:
        """
        Iterate over available signal handler types.

        Returns
        -------
        Iterable[BaseSignalHandler]
            An iterable of signal handler types.
        """
        yield from [
            DynamicSignaledType,
            BaseSignalHandler,
        ]

    @classmethod
    def __peek_handler(cls, target, *args, **kwargs) -> BaseSignalHandler:
        """
        Determine the appropriate signal handler for a given target.

        Parameters
        ----------
        target : Any
            The target value to be handled.
        args : tuple
            Positional arguments for the signal handler.
        kwargs : dict
            Keyword arguments for the signal handler.

        Returns
        -------
        BaseSignalHandler
            The signal handler that can handle the target.

        Raises
        ------
        ValueError
            If no appropriate signal handler is found.
        """
        if target is __sentinel__:
            target = (args, kwargs)
        for signaled_type in cls.__iter_signals_types():
            if signaled_type.accept(target):
                return signaled_type(target, *args, **kwargs)
        raise ValueError(f"Unsupported signal type: {type(target)}")

    @classmethod
    def __peek_stack_signals(cls) -> typing.Iterable["SignaledProperty"]:
        """
        Peek into the current call stack to find active signal instances.

        Returns
        -------
        Iterable[SignaledProperty]
            An iterable of active signal instances.
        """
        for frame in inspect.stack():
            if frame.function == "__get__":
                ref_signal = frame.frame.f_locals.get("self")
                if isinstance(ref_signal, cls):
                    yield ref_signal

    @classmethod
    def __mem_upstream_signals(cls) -> typing.Iterable["SignaledProperty"]:
        """
        Track upstream signal dependencies.

        Returns
        -------
        Iterable[SignaledProperty]
            An iterable of upstream signal dependencies.
        """
        try:
            refs_signals = cls.__peek_stack_signals()
            curr_signal: SignaledProperty = next(refs_signals)
            last_signal: SignaledProperty = next(refs_signals)
            curr_signal.__upstream_signals__[id(last_signal)] = last_signal
        except StopIteration:
            pass

    def __init__(self, target=__sentinel__, *args, **kwargs) -> None:
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
        self.__original_value__ = target
        self.__handler__ = self.__peek_handler(target, *args, **kwargs)

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
        (args, kwargs) = self.__handler__.original_value
        return self.__class__(target, *args, **kwargs)

    def __repr__(self) -> str:
        """
        Return a string representation of the SignaledProperty instance.

        Returns
        -------
        str
            String representation of the property.
        """
        return f"signal::<{self.__original_value__.__class__.__name__}>({repr(self.__original_value__)})"

    @contextmanager
    def visit(self, instance, owner):
        """
        Context manager for visiting the signal.

        Parameters
        ----------
        instance : Any
            The instance of the class where the signal is defined.
        owner : type
            The owner class where the signal is defined.

        Yields
        ------
        None
        """
        yield
        if not self.__skip_mem_upstream_signals__:
            self.__mem_upstream_signals()
            self.__skip_mem_upstream_signals__ = True

    def set_skip_mem_upstream_signals(self, value: bool):
        self.__skip_mem_upstream_signals__ = bool(value)

    def __set_name__(self, owner, name):
        self.__ref_name__ = name

    def __get__(self, instance, owner):
        with self.visit(instance, owner):
            # TODO: obfuscate the traceback to the user in order to avoid confusion
            return self.__handler__.get(self, instance, owner)

    def __set__(self, instance, value) -> None:
        if issubclass(type(value), SignaledProperty):
            # the behavior for setting a signal to another signal it's to trigger a change
            # in that way, the chain of signals will be updated correctly, this operation
            # might be useful for triggering a change in a signal that is not directly related
            # like the signal it's a mutable object and it's downstream attributes are not signals.
            # One example of this is a list or a dict, where the signal is the container
            return self.alter()
        try:
            stats = self.__handler__.set_value(instance, value)
            if stats:
                self.alter()
        except Exception as exc:
            # obfuscate the traceback to the user in order to avoid confusion
            exc.with_traceback(None)
            raise

    def altered(self):
        return self.__altered__

    def alter(self):
        if self.__altered__:
            return
        self.__altered__ = True
        for _, ref_signal in self.__upstream_signals__.items():
            ref_signal.alter()


class DynamicSignaledType(BaseSignalHandler):
    def __init__(self, callable, *args, expire: int = 0, **kwargs) -> None:
        super().__init__(callable, *args, **kwargs)
        self.__func_like__ = self.__compute_function_like(callable)
        self.__func__ = callable
        self.__value__ = __sentinel__
        self.expire = expire
        self.computed_at = datetime.datetime.min

    def __compute_function_like(self, original_value):
        signature = inspect.signature(original_value)
        parameters = list(signature.parameters.values())

        if not parameters:
            return "staticmethod"
        elif parameters[0].name == "self":
            return "method"
        elif parameters[0].name == "cls":
            return "classmethod"
        else:
            return "staticmethod"

    @classmethod
    def accept(cls, value: typing.Any) -> bool:
        return callable(value)

    def get_cache_value(self, instance) -> typing.Any:
        # if the value is expired, return the sentinel
        if (
            self.expire
            and (datetime.datetime.now() - self.computed_at).seconds > self.expire
        ):
            return __sentinel__
        return self.__value__

    def set_cache_value(self, instance, value):
        self.computed_at = datetime.datetime.now()
        # Todo: compare the value with the current value to avoid unnecessary updates
        if issubclass(type(self.property), SignaledProperty):
            self.property.alter()
        self.__value__ = value

    def compute_value(self, instance, owner) -> typing.Any:
        args = []
        if self.__func_like__ == "method":
            # here is the assumption that the instance is always not None
            args.append(instance)
        elif self.__func_like__ == "classmethod":
            args.append(owner)
        return self.__func__(*args)

    def get_value(self, instance, owner) -> typing.Any:
        cached_value = self.get_cache_value(instance)
        if cached_value is not __sentinel__:
            return cached_value
        self.property.set_skip_mem_upstream_signals(False)
        computed_value = self.compute_value(instance, owner)
        self.set_cache_value(instance, computed_value)
        return computed_value

    def alter(self):
        # alter the value to force a recompute
        self.__value__ = __sentinel__

    def set_value(self, instance, value) -> bool:
        raise AttributeError("Can't set dynamic signaled attribute")


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
    The signal class is a decorator and descriptor used to define reactive properties in a class. It allows
    for automatic recalculation and caching of dependent properties when the base properties change. This
    is particularly useful for scenarios where properties depend on each other and need to be recalculated
    when their dependencies change.
    """


if typing.TYPE_CHECKING:
    # this is a workaround to provide type hints for the signal class
    # see: https://github.com/python/typing/discussions/1102

    class signal(signal, DynamicSignaledType, property):  # noqa: N801
        ...

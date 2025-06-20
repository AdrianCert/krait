import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pytest_mock.plugin import MockerFixture

from krait.signal import signal

st_float = st.floats(min_value=100, max_value=10000)
st_percent = st.floats(min_value=0, max_value=1)
st_floats = st.lists(st_float, min_size=2, max_size=10)


@given(given_num=st_float)
def test_signal_initialization(given_num):
    """Test that a signal can be initialized with a value."""

    class Example:
        prop = signal(given_num)

    instance = Example()
    assert instance.prop == given_num


@given(given_nums=st_floats)
def test_signal_set_and_get(given_nums):
    """Test setting and getting signal values."""

    given_state_init, given_state_update, *_ = given_nums

    class Example:
        prop = signal(given_state_init)

    instance = Example()
    instance.prop = given_state_update
    assert instance.prop == given_state_update


@given(given_nums=st_floats)
def test_signal_dependency_propagation(given_nums):
    """Test that signals propagate changes to dependent signals."""

    given_state_init, given_state_update, *_ = given_nums

    class Example:
        a = signal(given_state_init)
        b = signal(lambda self: self.a + 1)

    instance = Example()
    assert instance.b == given_state_init + 1

    instance.a = given_state_update
    assert instance.b == given_state_update + 1


@given(given_num=st_float)
def test_signal_alter_behavior(given_num):
    """Test the alter method for signals."""

    class Example:
        prop = signal(42)

    instance = Example()
    instance.prop = given_num
    assert instance.prop == given_num


@given(given_num=st_float)
def test_dynamic_signal_handler(given_num):
    """Test dynamic signal handler behavior."""

    class Example:
        @signal
        def dynamic(self):
            return given_num

    instance = Example()
    assert instance.dynamic == given_num


@given(given_num=st_float)
def test_signal_shared_behavior(given_num):
    """Test shared signal behavior across instances."""

    class Example:
        shared_prop = signal(0, shared=True)

    instance1 = Example()
    instance2 = Example()

    instance1.shared_prop = given_num
    assert instance2.shared_prop == given_num


@given(
    given_num=st_float,
    given_factor=st_percent,
    given_price=st_float,
    given_updated_price=st_float,
)
def test_signal_cross_classes(
    given_num,
    given_factor,
    given_price,
    given_updated_price,
):
    """Test signal behavior across multiple classes."""

    class ConsumptionExample:
        value = signal(given_num)

    class BillExample:
        discount = signal(given_factor)
        price_rate = signal(given_price)

        def __init__(self, consumption: ConsumptionExample):
            self.consumption = consumption

        @signal
        def subtotal(self):
            return self.consumption.value * self.price_rate

        @signal
        def total(self):
            return self.subtotal - self.subtotal * self.discount

    consumer_1 = ConsumptionExample()
    bill_1 = BillExample(consumer_1)

    gross_price = given_num * given_price
    net_price = gross_price - gross_price * given_factor
    assert bill_1.total == net_price

    bill_1.price_rate = given_updated_price
    gross_price = given_num * given_updated_price
    net_price = gross_price - gross_price * given_factor
    assert bill_1.total == net_price


@given(given_num=st_float)
def test_signal_specs_first(given_num):
    """Test signal specs been specified first."""

    class Example:
        shared_prop = signal(shared=True)(0)

    instance1 = Example()
    instance2 = Example()

    instance1.shared_prop = given_num
    assert instance2.shared_prop == given_num


def test_signal_repr():
    """Test the string representation of a signal."""

    class Example:
        prop = signal(42)

    instance = Example()
    assert repr(instance.prop) == "42"

    prop_signal = Example.__dict__["prop"]
    repr_prop = repr(prop_signal)
    assert repr_prop.startswith("signal:prop")


@given(given_prices=st_floats, factor=st_percent)
def test_signal_working(fixture_price_calculator, given_prices, factor):
    cls_price_calculator, _ = fixture_price_calculator
    price_calculator = cls_price_calculator()
    price_calculator.factor = factor

    last_price = price_calculator.base_price
    for index, price in enumerate(given_prices):
        price_calculator.base_price = price
        if last_price != price:
            assert price_calculator.discount == pytest.approx(price * factor, rel=1e-5)
            if index > 1:
                break


@given(base_price=st.floats(min_value=1000, max_value=10000))
def test_shared_signal_across_instances(fixture_price_calculator, base_price):
    cls_price_calculator, is_shared = fixture_price_calculator
    pipeline1, pipeline2 = (
        cls_price_calculator(),
        cls_price_calculator(),
    )

    pipeline2.base_price = base_price

    if is_shared:
        # Since base_price might be shared, verify the expected behavior
        assert pipeline1.discount == pytest.approx(
            base_price * pipeline1.factor, rel=1e-5
        ), "on signal(shared=True) changes should be reflected in other instance"
    else:
        assert pipeline2.base_price != pipeline1.base_price, (
            "on signal(shared=False) changes should not affect other instance"
        )
    assert pipeline2.discount == pytest.approx(base_price * pipeline2.factor, rel=1e-5)


def test_cache_expire(mocker: MockerFixture):
    """
    Test the expiration behavior of the `@signal(expire=...)` decorator's cache.

    This test verifies that:
    - The cached value of a `@signal(expire=30*60)` property remains the same within the expiration window (30 minutes).
    - After the expiration window, the value is refreshed (i.e., the underlying function is called again).
    - Values accessed at 0 and 20 minutes are the same, while the value at 40 minutes is different (cache expired and refreshed),
      and the value at 60 minutes matches the one at 40 minutes (within the new cache window).
    """

    class Example:
        @signal(expire=30 * 60)
        def rss_feed(self):
            now = datetime.datetime.now()
            return "news of hour %s:%s" % (now.hour, now.minute)

    dt_cls = datetime.datetime
    dt_now = dt_cls(day=1, month=1, year=2000, hour=8)

    mock_dt = mocker.patch("datetime.datetime", wraps=datetime.datetime)

    mock_dt.now.return_value = dt_now
    mock_dt.min = dt_cls.min
    mock_dt.max = dt_cls.max

    obj = Example()

    access_log = []
    for minutes_pass in range(0, 80, 20):
        # Advance the mocked time
        mock_dt.now.return_value = dt_now + datetime.timedelta(minutes=minutes_pass)
        value = obj.rss_feed
        access_log.append(value)

    # The cache should expire after 30 minutes, so values at 0, 20 should be the same,
    # but at 40, 60, etc., should be refreshed.
    assert access_log[0] == access_log[1]
    assert access_log[1] != access_log[2]
    assert access_log[2] == access_log[3]


@given(number=st_float)
def test_signal_dynamic_set_raises_attributeerror(number):
    class MyClass:
        @signal
        def foo(self):
            return number

    inst = MyClass()
    # Should raise AttributeError when trying to set a dynamic signal
    with pytest.raises(AttributeError, match="Can't set dynamic signaled attribute"):
        inst.foo = number


def test_signal_alter_at_from_other_cache_expire(mocker: MockerFixture):
    counter = 0

    class Example:
        @signal(expire=30 * 60)
        def foo(self):
            return 1

        @signal
        def bar(self):
            nonlocal counter
            counter += 1
            return self.foo + counter

    dt_cls = datetime.datetime
    dt_now = dt_cls(day=1, month=1, year=2000, hour=8)

    mock_dt = mocker.patch("datetime.datetime", wraps=datetime.datetime)

    mock_dt.now.return_value = dt_now
    mock_dt.min = dt_cls.min
    mock_dt.max = dt_cls.max

    obj = Example()

    access_log = []
    for minutes_pass in range(0, 60, 20):
        # Advance the mocked time
        mock_dt.now.return_value = dt_now + datetime.timedelta(minutes=minutes_pass)
        value = obj.bar
        access_log.append(value)

    assert access_log == [2, 2, 3]

import hypothesis as hyp
import pytest

from krait.signal import signal

hyp.settings.register_profile(
    "default",
    suppress_health_check=[hyp.HealthCheck.function_scoped_fixture],
    phases=(hyp.Phase.explicit, hyp.Phase.reuse, hyp.Phase.generate, hyp.Phase.shrink),
)
hyp.settings.load_profile("default")


@pytest.fixture(params=[True, False], name="shared_signal")
def shared_signal(request):
    return request.param


@pytest.fixture
def fixture_price_calculator(shared_signal):
    class PriceCalculator:
        base_price = signal(100, shared=shared_signal)
        factor = signal(0.1)

        @signal
        def discount(self):
            return self.base_price * self.factor

    return PriceCalculator, shared_signal

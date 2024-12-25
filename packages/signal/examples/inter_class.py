from krait.signal import signal


class ExampleClass:
    """Represents a class with signals for a value and its derived computations."""

    def __init__(self, value):
        self._value = value

    @signal
    def value(self):
        """Returns the current value."""
        return self._value

    @signal
    def doubled_value(self):
        """Calculates and returns double the current value."""
        print("Calculating doubled value")
        return self.value * 2


class AnotherExampleClass:
    """
    Represents a class that derives values based on a base value
    and interacts with another ExampleClass instance.
    """

    def __init__(self, base_value, other=None):
        self._base_value = base_value
        self.other = other or ExampleClass(10)

    @signal
    def base_value(self):
        """Returns the base value."""
        return self._base_value

    @signal
    def squared_value(self):
        """Calculates and returns the square of the base value."""
        return self.base_value**2

    @signal
    def combined_value(self):
        """Calculates and returns the combined value of squared base and doubled other value."""
        return self.squared_value + self.other.doubled_value


# Example usage
example = ExampleClass(10)

# Accessing signals in ExampleClass
print("Initial value:", example.value)  # Outputs: 10
print("Doubled value:", example.doubled_value)  # Outputs: 20

# Creating AnotherExampleClass with reference to ExampleClass
another_example = AnotherExampleClass(10, example)
print("Combined value:", another_example.combined_value)  # Outputs: 120

# Modifying the value in ExampleClass and observing updates
example._value = 20
print("Updated value:", example.value)  # Outputs: 20
print("Updated doubled value:", example.doubled_value)  # Outputs: 40

# Demonstrating local assignment of the value
value_copy = example.value
print("Value copy:", value_copy)  # Outputs: 20

value_copy = 13  # Changing local variable
print("Doubled value (unchanged):", example.doubled_value)  # Outputs: 40

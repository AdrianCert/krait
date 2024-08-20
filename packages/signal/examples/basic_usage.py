from krait.signal import SignaledProperty as signal

import time


class PricingPipeline:
    # Initial base price for a product
    base_price = signal(100)

    @signal
    def discount(self):
        """Calculate the discount based on the current base price."""
        print(f"Calculating 'discount' for base price: {self.base_price}")
        time.sleep(0.5)  # Simulate some computation delay
        return self.base_price * 0.1  # 10% discount

    @signal
    def tax(self):
        """Calculate the tax based on the discounted price."""
        discounted_price = self.base_price - self.discount
        print(f"Calculating 'tax' for discounted price: {discounted_price}")
        time.sleep(0.5)  # Simulate some computation delay
        return discounted_price * 0.15  # 15% tax

    @signal
    def final_price(self):
        """Calculate the final price including tax."""
        discounted_price = self.base_price - self.discount
        total_price = discounted_price + self.tax
        print(
            f"Calculating 'final_price' based on discounted price: {discounted_price} and tax: {self.tax}"
        )
        time.sleep(0.5)  # Simulate some computation delay
        return total_price

    @signal
    def shipping_cost(self):
        """Calculate the shipping cost based on the final price."""
        print(f"Calculating 'shipping_cost' for final price: {self.final_price}")
        time.sleep(0.5)  # Simulate some computation delay
        return self.final_price * 0.05  # 5% of the final price

    @signal
    def total_cost(self):
        """Calculate the total cost, including final price and shipping cost."""
        print(
            f"Calculating 'total_cost' based on final price: {self.final_price} and shipping cost: {self.shipping_cost}"
        )
        time.sleep(0.5)  # Simulate some computation delay
        return self.final_price + self.shipping_cost


if __name__ == "__main__":
    # Instantiate the PricingPipeline class
    pipeline = PricingPipeline()

    # Initial access to the final price
    print("Initial 'final_price':", pipeline.final_price)

    # Access the total cost, which depends on the final price and shipping cost
    print("Step 1: Accessing 'total_cost'")
    print("total_cost:", pipeline.total_cost)

    # Modify the base price, which will affect all dependent calculations
    print("Step 2: Changing 'base_price' to 150")
    pipeline.base_price = 150

    # Re-access the total cost to observe the impact of the change in base price
    print("Step 3: Re-accessing 'total_cost'")
    print("total_cost:", pipeline.total_cost)

    # Access the final price multiple times to observe caching and recalculation
    print("Step 4: Accessing 'final_price' multiple times")
    print("final_price:", pipeline.final_price)
    print("final_price:", pipeline.final_price)
    print("final_price:", pipeline.final_price)

    # Change the base price again and access the total cost
    print("Step 5: Changing 'base_price' to 200")
    pipeline.base_price = 200
    print("total_cost:", pipeline.total_cost)

    # Keep the program running to observe the output
    input("Press Enter to exit...")

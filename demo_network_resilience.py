"""
Demo script showing network resilience features.
This simulates what happens when network issues occur.
"""

import time
from api_helpers.helpers.network_utils import (
    is_network_available,
    is_network_error,
    handle_network_outage,
    network_retry_wrapper,
    NetworkError,
)
from api_helpers.helpers.logging_config import I, W, E


def simulate_network_operation():
    """Simulate an operation that might fail due to network issues."""
    I("Performing network operation...")
    # In real scenario, this would be a betfair API call or database query
    return "Operation successful!"


def simulate_operation_with_errors():
    """Simulate different types of errors that might occur."""
    import random

    error_types = [
        ConnectionError("Connection refused"),
        TimeoutError("Request timed out"),
        OSError("Network is unreachable"),
        ValueError("Non-network error for comparison"),
    ]

    error = random.choice(error_types)
    raise error


def demo_network_resilience():
    """Demonstrate the network resilience features."""

    print("\n" + "=" * 50)
    print("NETWORK RESILIENCE DEMO")
    print("=" * 50)

    # Test 1: Check current network status
    print("\n1. Checking current network status...")
    network_status = is_network_available()
    print(f"Network available: {network_status}")

    # Test 2: Test error detection
    print("\n2. Testing error type detection...")

    test_errors = [
        ConnectionError("Connection refused"),
        TimeoutError("Request timed out"),
        ValueError("Not a network error"),
        OSError("Network unreachable"),
    ]

    for error in test_errors:
        is_net_error = is_network_error(error)
        print(f"'{error}' -> Network error: {is_net_error}")

    # Test 3: Show how the main loop would handle errors
    print("\n3. Demonstrating main loop resilience...")
    print("This shows how your applications will now handle network issues:")

    # Simulate the improved error handling
    attempt = 0
    max_attempts = 3

    while attempt < max_attempts:
        try:
            print(f"\nAttempt {attempt + 1}:")

            # Simulate checking network at start of loop
            if not is_network_available():
                print("❌ Network connectivity issue detected!")
                print("⏳ Would wait for network recovery...")
                break
            else:
                print("✅ Network connectivity verified")

            # Simulate the actual operation
            result = simulate_network_operation()
            print(f"✅ {result}")
            break

        except Exception as e:
            if is_network_error(e):
                print(f"❌ Network error detected: {e}")
                print("⏳ Would check network status and wait for recovery...")
                print("🔄 Network errors don't count towards exponential backoff")
            else:
                print(f"❌ Application error: {e}")
                print("⏳ Would apply exponential backoff for app errors")

            attempt += 1
            if attempt < max_attempts:
                print(f"🔄 Retrying in a moment...")
                time.sleep(1)  # Shortened for demo

    print("\n" + "=" * 50)
    print("KEY IMPROVEMENTS:")
    print("=" * 50)
    print("✅ Network connectivity checked at start of each loop")
    print("✅ Network errors distinguished from application errors")
    print("✅ No exponential backoff for network issues")
    print("✅ Waits for network recovery instead of giving up")
    print("✅ Only applies backoff to actual application errors")
    print("✅ Prevents unnecessary service restarts due to network blips")
    print("=" * 50)


if __name__ == "__main__":
    demo_network_resilience()

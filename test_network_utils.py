"""Simple test script to verify network utility functions work."""

from api_helpers.helpers.network_utils import (
    is_network_available,
    is_network_error,
    handle_network_outage,
)


def test_network_utils():
    """Test basic functionality of network utilities."""

    print("Testing network connectivity...")

    # Test basic connectivity
    connected = is_network_available()
    print(f"Network available: {connected}")

    # Test error detection
    connection_error = ConnectionError("Test connection error")
    timeout_error = TimeoutError("Test timeout")
    value_error = ValueError("Not a network error")

    print(f"ConnectionError is network error: {is_network_error(connection_error)}")
    print(f"TimeoutError is network error: {is_network_error(timeout_error)}")
    print(f"ValueError is network error: {is_network_error(value_error)}")

    print("Network utilities test completed successfully!")


if __name__ == "__main__":
    test_network_utils()

"""Network utility functions for connectivity checks and network error handling."""

import socket
import subprocess
import time
from typing import Tuple, Union

import requests
from api_helpers.helpers.logging_config import E, I, W


class NetworkError(Exception):
    """Custom exception for network-related errors."""

    pass


def is_network_available(timeout: int = 5) -> bool:
    """
    Check if network connectivity is available by testing multiple methods.

    Args:
        timeout: Timeout in seconds for each test

    Returns:
        True if network is available, False otherwise
    """

    # Method 1: Try to connect to a reliable DNS server
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except (socket.timeout, socket.error, OSError):
        pass

    # Method 2: Try HTTP request to a reliable service
    try:
        response = requests.get("https://httpbin.org/status/200", timeout=timeout)
        if response.status_code == 200:
            return True
    except (requests.RequestException, requests.Timeout, requests.ConnectionError):
        pass

    # Method 3: Try ping (platform specific)
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout * 1000), "8.8.8.8"],
            capture_output=True,
            timeout=timeout + 1,
        )
        if result.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass

    return False


def wait_for_network_recovery(
    max_wait_time: int = 300, check_interval: int = 30, log_progress: bool = True
) -> bool:
    """
    Wait for network connectivity to be restored.

    Args:
        max_wait_time: Maximum time to wait in seconds
        check_interval: Time between connectivity checks in seconds
        log_progress: Whether to log progress messages

    Returns:
        True if network is restored, False if timeout reached
    """

    start_time = time.time()
    elapsed = 0

    if log_progress:
        I(
            f"Waiting for network connectivity. Will check every {check_interval}s for up to {max_wait_time}s"
        )

    while elapsed < max_wait_time:
        if is_network_available():
            if log_progress:
                I(f"Network connectivity restored after {elapsed:.0f}s")
            return True

        time.sleep(check_interval)
        elapsed = time.time() - start_time

        if log_progress and elapsed % 60 == 0:  # Log every minute
            I(f"Still waiting for network... ({elapsed:.0f}s/{max_wait_time}s)")

    if log_progress:
        W(f"Network connectivity not restored after {max_wait_time}s")
    return False


def is_network_error(exception: Exception) -> bool:
    """
    Determine if an exception is network-related.

    Args:
        exception: The exception to check

    Returns:
        True if the exception appears to be network-related
    """

    # Check for common network-related exception types
    network_exception_types = (
        ConnectionError,
        TimeoutError,
        OSError,
        socket.error,
        socket.timeout,
    )

    if isinstance(exception, network_exception_types):
        return True

    # Check for requests library network errors
    try:
        import requests

        if isinstance(
            exception,
            (
                requests.ConnectionError,
                requests.Timeout,
                requests.exceptions.RequestException,
            ),
        ):
            return True
    except ImportError:
        pass

    # Check error message for network-related keywords
    error_message = str(exception).lower()
    network_keywords = [
        "connection",
        "network",
        "timeout",
        "unreachable",
        "resolve",
        "dns",
        "host",
        "socket",
        "refused",
        "reset",
        "broken pipe",
        "no route",
        "temporary failure",
        "name resolution",
        "getaddrinfo",
    ]

    return any(keyword in error_message for keyword in network_keywords)


def handle_network_outage(max_wait_time: int = 300, check_interval: int = 30) -> bool:
    """
    Handle a detected network outage by waiting for recovery.

    Args:
        max_wait_time: Maximum time to wait in seconds
        check_interval: Time between connectivity checks in seconds

    Returns:
        True if network recovered, False if timeout reached
    """

    W("Network outage detected. Pausing operations until connectivity is restored.")

    # Wait for network recovery
    recovered = wait_for_network_recovery(max_wait_time, check_interval)

    if recovered:
        I("Network connectivity restored. Resuming operations.")
        return True
    else:
        E(
            f"Network connectivity not restored after {max_wait_time}s. Manual intervention may be required."
        )
        return False


def network_retry_wrapper(
    func,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    network_wait_time: int = 300,
):
    """
    Wrapper function that retries operations with network error handling.

    Args:
        func: Function to execute
        max_retries: Maximum number of retries for non-network errors
        retry_delay: Initial delay between retries
        backoff_multiplier: Multiplier for exponential backoff
        network_wait_time: Time to wait for network recovery

    Returns:
        Result of the function call

    Raises:
        NetworkError: If network doesn't recover
        Exception: Original exception if max retries exceeded
    """

    current_delay = retry_delay

    for attempt in range(max_retries + 1):
        try:
            return func()

        except Exception as e:
            if is_network_error(e):
                W(f"Network error detected: {e}")

                # Check if network is actually down
                if not is_network_available():
                    I("Confirmed network outage. Waiting for recovery...")

                    if handle_network_outage(network_wait_time):
                        I("Network recovered. Retrying operation...")
                        continue
                    else:
                        raise NetworkError(
                            "Network connectivity could not be restored"
                        ) from e
                else:
                    I(
                        "Network appears to be available. This may be a service-specific issue."
                    )

            # For non-network errors or if we've exhausted retries
            if attempt == max_retries:
                raise e

            I(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
            time.sleep(current_delay)
            current_delay *= backoff_multiplier

    # This should never be reached, but just in case
    raise Exception("Unexpected end of retry loop")

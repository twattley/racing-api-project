# Network Resilience Improvements

This document describes the network resilience improvements made to the racing API project's main applications.

## What Was Changed

### 1. New Network Utility Module

Created `libraries/api-helpers/src/api_helpers/helpers/network_utils.py` with the following functions:

- **`is_network_available()`** - Tests network connectivity using multiple methods (DNS, HTTP, ping)
- **`is_network_error()`** - Determines if an exception is network-related
- **`handle_network_outage()`** - Waits for network recovery with configurable timeouts
- **`wait_for_network_recovery()`** - Monitors network status until connectivity is restored
- **`network_retry_wrapper()`** - Generic wrapper for operations requiring network resilience

### 2. Updated Applications

#### Betfair Live Prices (`apps/betfair-live-prices/src/betfair_live_prices/main.py`)

- Added network connectivity check at the start of each loop
- Network errors are distinguished from application errors
- Network outages trigger recovery waiting instead of exponential backoff
- Only application errors count toward the backoff counter

#### Trader (`apps/trader/src/trader/main.py`)

- Added network connectivity check at the start of each loop
- Network errors are handled separately from application errors
- Network outages pause operations until connectivity is restored
- Reduced unnecessary restarts due to temporary network issues

## How It Works

### Before (Original Behavior)

```python
try:
    # API operation
    data = api_call()
except Exception as e:
    # All errors treated the same
    backoff_counter += 1
    sleep(backoff_counter**2 * 10)  # Exponential backoff
    if backoff_counter > 10:
        exit()  # Give up after 10 attempts
```

### After (Network Resilient)

```python
# Check network at start of loop
if not is_network_available():
    handle_network_outage()  # Wait for recovery

try:
    # API operation
    data = api_call()
except Exception as e:
    if is_network_error(e):
        # Network error - wait for recovery
        if not is_network_available():
            handle_network_outage()
        continue  # Don't count toward backoff
    else:
        # Application error - apply backoff
        backoff_counter += 1
        sleep(backoff_counter**2 * 10)
```

## Benefits

1. **Reduced False Failures**: Network blips don't cause services to exit unnecessarily
2. **Faster Recovery**: Services resume immediately when network is restored
3. **Better Monitoring**: Clear distinction between network and application issues
4. **Configurable Timeouts**: Network recovery waiting can be tuned per application
5. **Multiple Detection Methods**: Uses DNS, HTTP, and ping to verify connectivity

## Network Error Detection

The system recognizes these as network errors:

- `ConnectionError`
- `TimeoutError`
- `OSError` (network-related)
- `socket.error` and `socket.timeout`
- `requests.ConnectionError` and `requests.Timeout`
- Error messages containing network-related keywords

## Configuration

Default settings:

- **Network check timeout**: 5 seconds
- **Recovery wait time**: 300 seconds (5 minutes)
- **Check interval**: 30 seconds
- **Maximum backoff**: 300 seconds (5 minutes)

These can be adjusted in the function calls within each application's main loop.

## Testing Network Resilience

To test the network resilience:

1. **Simulate network outage**: Disconnect your network connection
2. **Run the application**: It should detect the outage and wait for recovery
3. **Restore network**: The application should resume operations automatically
4. **Check logs**: Network errors should be clearly distinguished from app errors

## Future Enhancements

Potential improvements for the future:

- Health check endpoints for monitoring
- Metrics collection for network outage frequency
- Integration with external monitoring systems
- Configurable retry strategies per operation type

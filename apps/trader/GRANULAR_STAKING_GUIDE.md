# 🎯 Granular Time-Based Staking System

## Overview

Your trader now implements a sophisticated **granular time-based staking system** that dramatically improves liquidity matching and position building capabilities. Instead of the previous 4 basic time brackets, the system now uses **12 granular time brackets** with configurable stake percentages.

## Key Improvements

### ✅ **Before (Basic Time-Based Staking)**
- **4 time brackets only**
- Started betting at 2+ hours before race
- Large stake jumps (20% → 50% → 80% → 100%)
- Limited liquidity matching opportunities

### 🚀 **After (Granular Time-Based Staking)**
- **12 granular time brackets**
- Starts betting at 4+ hours before race
- Smooth stake progression (10% → 15% → 20% → 25% → ... → 100%)
- **3x more opportunities** to find and match liquidity

## Time-Based Stake Schedule

| Time to Race | Stake Percentage | Example (£50 max) | Purpose |
|--------------|------------------|-------------------|---------|
| 4+ hours (240+ min) | 10% | £5.00 | Early position building |
| 3.5+ hours (210+ min) | 15% | £7.50 | Gradual increase |
| 3+ hours (180+ min) | 20% | £10.00 | Building momentum |
| 2.5+ hours (150+ min) | 25% | £12.50 | Steady growth |
| 2+ hours (120+ min) | 30% | £15.00 | Accelerating |
| 1.5+ hours (90+ min) | 40% | £20.00 | Significant position |
| 1+ hour (60+ min) | 50% | £25.00 | Half stake deployed |
| 45+ minutes | 60% | £30.00 | Increasing urgency |
| 30+ minutes | 70% | £35.00 | Race approaching |
| 20+ minutes | 80% | £40.00 | Near full deployment |
| 10+ minutes | 90% | £45.00 | Almost complete |
| 5+ minutes | 100% | £50.00 | Full stake |

## Configuration Options

The system is fully configurable through `config.py`:

```python
# Enable/disable time-based staking
enable_time_based_staking: bool = True

# Configurable time thresholds and percentages
time_based_staking_thresholds: List[Tuple[int, float]] = [
    (240, 0.10),  # 4+ hours: 10%
    (210, 0.15),  # 3.5+ hours: 15%
    # ... more brackets
]

# Minimum liquidity threshold
min_liquidity_threshold: float = 2.0  # Won't bet below £2 liquidity
```

## Benefits for Liquidity Matching

### 🎯 **Smaller Chunks = Better Matching**
- **10% stakes** (£5) are much easier to match than **20% stakes** (£10)
- More frequent betting opportunities across longer timeframes
- Better chance of finding partial liquidity

### ⏰ **Extended Time Window**
- **Before**: Started at 2+ hours (120 minutes)
- **After**: Starts at 4+ hours (240 minutes)
- **2x longer** window to build positions

### 📈 **Gradual Position Building**
- Build positions slowly with small chunks
- Remaining stake automatically calculated for each time bracket
- If £15 placed at 2+ hours, looks for £10 more at 1.5+ hours (40% - 30% = 10%)

## Implementation Details

### Core Methods Updated

1. **`_calculate_time_based_stake_size()`**
   - Uses configurable thresholds from config
   - Calculates appropriate stake for current time to race
   - Logs detailed breakdown of stake distribution

2. **`_check_minimum_liquidity()`**
   - Filters out bets with insufficient liquidity
   - Configurable minimum threshold (default £2)
   - Separate checks for BACK and LAY bets

3. **Enhanced Integration**
   - Time-based staking can be enabled/disabled via config
   - Seamlessly integrated into existing trading pipeline
   - Works with existing remaining size calculations

### Remaining Size Logic

The system correctly handles **remaining stake calculations**:

```python
# Example: £50 max stake, 2+ hours to race (30% = £15)
if £10 already placed:
    remaining_stake = £15 - £10 = £5
    # Looks for £5 liquidity, not £15

# At 1+ hour (50% = £25):
    remaining_stake = £25 - £10 = £15  
    # Looks for £15 additional liquidity
```

## Logging and Monitoring

The system provides comprehensive logging:

```
INFO - Found 5 bets at 4.0h+ (240+ min): stake size = 5.00 (10%)
INFO - Found 3 bets at 2.0h+ (120+ min): stake size = 15.00 (30%)
INFO - Stake summary - Total bets: 8, Avg: 12.50, Min: 5.00, Max: 25.00
INFO - Filtered out 2 bets due to insufficient liquidity (min: £2.00)
INFO - Liquidity check: 6/8 bets have sufficient liquidity
```

## Expected Outcomes

### 🎯 **Improved Liquidity Matching**
- **Higher success rate** in finding available liquidity
- **Better position building** over extended timeframes
- **Reduced missed opportunities** due to all-or-nothing stakes

### 📊 **Better Risk Management**
- **Gradual exposure** building rather than sudden large positions
- **More granular control** over position sizing
- **Extended time window** for market assessment

### 💡 **Operational Benefits**
- **Earlier market entry** (4+ hours vs 2+ hours)
- **More frequent trading opportunities**
- **Better capital utilization** across race schedule

## Usage

The system is **automatically active** and requires no code changes to use. It integrates seamlessly with your existing trading logic while providing much more sophisticated staking behavior.

To customize the time brackets or percentages, simply modify the `time_based_staking_thresholds` list in `config.py` and restart the trader.

---

**🚀 Your trader now has a much more sophisticated and effective approach to building positions over time, with significantly better liquidity matching capabilities!**

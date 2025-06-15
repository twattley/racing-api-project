#!/usr/bin/env python3
"""
Test the granular time-based staking functionality.
"""

import pandas as pd
import numpy as np
from trader.market_trader import MarketTrader
from api_helpers.config import config

def test_granular_staking():
    """Test that the granular staking calculations work correctly."""
    
    print("🧪 Testing Granular Time-Based Staking")
    print("=" * 50)
    
    # Create a mock MarketTrader instance
    class MockMarketTrader(MarketTrader):
        def __init__(self):
            # Skip the normal constructor that requires clients
            pass
    
    trader = MockMarketTrader()
    
    # Test data with various time horizons
    test_data = pd.DataFrame({
        'minutes_to_race': [300, 240, 210, 180, 150, 120, 90, 60, 45, 30, 20, 10, 5, 2],
        'market_id': [f'market_{i}' for i in range(14)],
        'selection_id': [f'selection_{i}' for i in range(14)],
    })
    
    max_stake = 50.0
    
    # Calculate time-based stakes
    result = trader._calculate_time_based_stake_size(test_data, max_stake)
    
    print(f"Max stake configured: £{max_stake}")
    print()
    print("📊 Calculated Stakes by Time to Race:")
    print("-" * 60)
    print(f"{'Minutes':<10} {'Hours':<10} {'Stake £':<10} {'% of Max':<10}")
    print("-" * 60)
    
    for _, row in result.iterrows():
        minutes = row['minutes_to_race']
        stake = row['time_based_stake_size']
        percentage = (stake / max_stake) * 100
        hours = minutes / 60
        
        hours_display = f"{hours:.1f}h" if hours >= 1 else f"{minutes}min"
        
        print(f"{minutes:<10} {hours_display:<10} £{stake:<9.2f} {percentage:>6.1f}%")
    
    print("-" * 60)
    
    # Verify key thresholds
    print("\n🔍 Verification of Key Thresholds:")
    print("-" * 40)
    
    test_cases = [
        (300, 0.10, "5 hours"),
        (240, 0.10, "4 hours"), 
        (210, 0.15, "3.5 hours"),
        (180, 0.20, "3 hours"),
        (120, 0.30, "2 hours"),
        (60, 0.50, "1 hour"),
        (30, 0.70, "30 minutes"),
        (10, 0.90, "10 minutes"),
        (5, 1.00, "5 minutes"),
        (2, 1.00, "2 minutes"),
    ]
    
    all_correct = True
    for minutes, expected_percentage, description in test_cases:
        # Find the stake for this time
        matching_rows = result[result['minutes_to_race'] == minutes]
        if not matching_rows.empty:
            actual_stake = matching_rows['time_based_stake_size'].iloc[0]
            expected_stake = max_stake * expected_percentage
            actual_percentage = actual_stake / max_stake
            
            is_correct = abs(actual_stake - expected_stake) < 0.01
            status = "✅" if is_correct else "❌"
            
            print(f"{status} {description}: £{actual_stake:.2f} ({actual_percentage*100:.0f}%)")
            
            if not is_correct:
                all_correct = False
                print(f"   Expected: £{expected_stake:.2f} ({expected_percentage*100:.0f}%)")
    
    print()
    if all_correct:
        print("🎉 All threshold tests passed!")
    else:
        print("⚠️  Some threshold tests failed!")
    
    # Show the benefits
    print("\n✅ Benefits of Granular Approach:")
    print("  • 12 time brackets instead of 4")
    print("  • Starts betting from 4+ hours (vs 2+ hours before)")
    print("  • Smaller initial stakes improve liquidity matching")
    print("  • Gradual stake increases reduce risk")
    print("  • More opportunities to build positions over time")
    
    return result

if __name__ == "__main__":
    test_granular_staking()

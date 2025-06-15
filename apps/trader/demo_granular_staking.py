#!/usr/bin/env python3
"""
Demo script showing the new granular time-based staking system.
"""

import pandas as pd
from api_helpers.config import config

def demo_time_based_staking():
    """Demonstrate how the granular time-based staking works."""
    
    print("🎯 Granular Time-Based Staking Demo")
    print("=" * 50)
    print(f"Max stake size: £{config.stake_size}")
    print()
    
    # Create sample data with different time horizons
    sample_data = pd.DataFrame({
        'minutes_to_race': [300, 240, 210, 180, 150, 120, 90, 60, 45, 30, 20, 10, 5, 2],
        'market_id': [f'market_{i}' for i in range(14)],
    })
    
    print("📊 Stake Allocation by Time to Race:")
    print("-" * 60)
    print(f"{'Time to Race':<15} {'Minutes':<10} {'Stake %':<10} {'Stake £':<10}")
    print("-" * 60)
    
    for minutes, percentage in config.time_based_staking_thresholds:
        hours = minutes / 60
        if hours >= 1:
            time_display = f"{hours:.1f} hours"
        else:
            time_display = f"{minutes} minutes"
        
        stake_amount = config.stake_size * percentage
        print(f"{time_display:<15} {minutes:<10} {percentage*100:>6.0f}%{' ':<4} £{stake_amount:>6.2f}")
    
    print("-" * 60)
    print()
    
    # Show actual stake calculations for sample races
    print("🏇 Sample Race Stakes:")
    print("-" * 40)
    
    for _, row in sample_data.iterrows():
        minutes = row['minutes_to_race']
        
        # Find the appropriate stake percentage
        stake_percentage = 1.0  # Default to full stake
        for threshold_minutes, threshold_percentage in config.time_based_staking_thresholds:
            if minutes >= threshold_minutes:
                stake_percentage = threshold_percentage
                break
        
        stake_amount = config.stake_size * stake_percentage
        hours = minutes / 60
        
        if hours >= 1:
            time_display = f"{hours:.1f}h"
        else:
            time_display = f"{minutes}min"
        
        print(f"Race in {time_display:>6}: £{stake_amount:>6.2f} ({stake_percentage*100:>3.0f}%)")
    
    print()
    print("✅ Benefits of Granular Staking:")
    print("  • More opportunities to find liquidity with smaller chunks")
    print("  • Gradual stake increase as race approaches")
    print("  • Better risk management across longer timeframes")
    print("  • Higher chance of matching available liquidity")

if __name__ == "__main__":
    demo_time_based_staking()

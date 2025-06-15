#!/usr/bin/env python3
"""
Comparison between old basic time-based staking vs new granular approach.
"""

import pandas as pd
import matplotlib.pyplot as plt
from api_helpers.config import config

def compare_staking_approaches():
    """Compare old vs new staking approaches."""
    
    # Create time range from 5 hours to 0 minutes
    minutes_range = list(range(0, 301, 5))  # Every 5 minutes up to 5 hours
    
    # Old basic approach (4 brackets)
    def old_staking(minutes):
        if minutes >= 120:  # 2+ hours
            return 0.20
        elif minutes >= 60:  # 1+ hour  
            return 0.50
        elif minutes >= 15:  # 15+ minutes
            return 0.80
        else:  # < 15 minutes
            return 1.00
    
    # New granular approach
    def new_staking(minutes):
        for threshold_minutes, threshold_percentage in config.time_based_staking_thresholds:
            if minutes >= threshold_minutes:
                return threshold_percentage
        return 1.0  # Default for very short times
    
    # Calculate stakes for both approaches
    old_stakes = [old_staking(m) * config.stake_size for m in minutes_range]
    new_stakes = [new_staking(m) * config.stake_size for m in minutes_range]
    
    # Convert minutes to hours for better visualization
    hours_range = [m / 60 for m in minutes_range]
    
    # Create comparison chart
    plt.figure(figsize=(12, 8))
    plt.plot(hours_range, old_stakes, 'b-', linewidth=3, label='Old Basic Approach (4 brackets)', marker='o', markersize=4)
    plt.plot(hours_range, new_stakes, 'r-', linewidth=3, label='New Granular Approach (12 brackets)', marker='s', markersize=3)
    
    plt.xlabel('Hours to Race', fontsize=12)
    plt.ylabel('Stake Amount (£)', fontsize=12)
    plt.title('Time-Based Staking: Old vs New Approach', fontsize=14, fontweight='bold')
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 5)
    plt.ylim(0, config.stake_size + 5)
    
    # Add annotations for key differences
    plt.annotate('More gradual\nincrease', xy=(2.5, 15), xytext=(3.5, 25),
                arrowprops=dict(arrowstyle='->', color='red', lw=2),
                fontsize=10, color='red', fontweight='bold')
    
    plt.annotate('Sudden jumps', xy=(1.5, 25), xytext=(0.5, 35),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2),
                fontsize=10, color='blue', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('/Users/tomwattley/App/racing-api-project/racing-api-project/apps/trader/staking_comparison.png', 
                dpi=300, bbox_inches='tight')
    
    print("📈 Staking Comparison Chart saved as 'staking_comparison.png'")
    print()
    
    # Show key benefits in numbers
    print("🔍 Key Differences:")
    print("-" * 50)
    
    # Count opportunities at different time horizons
    times_4h = [m for m in minutes_range if m >= 240]
    times_2h = [m for m in minutes_range if 120 <= m < 240]
    times_1h = [m for m in minutes_range if 60 <= m < 120]
    
    print(f"4+ hours to race:")
    print(f"  Old approach: £{config.stake_size * 0.20:.2f} (only after 2+ hours)")
    print(f"  New approach: £{config.stake_size * 0.10:.2f} to £{config.stake_size * 0.25:.2f} (gradual steps)")
    print()
    
    print(f"2-4 hours to race:")
    print(f"  Old approach: £{config.stake_size * 0.20:.2f} (single bracket)")  
    print(f"  New approach: £{config.stake_size * 0.20:.2f} to £{config.stake_size * 0.30:.2f} (4 different levels)")
    print()
    
    print(f"1-2 hours to race:")
    print(f"  Old approach: £{config.stake_size * 0.50:.2f} (single bracket)")
    print(f"  New approach: £{config.stake_size * 0.40:.2f} to £{config.stake_size * 0.50:.2f} (2 different levels)")
    print()
    
    print("✅ Advantages of Granular Approach:")
    print("  • 12 brackets vs 4 = 3x more opportunities")
    print("  • Smaller initial stakes = better liquidity matching")
    print("  • Smoother stake progression")
    print("  • Earlier market entry (from 4+ hours vs 2+ hours)")
    print("  • More chances to build position over time")

if __name__ == "__main__":
    try:
        compare_staking_approaches()
    except ImportError:
        print("Note: matplotlib not available for chart generation")
        print("But granular staking is still active!")

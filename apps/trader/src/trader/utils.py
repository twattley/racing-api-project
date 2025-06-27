"""
Utility functions for the trader module.
"""

import yaml
from pathlib import Path
from typing import Dict, Union

from api_helpers.config import config


def load_staking_config(
    test_config: bool = False,
) -> Dict[str, Dict[int, float]]:
    """
    Load time-based staking configuration from YAML file.

    Args:
        config_file: Name of the YAML config file (defaults to production config)
                    Use "test_staking_config.yaml" for tests

    Returns:
        Dictionary containing:
        - time_based_back_staking_size: Dict mapping minutes to stake amounts
        - time_based_lay_staking_size: Dict mapping minutes to liability amounts

    Example:
        >>> config = load_staking_config()
        >>> back_stakes = config['time_based_back_staking_size']
        >>> lay_stakes = config['time_based_lay_staking_size']

        # For tests:
        >>> test_config = load_staking_config("test_staking_config.yaml")
    """

    if test_config:
        config_path = Path(
            f"{config.monorepo_root}/apps/trader/config/test_staking_config.yaml"
        )
    else:
        config_path = Path(
            f"{config.monorepo_root}/apps/trader/config/staking_config.yaml"
        )

    if not config_path.exists():
        raise FileNotFoundError(f"Staking config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as file:
        staking_config = yaml.safe_load(file)

    return staking_config


def get_time_based_stake(
    minutes_to_race: float, staking_config: Dict[int, float]
) -> float:
    """
    Get the appropriate stake size based on time to race.

    Args:
        minutes_to_race: Minutes until race start
        staking_config: Dictionary mapping time thresholds to stake amounts

    Returns:
        Stake amount for the given time to race

    Example:
        >>> back_config = load_staking_config()['time_based_back_staking_size']
        >>> stake = get_time_based_stake(65, back_config)  # Returns 20.0 (60 minute threshold)
    """
    # Find the appropriate time bracket
    # We want the largest threshold that is <= minutes_to_race
    valid_thresholds = [
        threshold for threshold in staking_config.keys() if threshold <= minutes_to_race
    ]

    if not valid_thresholds:
        # If no threshold found, use the smallest available threshold
        # (race is very close to start)
        min_threshold = min(staking_config.keys())
        return staking_config[min_threshold]

    # Use the largest valid threshold (closest to race time)
    selected_threshold = max(valid_thresholds)
    return staking_config[selected_threshold]

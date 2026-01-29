import numpy as np
import pandas as pd
from numba import njit


@njit(cache=True)
def _simulate_loop(base_probs, n_sims, n_places):
    """JIT-compiled inner loop - no seed setting per call."""
    n_horses = len(base_probs)
    win_counts = np.zeros(n_horses, dtype=np.int32)
    place_counts = np.zeros(n_horses, dtype=np.int32)

    # Pre-allocate arrays once (reuse in loop)
    ps = np.empty(n_horses, dtype=np.float64)
    indices = np.empty(n_horses, dtype=np.int32)
    cumsum_buf = np.empty(n_horses, dtype=np.float64)

    for _ in range(n_sims):
        # Reset to full field
        ps[:] = base_probs
        for idx in range(n_horses):
            indices[idx] = idx
        n_remaining = n_horses

        K = min(n_places, n_horses)
        for i in range(K):
            # Normalize in-place
            ps_sum = 0.0
            for j in range(n_remaining):
                ps_sum += ps[j]
            if ps_sum > 0:
                for j in range(n_remaining):
                    ps[j] /= ps_sum

            # Cumsum and sample
            cumsum_buf[0] = ps[0]
            for j in range(1, n_remaining):
                cumsum_buf[j] = cumsum_buf[j - 1] + ps[j]

            rand_val = np.random.rand()
            idx = 0
            for j in range(n_remaining):
                if rand_val <= cumsum_buf[j]:
                    idx = j
                    break

            horse_idx = indices[idx]

            # Record win/place
            if i == 0:
                win_counts[horse_idx] += 1
            place_counts[horse_idx] += 1

            # Remove selected horse (shift arrays left)
            for j in range(idx, n_remaining - 1):
                indices[j] = indices[j + 1]
                ps[j] = ps[j + 1]
            n_remaining -= 1

    return win_counts, place_counts


def simulate_place_counts(
    data: pd.DataFrame,
    price_col: str = "betfair_win_sp",
    horse_col: str = "horse_name",
    n_places: int = 3,
    n_sims: int = 10000,
    seed: int = 42,
):
    """Optimized - assumes unique horses in df."""
    horses = data[horse_col].values
    prices = data[price_col].values

    # Compute implied probabilities
    base_probs = 1.0 / prices
    base_probs = base_probs / base_probs.sum()

    np.random.seed(seed)
    win_counts, place_counts = _simulate_loop(base_probs, n_sims, n_places)

    out = (
        pd.DataFrame(
            {
                "horse": horses,
                "win_prob": win_counts / n_sims,
                "sim_place_prob": place_counts / n_sims,
            }
        )
        .sort_values(["sim_place_prob", "win_prob"], ascending=False)
        .reset_index(drop=True)
    )

    out["sim_place_price"] = 1 / out["sim_place_prob"]
    return out


def simulate_place_prices(data: pd.DataFrame) -> pd.DataFrame:
    """
    Simulate place prices and add sim_place_sp and diff_proba to original dataframe.

    Args:
        data: DataFrame with columns ['horse_name', 'betfair_win_sp', 'betfair_place_sp']

    Returns:
        Original dataframe with added columns: 'sim_place_sp' and 'diff_proba'
    """

    race_class = data["race_class"].iloc[0]
    # Create a copy to avoid modifying original data
    df_work = data[["horse_name", "betfair_win_sp", "betfair_place_sp"]].copy()

    # Ensure proper data types
    df_work = df_work.astype({"betfair_win_sp": "float", "betfair_place_sp": "float"})

    # Run simulation
    sim_results = simulate_place_counts(
        df_work,
        price_col="betfair_win_sp",
        horse_col="horse_name",
        n_places=calculate_num_places(len(df_work), race_class),
        n_sims=10000,
        seed=7,
    )

    # Calculate probabilities and differences
    sim_results["sim_proba"] = (1 / sim_results["sim_place_sp"]).round(4)
    sim_results["place_proba"] = (
        1
        / df_work.set_index("horse_name")
        .loc[sim_results["horse"], "betfair_place_sp"]
        .values
    ).round(4)
    sim_results["diff_proba"] = sim_results["sim_proba"] - sim_results["place_proba"]

    # Merge back to original dataframe
    result = data.merge(
        sim_results[["horse", "sim_place_sp", "diff_proba"]],
        left_on="horse_name",
        right_on="horse",
        how="left",
    ).drop(columns=["horse"])

    result = result.assign(
        sim_place_sp=result["sim_place_sp"].round(1),
        diff_proba=result["diff_proba"].round(2),
    )

    return result


def calculate_num_places(number_of_runners: int, race_class: str) -> int:
    if pd.to_numeric(race_class, errors="coerce") == 1:
        return 3
    if number_of_runners < 8:
        return 2
    if number_of_runners < 16:
        return 3
    return 4

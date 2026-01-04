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
    df,
    price_col="betfair_win_sp",
    horse_col="horse_name",
    n_places=3,
    n_sims=10000,
    seed=42,
):

    dict(zip(df["horse_name"], df["betfair_place_sp"]))
    """Optimized - assumes unique horses in df."""
    horses = df[horse_col].values
    prices = df[price_col].values

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
                "place_prob_topN": place_counts / n_sims,
            }
        )
        .sort_values(["place_prob_topN", "win_prob"], ascending=False)
        .reset_index(drop=True)
    )

    out["sim_place_sp"] = 1 / out["place_prob_topN"]
    return out

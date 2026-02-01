"""
TradeCycle - Single object representing one trading cycle's complete state.

Consolidates ReconciliationResult, DecisionResult, ExecutionSummary
and handles all logging in one place.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime

from api_helpers.helpers.logging_config import I, W

from .decision_engine import DecisionResult
from .executor import ExecutionSummary
from .models import SelectionState
from .reconciliation import ReconciliationResult


@dataclass
class CumulativeStats:
    """Running totals across all cycles."""

    cycles_run: int = 0
    orders_placed: int = 0
    orders_matched: int = 0
    orders_failed: int = 0
    cash_outs: int = 0
    invalidations: int = 0
    total_matched_value: float = 0.0

    def update(
        self, execution: ExecutionSummary | None, selections: list[SelectionState]
    ) -> None:
        """Update stats from a cycle's results."""
        self.cycles_run += 1
        if execution:
            self.orders_placed += execution.orders_placed
            self.orders_matched += execution.orders_matched
            self.orders_failed += execution.orders_failed
            self.cash_outs += execution.cash_outs
            self.invalidations += execution.invalidations

        # Sum total matched from all selections
        self.total_matched_value = sum(s.total_matched for s in selections)


# Global cumulative stats - persists across cycles
_cumulative_stats = CumulativeStats()


def get_cumulative_stats() -> CumulativeStats:
    """Get the global cumulative stats."""
    return _cumulative_stats


def reset_cumulative_stats() -> None:
    """Reset cumulative stats (e.g., for testing)."""
    global _cumulative_stats
    _cumulative_stats = CumulativeStats()


@dataclass
class TradeCycle:
    """Complete state of a single trading cycle."""

    cycle_num: int
    timestamp: datetime = field(default_factory=datetime.now)

    # Results from each stage (populated as cycle progresses)
    reconciliation: ReconciliationResult | None = None
    selections: list[SelectionState] = field(default_factory=list)
    decision: DecisionResult | None = None
    execution: ExecutionSummary | None = None

    def _build_selection_lookup(self) -> dict[str, SelectionState]:
        """Build a lookup from unique_id to SelectionState."""
        return {s.unique_id: s for s in self.selections}

    def _format_horse(self, unique_id: str, lookup: dict[str, SelectionState]) -> str:
        """Format horse name and race time for logging."""
        sel = lookup.get(unique_id)
        if not sel:
            return unique_id[:11]

        race_time = sel.race_time.strftime("%H:%M") if sel.race_time else "??:??"
        horse = sel.horse_name[:12]
        return f"{race_time} {horse}"

    @property
    def has_activity(self) -> bool:
        """Return True if anything meaningful happened this cycle."""
        if self.reconciliation and self.reconciliation.has_activity():
            return True
        if self.decision and (
            self.decision.orders
            or self.decision.cash_out_market_ids
            or self.decision.invalidations
        ):
            return True
        if self.execution and self.execution.has_activity:
            return True
        return False

    def log(self, verbose: bool = False, clear_screen: bool = True) -> None:
        """
        Log a summary of the entire cycle.

        Args:
            verbose: If True, log individual selections. If False, just summary.
            clear_screen: If True, clear terminal before logging.
        """
        # Update cumulative stats
        _cumulative_stats.update(self.execution, self.selections)

        # Clear screen for fresh view
        if clear_screen:
            os.system("clear" if os.name != "nt" else "cls")

        time_str = self.timestamp.strftime("%H:%M:%S")

        # Header with cumulative summary
        I(f"═══════════════════════════════════════════════════════════")
        I(f"TRADER | Cycle {self.cycle_num} @ {time_str}")
        I(f"═══════════════════════════════════════════════════════════")

        # Cumulative stats bar
        self._log_cumulative_summary()

        I(f"───────────────────────────────────────────────────────────")

        # Selections summary
        if self.selections:
            self._log_selections(verbose)

        # This cycle's activity
        if self.has_activity:
            I(f"───────────────────────────────────────────────────────────")
            I(f"THIS CYCLE:")

            if self.reconciliation:
                self._log_reconciliation()

            if self.decision:
                self._log_decision()

            if self.execution and self.execution.has_activity:
                self._log_execution()

        I(f"═══════════════════════════════════════════════════════════")

    def _log_cumulative_summary(self) -> None:
        """Log running totals."""
        s = _cumulative_stats

        # Compact summary line
        parts = []
        if s.orders_placed > 0:
            parts.append(f"📤 {s.orders_placed} placed")
        if s.orders_matched > 0:
            parts.append(f"✅ {s.orders_matched} matched")
        if s.orders_failed > 0:
            parts.append(f"❌ {s.orders_failed} failed")
        if s.cash_outs > 0:
            parts.append(f"💸 {s.cash_outs} cashed out")
        if s.invalidations > 0:
            parts.append(f"⚠️ {s.invalidations} voided")

        if parts:
            I(f"SESSION: {' | '.join(parts)}")
            I(f"         Total matched: £{s.total_matched_value:.2f}")
        else:
            I(f"SESSION: No activity yet")

    def _log_reconciliation(self) -> None:
        """Log reconciliation results."""
        r = self.reconciliation
        if not r:
            return

        if r.orders_cancelled > 0 or r.selections_upserted > 0:
            I(
                f"  RECONCILE: {r.orders_cancelled} cancelled, "
                f"{r.selections_upserted} synced"
            )
        if r.errors > 0:
            W(f"  ⚠️ {r.errors} reconciliation errors")

    def _log_selections(self, verbose: bool) -> None:
        """Log selection state summary grouped by race time."""
        total = len(self.selections)
        valid = sum(1 for s in self.selections if s.valid)
        has_bet = sum(1 for s in self.selections if s.has_bet)
        fully_matched = sum(1 for s in self.selections if s.fully_matched)
        pending = has_bet - fully_matched

        I(
            f"SELECTIONS: {total} total | {valid} valid | {has_bet} bets ({fully_matched} matched, {pending} pending)"
        )

        # Always show selections with bets (compact view)
        bets = [s for s in self.selections if s.has_bet]
        if bets:
            I(f"  ACTIVE BETS:")
            for s in sorted(bets, key=lambda x: x.race_time):
                race_time = s.race_time.strftime("%H:%M") if s.race_time else "??:??"
                status = "✅" if s.fully_matched else "⏳"
                progress = f"£{s.total_matched:.2f}/£{s.calculated_stake:.2f}"
                I(
                    f"    {status} {race_time} {s.horse_name[:15]:<15} {s.selection_type.value} @ {s.requested_odds} {progress}"
                )

        if verbose:
            # Group all by race time for full view
            by_race: dict[str, list[SelectionState]] = {}
            for s in self.selections:
                race_key = s.race_time.strftime("%H:%M") if s.race_time else "??:??"
                if race_key not in by_race:
                    by_race[race_key] = []
                by_race[race_key].append(s)

            I(f"  ALL SELECTIONS:")
            for race_time in sorted(by_race.keys()):
                selections = by_race[race_time]
                I(f"    ┌─ {race_time} ({len(selections)} selections)")
                for s in selections:
                    status = "✓" if s.valid else "✗"
                    bet = "💰" if s.has_bet else ""
                    back = s.current_back_price or "-"
                    lay = s.current_lay_price or "-"
                    I(
                        f"    │ {status} {s.horse_name[:15]:<15} "
                        f"{s.selection_type.value} @ {s.requested_odds:<5} "
                        f"B:{back:<5} L:{lay:<5} {bet}"
                    )

    def _log_decision(self) -> None:
        """Log decision results with horse names."""
        d = self.decision
        if not d:
            return

        orders = len(d.orders)
        cash_outs = len(d.cash_out_market_ids)
        invalidations = len(d.invalidations)

        if not (orders or cash_outs or invalidations):
            return

        lookup = self._build_selection_lookup()

        for order_with_state in d.orders:
            o = order_with_state.order
            limit = "✓" if order_with_state.within_stake_limit else "⚠️ LIMIT"
            horse_info = self._format_horse(o.strategy, lookup)
            I(f"  → ORDER {o.side} £{o.size:.2f} @ {o.price} | {horse_info} {limit}")

        for market_id in d.cash_out_market_ids:
            horses = [s.horse_name for s in self.selections if s.market_id == market_id]
            horse_str = ", ".join(horses[:2]) if horses else market_id
            I(f"  → CASH OUT {horse_str}")

        for unique_id, reason in d.invalidations:
            horse_info = self._format_horse(unique_id, lookup)
            W(f"  → INVALID {horse_info}: {reason}")

    def _log_execution(self) -> None:
        """Log execution results."""
        e = self.execution
        if not e:
            return

        parts = []
        if e.orders_placed > 0:
            parts.append(f"{e.orders_placed} placed")
        if e.orders_matched > 0:
            parts.append(f"{e.orders_matched} matched")
        if e.orders_failed > 0:
            parts.append(f"{e.orders_failed} failed")
        if e.orders_skipped > 0:
            parts.append(f"{e.orders_skipped} skipped")
        if e.orders_cancelled > 0:
            parts.append(f"{e.orders_cancelled} cancelled")
        if e.cash_outs > 0:
            parts.append(f"{e.cash_outs} cashed out")
        if e.invalidations > 0:
            parts.append(f"{e.invalidations} invalidated")

        if parts:
            I(f"  RESULT: {' | '.join(parts)}")

    def summary_dict(self) -> dict:
        """Return a dict summary of the cycle for programmatic use."""
        return {
            "cycle_num": self.cycle_num,
            "timestamp": self.timestamp.isoformat(),
            "reconciliation": (
                self.reconciliation.to_dict() if self.reconciliation else None
            ),
            "selections_count": len(self.selections),
            "selections_valid": sum(1 for s in self.selections if s.valid),
            "selections_with_bets": sum(1 for s in self.selections if s.has_bet),
            "orders_to_place": len(self.decision.orders) if self.decision else 0,
            "execution": {
                "placed": self.execution.orders_placed if self.execution else 0,
                "matched": self.execution.orders_matched if self.execution else 0,
                "failed": self.execution.orders_failed if self.execution else 0,
            },
            "cumulative": {
                "total_placed": _cumulative_stats.orders_placed,
                "total_matched": _cumulative_stats.orders_matched,
                "total_matched_value": _cumulative_stats.total_matched_value,
            },
        }

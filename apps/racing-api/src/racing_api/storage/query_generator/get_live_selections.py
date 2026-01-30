class LiveSelectionsSQLGenerator:
    @staticmethod
    def define_get_live_selection_sql(view_name: str) -> str:
        return f"""SELECT 
                unique_id, 
                race_id,
                race_time, 
                race_date, 
                horse_id, 
                horse_name, 
                selection_type, 
                market_type, 
                market_id, 
                selection_id, 
                requested_odds, 
                valid, 
                invalidated_at, 
                invalidated_reason, 
                size_matched, 
                average_price_matched, 
                cashed_out, 
                fully_matched,
                created_at,
                bet_outcome, 
                price_matched, 
                profit, 
                commission, 
                side,
                FALSE as is_pending,
                NULL::numeric as requested_size
            FROM live_betting.{view_name};
        """

    @staticmethod
    def get_to_run_sql():
        return LiveSelectionsSQLGenerator.define_get_live_selection_sql(
            "v_upcoming_bets"
        )

    @staticmethod
    def get_ran_sql():
        return LiveSelectionsSQLGenerator.define_get_live_selection_sql(
            "v_live_results"
        )

    @staticmethod
    def get_pending_orders_sql():
        """Fetch pending orders joined with selections to get horse/race info."""
        return """
            SELECT 
                s.unique_id,
                s.race_id,
                s.race_time,
                s.race_date,
                s.horse_id,
                s.horse_name,
                COALESCE(po.selection_type, s.selection_type) as selection_type,
                s.market_type,
                po.market_id,
                po.selection_id,
                po.requested_price as requested_odds,
                s.valid,
                s.invalidated_at,
                s.invalidated_reason,
                COALESCE(po.matched_size, 0) as size_matched,
                po.matched_price as average_price_matched,
                FALSE as cashed_out,
                FALSE as fully_matched,
                s.created_at,
                'TO_BE_RUN' as bet_outcome,
                po.matched_price as price_matched,
                NULL::numeric as profit,
                NULL::numeric as commission,
                po.side,
                TRUE as is_pending,
                po.requested_size as requested_size
            FROM live_betting.pending_orders po
            JOIN live_betting.selections s 
                ON LEFT(po.selection_unique_id, 11) = s.unique_id
            WHERE s.race_time > NOW()
              AND s.valid = TRUE
              AND po.status = 'PENDING'
              AND s.race_date = CURRENT_DATE;
        """

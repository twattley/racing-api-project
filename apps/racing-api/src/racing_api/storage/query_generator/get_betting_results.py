class BettingResultsSQLGenerator:
    @staticmethod
    def define_betting_results_sql():
        return """
            WITH selections AS (
                SELECT 
                    unique_id,
                    race_id,
                    race_time,
                    race_date,
                    horse_id,
                    valid,
                    horse_name,
                    selection_type,
                    market_type,
                    COALESCE(average_price_matched, requested_odds) AS betfair_sp,
                    created_at
                FROM live_betting.selections
                WHERE valid = true
            ),
            results_with_booleans AS (
                SELECT 
                    s.*, 
                    pd.finishing_position, 
                    pd.number_of_runners,
                    
                    -- Win boolean: true if finishing_position = '1'
                    CASE 
                        WHEN pd.finishing_position = '1' THEN true 
                        ELSE false 
                    END AS win,
                    
                    -- Place boolean based on number of runners  
                    CASE 
                        -- Less than 8 runners: places 1-2
                        WHEN pd.number_of_runners < 8 AND pd.finishing_position IN ('1', '2') THEN true
                        -- 8-15 runners: places 1-3  
                        WHEN pd.number_of_runners BETWEEN 8 AND 15 AND pd.finishing_position IN ('1', '2', '3') THEN true
                        -- 16+ runners: places 1-4
                        WHEN pd.number_of_runners >= 16 AND pd.finishing_position IN ('1', '2', '3', '4') THEN true
                        ELSE false
                    END AS placed
                    
                FROM selections s 
                LEFT JOIN public.unioned_results_data pd
                    ON s.horse_id = pd.horse_id
                    AND s.race_id = pd.race_id
                WHERE pd.finishing_position IS NOT NULL
            ),
            profit_loss_calc AS (
                SELECT 
                    *,
                    
                    -- Single profit/loss calculation for each bet
                    CASE 
                        -- Back Win bets
                        WHEN selection_type = 'BACK' AND market_type = 'WIN' AND win = true 
                            THEN 0.8 *(betfair_sp - 1)
                        WHEN selection_type = 'BACK' AND market_type = 'WIN' AND win = false 
                            THEN -1
                            
                        -- Back Place bets
                        WHEN selection_type = 'BACK' AND market_type = 'PLACE' AND placed = true 
                            THEN 0.8 *(betfair_sp - 1)
                        WHEN selection_type = 'BACK' AND market_type = 'PLACE' AND placed = false 
                            THEN -1
                            
                        -- Lay Win bets  
                        WHEN selection_type = 'LAY' AND market_type = 'WIN' AND win = true
                            THEN -(betfair_sp - 1)
                        WHEN selection_type = 'LAY' AND market_type = 'WIN' AND win = false
                            THEN 0.8
                            
                        -- Lay Place bets
                        WHEN selection_type = 'LAY' AND market_type = 'PLACE' AND placed = true
                            THEN -(betfair_sp - 1)
                        WHEN selection_type = 'LAY' AND market_type = 'PLACE' AND placed = false
                            THEN 0.8
                        ELSE 0
                    END AS profit_loss,
                    
                    -- Stake calculation for each bet type
                    CASE 
                        -- BACK bets always stake 1 unit
                        WHEN selection_type = 'BACK' THEN 1
                        -- LAY bets stake the liability (betfair_sp - 1)
                        WHEN selection_type = 'LAY' THEN betfair_sp - 1
                        ELSE 0
                    END AS stake
                    
                FROM results_with_booleans
            ),
            running_totals_and_counts AS (
                SELECT 
                    unique_id,
                    created_at,
                    profit_loss,
                    stake,
                    selection_type,
                    market_type,
                    
                    -- Running P&L totals - now using the pre-calculated profit_loss column
                    SUM(CASE 
                        WHEN selection_type = 'BACK' AND market_type = 'WIN' THEN profit_loss
                        ELSE 0 
                    END) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS running_total_back_win,
                    
                    SUM(CASE 
                        WHEN selection_type = 'BACK' AND market_type = 'PLACE' THEN profit_loss
                        ELSE 0 
                    END) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS running_total_back_place,
                    
                    SUM(CASE 
                        WHEN selection_type = 'LAY' AND market_type = 'WIN' THEN profit_loss
                        ELSE 0 
                    END) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS running_total_lay_win,
                    
                    SUM(CASE 
                        WHEN selection_type = 'LAY' AND market_type = 'PLACE' THEN profit_loss
                        ELSE 0 
                    END) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS running_total_lay_place,
                    
                    -- Overall running total - simplified
                    SUM(profit_loss) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS running_total_all_bets,
                    
                    -- Running stake totals for ROI calculation
                    SUM(CASE 
                        WHEN selection_type = 'BACK' AND market_type = 'WIN' THEN stake
                        ELSE 0 
                    END) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS running_stake_back_win,
                    
                    SUM(CASE 
                        WHEN selection_type = 'BACK' AND market_type = 'PLACE' THEN stake
                        ELSE 0 
                    END) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS running_stake_back_place,
                    
                    SUM(CASE 
                        WHEN selection_type = 'LAY' AND market_type = 'WIN' THEN stake
                        ELSE 0 
                    END) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS running_stake_lay_win,
                    
                    SUM(CASE 
                        WHEN selection_type = 'LAY' AND market_type = 'PLACE' THEN stake
                        ELSE 0 
                    END) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS running_stake_lay_place,
                    
                    -- Total running stake
                    SUM(stake) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS running_stake_total,
                    
                    -- Running counts for each bet type
                    COUNT(CASE 
                        WHEN selection_type = 'BACK' AND market_type = 'WIN' THEN 1 
                    END) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS total_back_win_count,
                    
                    COUNT(CASE 
                        WHEN selection_type = 'BACK' AND market_type = 'PLACE' THEN 1 
                    END) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS total_back_place_count,
                    
                    COUNT(CASE 
                        WHEN selection_type = 'LAY' AND market_type = 'WIN' THEN 1 
                    END) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS total_lay_win_count,
                    
                    COUNT(CASE 
                        WHEN selection_type = 'LAY' AND market_type = 'PLACE' THEN 1 
                    END) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS total_lay_place_count,
                    
                    -- Total bet count
                    COUNT(*) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS total_bet_count
                    
                FROM profit_loss_calc
            ),
            roi_calculations AS (
                SELECT 
                    *,
                    
                    -- Running ROI calculations (as percentages)
                    CASE 
                        WHEN running_stake_back_win > 0 
                        THEN ROUND((running_total_back_win / running_stake_back_win) * 100, 2)
                        ELSE NULL 
                    END AS running_roi_back_win,
                    
                    CASE 
                        WHEN running_stake_back_place > 0 
                        THEN ROUND((running_total_back_place / running_stake_back_place) * 100, 2)
                        ELSE NULL 
                    END AS running_roi_back_place,
                    
                    CASE 
                        WHEN running_stake_lay_win > 0 
                        THEN ROUND((running_total_lay_win / running_stake_lay_win) * 100, 2)
                        ELSE NULL 
                    END AS running_roi_lay_win,
                    
                    CASE 
                        WHEN running_stake_lay_place > 0 
                        THEN ROUND((running_total_lay_place / running_stake_lay_place) * 100, 2)
                        ELSE NULL 
                    END AS running_roi_lay_place,
                    
                    CASE 
                        WHEN running_stake_total > 0 
                        THEN ROUND((running_total_all_bets / running_stake_total) * 100, 2)
                        ELSE NULL 
                    END AS running_roi_overall
                    
                FROM running_totals_and_counts
            )
            SELECT 
                unique_id, 
                created_at,
                profit_loss,
                running_total_back_win, 
                running_total_back_place, 
                running_total_lay_win, 
                running_total_lay_place, 
                running_total_all_bets,
                running_stake_total,
                running_roi_back_win,
                running_roi_back_place,
                running_roi_lay_win,
                running_roi_lay_place,
                running_roi_overall,
                total_back_win_count,
                total_back_place_count,
                total_lay_win_count,
                total_lay_place_count,
                total_bet_count
            FROM roi_calculations
            ORDER BY created_at;
        """

    @staticmethod
    def get_betting_results_sql():
        """
        Returns the query for betting results.
        """
        query = BettingResultsSQLGenerator.define_betting_results_sql()
        return query

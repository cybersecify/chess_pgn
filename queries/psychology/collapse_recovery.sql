-- Collapse recovery: win rate after different types of losses (rapid)
-- Long loss (40+ moves) = you had a chance but lost = feels worse psychologically
-- Short loss (< 40 moves) = blunder/tactic missed early
WITH ordered AS (
  SELECT end_time, user_result, move_count,
         LAG(user_result) OVER (ORDER BY end_time) AS prev_result,
         LAG(move_count)  OVER (ORDER BY end_time) AS prev_moves
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = 'rapid' AND user_result IS NOT NULL AND end_time IS NOT NULL
)
SELECT
  CASE
    WHEN prev_result = 'lose' AND prev_moves >= 40 THEN 'After long loss  (40+ moves — collapse)'
    WHEN prev_result = 'lose' AND prev_moves <  40 THEN 'After short loss (< 40 moves — blunder)'
    WHEN prev_result = 'win'  AND prev_moves >= 40 THEN 'After long win   (40+ moves — grind)'
    WHEN prev_result = 'win'  AND prev_moves <  40 THEN 'After short win  (< 40 moves — quick)'
    WHEN prev_result = 'draw'                      THEN 'After draw'
    ELSE 'Other'
  END AS context,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM ordered
WHERE prev_result IS NOT NULL AND prev_moves IS NOT NULL
GROUP BY context
ORDER BY context

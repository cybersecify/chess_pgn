-- Win rate by game length bucket (half-moves, rapid)
-- Reveals if you're stronger in tactical short games or long grinds
SELECT
  CASE
    WHEN move_count <  20 THEN '1. < 20  moves (blunder/resign early)'
    WHEN move_count <  40 THEN '2. 20-39 moves (short game)'
    WHEN move_count <  60 THEN '3. 40-59 moves (medium game)'
    WHEN move_count <  80 THEN '4. 60-79 moves (long game)'
    ELSE                       '5. 80+   moves (endgame grind)'
  END AS length_bucket,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = 'rapid' AND move_count IS NOT NULL AND user_result IS NOT NULL
GROUP BY length_bucket
ORDER BY length_bucket

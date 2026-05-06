-- Tilt detection: win rate in the game immediately after a win/loss/draw (rapid)
-- Low win_pct after a loss = tilting; high win_pct after a win = hot streak
WITH ordered AS (
  SELECT end_time, user_result,
         LAG(user_result) OVER (ORDER BY end_time) AS prev_result
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = $TIME_CLASS AND user_result IS NOT NULL AND end_time IS NOT NULL
)
SELECT prev_result AS after_a,
       COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM ordered
WHERE prev_result IS NOT NULL
GROUP BY prev_result
ORDER BY prev_result

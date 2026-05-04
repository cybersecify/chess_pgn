-- White vs black mindset gap after a loss (rapid)
-- Does losing as white make you play passively as black next game (and vice versa)?
WITH ordered AS (
  SELECT end_time, color, user_result,
         LAG(user_result) OVER (ORDER BY end_time) AS prev_result,
         LAG(color)       OVER (ORDER BY end_time) AS prev_color
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = 'rapid' AND user_result IS NOT NULL
    AND color IS NOT NULL AND end_time IS NOT NULL
)
SELECT
  prev_result AS previous_game,
  prev_color  AS previous_color,
  color       AS current_color,
  COUNT(*) AS games,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM ordered
WHERE prev_result IS NOT NULL AND prev_color IS NOT NULL
GROUP BY prev_result, prev_color, color
ORDER BY prev_result, prev_color, color

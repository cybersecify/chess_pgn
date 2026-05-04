-- Rest effect: win rate based on how long since last game (rapid)
-- Shows whether rest helps or rust hurts
WITH ordered AS (
  SELECT end_time, user_result,
         LAG(end_time) OVER (ORDER BY end_time) AS prev_end_time
  FROM games
  WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
    AND time_class = 'rapid' AND user_result IS NOT NULL AND end_time IS NOT NULL
)
SELECT
  CASE
    WHEN prev_end_time IS NULL                          THEN '5. First game ever'
    WHEN end_time - prev_end_time > 7 * 86400           THEN '4. 7+ days break'
    WHEN end_time - prev_end_time > 3 * 86400           THEN '3. 3-7 days break'
    WHEN end_time - prev_end_time > 86400               THEN '2. 1-3 days break'
    WHEN end_time - prev_end_time > 3600                THEN '1. 1-24 hrs break'
    ELSE                                                     '0. Same session'
  END AS break_length,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM ordered
GROUP BY break_length
ORDER BY break_length

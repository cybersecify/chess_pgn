-- Rematch record: result in game N+1 vs the same opponent (rapid)
-- Shows revenge/tilt pattern — do you bounce back or crumble against same opponent?
WITH ordered AS (
  SELECT end_time, opponent, user_result,
         LAG(opponent)    OVER (ORDER BY end_time) AS prev_opponent,
         LAG(user_result) OVER (ORDER BY end_time) AS prev_result
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = $TIME_CLASS AND user_result IS NOT NULL AND opponent IS NOT NULL
)
SELECT prev_result AS first_game_result,
       COUNT(*) AS rematches,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM ordered
WHERE prev_opponent = opponent AND prev_result IS NOT NULL
GROUP BY prev_result
ORDER BY prev_result

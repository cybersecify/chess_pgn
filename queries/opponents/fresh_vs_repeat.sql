-- First game vs repeat opponent win rate (rapid)
-- Do you do better vs unknown opponents or when you have history?
WITH opponent_history AS (
  SELECT opponent, end_time, user_result,
         ROW_NUMBER() OVER (PARTITION BY opponent ORDER BY end_time) AS game_num
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = $TIME_CLASS AND user_result IS NOT NULL AND end_time IS NOT NULL
)
SELECT
  CASE
    WHEN game_num = 1 THEN '1st game (fresh opponent)'
    WHEN game_num = 2 THEN '2nd game (1 prior game)'
    WHEN game_num <= 4 THEN '3rd–4th game (some history)'
    ELSE                   '5th+ game (well known)'
  END AS familiarity,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM opponent_history
GROUP BY familiarity
ORDER BY
  CASE familiarity
    WHEN '1st game (fresh opponent)'    THEN 1
    WHEN '2nd game (1 prior game)'      THEN 2
    WHEN '3rd–4th game (some history)'  THEN 3
    ELSE 4
  END

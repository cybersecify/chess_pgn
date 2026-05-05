-- Longest winning streaks (rapid)
WITH ranked AS (
  SELECT end_time, user_result,
         ROW_NUMBER() OVER (ORDER BY end_time) -
         ROW_NUMBER() OVER (PARTITION BY user_result ORDER BY end_time) AS grp
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = 'rapid' AND user_result IS NOT NULL
),
streaks AS (
  SELECT user_result, COUNT(*) AS streak_len,
         MIN(end_time) AS started, MAX(end_time) AS ended
  FROM ranked
  GROUP BY user_result, grp
)
SELECT streak_len,
       strftime(to_timestamp(started), '%Y-%m-%d') AS started,
       strftime(to_timestamp(ended),   '%Y-%m-%d') AS ended
FROM streaks
WHERE user_result = 'win'
ORDER BY streak_len DESC
LIMIT 10

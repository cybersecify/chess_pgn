-- Monthly win rate trend (rapid, last 12 months)
SELECT strftime(to_timestamp(end_time), '%Y-%m') AS month,
       COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = $TIME_CLASS AND end_time IS NOT NULL
GROUP BY month
ORDER BY month DESC
LIMIT 12

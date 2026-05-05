-- Win rate by day of week (rapid, IST)
SELECT
  CASE dayofweek(to_timestamp(end_time))
    WHEN 0 THEN '0-Sun' WHEN 1 THEN '1-Mon' WHEN 2 THEN '2-Tue'
    WHEN 3 THEN '3-Wed' WHEN 4 THEN '4-Thu' WHEN 5 THEN '5-Fri' WHEN 6 THEN '6-Sat'
  END AS day,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) AS wins,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = 'rapid' AND end_time IS NOT NULL AND user_result IS NOT NULL
GROUP BY day
ORDER BY day

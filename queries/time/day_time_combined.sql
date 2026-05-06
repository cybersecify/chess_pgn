-- Day of week × time of day combined (rapid, IST, min 5 games)
-- Finds your best and worst specific slots e.g. "Friday night" vs "Monday morning"
SELECT
  CASE dayofweek(to_timestamp(end_time))
    WHEN 0 THEN '0-Sun' WHEN 1 THEN '1-Mon' WHEN 2 THEN '2-Tue'
    WHEN 3 THEN '3-Wed' WHEN 4 THEN '4-Thu' WHEN 5 THEN '5-Fri' WHEN 6 THEN '6-Sat'
  END AS day,
  CASE
    WHEN hour(to_timestamp(end_time)) BETWEEN 6  AND 11 THEN 'Morning   (06-12)'
    WHEN hour(to_timestamp(end_time)) BETWEEN 12 AND 16 THEN 'Afternoon (12-17)'
    WHEN hour(to_timestamp(end_time)) BETWEEN 17 AND 20 THEN 'Evening   (17-21)'
    ELSE                                                      'Night     (21-06)'
  END AS period,
  COUNT(*) AS games,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = $TIME_CLASS AND end_time IS NOT NULL AND user_result IS NOT NULL
GROUP BY day, dayofweek(to_timestamp(end_time)), period
HAVING COUNT(*) >= 5
ORDER BY dayofweek(to_timestamp(end_time)), period

-- Win rate by time of day (rapid, IST)
SELECT
  CASE
    WHEN hour(to_timestamp(end_time)) BETWEEN 6  AND 11 THEN '1. Morning   (06-12)'
    WHEN hour(to_timestamp(end_time)) BETWEEN 12 AND 16 THEN '2. Afternoon (12-17)'
    WHEN hour(to_timestamp(end_time)) BETWEEN 17 AND 20 THEN '3. Evening   (17-21)'
    ELSE                                                      '4. Night     (21-06)'
  END AS period,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) AS wins,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND end_time IS NOT NULL AND user_result IS NOT NULL
GROUP BY period
ORDER BY period

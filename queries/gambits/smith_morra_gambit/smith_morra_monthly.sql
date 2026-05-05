-- Smith-Morra Gambit — monthly win rate trend
SELECT
  strftime(to_timestamp(end_time), '%Y-%m')                                          AS month,
  time_class,
  COUNT(*)                                                                             AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                             AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                             AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE white = $USERNAME
  AND opening LIKE '%Smith Morra%'
GROUP BY month, time_class
HAVING COUNT(*) >= 3
ORDER BY time_class, month

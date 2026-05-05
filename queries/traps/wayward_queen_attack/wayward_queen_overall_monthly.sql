SELECT
  strftime(to_timestamp(end_time), '%Y-%m') AS month,
  COUNT(*) AS total_games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE white = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
  AND pgn LIKE '%1. e4%'
GROUP BY month
HAVING COUNT(*) >= 5
ORDER BY month

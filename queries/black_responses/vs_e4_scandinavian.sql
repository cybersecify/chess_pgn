-- vs 1.e4 — Scandinavian (1...d5) win rate by time class and monthly trend
SELECT
  time_class,
  strftime(to_timestamp(end_time), '%Y-%m') AS month,
  COUNT(*)                                   AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE black = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])1\. e4')
  AND regexp_matches(pgn, '(^|[\s}])1\.\.\. d5')
GROUP BY time_class, month
HAVING COUNT(*) >= 5
ORDER BY time_class, month

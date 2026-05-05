SELECT
  CAST(strftime(to_timestamp(end_time), '%Y') AS INTEGER) * 10 +
    CASE WHEN CAST(strftime(to_timestamp(end_time), '%m') AS INTEGER) <= 6 THEN 1 ELSE 2 END AS half,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct,
  ROUND(AVG(CASE WHEN color = 'white' THEN white_elo ELSE black_elo END), 0) AS avg_my_elo,
  ROUND(AVG(CASE WHEN color = 'white' THEN black_elo ELSE white_elo END), 0) AS avg_opp_elo
FROM games
WHERE white = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
  AND pgn LIKE '%1. e4%'
  AND move_count > 5
GROUP BY half
HAVING COUNT(*) >= 5
ORDER BY half

-- Icelandic Gambit — monthly win rate trend
SELECT strftime(to_timestamp(end_time), '%Y-%m')                                          AS month,
       COUNT(*)                                                                            AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                             AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                             AS losses,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct,
       ROUND(AVG(CASE WHEN color = 'black' THEN white_elo ELSE black_elo END), 0)        AS avg_opp_elo
FROM games
WHERE black = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])3\.\.\. e5')
  AND opening LIKE '%Scandinavian%'
GROUP BY month
HAVING COUNT(*) >= 3
ORDER BY month

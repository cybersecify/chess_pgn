-- Icelandic Gambit — overall summary by time class
SELECT time_class,
       COUNT(*)                                                                            AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                             AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                             AS losses,
       SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END)                             AS draws,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct,
       ROUND(AVG(move_count), 1)                                                          AS avg_moves,
       ROUND(AVG(CASE WHEN color = 'black' THEN white_elo ELSE black_elo END), 0)        AS avg_opp_elo
FROM games
WHERE black = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])3\.\.\. e5')
  AND opening LIKE '%Scandinavian%'
GROUP BY time_class
ORDER BY games DESC

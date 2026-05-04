-- Icelandic Gambit — how White responds to 3...e5 and win rate per response
SELECT regexp_extract(pgn, '4\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)                        AS white_4th_move,
       COUNT(*)                                                                            AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                             AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                             AS losses,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct,
       ROUND(AVG(move_count), 1)                                                          AS avg_moves
FROM games
WHERE black = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])3\.\.\. e5')
  AND opening LIKE '%Scandinavian%'
GROUP BY white_4th_move
HAVING COUNT(*) >= 3
ORDER BY games DESC

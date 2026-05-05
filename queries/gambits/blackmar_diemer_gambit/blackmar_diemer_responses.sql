-- Blackmar-Diemer Gambit — how Black responds (3rd move) and win rate
SELECT
  regexp_extract(pgn, '3\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)                    AS black_3rd_move,
  COUNT(*)                                                                             AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                             AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                             AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE white = $USERNAME
  AND opening LIKE '%Blackmar%'
GROUP BY black_3rd_move
HAVING COUNT(*) >= 3
ORDER BY games DESC

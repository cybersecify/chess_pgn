-- vs 1...c6 and 1...e6 — consistent d4 system, win rate by time class
SELECT
  regexp_extract(pgn, '1\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1) AS black_1st_move,
  time_class,
  regexp_extract(pgn, '2\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)     AS your_2nd_move,
  COUNT(*)                                                         AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)          AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)          AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE white = $USERNAME
  AND regexp_extract(pgn, '1\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1) IN ('c6', 'e6')
GROUP BY black_1st_move, time_class, your_2nd_move
HAVING COUNT(*) >= 3
ORDER BY black_1st_move, time_class, games DESC

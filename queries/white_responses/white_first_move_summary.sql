-- White responses — your 2nd move vs every Black first move with win rate
SELECT
  regexp_extract(pgn, '1\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1) AS black_1st_move,
  regexp_extract(pgn, '2\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)     AS your_2nd_move,
  COUNT(*)                                                         AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)          AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)          AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE white = $USERNAME
GROUP BY black_1st_move, your_2nd_move
HAVING COUNT(*) >= 10
ORDER BY black_1st_move, games DESC

-- Black responses — your reply to every White first move with win rate
SELECT
  regexp_extract(pgn, '1\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)   AS white_1st_move,
  regexp_extract(pgn, '1\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1) AS your_reply,
  COUNT(*)                                                        AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)         AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)         AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE black = $USERNAME
GROUP BY white_1st_move, your_reply
HAVING COUNT(*) >= 10
ORDER BY white_1st_move, games DESC

-- vs 1.Nc3 — second biggest gap (~22% win rate), breakdown by reply
SELECT
  time_class,
  regexp_extract(pgn, '1\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1) AS your_reply,
  regexp_extract(pgn, '2\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)     AS white_2nd_move,
  COUNT(*)                                                         AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)          AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)          AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE black = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])1\. Nc3')
GROUP BY time_class, your_reply, white_2nd_move
HAVING COUNT(*) >= 3
ORDER BY time_class, games DESC

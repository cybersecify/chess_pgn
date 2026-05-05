-- vs 1.d4 — your replies and win rate per time class
SELECT
  time_class,
  regexp_extract(pgn, '1\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1) AS your_reply,
  COUNT(*)                                                         AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)          AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)          AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE black = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])1\. d4')
GROUP BY time_class, your_reply
HAVING COUNT(*) >= 5
ORDER BY time_class, games DESC

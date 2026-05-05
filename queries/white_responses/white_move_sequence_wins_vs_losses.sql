-- vs 1...e5 (WQ) — White moves 3-8 win rate per move choice (wins vs losses)
SELECT
  move_num,
  white_move,
  COUNT(*)                                                        AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)         AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)         AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM (
  SELECT user_result, 3 AS move_num,
    regexp_extract(pgn, '3\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1) AS white_move
  FROM games WHERE white = $USERNAME AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
  UNION ALL
  SELECT user_result, 4,
    regexp_extract(pgn, '4\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)
  FROM games WHERE white = $USERNAME AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
  UNION ALL
  SELECT user_result, 5,
    regexp_extract(pgn, '5\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)
  FROM games WHERE white = $USERNAME AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
  UNION ALL
  SELECT user_result, 6,
    regexp_extract(pgn, '6\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)
  FROM games WHERE white = $USERNAME AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
  UNION ALL
  SELECT user_result, 7,
    regexp_extract(pgn, '7\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)
  FROM games WHERE white = $USERNAME AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
  UNION ALL
  SELECT user_result, 8,
    regexp_extract(pgn, '8\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)
  FROM games WHERE white = $USERNAME AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
) t
WHERE white_move != ''
GROUP BY move_num, white_move
HAVING COUNT(*) >= 5
ORDER BY move_num, games DESC

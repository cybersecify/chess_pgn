-- Scandinavian vs 1.e4 — your moves 2-6 as Black: win rate per move choice
SELECT
  move_num,
  your_move,
  COUNT(*)                                                        AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)         AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)         AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM (
  SELECT user_result, 2 AS move_num,
    regexp_extract(pgn, '2\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1) AS your_move
  FROM games WHERE black = $USERNAME
    AND regexp_matches(pgn, '(^|[\s}])1\. e4')
    AND regexp_matches(pgn, '(^|[\s}])1\.\.\. d5')
  UNION ALL
  SELECT user_result, 3,
    regexp_extract(pgn, '3\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)
  FROM games WHERE black = $USERNAME
    AND regexp_matches(pgn, '(^|[\s}])1\. e4')
    AND regexp_matches(pgn, '(^|[\s}])1\.\.\. d5')
  UNION ALL
  SELECT user_result, 4,
    regexp_extract(pgn, '4\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)
  FROM games WHERE black = $USERNAME
    AND regexp_matches(pgn, '(^|[\s}])1\. e4')
    AND regexp_matches(pgn, '(^|[\s}])1\.\.\. d5')
  UNION ALL
  SELECT user_result, 5,
    regexp_extract(pgn, '5\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)
  FROM games WHERE black = $USERNAME
    AND regexp_matches(pgn, '(^|[\s}])1\. e4')
    AND regexp_matches(pgn, '(^|[\s}])1\.\.\. d5')
  UNION ALL
  SELECT user_result, 6,
    regexp_extract(pgn, '6\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)
  FROM games WHERE black = $USERNAME
    AND regexp_matches(pgn, '(^|[\s}])1\. e4')
    AND regexp_matches(pgn, '(^|[\s}])1\.\.\. d5')
) t
WHERE your_move != ''
GROUP BY move_num, your_move
HAVING COUNT(*) >= 10
ORDER BY move_num, games DESC

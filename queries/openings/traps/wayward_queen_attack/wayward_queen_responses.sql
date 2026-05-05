-- Wayward Queen Attack — win rate vs each Black response (blitz)
-- Shows which defenses give you the most trouble
WITH base AS (
  SELECT user_result, move_count,
         regexp_extract(pgn, '2\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1) AS response
  FROM games
  WHERE white = $USERNAME
    AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
    AND pgn LIKE '%1. e4%'
    AND time_class = 'blitz'
)
SELECT
  response                                                                              AS black_plays,
  COUNT(*)                                                                              AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                               AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                               AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1)  AS win_pct,
  ROUND(AVG(move_count), 1)                                                            AS avg_moves
FROM base
WHERE response != ''
GROUP BY response
HAVING COUNT(*) >= 5
ORDER BY games DESC

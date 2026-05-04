-- Wayward Queen Attack (1.e4 e5 2.Qh5) — summary by format
-- Detected from PGN moves; chess.com often mislabels these as "Kings Pawn Opening 1...e5"
SELECT time_class,
       COUNT(*)                                                                            AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                             AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                             AS losses,
       SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END)                             AS draws,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct,
       ROUND(AVG(move_count), 1)                                                          AS avg_moves
FROM games
WHERE white = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
  AND pgn LIKE '%1. e4%'
GROUP BY time_class
ORDER BY games DESC

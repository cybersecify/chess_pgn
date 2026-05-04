-- Which openings produce the most checkmates (delivered and received)?
SELECT opening,
       COUNT(*)                                                                            AS checkmate_games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                             AS you_mated,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                             AS got_mated,
       ROUND(AVG(CASE WHEN user_result = 'win'  THEN move_count END), 1)                 AS avg_moves_when_you_mate,
       ROUND(AVG(CASE WHEN user_result = 'lose' THEN move_count END), 1)                 AS avg_moves_when_mated
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND termination LIKE '%checkmate'
  AND opening IS NOT NULL AND move_count IS NOT NULL
GROUP BY opening
HAVING COUNT(*) >= 5
ORDER BY checkmate_games DESC
LIMIT 15

-- Toughest opponents — most losses (min 3 games, rapid)
SELECT opponent, COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = 'rapid' AND opponent IS NOT NULL
GROUP BY opponent
HAVING COUNT(*) >= 3
ORDER BY losses DESC
LIMIT 20

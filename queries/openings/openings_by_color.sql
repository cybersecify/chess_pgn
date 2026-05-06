-- Opening performance split by color (min 5 games, rapid)
SELECT opening, color, COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) AS wins,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = $TIME_CLASS AND opening IS NOT NULL AND color IS NOT NULL
GROUP BY opening, color
HAVING COUNT(*) >= 5
ORDER BY win_pct DESC
LIMIT 30

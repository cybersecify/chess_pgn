-- Worst openings by win rate (min 10 games, rapid)
SELECT opening, COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) AS wins,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND opening IS NOT NULL AND user_result IS NOT NULL
GROUP BY opening
HAVING COUNT(*) >= 10
ORDER BY win_pct ASC
LIMIT 10

-- Openings with highest draw rate (min 10 games, rapid)
-- High draw_pct with low win_pct = passive/drawish repertoire
SELECT opening,
       COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) / COUNT(*), 1) AS draw_pct,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND opening IS NOT NULL AND user_result IS NOT NULL
GROUP BY opening
HAVING COUNT(*) >= 10
ORDER BY draw_pct DESC
LIMIT 20

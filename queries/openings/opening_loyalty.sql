-- Opening repertoire: core vs regular vs experiments (rapid)
-- Shows which openings are your main weapons vs one-offs, and which perform best
SELECT opening,
       COUNT(*) AS games,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct,
       CASE
         WHEN COUNT(*) >= 20 THEN 'Core  (20+ games)'
         WHEN COUNT(*) >= 5  THEN 'Regular (5-19 games)'
         ELSE                     'Experiment (1-4 games)'
       END AS loyalty
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = $TIME_CLASS AND opening IS NOT NULL AND user_result IS NOT NULL
GROUP BY opening
ORDER BY games DESC

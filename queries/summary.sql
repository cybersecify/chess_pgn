-- Total games, wins, and win% by time control
SELECT time_class, COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE white = 'rathnakaragn' OR black = 'rathnakaragn'
GROUP BY time_class
ORDER BY games DESC

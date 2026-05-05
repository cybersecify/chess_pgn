-- Win rate by clock usage bucket (rapid)
SELECT
  CASE
    WHEN (CASE WHEN color = 'white' THEN white_time_used_secs ELSE black_time_used_secs END) * 100.0
         / CAST(regexp_extract(time_control, '^\d+') AS INTEGER) < 30 THEN '1. < 30%  (comfortable)'
    WHEN (CASE WHEN color = 'white' THEN white_time_used_secs ELSE black_time_used_secs END) * 100.0
         / CAST(regexp_extract(time_control, '^\d+') AS INTEGER) < 70 THEN '2. 30-70% (moderate)'
    ELSE                                                                    '3. > 70%  (under pressure)'
  END AS pressure,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) AS wins,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = 'rapid' AND color IS NOT NULL AND user_result IS NOT NULL
  AND white_time_used_secs IS NOT NULL AND black_time_used_secs IS NOT NULL
  AND time_control NOT LIKE '%/%'
GROUP BY pressure
ORDER BY pressure

-- Format switching: win rate when switching formats vs staying in same format
-- Context switching between rapid/blitz/bullet within a session
WITH ordered AS (
  SELECT end_time, time_class, user_result,
         LAG(time_class) OVER (ORDER BY end_time) AS prev_format,
         LAG(end_time)   OVER (ORDER BY end_time) AS prev_end_time
  FROM games
  WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
    AND user_result IS NOT NULL AND end_time IS NOT NULL
    AND time_class IN ('rapid', 'blitz', 'bullet')
)
SELECT
  CASE
    WHEN prev_end_time IS NULL OR end_time - prev_end_time > 3600 THEN 'First of session'
    WHEN prev_format != time_class                                 THEN 'Switched format'
    ELSE                                                               'Same format'
  END AS context,
  time_class AS format,
  COUNT(*) AS games,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM ordered
GROUP BY context, time_class
ORDER BY time_class, context

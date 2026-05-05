-- Wayward Queen Attack — monthly trend across all formats
-- Shows how your win rate with this attack has changed over time
SELECT strftime(to_timestamp(end_time), '%Y-%m')                                        AS month,
       time_class,
       COUNT(*)                                                                          AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                           AS wins,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE white = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
  AND pgn LIKE '%1. e4%'
  AND time_class IN ('blitz', 'rapid', 'bullet')
  AND end_time IS NOT NULL
GROUP BY month, time_class
HAVING COUNT(*) >= 3
ORDER BY month DESC, time_class
LIMIT 36

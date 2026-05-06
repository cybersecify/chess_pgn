-- Monthly game volume vs win rate (rapid) — do you play better with more or fewer games?
-- High volume months with low win% = grinding too much; low volume with high win% = fresh mind
SELECT strftime(to_timestamp(end_time), '%Y-%m') AS month,
       COUNT(*) AS games,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct,
       CASE
         WHEN COUNT(*) < 10  THEN 'low (<10)'
         WHEN COUNT(*) < 25  THEN 'medium (10-24)'
         WHEN COUNT(*) < 50  THEN 'high (25-49)'
         ELSE                     'very high (50+)'
       END AS volume_band
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = $TIME_CLASS AND user_result IS NOT NULL AND end_time IS NOT NULL
GROUP BY month
HAVING COUNT(*) >= 5
ORDER BY month DESC
LIMIT 24

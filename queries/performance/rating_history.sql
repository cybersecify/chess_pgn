-- Rating history (rapid, monthly)
SELECT strftime(to_timestamp(end_time), '%Y-%m') AS month,
       MAX(CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) AS elo_high,
       MIN(CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) AS elo_low
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = $TIME_CLASS AND end_time IS NOT NULL
GROUP BY month
ORDER BY month DESC
LIMIT 24

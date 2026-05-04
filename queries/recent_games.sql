-- Last 30 rapid games
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
       user_result, color, opponent,
       CASE WHEN color = 'white' THEN white_elo ELSE black_elo END AS my_elo,
       CASE WHEN color = 'white' THEN black_elo ELSE white_elo END AS opp_elo,
       opening
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND end_time IS NOT NULL
ORDER BY end_time DESC
LIMIT 30

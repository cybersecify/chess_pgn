-- Fastest games you were checkmated — shortest losses by checkmate
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
       time_class,
       color,
       move_count,
       opponent,
       CASE WHEN color = 'white' THEN white_elo ELSE black_elo END  AS my_elo,
       CASE WHEN color = 'white' THEN black_elo ELSE white_elo END  AS opp_elo,
       opening,
       url
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND user_result = 'lose'
  AND termination LIKE '%checkmate'
  AND move_count IS NOT NULL
ORDER BY move_count ASC, end_time DESC
LIMIT 20

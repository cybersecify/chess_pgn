-- Biggest upsets: wins against much stronger opponents (rapid)
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
       opponent,
       CASE WHEN color = 'white' THEN white_elo ELSE black_elo END AS my_elo,
       CASE WHEN color = 'white' THEN black_elo ELSE white_elo END AS opp_elo,
       (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) -
       (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) AS elo_diff,
       opening
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = 'rapid' AND user_result = 'win'
  AND (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) >
      (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) + 100
ORDER BY elo_diff DESC
LIMIT 20

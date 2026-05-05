SELECT
  strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
  opponent,
  CASE WHEN color = 'white' THEN black_elo ELSE white_elo END AS opp_elo,
  CASE WHEN color = 'white' THEN white_elo ELSE black_elo END AS my_elo,
  move_count,
  CASE
    WHEN termination LIKE '%checkmate'   THEN 'checkmate'
    WHEN termination LIKE '%resignation' THEN 'resignation'
    WHEN termination LIKE '%on time'     THEN 'timeout'
    ELSE                                      'other'
  END AS ended_by,
  url
FROM games
WHERE white = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
  AND pgn LIKE '%1. e4%'
  AND user_result = 'win'
ORDER BY opp_elo DESC
LIMIT 15

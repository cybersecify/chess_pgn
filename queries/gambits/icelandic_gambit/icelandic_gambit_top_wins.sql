-- Icelandic Gambit — highest rated opponents beaten
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d')                                      AS date,
       opponent,
       CASE WHEN color = 'black' THEN white_elo ELSE black_elo END                       AS opp_elo,
       CASE WHEN color = 'black' THEN black_elo ELSE white_elo END                       AS my_elo,
       move_count,
       CASE
         WHEN termination LIKE '%checkmate'   THEN 'checkmate'
         WHEN termination LIKE '%resignation' THEN 'resignation'
         WHEN termination LIKE '%on time'     THEN 'timeout'
         ELSE                                      'other'
       END                                                                                AS ended_by,
       url
FROM games
WHERE black = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])3\.\.\. e5')
  AND opening LIKE '%Scandinavian%'
  AND user_result = 'win'
ORDER BY opp_elo DESC
LIMIT 15

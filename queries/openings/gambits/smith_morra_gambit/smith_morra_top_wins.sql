-- Smith-Morra Gambit — highest rated opponents beaten
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d')                                  AS date,
       opponent,
       black_elo                                                                      AS opp_elo,
       white_elo                                                                      AS my_elo,
       move_count,
       CASE
         WHEN termination LIKE '%checkmate'   THEN 'checkmate'
         WHEN termination LIKE '%resignation' THEN 'resignation'
         WHEN termination LIKE '%on time'     THEN 'timeout'
         ELSE                                      'other'
       END                                                                            AS ended_by,
       url
FROM games
WHERE white = $USERNAME
  AND opening LIKE '%Smith Morra%'
  AND user_result = 'win'
ORDER BY opp_elo DESC
LIMIT 15

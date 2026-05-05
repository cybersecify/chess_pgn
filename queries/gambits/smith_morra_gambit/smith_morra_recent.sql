-- Smith-Morra Gambit — 20 most recent games with full details
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d')                                  AS date,
       time_class,
       opponent,
       CASE WHEN color = 'white' THEN white_elo ELSE black_elo END                  AS my_elo,
       CASE WHEN color = 'white' THEN black_elo ELSE white_elo END                  AS opp_elo,
       user_result,
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
ORDER BY end_time DESC
LIMIT 20

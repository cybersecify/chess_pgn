-- Icelandic Gambit — 20 most recent games with full details
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d')                                      AS date,
       time_class,
       opponent,
       CASE WHEN color = 'black' THEN black_elo ELSE white_elo END                       AS my_elo,
       CASE WHEN color = 'black' THEN white_elo ELSE black_elo END                       AS opp_elo,
       user_result,
       move_count,
       regexp_extract(pgn, '4\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)                        AS white_4th_move,
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
ORDER BY end_time DESC
LIMIT 20

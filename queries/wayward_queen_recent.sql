-- Wayward Queen Attack — 20 most recent games with full details
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d')                                      AS date,
       time_class,
       opponent,
       CASE WHEN color = 'white' THEN white_elo ELSE black_elo END                       AS my_elo,
       CASE WHEN color = 'white' THEN black_elo ELSE white_elo END                       AS opp_elo,
       user_result,
       move_count,
       regexp_extract(pgn, '2\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)                    AS black_response,
       CASE
         WHEN termination LIKE '%checkmate'   THEN 'checkmate'
         WHEN termination LIKE '%resignation' THEN 'resignation'
         WHEN termination LIKE '%on time'     THEN 'timeout'
         ELSE                                      'other'
       END                                                                                AS ended_by,
       url
FROM games
WHERE white = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
  AND pgn LIKE '%1. e4%'
ORDER BY end_time DESC
LIMIT 20

-- Icelandic Gambit — how games end and win rate per termination type
SELECT
  CASE
    WHEN termination LIKE '%checkmate'   THEN 'checkmate'
    WHEN termination LIKE '%resignation' THEN 'resignation'
    WHEN termination LIKE '%on time'     THEN 'timeout'
    ELSE                                      'other'
  END                                                                                     AS ended_by,
  COUNT(*)                                                                                AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                                 AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                                 AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1)     AS win_pct
FROM games
WHERE black = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])3\.\.\. e5')
  AND opening LIKE '%Scandinavian%'
GROUP BY ended_by
ORDER BY games DESC

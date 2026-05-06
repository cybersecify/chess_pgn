-- Wayward Queen Attack — how games end (blitz)
-- checkmate = you delivered mate; resignation = opponent gave up; timeout = flagged
WITH cat AS (
  SELECT user_result, move_count,
    CASE
      WHEN termination LIKE '%checkmate'   THEN 'checkmate'
      WHEN termination LIKE '%resignation' THEN 'resignation'
      WHEN termination LIKE '%on time'     THEN 'timeout'
      WHEN termination LIKE '%abandoned'   THEN 'abandoned'
      ELSE                                      'other'
    END AS how
  FROM games
  WHERE white = $USERNAME
    AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
    AND pgn LIKE '%1. e4%'
    AND time_class = $TIME_CLASS
    AND user_result IS NOT NULL
)
SELECT how,
       COUNT(*)                                                                           AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                            AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                            AS losses,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct,
       ROUND(AVG(move_count), 1)                                                          AS avg_moves
FROM cat
GROUP BY how
ORDER BY games DESC

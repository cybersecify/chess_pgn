-- How you win and lose: resignation vs checkmate vs timeout vs abandoned (rapid)
-- High resignation losses = giving up too early; high timeout losses = clock problem
WITH categorised AS (
  SELECT user_result, color,
    CASE
      WHEN termination LIKE '%checkmate'   THEN 'checkmate'
      WHEN termination LIKE '%resignation' THEN 'resignation'
      WHEN termination LIKE '%on time'     THEN 'timeout'
      WHEN termination LIKE '%abandoned'   THEN 'abandoned'
      ELSE                                      'other'
    END AS how
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = $TIME_CLASS AND user_result IS NOT NULL
)
SELECT how,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
       COUNT(*) AS total,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM categorised
GROUP BY how
ORDER BY total DESC

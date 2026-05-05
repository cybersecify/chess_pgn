SELECT
  CASE
    WHEN opp_elo < 300  THEN '01. < 300'
    WHEN opp_elo < 400  THEN '02. 300-399'
    WHEN opp_elo < 500  THEN '03. 400-499'
    WHEN opp_elo < 600  THEN '04. 500-599'
    WHEN opp_elo < 700  THEN '05. 600-699'
    WHEN opp_elo < 800  THEN '06. 700-799'
    WHEN opp_elo < 900  THEN '07. 800-899'
    WHEN opp_elo < 1000 THEN '08. 900-999'
    ELSE                     '09. 1000+'
  END AS opp_rating_bucket,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct,
  ROUND(AVG(opp_elo), 0) AS avg_opp_elo
FROM (
  SELECT
    user_result,
    CASE WHEN color = 'white' THEN black_elo ELSE white_elo END AS opp_elo
  FROM games
  WHERE white = $USERNAME
    AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
    AND pgn LIKE '%1. e4%'
) t
GROUP BY opp_rating_bucket
HAVING COUNT(*) >= 5
ORDER BY opp_rating_bucket

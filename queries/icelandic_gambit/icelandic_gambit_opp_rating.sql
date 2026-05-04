-- Icelandic Gambit — win rate by opponent ELO bucket
SELECT
  CASE
    WHEN opp_elo < 300  THEN '01. < 300'
    WHEN opp_elo < 400  THEN '02. 300-399'
    WHEN opp_elo < 500  THEN '03. 400-499'
    WHEN opp_elo < 600  THEN '04. 500-599'
    WHEN opp_elo < 700  THEN '05. 600-699'
    WHEN opp_elo < 800  THEN '06. 700-799'
    ELSE                     '07. 800+'
  END                                                                                     AS opp_rating_bucket,
  COUNT(*)                                                                                AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                                 AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                                 AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1)     AS win_pct
FROM (
  SELECT user_result,
    CASE WHEN color = 'black' THEN white_elo ELSE black_elo END AS opp_elo
  FROM games
  WHERE black = $USERNAME
    AND regexp_matches(pgn, '(^|[\s}])3\.\.\. e5')
    AND opening LIKE '%Scandinavian%'
) t
GROUP BY opp_rating_bucket
HAVING COUNT(*) >= 3
ORDER BY opp_rating_bucket

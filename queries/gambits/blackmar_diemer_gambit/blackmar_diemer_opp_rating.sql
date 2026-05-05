-- Blackmar-Diemer Gambit — win rate by opponent ELO bucket
SELECT
  CASE
    WHEN white_elo - black_elo < -200 THEN '01. Much stronger (200+)'
    WHEN white_elo - black_elo < -100 THEN '02. Stronger (100-200)'
    WHEN white_elo - black_elo <    0 THEN '03. Slightly stronger (0-100)'
    WHEN white_elo - black_elo <  100 THEN '04. Slightly weaker (0-100)'
    WHEN white_elo - black_elo <  200 THEN '05. Weaker (100-200)'
    ELSE                                   '06. Much weaker (200+)'
  END                                                                                 AS opp_strength,
  COUNT(*)                                                                             AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                             AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                             AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE white = $USERNAME
  AND opening LIKE '%Blackmar%'
GROUP BY opp_strength
ORDER BY opp_strength

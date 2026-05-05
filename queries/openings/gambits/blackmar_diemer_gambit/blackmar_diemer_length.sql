-- Blackmar-Diemer Gambit — win rate by game length
SELECT
  CASE
    WHEN move_count <= 10 THEN '01. 1-10  moves (opening trap)'
    WHEN move_count <= 20 THEN '02. 11-20 moves (early attack)'
    WHEN move_count <= 30 THEN '03. 21-30 moves (middlegame)'
    WHEN move_count <= 40 THEN '04. 31-40 moves (late middlegame)'
    ELSE                       '05. 40+  moves  (endgame)'
  END                                                                                 AS bucket,
  COUNT(*)                                                                             AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                             AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                             AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE white = $USERNAME
  AND opening LIKE '%Blackmar%'
GROUP BY bucket
ORDER BY bucket

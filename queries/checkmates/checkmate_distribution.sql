-- Checkmate distribution — how many moves did your checkmates take? (all formats)
SELECT
  CASE
    WHEN move_count <= 5  THEN '01. ≤5  moves  (Scholar / trap)'
    WHEN move_count <= 10 THEN '02. 6–10 moves  (opening trap)'
    WHEN move_count <= 15 THEN '03. 11–15 moves (early attack)'
    WHEN move_count <= 20 THEN '04. 16–20 moves (quick attack)'
    WHEN move_count <= 30 THEN '05. 21–30 moves (middlegame)'
    WHEN move_count <= 40 THEN '06. 31–40 moves (late middlegame)'
    ELSE                       '07. 40+  moves  (endgame mate)'
  END                                                                       AS bucket,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                   AS you_mated,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                   AS got_mated
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND termination LIKE '%checkmate'
  AND move_count IS NOT NULL
GROUP BY bucket
ORDER BY bucket

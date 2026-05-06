-- Wayward Queen Attack — win rate by game length (blitz)
-- Scholar's Mate attempts end < 5 moves; longer games mean opponent defused the attack
SELECT
  CASE
    WHEN move_count <= 4  THEN '1. Scholar mate (≤4 moves)'
    WHEN move_count <= 9  THEN '2. Quick crush  (5–9)'
    WHEN move_count <= 19 THEN '3. Short game   (10–19)'
    WHEN move_count <= 34 THEN '4. Medium game  (20–34)'
    ELSE                       '5. Long game    (35+)'
  END AS phase,
  COUNT(*)                                                                              AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                               AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                               AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1)  AS win_pct
FROM games
WHERE white = $USERNAME
  AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
  AND pgn LIKE '%1. e4%'
  AND time_class = $TIME_CLASS
  AND move_count IS NOT NULL
GROUP BY phase
ORDER BY phase

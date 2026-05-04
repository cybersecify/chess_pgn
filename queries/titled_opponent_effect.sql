-- Titled opponent effect: intimidation factor vs GM/IM/FM/CM vs untitled (rapid)
SELECT
  CASE
    WHEN opponent LIKE 'GM_%'  OR opponent LIKE 'WGM_%' THEN '1. GM  (Grandmaster)'
    WHEN opponent LIKE 'IM_%'  OR opponent LIKE 'WIM_%' THEN '2. IM  (International Master)'
    WHEN opponent LIKE 'FM_%'  OR opponent LIKE 'WFM_%' THEN '3. FM  (FIDE Master)'
    WHEN opponent LIKE 'CM_%'  OR opponent LIKE 'WCM_%' THEN '4. CM  (Candidate Master)'
    WHEN opponent LIKE 'NM_%'                           THEN '4. NM  (National Master)'
    ELSE                                                     '5. Untitled'
  END AS opponent_title,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND user_result IS NOT NULL AND opponent IS NOT NULL
GROUP BY opponent_title
ORDER BY opponent_title

-- Performance by ECO opening family (rapid)
-- A=Flank/English/Dutch, B=Semi-Open (1.e4), C=Open (1.e4 e5), D=Closed (1.d4), E=Indian defenses
SELECT LEFT(eco, 1) AS family,
       CASE LEFT(eco, 1)
         WHEN 'A' THEN 'A — Flank / English / Dutch'
         WHEN 'B' THEN 'B — Semi-Open (1.e4, not 1...e5)'
         WHEN 'C' THEN 'C — Open (1.e4 e5)'
         WHEN 'D' THEN 'D — Closed / Semi-Closed (1.d4 d5)'
         WHEN 'E' THEN 'E — Indian Defenses (1.d4 Nf6)'
       END AS description,
       COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND eco IS NOT NULL AND user_result IS NOT NULL
GROUP BY family, description
ORDER BY family

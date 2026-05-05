-- Recent missed mates with game links (last 30)
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
       mate_in,
       move_number,
       color,
       opponent,
       best_move,
       played_move,
       opening,
       game_url
FROM missed_mates
ORDER BY end_time DESC
LIMIT 30

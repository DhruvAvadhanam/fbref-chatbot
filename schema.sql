CREATE SCHEMA IF NOT EXISTS md.fbref;

-- Raw long-form fact table.
CREATE TABLE IF NOT EXISTS md.fbref_player_stats_long (
    player        TEXT,
    team          TEXT,
    position      TEXT,
    nationality   TEXT,
    age           DOUBLE,       -- FBref age often includes fraction; store numeric
    competition   TEXT,         -- 'Premier-League', 'La-Liga', etc (slug with dashes)
    season        TEXT,         -- '2024-2025'
    stat_type     TEXT,         -- 'standard'|'keeper'|'defensive'|'shooting'|'passing'|'possession'
    stat_name     TEXT,         -- normalized, e.g. 'goals', 'assists', 'xg'
    stat_value    DOUBLE,
    source_at     TIMESTAMP DEFAULT now()
);

-- Optional helper view to pivot a few top metrics for human reading.
CREATE OR REPLACE VIEW md.fbref_goals_by_player AS
SELECT
  player, competition, season, SUM(stat_value) AS goals
FROM md.fbref_player_stats_long
WHERE stat_name = 'goals' AND stat_type = 'standard'
GROUP BY 1,2,3;

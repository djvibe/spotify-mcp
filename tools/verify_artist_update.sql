-- Verify artist enhanced metrics update
-- Replace {ARTIST_ID} with the actual artist ID

-- Check main artist data
SELECT 
    name,
    popularity,
    followers,
    monthly_listeners,
    top_tracks_total_plays,
    upcoming_tours_count,
    datetime(last_updated) as last_updated
FROM artists
WHERE id = '{ARTIST_ID}';

-- Check social links
SELECT 
    json_extract(social_links_json, '$.facebook') as facebook_link,
    json_extract(social_links_json, '$.twitter') as twitter_link,
    json_extract(social_links_json, '$.instagram') as instagram_link
FROM artists
WHERE id = '{ARTIST_ID}';

-- Get top cities
SELECT 
    city,
    country,
    region,
    listeners,
    datetime(snapshot_date) as date_recorded
FROM artist_top_cities
WHERE artist_id = '{ARTIST_ID}'
ORDER BY listeners DESC;

-- Check upcoming tours
SELECT 
    json_extract(upcoming_tours_json, '$.total_count') as total_tours,
    json_extract(upcoming_tours_json, '$.dates[0].title') as first_tour_title,
    json_extract(upcoming_tours_json, '$.dates[0].date') as first_tour_date,
    json_extract(upcoming_tours_json, '$.dates[0].location.name') as first_tour_venue,
    json_extract(upcoming_tours_json, '$.dates[0].location.city') as first_tour_city
FROM artists
WHERE id = '{ARTIST_ID}' AND upcoming_tours_count > 0;

-- Check stats history
SELECT 
    datetime(snapshot_date) as date,
    follower_count,
    monthly_listeners,
    top_tracks_total_plays,
    upcoming_tours_count
FROM artist_stats_history
WHERE artist_id = '{ARTIST_ID}'
ORDER BY snapshot_date DESC
LIMIT 10;

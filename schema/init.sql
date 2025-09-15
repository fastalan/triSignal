-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Devices: Unique signal emitters (WiFi, Bluetooth, Cell)
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_type TEXT CHECK (device_type IN ('wifi', 'bluetooth', 'cell')) NOT NULL,
    device_id TEXT NOT NULL,
    name TEXT,
    location GEOMETRY(POINT, 4326),  -- General or last known location
    first_seen TIMESTAMPTZ,
    last_seen TIMESTAMPTZ,
    mobility TEXT CHECK (mobility IN ('unknown', 'fixed', 'mobile')) DEFAULT 'unknown',
    confidence FLOAT,
    notes TEXT,
    UNIQUE(device_type, device_id)
);

-- Observations: Timestamped sightings with GPS
CREATE TABLE device_observations (
    id SERIAL PRIMARY KEY,
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    location GEOMETRY(POINT, 4326) NOT NULL,
    signal INTEGER,
    frequency INTEGER,
    source TEXT,
    raw_json JSONB
);

-- Estimated locations from triangulation or weighted centroid
CREATE TABLE estimated_locations (
    device_id UUID PRIMARY KEY REFERENCES devices(id) ON DELETE CASCADE,
    location GEOMETRY(POINT, 4326),
    accuracy FLOAT,
    confidence FLOAT,
    method TEXT,
    last_updated TIMESTAMPTZ
);
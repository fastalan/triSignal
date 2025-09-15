import asyncio
import asyncpg
import sqlite3
import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load .env file from project root (two levels up from this script)
script_dir = Path(__file__).parent
project_root = script_dir.parent
env_path = project_root / '.env'
load_dotenv(env_path)

# Convert epoch milliseconds to timestamptz
def parse_timestamp(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)

async def insert_device(conn, device_type, device_id, device_name, first_seen, last_seen, lat, lon):
    await conn.execute("""
        INSERT INTO devices (device_type, device_id, name, location, first_seen, last_seen)
        VALUES ($1, $2, $3, ST_SetSRID(ST_MakePoint($4, $5), 4326), $6, $7)
        ON CONFLICT (device_type, device_id) DO NOTHING;
    """, device_type, device_id, device_name, lon, lat, first_seen, last_seen)

async def insert_observation(conn, device_uuid, timestamp, lat, lon, signal, raw_json):
    await conn.execute("""
        INSERT INTO device_observations (device_id, timestamp, location, signal, source, raw_json)
        VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, 'wigle', $6);
    """, device_uuid, timestamp, lon, lat, signal, json.dumps(raw_json))

async def main(sqlite_file, pg_url):
    # Load WiGLE data
    sqlite_conn = sqlite3.connect(sqlite_file)
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.execute("SELECT * FROM network")

    # Open PostgreSQL connection
    pg_conn = await asyncpg.connect(pg_url)

    # Get column names to debug
    first_row = cursor.fetchone()
    if first_row:
        print(f"Available columns: {list(first_row.keys())}")
        cursor = sqlite_conn.execute("SELECT * FROM network")  # Reset cursor
    
    for row in cursor:
        # Handle different possible column names for timestamp
        timestamp_col = None
        for col in ["time", "lasttime", "lastupdt", "lastseen"]:
            if col in row.keys():
                timestamp_col = col
                break
        
        if not timestamp_col:
            print(f"Warning: No timestamp column found. Available columns: {list(row.keys())}")
            continue
            
        bssid = row["bssid"]
        # Clean SSID data to remove null bytes and other problematic characters
        raw_ssid = row["ssid"] if "ssid" in row.keys() and row["ssid"] is not None else None
        ssid = None
        if raw_ssid is not None:
            clean_ssid = str(raw_ssid).replace('\x00', '').replace('\u0000', '').strip()
            if clean_ssid:
                ssid = clean_ssid
        
        # Map WiGLE type codes to our device types
        type_code = row["type"] if "type" in row.keys() and row["type"] is not None else "W"
        device_type_map = {
            "W": "wifi",
            "B": "bluetooth", # Bluetooth classic
            "D": "cell", # 2G/3G/4G/5G
            "G": "cell", # GSM
            "E": "bluetooth" # Bluetooth LE
        }
        device_type = device_type_map.get(type_code, "wifi")
        
        timestamp = parse_timestamp(row[timestamp_col])
        
        # Use best coordinates if available, otherwise use last coordinates for device location
        device_lat = row["bestlat"] if "bestlat" in row.keys() and row["bestlat"] is not None else row["lastlat"]
        device_lon = row["bestlon"] if "bestlon" in row.keys() and row["bestlon"] is not None else row["lastlon"]
        signal = row["bestlevel"] if "bestlevel" in row.keys() and row["bestlevel"] is not None else 0
        
        # Skip if we don't have coordinates
        if device_lat is None or device_lon is None:
            print(f"Warning: Skipping {bssid} - no coordinates available")
            continue
            
        # Debug: Print first few coordinates to verify they're being read
        if hasattr(main, 'debug_count'):
            main.debug_count += 1
        else:
            main.debug_count = 1
            
        if main.debug_count <= 5:
            print(f"Debug: {bssid} -> lat: {device_lat}, lon: {device_lon}, signal: {signal}")
            
        # Clean the raw data to remove null bytes and other problematic characters
        raw = {}
        for key, value in dict(row).items():
            if value is not None:
                # Convert to string and remove null bytes
                clean_value = str(value).replace('\x00', '').replace('\u0000', '')
                # Only include non-empty values
                if clean_value.strip():
                    raw[key] = clean_value

        # Insert or ignore device (using best/last coordinates for general device location)
        await insert_device(pg_conn, device_type, bssid, ssid, timestamp, timestamp, device_lat, device_lon)

        # Get UUID of device
        device_row = await pg_conn.fetchrow(
            "SELECT id FROM devices WHERE device_type = $1 AND device_id = $2", device_type, bssid
        )
        if device_row:
            # For observations, use the same coordinates (this represents the sighting location)
            await insert_observation(pg_conn, device_row["id"], timestamp, device_lat, device_lon, signal, raw)

    await pg_conn.close()
    sqlite_conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import WiGLE SQLite into triSignal database.")
    parser.add_argument("--db", required=True, help="Path to WiGLE .sqlite file")
    parser.add_argument("--pg", required=False, help="PostgreSQL DSN (overrides .env settings)")
    args = parser.parse_args()

    # Build PostgreSQL connection string from environment variables
    if args.pg:
        pg_url = args.pg
    else:
        db_name = os.getenv("POSTGRES_DB", "trisignal")
        db_user = os.getenv("POSTGRES_USER", "trisignal_admin")
        db_password = os.getenv("POSTGRES_PASSWORD", "changeme")
        
        # URL encode the password to handle special characters
        import urllib.parse
        encoded_password = urllib.parse.quote_plus(db_password)
        encoded_user = urllib.parse.quote_plus(db_user)
        
        pg_url = f"postgresql://{encoded_user}:{encoded_password}@localhost:5432/{db_name}"
        
        print(f"Connecting to: postgresql://{encoded_user}:***@localhost:5432/{db_name}")

    asyncio.run(main(args.db, pg_url))
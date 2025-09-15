# triSignal

**triSignal** is a self-hosted system for importing and analyzing wireless signal observations (WiFi, Bluetooth, Cell) to estimate device locations and movement paths using PostGIS and Python.

---

## 🎯 Scope

- Store GPS-tagged signal observations (WiGLE, Kismet, Pineapple)
- Triangulate fixed signal emitters from multiple sightings
- Project movement paths from scan traces
- Classify devices as fixed or mobile over time

---

## 🧰 Stack

| Component     | Purpose                         |
|---------------|---------------------------------|
| PostgreSQL + PostGIS | Spatial database for all observations |
| Python ETL    | Load data from Wigle/Kismet logs |
| Docker Compose| Easy local setup                |
| pgAdmin       | Web GUI for DB browsing         |
| QGIS / Leaflet| (optional) Geospatial visualization |

---

## 🚀 Quickstart

```bash
# Clone the repository
git clone https://github.com/fastalan/triSignal.git
cd triSignal

# Create environment file
cp .env.example .env
# Edit .env with your database credentials

# Spin up PostGIS + pgAdmin
docker compose up -d

# Access pgAdmin at http://localhost:8080
# Database connection: localhost:5432
```

---

## ⚙️ Configuration

### Customizing Data Paths

By default, Docker Compose uses named volumes for data persistence. To customize where data is stored on your host system, create a `docker-compose.override.yml` file:

```yaml
services:
  pgadmin:
    volumes:
      - /path/to/your/pgadmin/data:/var/lib/pgadmin
```

**Example for Windows:**
```yaml
services:
  pgadmin:
    volumes:
      - G:/dockerdata/trisignal/pgadmin:/var/lib/pgadmin
```

**Example for Linux/macOS:**
```yaml
services:
  pgadmin:
    volumes:
      - /home/user/trisignal/pgadmin:/var/lib/pgadmin
```

This override file will be automatically loaded by Docker Compose and allows you to:
- Persist pgAdmin settings and server configurations
- Store data in a specific location on your host system
- Share configurations across different environments

### Environment Variables

Create a `.env` file with the following variables:

```env
POSTGRES_DB=trisignal
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=your_pgadmin_password
```

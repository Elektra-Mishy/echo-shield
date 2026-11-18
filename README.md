# ECHO-SHIELD

**An AI-powered community early-warning and infrastructure monitoring system.**
Built by Team ECHO for the Inter-University Hackathon 2026 (theme area: Cyber Security and Digital Trust).

ECHO-SHIELD turns ordinary smartphones into a low-cost sensing network. Phones feel road shocks with their built-in motion sensors and report them anonymously. A trust engine only raises an alert when several independent devices agree, so one person, or a swarm of cloned bots, cannot fake an emergency.

## How it works

1. **Sensing.** A phone opens the sensor page, reads its accelerometer and GPS, and sends shocks to the server. While moving, it also sends small "normal vibration" readings.
2. **Anomaly detection.** The server learns what normal vibration feels like in each ~110 m grid cell. A shock counts as an anomaly only if it is at least 6 times stronger than normal for that place, and at least 8 m/s². The same shock can be an anomaly on a smooth road and normal on a rough one.
3. **Trust scoring.** For each cell, trust score = 45% independent sources + 25% time clustering + 30% device reliability. Devices with the same fingerprint count as one source.
4. **Live map.** A dashboard shows each zone as high-risk (red), suspicious (amber) or rejected (grey), and explains how the score was worked out.

## Tech stack

Python, Django, PostgreSQL, HTML, CSS, JavaScript, Leaflet and OpenStreetMap.

## Pages and API

| Address | What it does |
| --- | --- |
| `/` | Live dashboard with the zone map and demo scenarios |
| `/sense/` | Phone sensor page |
| `/admin/` | Django admin for devices, reports and baselines |
| `POST /api/report/` | A phone sends a shock reading |
| `POST /api/baseline/` | A moving phone sends a normal-vibration reading |
| `GET /api/cells/` | All zones with recent reports and their trust scores |
| `POST /api/demo/<scenario>/` | Demo scenarios: `real`, `fake`, `bot`, `clear` (only when `DEBUG=True`) |

## Run it locally

1. Install Python 3.12 and PostgreSQL, and create an empty database named `echoshield`.
2. Create and activate a virtual environment, then install the packages:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and put your PostgreSQL password in it.
4. Set up the database and start the server:

```
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

5. Open `http://127.0.0.1:8000/`.

Phone browsers only allow motion sensors on HTTPS pages. To test on a real phone, expose the server with a free Cloudflare quick tunnel and open the address it prints:

```
cloudflared tunnel --url http://localhost:8000
```

## Current limits

This is a hackathon prototype. The thresholds have not been tuned on real road data. The device fingerprint is created by the phone itself, so a production version would use Android and Apple device verification, rate limits, and reliability-weighted baselines. Flooding detection is planned work.
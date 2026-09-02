from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
CORS(app)

# ── Database setup ────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sahayog.db")

SEED_WORKERS = [
    ("Ravi Kumar",    "Plumbing",       "Andheri, Mumbai",        "9876543210", 4.8, 350, 6),
    ("Sunita Devi",   "House Cleaning", "Koramangala, Bangalore",  "9845012345", 4.9, 250, 8),
    ("Arjun Singh",   "Electrician",    "Lajpat Nagar, Delhi",    "9712345678", 4.7, 400, 5),
    ("Mohan Lal",     "Plumbing",       "Shivaji Nagar, Pune",    "9823456789", 4.8, 320, 7),
    ("Kavitha R.",    "AC Repair",      "T. Nagar, Chennai",      "9944556677", 4.9, 500, 10),
    ("Deepak Sharma", "Carpentry",      "Salt Lake, Kolkata",     "9334455667", 4.7, 380, 4),
    ("Prakash Nair",  "Painting",       "Baner, Pune",            "9021234567", 4.8, 300, 6),
]


def get_db():
    """Return a SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and seed demo data if the DB is fresh."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    NOT NULL,
            service          TEXT    NOT NULL,
            location         TEXT    NOT NULL,
            phone            TEXT    NOT NULL,
            rating           REAL    DEFAULT 5.0,
            hourly_rate      INTEGER DEFAULT 300,
            experience_years INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name  TEXT NOT NULL,
            client_phone TEXT NOT NULL,
            service      TEXT NOT NULL,
            worker_name  TEXT DEFAULT '',
            address      TEXT NOT NULL,
            booking_date TEXT NOT NULL,
            status       TEXT DEFAULT 'Pending',
            created_at   TEXT NOT NULL
        )
    """)

    # Seed workers only if table is empty
    count = cur.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
    if count == 0:
        cur.executemany(
            "INSERT INTO workers (name, service, location, phone, rating, hourly_rate, experience_years) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            SEED_WORKERS
        )

    conn.commit()
    conn.close()
    print(f"[sahayog] Database ready -> {DB_PATH}")


# Initialise on startup
init_db()


# ── Serve index.html at root ────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')

@app.route('/style.css')
def style():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'style.css')


@app.route('/assets/<path:filename>')
def assets(filename):
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
    return send_from_directory(assets_dir, filename)


# ── GET /api/workers ──────────────────────────────────────────────────────────
@app.route("/api/workers", methods=["GET"])
def get_workers():
    service  = request.args.get("service",  "").strip().lower()
    location = request.args.get("location", "").strip().lower()

    query  = "SELECT * FROM workers WHERE 1=1"
    params = []

    if service:
        query  += " AND LOWER(service) LIKE ?"
        params.append(f"%{service}%")
    if location:
        query  += " AND LOWER(location) LIKE ?"
        params.append(f"%{location}%")

    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    workers = [dict(r) for r in rows]
    return jsonify({"success": True, "workers": workers, "count": len(workers)})


# ── POST /api/book ────────────────────────────────────────────────────────────
@app.route("/api/book", methods=["POST"])
def book_service():
    data = request.get_json()
    required = ["name", "phone", "service", "date", "address"]
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing)}"}), 400

    client_name  = data["name"].strip()
    client_phone = data["phone"].strip()
    service      = data["service"].strip()
    worker_name  = data.get("worker_name", "").strip()
    address      = data["address"].strip()
    booking_date = data["date"].strip()
    created_at   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO bookings (client_name, client_phone, service, worker_name, address, booking_date, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?)",
        (client_name, client_phone, service, worker_name, address, booking_date, created_at)
    )
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()

    booking = {
        "id":          booking_id,
        "name":        client_name,
        "phone":       client_phone,
        "service":     service,
        "worker_name": worker_name,
        "date":        booking_date,
        "address":     address,
        "status":      "Pending",
        "created_at":  created_at,
    }
    return jsonify({
        "success": True,
        "message": f"Booking confirmed! Booking ID: BK{booking_id:04d}. A worker will contact you shortly.",
        "booking": booking
    }), 201


# ── POST /api/register-worker ─────────────────────────────────────────────────
@app.route("/api/register-worker", methods=["POST"])
def register_worker():
    data = request.get_json()
    required = ["name", "phone", "service", "location"]
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing)}"}), 400

    name             = data["name"].strip()
    service          = data["service"].strip()
    location         = data["location"].strip()
    phone            = data["phone"].strip()
    hourly_rate      = int(data.get("hourly_rate", 300))
    experience_years = int(data.get("experience_years", 1))

    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO workers (name, service, location, phone, rating, hourly_rate, experience_years) "
        "VALUES (?, ?, ?, ?, 5.0, ?, ?)",
        (name, service, location, phone, hourly_rate, experience_years)
    )
    worker_id = cur.lastrowid
    conn.commit()
    conn.close()

    new_worker = {
        "id":               worker_id,
        "name":             name,
        "service":          service,
        "location":         location,
        "phone":            phone,
        "rating":           5.0,
        "hourly_rate":      hourly_rate,
        "experience_years": experience_years,
    }
    return jsonify({
        "success": True,
        "message": "Worker registered successfully! Welcome to the cooperative.",
        "worker":  new_worker
    }), 201


# ── GET /api/bookings ─────────────────────────────────────────────────────────
@app.route("/api/bookings", methods=["GET"])
def get_bookings():
    conn     = get_db()
    rows     = conn.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()
    conn.close()
    bookings = [dict(r) for r in rows]
    return jsonify({"success": True, "bookings": bookings, "count": len(bookings)})


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    conn = get_db()
    worker_count  = conn.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
    booking_count = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    conn.close()
    return jsonify({
        "status":   "ok",
        "message":  "Velocity SIH API is running!",
        "db":       DB_PATH,
        "workers":  worker_count,
        "bookings": booking_count,
    })


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

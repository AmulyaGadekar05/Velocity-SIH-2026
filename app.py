from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# In-memory store for prototype (replace with DB later)
bookings = []
workers = [
    {"id": 1, "name": "Ravi Kumar",    "service": "Plumbing",    "rating": 4.8, "jobs": 120, "available": True,  "location": "Pune"},
    {"id": 2, "name": "Sunita Devi",   "service": "Cleaning",    "rating": 4.9, "jobs": 245, "available": True,  "location": "Mumbai"},
    {"id": 3, "name": "Arjun Singh",   "service": "Electrician", "rating": 4.7, "jobs": 89,  "available": False, "location": "Pune"},
    {"id": 4, "name": "Meena Bai",     "service": "Cooking",     "rating": 5.0, "jobs": 310, "available": True,  "location": "Delhi"},
    {"id": 5, "name": "Ramesh Gupta",  "service": "Carpentry",   "rating": 4.6, "jobs": 74,  "available": True,  "location": "Mumbai"},
    {"id": 6, "name": "Lakshmi P.",    "service": "Babysitting", "rating": 4.9, "jobs": 156, "available": True,  "location": "Bangalore"},
]

# ── GET /api/workers ──────────────────────────────────────────────────────────
@app.route("/api/workers", methods=["GET"])
def get_workers():
    service  = request.args.get("service", "").strip().lower()
    location = request.args.get("location", "").strip().lower()
    filtered = workers
    if service:
        filtered = [w for w in filtered if service in w["service"].lower()]
    if location:
        filtered = [w for w in filtered if location in w["location"].lower()]
    return jsonify({"success": True, "workers": filtered, "count": len(filtered)})

# ── POST /api/book ────────────────────────────────────────────────────────────
@app.route("/api/book", methods=["POST"])
def book_service():
    data = request.get_json()
    required = ["name", "phone", "service", "date", "address"]
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing)}"}), 400

    booking = {
        "id":        len(bookings) + 1,
        "name":      data["name"].strip(),
        "phone":     data["phone"].strip(),
        "service":   data["service"].strip(),
        "date":      data["date"].strip(),
        "address":   data["address"].strip(),
        "note":      data.get("note", "").strip(),
        "status":    "Pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    bookings.append(booking)
    return jsonify({"success": True, "message": "Booking confirmed! A worker will contact you shortly.", "booking": booking}), 201

# ── POST /api/register-worker ─────────────────────────────────────────────────
@app.route("/api/register-worker", methods=["POST"])
def register_worker():
    data = request.get_json()
    required = ["name", "phone", "service", "location"]
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing)}"}), 400

    new_worker = {
        "id":        len(workers) + 1,
        "name":      data["name"].strip(),
        "service":   data["service"].strip(),
        "rating":    5.0,
        "jobs":      0,
        "available": True,
        "location":  data["location"].strip(),
        "phone":     data["phone"].strip(),
    }
    workers.append(new_worker)
    return jsonify({"success": True, "message": "Worker registered successfully! Welcome to the cooperative.", "worker": new_worker}), 201

# ── GET /api/bookings ─────────────────────────────────────────────────────────
@app.route("/api/bookings", methods=["GET"])
def get_bookings():
    return jsonify({"success": True, "bookings": bookings, "count": len(bookings)})

# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Velocity SIH API is running!"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)

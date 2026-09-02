import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.secret_key = os.getenv('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///sahayog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ── Models ──────────────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'client' or 'worker'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    worker_profile = db.relationship('Worker', backref='user', uselist=False, cascade='all, delete-orphan')

class Worker(db.Model):
    __tablename__ = 'workers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Float, default=5.0)
    hourly_rate = db.Column(db.Integer, default=300)
    experience_years = db.Column(db.Integer, default=1)
    availability_status = db.Column(db.String(20), default='available') # 'available', 'busy'

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True) # Optional if auto-assigning
    service = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    booking_date = db.Column(db.String(50), nullable=False)
    note = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending') # 'pending', 'confirmed', 'completed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ── Seed Data ────────────────────────────────────────────────────────────────
def seed_db():
    if User.query.count() == 0:
        seed_workers = [
            ("Ravi Kumar",    "Plumbing",       "Andheri, Mumbai",        "9876543210", 4.8, 350, 6),
            ("Sunita Devi",   "House Cleaning", "Koramangala, Bangalore",  "9845012345", 4.9, 250, 8),
            ("Arjun Singh",   "Electrician",    "Lajpat Nagar, Delhi",    "9712345678", 4.7, 400, 5),
            ("Mohan Lal",     "Plumbing",       "Shivaji Nagar, Pune",    "9823456789", 4.8, 320, 7),
            ("Kavitha R.",    "AC Repair",      "T. Nagar, Chennai",      "9944556677", 4.9, 500, 10),
            ("Deepak Sharma", "Carpentry",      "Salt Lake, Kolkata",     "9334455667", 4.7, 380, 4),
            ("Prakash Nair",  "Painting",       "Baner, Pune",            "9021234567", 4.8, 300, 6),
        ]
        
        for name, service, location, phone, rating, rate, exp in seed_workers:
            u = User(name=name, phone=phone, role='worker')
            db.session.add(u)
            db.session.commit()
            w = Worker(user_id=u.id, service=service, location=location, rating=rating, hourly_rate=rate, experience_years=exp)
            db.session.add(w)
        db.session.commit()

with app.app_context():
    db.create_all()
    seed_db()

# ── Routes ──────────────────────────────────────────────────────────────────
@app.route('/style.css')
def style():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'style.css')

@app.route('/assets/<path:filename>')
def assets(filename):
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
    return send_from_directory(assets_dir, filename)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login_page'))
        
    if user.role == 'worker':
        return redirect(url_for('worker_profile'))
        
    return render_template('index.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/worker-profile')
def worker_profile():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
        
    user = db.session.get(User, session['user_id'])
    if not user or user.role != 'worker':
        return redirect(url_for('index'))
        
    worker = Worker.query.filter_by(user_id=user.id).first()
    
    # Get active bookings
    active_bookings = Booking.query.filter_by(worker_id=worker.id, status='pending').all()
    
    return render_template('worker-profile.html', user=user, worker=worker, active_bookings=active_bookings)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ── API Endpoints ────────────────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    phone = data.get("phone", "").strip()
    
    if not phone:
        return jsonify({"success": False, "message": "Phone number required"}), 400
        
    user = User.query.filter_by(phone=phone).first()
    if not user:
        return jsonify({"success": False, "message": "User not found. Please sign up."}), 404
        
    session['user_id'] = user.id
    session['role'] = user.role
    session['name'] = user.name
    
    return jsonify({"success": True, "message": "Login successful", "role": user.role})

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    role = data.get("role", "client").strip().lower()
    
    if not name or not phone:
        return jsonify({"success": False, "message": "Name and phone are required"}), 400
        
    user = User.query.filter_by(phone=phone).first()
    if user:
        return jsonify({"success": False, "message": "Phone number already registered"}), 400
        
    u = User(name=name, phone=phone, role=role)
    db.session.add(u)
    db.session.commit()
    
    if role == 'worker':
        service = data.get("service", "").strip()
        location = data.get("location", "").strip()
        experience_years = int(data.get("experience_years", 1))
        
        w = Worker(user_id=u.id, service=service, location=location, experience_years=experience_years)
        db.session.add(w)
        db.session.commit()
        
    session['user_id'] = u.id
    session['role'] = u.role
    session['name'] = u.name
    
    return jsonify({"success": True, "message": "Registration successful", "role": u.role})

@app.route("/api/workers", methods=["GET"])
def get_workers():
    service = request.args.get("service", "").strip().lower()
    location = request.args.get("location", "").strip().lower()
    
    query = Worker.query.join(User)
    if service:
        query = query.filter(Worker.service.ilike(f"%{service}%"))
    if location:
        query = query.filter(Worker.location.ilike(f"%{location}%"))
        
    workers = query.all()
    
    res = []
    for w in workers:
        res.append({
            "id": w.id,
            "name": w.user.name,
            "service": w.service,
            "location": w.location,
            "phone": w.user.phone,
            "rating": w.rating,
            "hourly_rate": w.hourly_rate,
            "experience_years": w.experience_years,
            "availability_status": w.availability_status
        })
        
    return jsonify({"success": True, "workers": res, "count": len(res)})

@app.route("/api/book", methods=["POST"])
def book_service():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json()
    service = data.get("service", "").strip()
    address = data.get("address", "").strip()
    booking_date = data.get("date", "").strip()
    note = data.get("note", "").strip()
    worker_name = data.get("worker_name", "").strip()
    
    if not service or not address or not booking_date:
        return jsonify({"success": False, "message": "Missing required fields"}), 400
        
    worker_id = None
    if worker_name:
        worker = Worker.query.join(User).filter(User.name == worker_name).first()
        if worker:
            worker_id = worker.id
            worker.availability_status = 'busy'
            db.session.commit()
            
    b = Booking(
        client_id=session['user_id'],
        worker_id=worker_id,
        service=service,
        address=address,
        booking_date=booking_date,
        note=note,
        status='pending'
    )
    db.session.add(b)
    db.session.commit()
    
    return jsonify({
        "success": True, 
        "message": f"Booking confirmed! Booking ID: BK{b.id:04d}."
    })

@app.route("/api/complete-job/<int:booking_id>", methods=["POST"])
def complete_job(booking_id):
    if 'user_id' not in session or session.get('role') != 'worker':
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return jsonify({"success": False, "message": "Booking not found"}), 404
        
    user = db.session.get(User, session['user_id'])
    worker = Worker.query.filter_by(user_id=user.id).first()
    
    if booking.worker_id != worker.id:
        return jsonify({"success": False, "message": "Not your booking"}), 403
        
    booking.status = 'completed'
    worker.availability_status = 'available'
    db.session.commit()
    
    return jsonify({"success": True, "message": "Job marked as completed"})

if __name__ == "__main__":
    # We must remove the existing sqlite file to avoid schema mismatch
    if os.path.exists("sahayog.db"):
        try:
            os.remove("sahayog.db")
        except:
            pass
    app.run(host='0.0.0.0', port=5000, debug=True)

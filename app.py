import os
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.secret_key = os.getenv('SECRET_KEY', 'sahayog-sih-2026-dev-secret')
db_url = os.getenv('DATABASE_URL', 'sqlite:///sahayog.db')
# Supabase/Render sends postgres://, SQLAlchemy needs postgresql://
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ── Models ────────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='client')  # 'client' or 'worker'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    worker_profile = db.relationship(
        'Worker', backref='user', uselist=False, cascade='all, delete-orphan'
    )
    client_bookings = db.relationship(
        'Booking', foreign_keys='Booking.client_id', backref='client', lazy='dynamic'
    )


class Worker(db.Model):
    __tablename__ = 'workers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Float, default=4.8)
    hourly_rate = db.Column(db.Integer, default=300)
    experience_years = db.Column(db.Integer, default=1)
    availability_status = db.Column(db.String(20), default='available')  # 'available' or 'busy'

    bookings = db.relationship(
        'Booking', foreign_keys='Booking.worker_id', backref='worker', lazy='dynamic'
    )


class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)
    service = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    booking_date = db.Column(db.String(50), nullable=False)
    note = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='confirmed')  # 'confirmed', 'completed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ── Seed Data (only runs when DB is empty) ────────────────────────────────────

def seed_db():
    if User.query.count() == 0:
        seed_workers = [
            ("Ravi Kumar",    "Plumbing",       "Andheri, Mumbai",         "9876543210", 4.8, 350, 6),
            ("Sunita Devi",   "House Cleaning", "Koramangala, Bangalore",  "9845012345", 4.9, 250, 8),
            ("Arjun Singh",   "Electrician",    "Lajpat Nagar, Delhi",     "9712345678", 4.7, 400, 5),
            ("Mohan Lal",     "Plumbing",       "Shivaji Nagar, Pune",     "9823456789", 4.8, 320, 7),
            ("Kavitha R.",    "AC Repair",      "T. Nagar, Chennai",       "9944556677", 4.9, 500, 10),
            ("Deepak Sharma", "Carpentry",      "Salt Lake, Kolkata",      "9334455667", 4.7, 380, 4),
            ("Prakash Nair",  "Painting",       "Baner, Pune",             "9021234567", 4.8, 300, 6),
        ]
        for name, service, location, phone, rating, rate, exp in seed_workers:
            u = User(name=name, phone=phone, role='worker')
            db.session.add(u)
            db.session.flush()  # get u.id without full commit
            w = Worker(
                user_id=u.id, service=service, location=location,
                rating=rating, hourly_rate=rate, experience_years=exp
            )
            db.session.add(w)
        db.session.commit()


with app.app_context():
    db.create_all()
    seed_db()


# ── Static File Routes ────────────────────────────────────────────────────────

@app.route('/style.css')
def serve_css():
    return send_from_directory('.', 'style.css')


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
    return send_from_directory(assets_dir, filename)


# ── Page Routes ───────────────────────────────────────────────────────────────

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


@app.route('/login', methods=['GET'])
def login_page():
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user and user.role == 'worker':
            return redirect(url_for('worker_profile'))
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
    if not worker:
        session.clear()
        return redirect(url_for('login_page'))
    active_bookings = Booking.query.filter_by(
        worker_id=worker.id, status='confirmed'
    ).order_by(Booking.created_at.desc()).all()
    completed_count = Booking.query.filter_by(
        worker_id=worker.id, status='completed'
    ).count()
    return render_template(
        'worker-profile.html',
        user=user,
        worker=worker,
        active_bookings=active_bookings,
        completed_count=completed_count
    )


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


# ── Auth API ──────────────────────────────────────────────────────────────────

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(force=True)
    phone = (data.get('phone') or '').strip()
    if not phone:
        return jsonify({'success': False, 'message': 'Phone number is required.'}), 400
    user = User.query.filter_by(phone=phone).first()
    if not user:
        return jsonify({'success': False, 'message': 'No account found. Please sign up first.'}), 404
    session['user_id'] = user.id
    session['role'] = user.role
    session['name'] = user.name
    return jsonify({'success': True, 'message': 'Login successful!', 'role': user.role})


@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json(force=True)
    name = (data.get('name') or '').strip()
    phone = (data.get('phone') or '').strip()
    role = (data.get('role') or 'client').strip().lower()
    if not name or not phone:
        return jsonify({'success': False, 'message': 'Name and phone number are required.'}), 400
    if User.query.filter_by(phone=phone).first():
        return jsonify({'success': False, 'message': 'This phone number is already registered.'}), 409
    u = User(name=name, phone=phone, role=role)
    db.session.add(u)
    db.session.flush()
    if role == 'worker':
        service = (data.get('service') or '').strip()
        location = (data.get('location') or '').strip()
        experience_years = int(data.get('experience_years') or 1)
        hourly_rate = int(data.get('hourly_rate') or 300)
        if not service or not location:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Service and location are required for workers.'}), 400
        w = Worker(
            user_id=u.id, service=service, location=location,
            experience_years=experience_years, hourly_rate=hourly_rate
        )
        db.session.add(w)
    db.session.commit()
    session['user_id'] = u.id
    session['role'] = u.role
    session['name'] = u.name
    return jsonify({'success': True, 'message': 'Account created!', 'role': u.role})


# ── Worker API ────────────────────────────────────────────────────────────────

@app.route('/api/workers', methods=['GET'])
def get_workers():
    service = (request.args.get('service') or '').strip().lower()
    location = (request.args.get('location') or '').strip().lower()
    query = Worker.query.join(User)
    if service:
        query = query.filter(Worker.service.ilike(f'%{service}%'))
    if location:
        query = query.filter(Worker.location.ilike(f'%{location}%'))
    workers = query.order_by(Worker.rating.desc()).all()
    return jsonify({
        'success': True,
        'workers': [{
            'id': w.id,
            'name': w.user.name,
            'service': w.service,
            'location': w.location,
            'phone': w.user.phone,
            'rating': w.rating,
            'hourly_rate': w.hourly_rate,
            'experience_years': w.experience_years,
            'availability_status': w.availability_status
        } for w in workers],
        'count': len(workers)
    })


@app.route('/api/worker/status', methods=['POST'])
def toggle_worker_status():
    if 'user_id' not in session or session.get('role') != 'worker':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    user = db.session.get(User, session['user_id'])
    worker = Worker.query.filter_by(user_id=user.id).first()
    if not worker:
        return jsonify({'success': False, 'message': 'Worker profile not found.'}), 404
    worker.availability_status = 'busy' if worker.availability_status == 'available' else 'available'
    db.session.commit()
    return jsonify({'success': True, 'new_status': worker.availability_status})


# ── Booking API ───────────────────────────────────────────────────────────────

@app.route('/api/book', methods=['POST'])
def book_service():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in to book a service.'}), 401
    data = request.get_json(force=True)
    service = (data.get('service') or '').strip()
    address = (data.get('address') or '').strip()
    booking_date = (data.get('date') or '').strip()
    note = (data.get('note') or '').strip()
    worker_name = (data.get('worker_name') or '').strip()
    if not service or not address or not booking_date:
        return jsonify({'success': False, 'message': 'Service, address, and date are required.'}), 400
    worker_id = None
    if worker_name:
        matched = Worker.query.join(User).filter(User.name == worker_name).first()
        if matched:
            worker_id = matched.id
            matched.availability_status = 'busy'
    b = Booking(
        client_id=session['user_id'],
        worker_id=worker_id,
        service=service,
        address=address,
        booking_date=booking_date,
        note=note,
        status='confirmed'
    )
    db.session.add(b)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'Booking confirmed! ID: BK{b.id:04d}',
        'booking_id': b.id
    })


@app.route('/api/complete-job/<int:booking_id>', methods=['POST'])
def complete_job(booking_id):
    if 'user_id' not in session or session.get('role') != 'worker':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return jsonify({'success': False, 'message': 'Booking not found.'}), 404
    user = db.session.get(User, session['user_id'])
    worker = Worker.query.filter_by(user_id=user.id).first()
    if not worker or booking.worker_id != worker.id:
        return jsonify({'success': False, 'message': 'Not authorized for this booking.'}), 403
    booking.status = 'completed'
    worker.availability_status = 'available'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Job marked as completed. You are now available!'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

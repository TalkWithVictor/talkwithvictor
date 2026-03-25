import os
import stripe
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
from models import db, User, Video, VideoView, Category, Payment, Correction
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///talkwithvictor.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads', 'videos')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max upload
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'victor9232005@gmail.com')
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_ENROLLMENT_PRICE = os.environ.get('STRIPE_ENROLLMENT_PRICE', '')
STRIPE_MONTHLY_PRICE = os.environ.get('STRIPE_MONTHLY_PRICE', '')
APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Necesitas iniciar sesión para acceder.'
login_manager.login_message_category = 'warning'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Acceso restringido.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def member_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_active_member and current_user.role != 'admin':
            flash('Necesitas ser miembro activo para acceder al contenido.', 'warning')
            return redirect(url_for('pricing'))
        return f(*args, **kwargs)
    return decorated

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ─── Public routes ────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=bool(remember))
            next_page = request.args.get('next')
            if user.role == 'admin':
                return redirect(next_page or url_for('admin_dashboard'))
            return redirect(next_page or url_for('student_dashboard'))
        flash('Email o contraseña incorrectos.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

# ─── Stripe / Payments ────────────────────────────────────────────────────────
@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    if not stripe.api_key:
        flash('El sistema de pagos no está configurado todavía. Contacta con Victor.', 'warning')
        return redirect(url_for('pricing'))
    try:
        session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[
                {'price': STRIPE_ENROLLMENT_PRICE, 'quantity': 1},
                {'price': STRIPE_MONTHLY_PRICE, 'quantity': 1},
            ],
            mode='subscription',
            success_url=APP_URL + '/payment/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=APP_URL + '/pricing',
        )
        return redirect(session.url, code=303)
    except Exception as e:
        flash(f'Error al procesar el pago: {str(e)}', 'danger')
        return redirect(url_for('pricing'))

@app.route('/payment/success')
@login_required
def payment_success():
    session_id = request.args.get('session_id')
    if session_id and stripe.api_key:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            current_user.is_active_member = True
            current_user.stripe_customer_id = session.customer
            current_user.stripe_subscription_id = session.subscription
            payment = Payment(
                user_id=current_user.id,
                stripe_payment_id=session_id,
                amount=session.amount_total / 100 if session.amount_total else 85,
                payment_type='enrollment+monthly',
                status='completed'
            )
            db.session.add(payment)
            db.session.commit()
        except Exception:
            pass
    else:
        # No Stripe configured — manually activate (useful for testing)
        current_user.is_active_member = True
        db.session.commit()
    flash('¡Pago exitoso! Ya tienes acceso completo.', 'success')
    return redirect(url_for('student_dashboard'))

@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    if not webhook_secret:
        return jsonify({'status': 'no webhook secret'}), 400
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        return jsonify({'error': 'invalid signature'}), 400

    if event['type'] == 'customer.subscription.deleted':
        sub_id = event['data']['object']['id']
        user = User.query.filter_by(stripe_subscription_id=sub_id).first()
        if user:
            user.is_active_member = False
            db.session.commit()
    return jsonify({'status': 'ok'})

# ─── Student routes ───────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
@member_required
def student_dashboard():
    videos = Video.query.filter_by(is_published=True).order_by(Video.created_at.desc()).limit(6).all()
    categories = Category.query.order_by(Category.order_num).all()
    viewed_ids = {v.video_id for v in VideoView.query.filter_by(user_id=current_user.id).all()}
    total_videos = Video.query.filter_by(is_published=True).count()
    corrections = Correction.query.filter_by(user_id=current_user.id).order_by(Correction.created_at.desc()).limit(5).all()
    return render_template('student/dashboard.html',
                           videos=videos, categories=categories,
                           viewed_ids=viewed_ids, total_videos=total_videos,
                           corrections=corrections)

@app.route('/videos')
@login_required
@member_required
def student_videos():
    category_filter = request.args.get('category', '')
    level_filter = request.args.get('level', '')
    search = request.args.get('q', '')

    query = Video.query.filter_by(is_published=True)
    if category_filter:
        query = query.filter_by(category=category_filter)
    if level_filter:
        query = query.filter_by(level=level_filter)
    if search:
        query = query.filter(Video.title.ilike(f'%{search}%'))

    videos = query.order_by(Video.created_at.desc()).all()
    categories = Category.query.order_by(Category.order_num).all()
    viewed_ids = {v.video_id for v in VideoView.query.filter_by(user_id=current_user.id).all()}

    return render_template('student/videos.html',
                           videos=videos, categories=categories,
                           viewed_ids=viewed_ids, category_filter=category_filter,
                           level_filter=level_filter, search=search)

@app.route('/video/<int:video_id>')
@login_required
@member_required
def watch_video(video_id):
    video = Video.query.get_or_404(video_id)
    video.view_count += 1
    # Record view
    existing = VideoView.query.filter_by(user_id=current_user.id, video_id=video_id).first()
    if not existing:
        view = VideoView(user_id=current_user.id, video_id=video_id)
        db.session.add(view)
    db.session.commit()
    return render_template('student/watch.html', video=video)

@app.route('/video/<int:video_id>/complete', methods=['POST'])
@login_required
def mark_complete(video_id):
    view = VideoView.query.filter_by(user_id=current_user.id, video_id=video_id).first()
    if view:
        view.completed = True
        db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/serve-video/<int:video_id>')
@login_required
@member_required
def serve_video(video_id):
    video = Video.query.get_or_404(video_id)
    if not video.filename:
        return 'No file', 404
    return send_from_directory(app.config['UPLOAD_FOLDER'], video.filename)

@app.route('/corrections', methods=['GET', 'POST'])
@login_required
@member_required
def corrections():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        if title and content:
            correction = Correction(user_id=current_user.id, title=title, content=content)
            db.session.add(correction)
            db.session.commit()
            flash('¡Envío recibido! Victor lo revisará pronto.', 'success')
            return redirect(url_for('corrections'))
    my_corrections = Correction.query.filter_by(user_id=current_user.id).order_by(Correction.created_at.desc()).all()
    return render_template('student/corrections.html', corrections=my_corrections)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name).strip()
        new_password = request.form.get('new_password', '').strip()
        if new_password:
            if len(new_password) >= 6:
                current_user.set_password(new_password)
            else:
                flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
                return redirect(url_for('profile'))
        db.session.commit()
        flash('Perfil actualizado.', 'success')
    return render_template('student/profile.html')

# ─── Admin routes ─────────────────────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin_dashboard():
    students = User.query.filter_by(role='student').all()
    videos = Video.query.count()
    active_members = User.query.filter_by(is_active_member=True, role='student').count()
    pending_corrections = Correction.query.filter_by(status='pending').count()
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html',
                           students=students, video_count=videos,
                           active_members=active_members,
                           pending_corrections=pending_corrections,
                           recent_payments=recent_payments)

@app.route('/admin/students')
@admin_required
def admin_students():
    students = User.query.filter_by(role='student').order_by(User.joined_at.desc()).all()
    return render_template('admin/students.html', students=students)

@app.route('/admin/students/create', methods=['GET', 'POST'])
@admin_required
def admin_create_student():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        level = request.form.get('level', 'beginner')
        active = request.form.get('active', 'false') == 'true'

        if User.query.filter_by(email=email).first():
            flash('Ya existe un usuario con ese email.', 'danger')
            return redirect(url_for('admin_create_student'))

        user = User(name=name, email=email, role='student',
                    is_active_member=active, level=level)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'Alumno {name} creado correctamente.', 'success')
        return redirect(url_for('admin_students'))
    return render_template('admin/create_student.html')

@app.route('/admin/students/<int:user_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_student(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_member = not user.is_active_member
    db.session.commit()
    status = 'activado' if user.is_active_member else 'desactivado'
    flash(f'Alumno {user.name} {status}.', 'success')
    return redirect(url_for('admin_students'))

@app.route('/admin/students/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_student(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Alumno eliminado.', 'success')
    return redirect(url_for('admin_students'))

@app.route('/admin/videos')
@admin_required
def admin_videos():
    videos = Video.query.order_by(Video.created_at.desc()).all()
    categories = Category.query.order_by(Category.order_num).all()
    return render_template('admin/videos.html', videos=videos, categories=categories)

@app.route('/admin/videos/upload', methods=['GET', 'POST'])
@admin_required
def admin_upload_video():
    categories = Category.query.order_by(Category.order_num).all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        level = request.form.get('level', 'all')
        youtube_url = request.form.get('youtube_url', '').strip()
        duration = request.form.get('duration', '').strip()

        video = Video(title=title, description=description, category=category,
                      level=level, youtube_url=youtube_url if youtube_url else None,
                      duration=duration)

        file = request.files.get('video_file')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            video.filename = filename

        if not video.filename and not video.youtube_url:
            flash('Debes subir un vídeo o añadir una URL de YouTube.', 'danger')
            return render_template('admin/upload_video.html', categories=categories)

        db.session.add(video)
        db.session.commit()
        flash(f'Vídeo "{title}" añadido correctamente.', 'success')
        return redirect(url_for('admin_videos'))

    return render_template('admin/upload_video.html', categories=categories)

@app.route('/admin/videos/<int:video_id>/delete', methods=['POST'])
@admin_required
def admin_delete_video(video_id):
    video = Video.query.get_or_404(video_id)
    if video.filename:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], video.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    db.session.delete(video)
    db.session.commit()
    flash('Vídeo eliminado.', 'success')
    return redirect(url_for('admin_videos'))

@app.route('/admin/videos/<int:video_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_video(video_id):
    video = Video.query.get_or_404(video_id)
    video.is_published = not video.is_published
    db.session.commit()
    return redirect(url_for('admin_videos'))

@app.route('/admin/categories', methods=['GET', 'POST'])
@admin_required
def admin_categories():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        emoji = request.form.get('emoji', '📚').strip()
        description = request.form.get('description', '').strip()
        if name:
            cat = Category(name=name, emoji=emoji, description=description)
            db.session.add(cat)
            db.session.commit()
            flash(f'Categoría "{name}" creada.', 'success')
    categories = Category.query.order_by(Category.order_num).all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/corrections')
@admin_required
def admin_corrections():
    corrections = Correction.query.order_by(Correction.created_at.desc()).all()
    return render_template('admin/corrections.html', corrections=corrections)

@app.route('/admin/corrections/<int:correction_id>', methods=['GET', 'POST'])
@admin_required
def admin_correction_detail(correction_id):
    correction = Correction.query.get_or_404(correction_id)
    if request.method == 'POST':
        correction.correction = request.form.get('correction', '').strip()
        correction.status = 'corrected'
        correction.corrected_at = datetime.utcnow()
        db.session.commit()
        flash('Corrección guardada.', 'success')
        return redirect(url_for('admin_corrections'))
    return render_template('admin/correction_detail.html', correction=correction)

# ─── Init DB ──────────────────────────────────────────────────────────────────
def init_db():
    with app.app_context():
        db.create_all()
        # Create admin if not exists
        admin = User.query.filter_by(email=ADMIN_EMAIL).first()
        if not admin:
            admin = User(
                name='Victor',
                email=ADMIN_EMAIL,
                role='admin',
                is_active_member=True
            )
            admin.set_password(os.environ.get('ADMIN_PASSWORD', 'changeme123'))
            db.session.add(admin)

        # Default categories
        default_cats = [
            ('Gramática', '📖', 'Reglas y estructuras del español'),
            ('Vocabulario', '💬', 'Palabras y expresiones esenciales'),
            ('Pronunciación', '🎙️', 'Habla como un nativo'),
            ('Cultura', '🇪🇸', 'España y el mundo hispanohablante'),
            ('Conversación', '🗣️', 'Practica situaciones reales'),
            ('Expresiones', '💡', 'Frases hechas y coloquialismos'),
        ]
        for name, emoji, desc in default_cats:
            if not Category.query.filter_by(name=name).first():
                cat = Category(name=name, emoji=emoji, description=desc)
                db.session.add(cat)

        db.session.commit()
        print(f"✅ Base de datos inicializada. Admin: {ADMIN_EMAIL}")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)

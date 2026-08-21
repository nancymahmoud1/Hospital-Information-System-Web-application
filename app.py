import datetime
import os
from flask import Flask, jsonify, render_template, redirect, session, request, flash, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

# Import after dotenv
from main import cursor, database_session

app = Flask(__name__)

# --- CONFIG FOR DEPLOYMENT ---
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.template_filter('enumerate')
def jinja2_enumerate(iterable):
    return enumerate(iterable)


def execute_sql_file(filename):
    """Run SQL file safely - use only on first setup"""
    try:
        with open(filename, 'r') as sql_file:
            sql_content = sql_file.read()
            cursor.execute(sql_content)
        database_session.commit()
        print(f"Successfully executed {filename}")
    except Exception as e:
        database_session.rollback()
        print(f"Error executing {filename}: {e}")
        # Don't crash app if tables already exist


@app.route('/')
def index():
    data = session.get('data')
    if data is None:
        return redirect(url_for('login'))

    if not data.get('photo'):
        data['photo'] = 'https://cdn1.iconfinder.com/data/icons/avatar-3/512/Doctor-512.png'

    try:
        cursor.execute('SELECT doc_id, fname, lname, photo, brief FROM doctor')
        doctors = cursor.fetchall()
    except Exception:
        database_session.rollback()
        doctors = []

    try:
        cursor.execute('SELECT number, fname, lname FROM nurse')
        nurses = cursor.fetchall()
        nurse_ids = [row[0] for row in nurses]
        nurse_names = [f"{row[1]} {row[2]}" for row in nurses]
    except Exception:
        database_session.rollback()
        nurses = []
        nurse_ids = []
        nurse_names = []

    prescriptions = []
    appointments = []

    is_patient = data['job'] == 'patient'
    is_doctor = data['job'] == 'doctor'
    is_nurse = data['job'] == 'nurse'

    try:
        if is_nurse:
            cursor.execute(
                'SELECT p.fname, p.lname, pr.drug, pr.dosage FROM prescriptions pr JOIN patient p ON pr.p_id = p.p_id WHERE pr.n_id = %s',
                (data['number'],))
            prescriptions = cursor.fetchall()
        elif is_doctor:
            cursor.execute(
                '''
                SELECT a.id,
                       p.fname,
                       p.lname,
                       a.appointment_date,
                       a.appointment_time,
                       (CASE WHEN (a.appointment_date + a.appointment_time::interval)::timestamp < NOW() THEN 1 ELSE 0 END) AS is_past,
                       (CASE WHEN a.appointment_date = CURRENT_DATE THEN 1 ELSE 0 END)                                      AS is_today
                FROM appointments a
                         JOIN patient p ON a.p_id = p.p_id
                WHERE a.doc_id = %s
                ORDER BY is_past, a.appointment_date, a.appointment_time
                ''',
                (data['doc_id'],)
            )
            appointments = cursor.fetchall()
        elif is_patient:
            cursor.execute(
                '''
                SELECT a.id,
                       dr.fname,
                       dr.lname,
                       a.appointment_date,
                       a.appointment_time,
                       (CASE WHEN (a.appointment_date + a.appointment_time::interval)::timestamp < NOW() THEN 1 ELSE 0 END) AS is_past,
                       (CASE WHEN a.appointment_date = CURRENT_DATE THEN 1 ELSE 0 END)                                      AS is_today
                FROM appointments a
                         JOIN doctor dr ON a.doc_id = dr.doc_id
                WHERE a.p_id = %s
                ORDER BY is_past, a.appointment_date, a.appointment_time
                ''',
                (data['p_id'],)
            )
            appointments = cursor.fetchall()
            cursor.execute(
                'SELECT n.fname, n.lname, pr.drug FROM prescriptions pr JOIN nurse n ON pr.n_id = n.number WHERE pr.p_id = %s',
                (data['p_id'],))
            prescriptions = cursor.fetchall()
    except Exception as e:
        print(f"DB error: {e}")
        database_session.rollback()
        appointments = []
        prescriptions = []

    try:
        if is_doctor:
            cursor.execute(
                'SELECT p_id, fname, lname FROM patient WHERE p_id IN (SELECT p_id FROM appointments WHERE doc_id = %s)',
                (data['doc_id'],))
            patient_info = cursor.fetchall()
            patient_ids = [row[0] for row in patient_info]
            patient_names = [f"{row[1]} {row[2]}" for row in patient_info]
        else:
            patient_ids = []
            patient_names = []
    except Exception:
        database_session.rollback()
        patient_ids = []
        patient_names = []

    unique_doctors = {}
    try:
        if is_patient:
            cursor.execute(
                'SELECT d.doc_id, d.fname, d.lname FROM doctor d JOIN appointments a ON d.doc_id = a.doc_id WHERE a.p_id = %s',
                (data['p_id'],))
            doctor_info = cursor.fetchall()
            unique_doctors = {row[0]: f"{row[1]} {row[2]}" for row in doctor_info}
    except Exception:
        database_session.rollback()
        unique_doctors = {}

    try:
        cursor.execute(
            'SELECT r.rating, r.review, p.fname, p.lname FROM reviews r JOIN patient p ON r.p_id = p.p_id WHERE r.doc_id = %s',
            (data['doc_id'],))
        reviews = cursor.fetchall()
    except Exception:
        database_session.rollback()
        reviews = []

    try:
        cursor.execute('''
                       SELECT d.doc_id, AVG(r.rating) AS avg_rating
                       FROM doctor d
                                LEFT JOIN reviews r ON d.doc_id = r.doc_id
                       GROUP BY d.doc_id
                       ''')
        doctor_ratings = {row[0]: row[1] for row in cursor.fetchall()}
    except Exception:
        database_session.rollback()
        doctor_ratings = {}

    return render_template("home.html", data=data, doctors=doctors, is_patient=is_patient, is_doctor=is_doctor,
                           is_nurse=is_nurse, doc_ids=list(unique_doctors.keys()),
                           doc_names=list(unique_doctors.values()),
                           unique_doctors=unique_doctors, patient_ids=patient_ids, patient_names=patient_names,
                           appointments=appointments, prescriptions=prescriptions, nurse_ids=nurse_ids,
                           nurse_names=nurse_names, reviews=reviews, doctor_ratings=doctor_ratings)


@app.route('/profile')
def profile():
    data = session.get('data')
    if data is None:
        return redirect(url_for('login'))
    return render_template('profile.html', data=data)


@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    data = session.get('data')
    if data is None:
        return redirect(url_for('login'))

    fname = request.form.get('fname')
    lname = request.form.get('lname')
    email = request.form.get('email')
    phone = request.form.get('phoneNumber')
    address = request.form.get('address')

    table = data['job']
    id_col = 'p_id' if table == 'patient' else 'doc_id' if table == 'doctor' else 'number'
    id_val = data.get('p_id') or data.get('doc_id') or data.get('number')

    try:
        # Handle photo upload
        photo_url = data.get('photo')
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{id_val}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                photo_url = f"/{filepath.replace(os.sep, '/')}"

        cursor.execute(
            f'UPDATE {table} SET fname=%s, lname=%s, email=%s, phonenumber=%s, address=%s, photo=%s WHERE {id_col}=%s',
            (fname, lname, email, phone, address, photo_url, id_val))
        database_session.commit()

        # Update session
        data.update({'fname': fname, 'lname': lname, 'email': email, 'phoneNumber': phone, 'address': address,
                     'photo': photo_url})
        session['data'] = data

    except Exception as e:
        database_session.rollback()
        flash(f"Error updating profile: {e}", "danger")

    return redirect(url_for('profile'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = None
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phoneNumber')
        address = request.form.get('address')
        job = request.form.get('job')

        photo_path = 'https://cdn1.iconfinder.com/data/icons/avatar-3/512/Doctor-512.png'
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{email}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                photo_path = f"/{filepath.replace(os.sep, '/')}"

        try:
            if job == 'doctor':
                cursor.execute(
                    'INSERT INTO doctor (fname, lname, email, password, address, phonenumber, photo, job) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                    (fname, lname, email, password, address, phone, photo_path, job))
            elif job == 'nurse':
                cursor.execute(
                    'INSERT INTO nurse (fname, lname, email, password, address, phonenumber, photo, job) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                    (fname, lname, email, password, address, phone, photo_path, job))
            else:
                cursor.execute(
                    'INSERT INTO patient (fname, lname, email, password, address, phonenumber, photo, job) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                    (fname, lname, email, password, address, phone, photo_path, job))
            database_session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            database_session.rollback()
            message = f"Registration failed: {e}"

    return render_template('register.html', message=message)


@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        job = request.form.get('job')

        try:
            if job == 'doctor':
                cursor.execute('SELECT * from doctor where email = %s and password = %s', (email, password))
                user = cursor.fetchone()
            elif job == 'nurse':
                cursor.execute('SELECT * from nurse where email = %s and password = %s', (email, password))
                user = cursor.fetchone()
            else:
                cursor.execute('SELECT * from patient where email = %s and password = %s', (email, password))
                user = cursor.fetchone()

            if user is None:
                message = 'Invalid email or password.'
            else:
                session['data'] = dict(user)
                return redirect(url_for('index'))
        except Exception as e:
            database_session.rollback()
            message = f"Login error: {e}"

    return render_template('login.html', message=message)


@app.route('/make_appointment', methods=['POST'])
def make_appointment():
    data = session.get('data')
    if data is None:
        return redirect(url_for('login'))

    doctor_id = request.form.get('doctor')
    appointment_date = request.form.get('appointment_date')
    appointment_time = request.form.get('appointment_time')

    if data['job'] == 'patient':
        patient_id = data['p_id']
    else:
        patient_id = request.form.get('p_id')

    try:
        cursor.execute(
            'INSERT INTO appointments (p_id, doc_id, appointment_date, appointment_time) VALUES (%s, %s, %s, %s)',
            (patient_id, doctor_id, appointment_date, appointment_time)
        )
        database_session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error saving appointment: {e}")
        database_session.rollback()
        return redirect(url_for('index'))


@app.route('/prescribe', methods=['GET', 'POST'])
def prescribe():
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        drug = request.form.get('drug')
        dosage = request.form.get('dosage')
        nurse_id = request.form.get('nurse_id')
        doctor_id = session['data']['doc_id']

        cursor.execute('SELECT fname, lname FROM patient WHERE p_id = %s', (patient_id,))
        patient_name = cursor.fetchone()
        patient_name = f"{patient_name[0]} {patient_name[1]}" if patient_name else "Unknown"

        cursor.execute(
            'INSERT INTO prescriptions (p_id, drug, dosage, doc_id, n_id, patient_name) VALUES (%s, %s, %s, %s, %s, %s)',
            (patient_id, drug, dosage, doctor_id, nurse_id, patient_name)
        )
        database_session.commit()
        return redirect(url_for('index'))
    return render_template('home.html')


@app.route('/reviews', methods=['POST'])
def reviews():
    data = session.get('data')
    if data is None:
        return redirect(url_for('login'))

    if request.method == 'POST':
        p_id = data['p_id']
        p_name = f"{data['fname']} {data['lname']}"
        doc_id = request.form.get('doc_id')
        rating = request.form.get('rating')
        review = request.form.get('review')

        try:
            cursor.execute('SELECT fname, lname FROM doctor WHERE doc_id = %s', (doc_id,))
            doctor_name = cursor.fetchone()
            doctor_name = f"{doctor_name[0]} {doctor_name[1]}" if doctor_name else "Unknown Doctor"

            cursor.execute(
                "INSERT INTO reviews (p_id, doc_id, rating, review, patient_name, doc_name) VALUES (%s, %s, %s, %s, %s, %s)",
                (p_id, doc_id, rating, review, p_name, doctor_name)
            )
            database_session.commit()
            flash('Review submitted successfully!', 'success')
        except Exception as e:
            database_session.rollback()
            flash(f'Error saving review: {e}', 'danger')

        return redirect(url_for('index'))


@app.route('/get_available_times', methods=['POST'])
def get_available_times():
    data = request.get_json()
    doc_id = data.get('doctor_id')
    appointment_date = data.get('appointment_date')
    patient_id = session.get('data').get('p_id')

    if not doc_id or not appointment_date:
        return jsonify({'error': 'Missing data'}), 400

    try:
        cursor.execute(
            'SELECT appointment_time FROM appointments WHERE doc_id = %s AND appointment_date = %s',
            (doc_id, appointment_date)
        )
        existing_doctor_appointments = cursor.fetchall()
        booked_doctor_times = {row[0] for row in existing_doctor_appointments}

        cursor.execute(
            'SELECT appointment_time FROM appointments WHERE p_id = %s AND appointment_date = %s',
            (patient_id, appointment_date)
        )
        existing_patient_appointments = cursor.fetchall()
        booked_patient_times = {row[0] for row in existing_patient_appointments}

        booked_times = booked_doctor_times.union(booked_patient_times)

        all_times = []
        start_hour = 8
        end_hour = 16
        interval = 30
        for hour in range(start_hour, end_hour):
            for minutes in range(0, 60, interval):
                time = datetime.time(hour, minutes)
                all_times.append(time)

        available_times = [time.strftime('%H:%M') for time in all_times if time not in booked_times]
        return jsonify({'available_times': available_times})

    except Exception as e:
        database_session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/logout')
def logout():
    session.pop('data', None)
    return redirect(url_for('login'))


@app.route('/health')
def health():
    try:
        cursor.execute('SELECT 1')
        return jsonify({"status": "ok", "db": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "error", "db": str(e)}), 500


if __name__ == '__main__':
    # Only run SQL init if INIT_DB=true - don't run on every deploy
    if os.getenv("INIT_DB", "false").lower() == "true":
        execute_sql_file('SQLQuery1.sql')

    port = int(os.getenv("PORT", 5000))
    # debug False for production
    app.run(host='0.0.0.0', port=port, debug=os.getenv("FLASK_ENV") != "production")

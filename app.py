import datetime
import os
from flask import Flask, jsonify, render_template, redirect, session, request, flash, url_for
from werkzeug.utils import secure_filename
from main import cursor, database_session

app = Flask(__name__)
app.secret_key = 'yassien'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

@app.template_filter('enumerate')
def jinja2_enumerate(iterable):
    return enumerate(iterable)


def execute_sql_file(filename):
    with open(filename, 'r') as sql_file:
        cursor.execute(sql_file.read())
    database_session.commit()


@app.route('/')
def index():
    data = session.get('data')
    if data is None:
        return redirect(url_for('login'))

    # Set default photo URL if not set
    if not data.get('photo'):
        data['photo'] = 'https://cdn1.iconfinder.com/data/icons/avatar-3/512/Doctor-512.png'

    # Fetch the list of doctors from the database
    try:
        cursor.execute('SELECT doc_id, fname, lname, photo, brief FROM doctor')
        doctors = cursor.fetchall()
    except Exception as e:
        doctors = []

    # Fetch the list of nurses from the database
    try:
        cursor.execute('SELECT number, fname, lname FROM nurse')
        nurses = cursor.fetchall()
        nurse_ids = [row[0] for row in nurses]
        nurse_names = [f"{row[1]} {row[2]}" for row in nurses]
    except Exception as e:
        nurses = []
        nurse_ids = []
        nurse_names = []

    # Initialize prescriptions to avoid UnboundLocalError
    prescriptions = []
    appointments = []

    # Check if the user is a Patient
    is_patient = data['job'] == 'patient'
    # Check if the user is a Doctor
    is_doctor = data['job'] == 'doctor'
    # Check if the user is a Nurse
    is_nurse = data['job'] == 'nurse'

    # Fetch the prescriptions for the current nurse
    try:
        if is_nurse:
            cursor.execute(
                'SELECT p.fname, p.lname, pr.drug, pr.dosage FROM prescriptions pr JOIN patient p ON pr.p_id = p.p_id WHERE pr.n_id = %s',
                (data['number'],))
            prescriptions = cursor.fetchall()
        elif is_doctor:
            cursor.execute(
                '''
                SELECT a.id, p.fname, p.lname, a.appointment_date, a.appointment_time,
                (CASE WHEN (a.appointment_date + a.appointment_time::interval)::timestamp < NOW() THEN 1 ELSE 0 END) AS is_past,
                (CASE WHEN a.appointment_date = CURRENT_DATE THEN 1 ELSE 0 END) AS is_today
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
                SELECT a.id, dr.fname, dr.lname, a.appointment_date, a.appointment_time,
                (CASE WHEN (a.appointment_date + a.appointment_time::interval)::timestamp < NOW() THEN 1 ELSE 0 END) AS is_past,
                (CASE WHEN a.appointment_date = CURRENT_DATE THEN 1 ELSE 0 END) AS is_today
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
        appointments = []
        prescriptions = []

    # Fetch the list of patient IDs and names for the current doctor
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
    except Exception as e:
        patient_ids = []

    unique_doctors = {}
    try:
        if is_patient:
            cursor.execute(
                'SELECT d.doc_id, d.fname, d.lname FROM doctor d JOIN appointments a ON d.doc_id = a.doc_id WHERE a.p_id = %s',
                (data['p_id'],))
            doctor_info = cursor.fetchall()

            # Use a dictionary to ensure uniqueness
            unique_doctors = {row[0]: f"{row[1]} {row[2]}" for row in doctor_info}
    except Exception as e:
        unique_doctors = {}

    # Fetch the list of reviews from the database
    try:
        cursor.execute('SELECT r.rating, r.review, p.fname, p.lname FROM reviews r JOIN patient p ON r.p_id = p.p_id WHERE r.doc_id = %s', (data['doc_id'],))
        reviews = cursor.fetchall()
    except Exception as e:
        reviews = []

    # Fetch the average rating for each doctor
    try:
        cursor.execute('''
            SELECT d.doc_id, AVG(r.rating) AS avg_rating 
            FROM doctor d 
            LEFT JOIN reviews r ON d.doc_id = r.doc_id 
            GROUP BY d.doc_id
        ''')
        doctor_ratings = {row[0]: row[1] for row in cursor.fetchall()}
    except Exception as e:
        doctor_ratings = {}

    return render_template("home.html", data=data, doctors=doctors, is_patient=is_patient, is_doctor=is_doctor,
                            is_nurse=is_nurse, doc_ids=list(unique_doctors.keys()), doc_names=list(unique_doctors.values()), 
                            unique_doctors=unique_doctors, patient_ids=patient_ids, patient_names=patient_names, 
                            appointments=appointments, prescriptions=prescriptions, nurse_ids=nurse_ids, 
                            nurse_names=nurse_names, reviews=reviews, doctor_ratings=doctor_ratings)

@app.route('/profile')
def profile():
    data = session.get('data')
    if data is None:
        return redirect(url_for('login'))

    # Initialize prescriptions to avoid UnboundLocalError
    prescriptions = []
    appointments = []
    reviews = []
    doctor_ratings = {}
    is_patient = data['job'] == 'patient'
    is_doctor = data['job'] == 'doctor'
    is_nurse = data['job'] == 'nurse'

    now = datetime.datetime.now()
    today_date = now.date().strftime('%Y-%m-%d')

    if is_doctor:
        cursor.execute(
            '''
            SELECT a.id, p.fname, p.lname, a.appointment_date, a.appointment_time,
            (CASE WHEN (a.appointment_date + a.appointment_time::interval)::timestamp < %s THEN 1 ELSE 0 END) AS is_past,
            (CASE WHEN a.appointment_date = %s THEN 1 ELSE 0 END) AS is_today
            FROM appointments a
            JOIN patient p ON a.p_id = p.p_id
            WHERE a.doc_id = %s
            ORDER BY is_past, a.appointment_date, a.appointment_time
            ''',
            (now, today_date, data['doc_id'])
        )
        appointments = cursor.fetchall()
        cursor.execute('SELECT p.fname, p.lname, r.rating, r.review FROM reviews r JOIN patient p ON r.p_id = p.p_id WHERE r.doc_id = %s', (data['doc_id'],))
        reviews = cursor.fetchall()
        cursor.execute('SELECT d.doc_id, AVG(r.rating) AS avg_rating FROM doctor d LEFT JOIN reviews r ON d.doc_id = r.doc_id WHERE d.doc_id = %s GROUP BY d.doc_id', (data['doc_id'],))
        doctor_ratings = {row[0]: row[1] for row in cursor.fetchall()}
    elif is_nurse:
        cursor.execute(
            'SELECT pr.patient_name, pr.drug, pr.dosage FROM prescriptions pr JOIN nurse n ON pr.n_id = n.number WHERE pr.n_id = %s',
            (data['number'],))
        prescriptions = cursor.fetchall()
    else:
        cursor.execute(
            '''
            SELECT a.id, dr.fname, dr.lname, a.appointment_date, a.appointment_time,
            (CASE WHEN (a.appointment_date + a.appointment_time::interval)::timestamp < %s THEN 1 ELSE 0 END) AS is_past,
            (CASE WHEN a.appointment_date = %s THEN 1 ELSE 0 END) AS is_today
            FROM appointments a
            JOIN doctor dr ON a.doc_id = dr.doc_id
            WHERE a.p_id = %s
            ORDER BY is_past, a.appointment_date, a.appointment_time
            ''',
            (now, today_date, data['p_id'])
        )
        appointments = cursor.fetchall()
        cursor.execute('SELECT patient_name, drug, dosage FROM prescriptions WHERE p_id = %s', (data['p_id'],))
        prescriptions = cursor.fetchall()

    unique_doctors = {}
    try:
        if is_patient:
            cursor.execute(
                'SELECT d.doc_id, d.fname, d.lname FROM doctor d JOIN appointments a ON d.doc_id = a.doc_id WHERE a.p_id = %s',
                (data['p_id'],))
            doctor_info = cursor.fetchall()
            
            # Use a set to ensure uniqueness
            unique_doctors = set((row[0], f"{row[1]} {row[2]}") for row in doctor_info)
            doc_ids, doc_names = zip(*unique_doctors) if unique_doctors else ([], [])
        else:
            doc_ids = []
            doc_names = []
    except Exception as e:
        doc_ids = []
        doc_names = []

    return render_template("profile.html", data=data, appointments=appointments, prescriptions=prescriptions,
                            is_doctor=is_doctor, is_patient=is_patient, is_nurse=is_nurse, reviews=reviews, doctor_ratings=doctor_ratings, doc_ids=doc_ids, doc_names=doc_names)


@app.route('/update', methods=['POST'])
def update():
    data = session.get('data')
    if data is None:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Retrieve updated information from the form
        updated_firstname = request.form.get('firstname')
        updated_lastname = request.form.get('lastname')
        updated_email = request.form.get('email')
        updated_phone = request.form.get('phone')
        updated_address = request.form.get('address')
        updated_brief = request.form.get('brief') if data['job'] == 'doctor' else None
        updated_job = data['job']
        remove_photo = request.form.get('remove_photo', False)

        profile_photo = request.files.get('profile_photo')
        default_photo_url = 'https://cdn1.iconfinder.com/data/icons/avatar-3/512/Doctor-512.png'
        photo_url = data['photo']  # Keep the current photo URL by default

        if remove_photo:
            photo_url = default_photo_url
        elif profile_photo and profile_photo.filename != '':
            # Ensure the uploads directory exists
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            photo_filename = secure_filename(profile_photo.filename)
            profile_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
            photo_url = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)

        # Update the user's information in the database
        try:
            if updated_job == 'doctor':
                cursor.execute(
                    'UPDATE doctor SET fname=%s, lname=%s, email=%s, phonenumber=%s, address=%s, brief=%s, photo=%s WHERE email=%s',
                    (updated_firstname, updated_lastname, updated_email, updated_phone, updated_address, updated_brief,
                        photo_url, data['email'])
                )
            elif updated_job == 'nurse':
                cursor.execute(
                    'UPDATE nurse SET fname=%s, lname=%s, email=%s, phonenumber=%s, address=%s, photo=%s WHERE email=%s',
                    (updated_firstname, updated_lastname, updated_email, updated_phone, updated_address, photo_url,
                        data['email'])
                )
            else:
                cursor.execute(
                    'UPDATE patient SET fname=%s, lname=%s, email=%s, phonenumber=%s, address=%s, photo=%s WHERE email=%s',
                    (updated_firstname, updated_lastname, updated_email, updated_phone, updated_address, photo_url,
                        data['email'])
                )
            database_session.commit()

            # Retrieve the updated user data from the database
            if updated_job == 'doctor':
                cursor.execute('SELECT * FROM doctor WHERE email = %s', (updated_email,))
            elif updated_job == 'nurse':
                cursor.execute('SELECT * FROM nurse WHERE email = %s', (updated_email,))
            else:
                cursor.execute('SELECT * FROM patient WHERE email = %s', (updated_email,))

            updated_user = cursor.fetchone()

            if updated_user is None:
                print(f"Error: No user found with email {updated_email}")
                return redirect(url_for('profile'))

            # Update the session['data'] variable with the new values
            session['data'] = dict(updated_user)

            return redirect(url_for('profile'))

        except Exception as e:
            print(f"Error updating user: {e}")
            database_session.rollback()
            return redirect(url_for('profile'))


@app.route('/register', methods=["GET", "POST"])
def register():
    message = None
    if request.method == "POST":
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone = request.form.get('phone')
        address = request.form.get('address')
        job = request.form.get('job')
        profile_photo = request.files.get('profile_photo')
        brief = request.form.get('brief') if job == 'doctor' else None

        default_photo_url = 'https://cdn1.iconfinder.com/data/icons/avatar-3/512/Doctor-512.png'

        if profile_photo:
            # Ensure the uploads directory exists
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            photo_filename = secure_filename(profile_photo.filename)
            profile_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
            photo_url = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
        else:
            photo_url = default_photo_url

        cursor.execute('SELECT email FROM doctor WHERE email = %s', (email,))
        email_database = cursor.fetchone()
        if email_database is None:
            if job == 'doctor':
                cursor.execute(
                    'INSERT INTO doctor(fname, lname, email, password, phonenumber, address, photo, brief) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                    (firstname, lastname, email, password, phone, address, photo_url, brief)
                )
                database_session.commit()
                message = 'Thank you for registering. Please login.'
                return redirect(url_for('login'))
            elif job == 'nurse':
                cursor.execute(
                    'INSERT INTO nurse(fname, lname, email, password, phonenumber, address, photo) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (firstname, lastname, email, password, phone, address, photo_url)
                )
                database_session.commit()
                message = 'Thank you for registering. Please login.'
                return redirect(url_for('login'))
            else:
                cursor.execute(
                    'INSERT INTO patient(fname, lname, email, password, phonenumber, address, photo) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (firstname, lastname, email, password, phone, address, photo_url)
                )
                database_session.commit()
                message = 'Thank you for registering. Please login.'
                return redirect(url_for('login'))
        else:
            message = 'Account already exists!'
    return render_template('register.html', msg=message)


@app.route('/login', methods=["GET", "POST"])
def login():
    message = None
    if request.method == "POST":
        job = request.form.get('job')
        email = request.form.get('email')
        password = request.form.get('password')
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
    return render_template('login.html', message=message)


@app.route('/make_appointment', methods=['POST'])
def make_appointment():
    data = session.get('data')
    if data is None:
        return redirect(url_for('login'))

    # Fetch doctor ID from the database (assuming doctor name is submitted)
    doctor_id = request.form.get('doctor')
    cursor.execute('SELECT doc_id FROM doctor WHERE fname = %s', (doctor_id,))

    appointment_date = request.form.get('appointment_date')
    appointment_time = request.form.get('appointment_time')

    if data['job'] == 'patient':
        patient_id = data['p_id']
    else:
        patient_id = request.form.get('p_id')

    try:
        # Insert the appointment data into the appointments table
        cursor.execute(
            'INSERT INTO appointments (p_id, doc_id, appointment_date, appointment_time) VALUES (%s, %s, %s, %s)',
            (patient_id, doctor_id, appointment_date, appointment_time)
        )
        database_session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        # Handle any errors that occur during the database insertion
        print(f"Error saving appointment: {e}")
        database_session.rollback()
        return redirect(url_for('index'))


@app.route('/prescribe', methods=['GET', 'POST'])
def prescribe():
    if request.method == 'POST':
        # Get the data from the form
        patient_id = request.form.get('patient_id')
        drug = request.form.get('drug')
        dosage = request.form.get('dosage')
        nurse_id = request.form.get('nurse_id')
        doctor_id = session['data']['doc_id']

        # Fetch the patient name from the database
        cursor.execute('SELECT fname, lname FROM patient WHERE p_id = %s', (patient_id,))
        patient_name = cursor.fetchone()
        if patient_name:
            patient_name = f"{patient_name[0]} {patient_name[1]}"
        else:
            patient_name = "Unknown"

        # Insert the prescription into the database
        cursor.execute(
            'INSERT INTO prescriptions (p_id, drug, dosage, doc_id, n_id, patient_name) VALUES (%s, %s, %s, %s, %s, %s)',
            (patient_id, drug, dosage, doctor_id, nurse_id, patient_name)
        )
        database_session.commit()

        # Redirect the user to the appropriate page
        return redirect(url_for('index'))

    return render_template('home.html')


@app.route('/reviews', methods=['POST'])
def reviews():
    data = session.get('data')
    if data is None:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get the form data
        p_id = data['p_id']
        p_name = f"{data['fname']} {data['lname']}"
        doc_id = request.form.get('doc_id')
        rating = request.form.get('rating')
        review = request.form.get('review')
        
        try:
            # Fetch doctor name
            cursor.execute('SELECT fname, lname FROM doctor WHERE doc_id = %s', (doc_id,))
            doctor_name = cursor.fetchone()
            if doctor_name:
                doctor_name = f"{doctor_name[0]} {doctor_name[1]}"
            else:
                doctor_name = "Unknown Doctor"

            # Insert the review into the database
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
        # Fetch doctor's existing appointments
        cursor.execute(
            'SELECT appointment_time FROM appointments WHERE doc_id = %s AND appointment_date = %s',
            (doc_id, appointment_date)
        )
        existing_doctor_appointments = cursor.fetchall()
        booked_doctor_times = {row[0] for row in existing_doctor_appointments}

        # Fetch patient's existing appointments
        cursor.execute(
            'SELECT appointment_time FROM appointments WHERE p_id = %s AND appointment_date = %s',
            (patient_id, appointment_date)
        )
        existing_patient_appointments = cursor.fetchall()
        booked_patient_times = {row[0] for row in existing_patient_appointments}

        # Combine booked times
        booked_times = booked_doctor_times.union(booked_patient_times)

        # Generate all possible times from 8 AM to 4 PM in 30-minute intervals
        all_times = []
        start_hour = 8
        end_hour = 16
        interval = 30  # 30 minutes
        for hour in range(start_hour, end_hour):
            for minutes in range(0, 60, interval):
                time = datetime.time(hour, minutes)
                all_times.append(time)

        available_times = [time.strftime('%H:%M') for time in all_times if time not in booked_times]

        return jsonify({'available_times': available_times})

    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/logout')
def logout():
    session.pop('data', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    # Initialize the database by executing the SQL script
    execute_sql_file('SQLQuery1.sql')
    app.run(debug=True)

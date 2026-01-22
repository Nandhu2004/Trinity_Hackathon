from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from ml_engine import chatbot_reply,summarize_consultation,analyze_symptoms

app = Flask(__name__)
app.secret_key = "telemedicine_2026_secret"


# ---------------- DATABASE ----------------

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- LOGIN REQUIRED DECORATOR ----------------

def login_required(role=None):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'username' not in session:
                flash("Please login first", "danger")
                return redirect(url_for('login'))

            if role and session.get('role') != role:
                flash("Unauthorized access", "danger")
                return redirect(url_for('login'))

            return f(*args, **kwargs)
        return decorated
    return wrapper


# ---------------- INDEX ----------------

@app.route('/')
def index():
    return render_template('index.html')


# ---------------- LOGIN ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('psw')

        db = get_db_connection()
        user = db.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
        db.close()

        if user and check_password_hash(user['password'], password):

            # clear old session
            session.clear()

            # standard session keys
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['fullname'] = user['fullname']

            flash("Login successful!", "success")

            # role based redirect
            if user['role'] == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))

        flash("Invalid username or password", "danger")

    return render_template("login.html")


# ---------------- REGISTER PATIENT ----------------

@app.route('/register/patient', methods=['GET', 'POST'])
def register_patient():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        username = request.form['uname']
        password = generate_password_hash(request.form['psw'])

        try:
            db = get_db_connection()
            db.execute("""
                INSERT INTO users (fullname, email, username, password, role)
                VALUES (?, ?, ?, ?, ?)
            """, (fullname, email, username, password, 'patient'))
            db.commit()
            db.close()

            flash("Patient registered successfully. Please login.", "success")
            return redirect(url_for('login'))

        except sqlite3.IntegrityError:
            flash("Username or Email already exists", "danger")

    return render_template("register_patient.html")


# ---------------- REGISTER DOCTOR ----------------

@app.route('/register/doctor', methods=['GET', 'POST'])
def register_doctor():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        username = request.form['uname']
        password = generate_password_hash(request.form['psw'])
        specialization = request.form['specialization']
        license_id = request.form['license_id']

        try:
            db = get_db_connection()
            db.execute("""
                INSERT INTO users (fullname, email, username, password, role, specialization, license_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (fullname, email, username, password, 'doctor', specialization, license_id))
            db.commit()
            db.close()

            flash("Doctor registered successfully. Please login.", "success")
            return redirect(url_for('login'))

        except sqlite3.IntegrityError:
            flash("Username or Email already exists", "danger")

    return render_template("register_doctor.html")


# ---------------- DOCTOR DASHBOARD ----------------

@app.route('/doctor_dashboard')
@login_required('doctor')
def doctor_dashboard():

    doctor = session['username']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM appointments 
        WHERE doctor_username=? AND status='Pending'
    """, (doctor,))
    pending = cursor.fetchall()

    cursor.execute("""
        SELECT * FROM appointments 
        WHERE doctor_username=? AND status='Approved'
    """, (doctor,))
    approved = cursor.fetchall()

    conn.close()

    return render_template(
        "doctor_dashboard.html",
        pending=pending,
        approved=approved
    )


# ---------------- PATIENT DASHBOARD ----------------

@app.route('/patient/dashboard')
@login_required('patient')
def patient_dashboard():

    username = session['username']

    conn = get_db_connection()
    cursor = conn.cursor()

    # profile
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    profile = cursor.fetchone()

    # appointments
    cursor.execute("""
        SELECT * FROM appointments 
        WHERE patient_username=?
    """, (username,))
    appointments = cursor.fetchall()

    conn.close()

    return render_template(
        "patient_dashboard.html",
        profile=profile,
        appointments=appointments
    )


# ---------------- BOOKING PAGE ----------------

@app.route('/booking', methods=['GET', 'POST'])
@login_required('patient')
def booking():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT specialization FROM users WHERE role='doctor'")
    specializations = [row[0] for row in cursor.fetchall()]

    doctors = []
    specialization = None

    if request.method == 'POST':
        specialization = request.form['specialization']

        cursor.execute("""
            SELECT username, fullname, specialization 
            FROM users 
            WHERE role='doctor' AND specialization=?
        """, (specialization,))
        doctors = cursor.fetchall()

    conn.close()

    return render_template(
        "booking.html",
        specializations=specializations,
        doctors=doctors,
        specialization=specialization
    )


# ---------------- FINALIZE APPOINTMENT ----------------

@app.route('/finalize/<doctor_username>/<specialization>', methods=['GET', 'POST'])
@login_required('patient')
def finalize(doctor_username, specialization):

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get doctor details
    cursor.execute("SELECT fullname FROM users WHERE username=?", (doctor_username,))
    doctor = cursor.fetchone()

    # Get doctor's fee and UPI if set
    cursor.execute("SELECT fee_amount, upi_id FROM doctor_fees WHERE doctor_username=?", (doctor_username,))
    fee_data = cursor.fetchone()

    fee_amount = fee_data[0] if fee_data else "Not set"
    upi_id = fee_data[1] if fee_data else "Not set"

    if request.method == 'POST':
        medical_info = request.form['medical_info']
        appointment_time = request.form['appointment_time']
        patient_username = session['username']

        cursor.execute("""
            INSERT INTO appointments 
            (patient_username, doctor_username, specialization, medical_info, appointment_date, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
        """, (patient_username, doctor_username, specialization, medical_info, appointment_time))

        conn.commit()
        conn.close()

        flash("Appointment booked successfully!", "success")
        return redirect(url_for('patient_dashboard'))

    conn.close()

    return render_template(
        "finalize.html",
        doctor=doctor,
        specialization=specialization,
        fee_amount=fee_amount,
        upi_id=upi_id
    )

# ---------------- UPDATE APPOINTMENT STATUS (DOCTOR) ----------------

@app.route('/appointment_status/<int:id>/<status>')
@login_required('doctor')
def appointment_status(id, status):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE appointments SET status=? WHERE id=?", (status, id))

    conn.commit()
    conn.close()

    return redirect(url_for('doctor_dashboard'))


# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))

@app.route("/book_appointment")
@login_required('patient')
def book_appointment():
    patient = session["username"]  # correct key

    conn = get_db_connection()
    cursor = conn.cursor()

    # 🔹 Get all available specializations
    cursor.execute("""
        SELECT DISTINCT specialization 
        FROM users 
        WHERE role='doctor' AND specialization IS NOT NULL
    """)
    specializations = [row["specialization"] for row in cursor.fetchall()]

    # 🔹 Get patient's current appointments with status
    cursor.execute("""
        SELECT a.specialization, a.status, u.fullname AS doctor_name
        FROM appointments a
        JOIN users u ON a.doctor_username = u.username
        WHERE a.patient_username = ?
        ORDER BY a.appointment_date DESC
    """, (patient,))

    bookings = cursor.fetchall()
    conn.close()

    return render_template(
        "patient_booking.html",
        specializations=specializations,
        bookings=bookings
    )

@app.route("/confirm", methods=["GET", "POST"])
def confirm():
    chat_state = session.get("chat_state", {})
    if chat_state.get("stage") != "done":
        return redirect("/chatbot")  # chatbot incomplete

    symptoms = (
        f"Symptom: {chat_state.get('symptom','')}\n"
        f"Location: {chat_state.get('location','')}\n"
        f"Severity: {chat_state.get('severity','')}/10\n"
        f"Duration: {chat_state.get('duration','')}\n"
        f"Additional info: {chat_state.get('additional','')}"
    )
    session["symptoms"] = symptoms

    if request.method == "POST":
        choice = request.form["choice"]
        if choice == "enough":
            return redirect("/chatbotsummary")
        else:
            return redirect("/consult_manual")

    return render_template("confirm.html", symptoms=symptoms)

@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    # Initialize session if missing
    if "chat_state" not in session:
        session["chat_state"] = {}
    if "chat_log" not in session:
        session["chat_log"] = []

    chat_state = session["chat_state"]
    chat_log = session["chat_log"]

    # --- Handle Clear Chat button ---
    if request.method == "POST" and "clear_chat" in request.form:
        # Reset session
        session["chat_state"] = {}
        session["chat_log"] = []

        chat_state = session["chat_state"]
        chat_log = session["chat_log"]

        # Start fresh conversation
        chat_state["stage"] = "start"
        initial_msg = chatbot_reply("", chat_state)
        chat_log.append(("AI", initial_msg))

        session["chat_state"] = chat_state
        session["chat_log"] = chat_log

        return render_template("chatbot.html", chat=chat_log, state=chat_state)

    # --- Handle user message ---
    if request.method == "POST" and "message" in request.form:
        user_msg = request.form["message"]
        if user_msg.strip():  # only add if not empty
            chat_log.append(("Patient", user_msg))
            reply = chatbot_reply(user_msg, chat_state)
            chat_log.append(("AI", reply))

            session["chat_state"] = chat_state
            session["chat_log"] = chat_log

    # --- GET request or first load ---
    if request.method == "GET" and not chat_log:
        chat_state["stage"] = "start"
        initial_msg = chatbot_reply("", chat_state)
        chat_log.append(("AI", initial_msg))
        session["chat_state"] = chat_state
        session["chat_log"] = chat_log

    return render_template("chatbot.html", chat=chat_log, state=chat_state)

@app.route("/consult_manual", methods=["GET", "POST"])
def consult_manual():
    chatbot_symptoms = session.get("symptoms", "")

    if request.method == "POST":
        manual_input = request.form.get("symptoms", "")
        # Combine chatbot + manual input
        if manual_input.strip():
            combined = f"{chatbot_symptoms}\nAdditional info: {manual_input}"
        else:
            combined = chatbot_symptoms

        session["symptoms"] = combined

        # Generate AI summary (or call analyze_symptoms)
        if "ai_consent" in request.form:
            session["ai"] = analyze_symptoms(combined)
        else:
            session["ai"] = {
                "risk": "N/A",
                "recommendation": "AI analysis disabled by patient",
                "explanation": "Patient did not provide consent"
            }

        return redirect("/chatbotsummary")

    return render_template("consult_manual.html")

@app.route("/chatbotsummary")
@login_required('patient')
def chatbotsummary():
    symptoms = session.get("symptoms", "")

    if "ai" not in session:
        session["ai"] = analyze_symptoms(symptoms)

    ai_summary = session["ai"]

    # Generate readable summary
    summary_text = summarize_consultation(symptoms)

    return render_template(
        "chatbot_summary.html",
        ai=ai_summary,
        summary=summary_text
    )

@app.route("/doctor/set_fee", methods=["GET", "POST"])
@login_required('doctor')
def set_fee():
    doctor_username = session["username"]  # use username as key

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        fee_amount = request.form["fee_amount"]
        upi_id = request.form.get("upi_id", "")  # optional

        # Check if fee already exists
        cursor.execute("SELECT * FROM doctor_fees WHERE doctor_username=?", (doctor_username,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE doctor_fees
                SET fee_amount = ?, upi_id = ?, last_updated = CURRENT_TIMESTAMP
                WHERE doctor_username = ?
            """, (fee_amount, upi_id, doctor_username))
        else:
            cursor.execute("""
                INSERT INTO doctor_fees (doctor_username, fee_amount, upi_id)
                VALUES (?, ?, ?)
            """, (doctor_username, fee_amount, upi_id))

        conn.commit()
        conn.close()

        flash("Consultation fee updated successfully!", "success")
        return redirect("/doctor_dashboard")

    # GET request — fetch current fee to pre-fill form
    cursor.execute("SELECT fee_amount, upi_id FROM doctor_fees WHERE doctor_username=?", (doctor_username,))
    fee_data = cursor.fetchone()
    conn.close()

    fee_amount = fee_data[0] if fee_data else ""
    upi_id = fee_data[1] if fee_data else ""

    return render_template("doc_pay.html", fee_amount=fee_amount, upi_id=upi_id)



# ---------------- RUN ----------------

if __name__ == '__main__':
    app.run(debug=True)

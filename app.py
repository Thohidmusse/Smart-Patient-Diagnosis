from flask import Flask, render_template, request, redirect, send_from_directory, url_for, flash, session
import joblib
import pyodbc
import pickle
from fpdf import FPDF
import bcrypt
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Use a strong secret key

# Database Configuration
server = '88.222.244.120'
database = 'newHosp'
username = 'ams'
password = 'pC6p[Pb84et0'
conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"

# Load trained ML model and vectorizer
model = joblib.load('models/ai_model.pkl')
vectorizer = joblib.load('models/vectorizer.pkl')

# Function to establish database connection
def get_db_connection():
    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        return conn
    except pyodbc.Error as e:
        print("❌ Database Connection Error:", e)
        return None


# Function to establish database connection
def get_db_connection():
    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        return conn
    except pyodbc.Error as e:
        print("❌ Database Connection Error:", e)
        return None

# Home Page
@app.route('/')
def index():
    return render_template('index.html')

# Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        contact = request.form.get('contact')
        email = request.form.get('email')
        password = request.form.get('password')

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = get_db_connection()
        if not conn:
            flash("Database connection failed!", "error")
            return render_template('register.html')

        cursor = conn.cursor()
        try:
            # Check if email exists
            cursor.execute("SELECT COUNT(*) FROM Users WHERE Email=?", (email,))
            if cursor.fetchone()[0] > 0:
                flash("Email already exists. Use a different email.", "error")
                return render_template('register.html')

            # Insert data
            cursor.execute("INSERT INTO Users (Name, Phone, Email, Password) VALUES (?, ?, ?, ?)", 
                           (name, contact, email, hashed_password))
            conn.commit()
            flash("Registration Successful! Please log in.", "success")
            return redirect(url_for('login'))
        except pyodbc.Error as e:
            flash(f"Database error: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        if not conn:
            flash("Database connection failed!", "error")
            return render_template('login.html')

        cursor = conn.cursor()
        try:
            # ✅ Fetch UserID, Name, and Password
            cursor.execute("SELECT UserID, Name, Password FROM Users WHERE Email=?", (email,))
            user = cursor.fetchone()

            if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):  
                session['user_id'] = user[0]      # ✅ Store UserID
                session['user_name'] = user[1]    # ✅ Store actual Name
                flash("Login Successful!", "success")
                return redirect(url_for('symptoms_form'))
            else:
                flash("Invalid email or password!", "error")
        except pyodbc.Error as e:
            flash(f"Database error: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template('login.html')

# Symptoms Form
# Load model & vectorizer at the start
model = joblib.load('models/ai_model.pkl')
vectorizer = joblib.load('models/vectorizer.pkl')

@app.route('/symptoms_form', methods=['GET', 'POST'])
def symptoms_form():
    if request.method == 'POST':
        conn = get_db_connection()
        if not conn:
            flash("Database connection failed!", "error")
            return render_template('symptoms_form.html')

        cursor = conn.cursor()
        try:
            # Convert checkboxes to 1/0
            consent_for_treatment = 1 if request.form.get("ConsentForTreatment") == "on" else 0
            privacy_agreement = 1 if request.form.get("PrivacyAgreement") == "on" else 0

            # Collect user input
            user_id = session.get("user_id")
            user_name = session.get("user_name")
            age = request.form["age"]
            gender = request.form["Gender"]
            pre_existing_conditions = request.form["PreExistingConditions"]
            allergies = request.form["Allergies"]
            medications = request.form["CurrentMedications"]
            surgeries = request.form["RecentSurgeries"]
            severity = request.form["SeverityOfSymptoms"]
            pain_level = request.form["PainLevel"]
            other_symptoms = request.form["OtherSymptoms"]
            diet = request.form["Diet"]
            exercise = request.form["Exercise"]
            smoking_alcohol = request.form["SmokingAlcohol"]
            emergency_contact = request.form["EmergencyContact"]
            travel_history = request.form["TravelHistory"]

            # Insert into DB
            query = """INSERT INTO SymptomsDetails 
                        (UserId, age, Gender, PreExistingConditions, Allergies, CurrentMedications, RecentSurgeries,     
                         SeverityOfSymptoms, PainLevel, OtherSymptoms, Diet, Exercise, SmokingAlcohol,
                         EmergencyContact, TravelHistory, ConsentForTreatment, PrivacyAgreement)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

            values = (user_id, age, gender, pre_existing_conditions, allergies, medications, surgeries, 
                      severity, pain_level, other_symptoms, diet, exercise, smoking_alcohol, 
                      emergency_contact, travel_history, consent_for_treatment, privacy_agreement)

            cursor.execute(query, values)
            conn.commit()
            flash("Data inserted successfully!", "success")

            # **🔹 AI/ML Disease Prediction**
            symptoms_text = " ".join(filter(None, [pre_existing_conditions, allergies, other_symptoms, medications]))
            symptoms_vectorized = vectorizer.transform([symptoms_text])
            predicted_disease = model.predict(symptoms_vectorized)[0] if symptoms_vectorized.nnz else "Unknown"

            # **🔹 Assign the Correct Doctor**
            assigned_doctor = assign_doctor(predicted_disease)

            # **🔹 Generate PDF Report**
            pdf_path = generate_pdf(user_name, age, predicted_disease, assigned_doctor)

            return render_template('result.html', name=user_name, age=age, disease=predicted_disease, doctor=assigned_doctor, pdf_path=pdf_path)

        except Exception as e:
            flash("❌ Error: " + str(e), "error")
        finally:
            cursor.close()
            conn.close()

    return render_template('symptoms_form.html')

# **🔹 Assign the Correct Doctor**
def assign_doctor(disease):
    conn = get_db_connection()
    if not conn:
        print("⚠️ Database Connection Failed! Assigning General Practitioner")
        return "General Practitioner"

    cursor = conn.cursor()
    try:
        print(f"🔍 Searching for a doctor for disease: {disease}")

        # Ensure disease name is lowercased before comparison
        cursor.execute("SELECT Specialty FROM DiseaseMapping WHERE LOWER(Disease) = LOWER(?)", (disease,))
        specialty = cursor.fetchone()

        if not specialty:
            print(f"⚠️ No specialty found for '{disease}'. Assigning General Practitioner.")
            return "General Practitioner"

        specialty = specialty[0]

        cursor.execute("SELECT Name FROM Doctors WHERE LOWER(Specialty) = LOWER(?)", (specialty,))
        doctors = cursor.fetchall()

        if not doctors:
            print(f"⚠️ No doctors found for '{specialty}'. Assigning General Practitioner.")
            return "General Practitioner"

        assigned_doctors = ", ".join([doc[0] for doc in doctors])
        print(f"✅ Assigned Doctor(s): {assigned_doctors}")
        return assigned_doctors

    except Exception as e:
        print("❌ Database Error:", e)
        return "General Practitioner"

    finally:
        cursor.close()
        conn.close()   
             
# Function to generate PDF
class PDF(FPDF):
    def header(self):
        """Add a header with a hospital logo and title."""
        logo_path = "static/images/hospital_logo.png"  # Ensure logo exists
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 25)  # (x, y, width)
        self.set_font("Arial", "B", 16)
        self.cell(200, 10, "Diagnosis Report", ln=True, align="C")
        self.ln(10)  # Add spacing

    def footer(self):
        """Add a footer with date and signature line."""
        self.set_y(-30)  # Position from bottom
        self.set_font("Arial", "I", 10)
        self.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align="L")
        self.cell(0, 10, "Doctor's Signature: ______________", ln=True, align="R")

def generate_pdf(name, age, disease, doctor):
    pdf_dir = "static/reports"
    os.makedirs(pdf_dir, exist_ok=True)  # Ensure directory exists

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Patient Details - Styled Table
    pdf.set_fill_color(200, 220, 255)  # Light blue background
    pdf.set_text_color(0, 0, 0)  # Black text
    pdf.set_font("Arial", "B", 12)

    pdf.cell(50, 10, "Patient Name:", border=1, fill=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(140, 10, name, border=1, ln=True)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(50, 10, "Patient Age:", border=1, fill=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(140, 10, str(age), border=1, ln=True)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(50, 10, "Disease:", border=1, fill=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(140, 10, disease, border=1, ln=True)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(50, 10, "Assigned Doctor:", border=1, fill=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(140, 10, doctor, border=1, ln=True)

    # Save the PDF
    pdf_filename = f"consultation_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf_path = os.path.join(pdf_dir, pdf_filename)
    pdf.output(pdf_path)

    return pdf_filename  # ✅ Return only filename

# Route to download PDF
@app.route("/download_pdf/<filename>")
def download_pdf(filename):
    pdf_dir = os.path.join(os.getcwd(), "static", "reports")  # Ensure correct path
    return send_from_directory(directory=pdf_dir, path=filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)




    
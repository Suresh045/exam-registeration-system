from flask import Flask, render_template, request, redirect, session, flash, send_file
import sqlite3
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib import colors
import random

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database and tables
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Create users table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY,
              username TEXT,
              password TEXT,
              name TEXT,
              dob DATE,
              phone TEXT,
              email TEXT,
              year INTEGER,
              semester INTEGER,
              is_admin BOOLEAN DEFAULT 0)''')

# Create subjects table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS subjects
             (id INTEGER PRIMARY KEY,
              name TEXT,
              credits INTEGER,
              code TEXT)''')

# Update database schema to include exam registrations
c.execute('''CREATE TABLE IF NOT EXISTS exam_registrations
             (id INTEGER PRIMARY KEY,
              user_id INTEGER,
              subject_id INTEGER,
              registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              status TEXT DEFAULT 'Pending',
              FOREIGN KEY(user_id) REFERENCES users(id),
              FOREIGN KEY(subject_id) REFERENCES subjects(id))''')

conn.commit()
conn.close()


# Function to generate hall ticket
def generate_hall_ticket(student_info, exam_info, university_name, exam_rules, student_image_path, logo_path="", verification_status=False):
    # Generate a random hall ticket number
    hall_ticket_number = random.randint(100000, 999999)

    # Create a PDF canvas
    c = canvas.Canvas("hall_ticket.pdf", pagesize=letter)

    # Add University Name
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(300, 750, university_name)

    # Add Logo if provided
    if logo_path:
        c.drawImage(logo_path, 50, 730, width=50, height=50)

    # Set font for content
    c.setFont("Helvetica", 12)

    # Write Hall Ticket Number
    c.drawString(50, 710, "Hall Ticket Number: {}".format(hall_ticket_number))

    # Write Student Information
    y_offset = 680
    for key, value in student_info.items():
        c.drawString(50, y_offset, "{}: {}".format(key, value))
        y_offset -= 20

    # Write Exam Information
    y_offset -= 20
    for key, value in exam_info.items():
        c.drawString(50, y_offset, "{}: {}".format(key, value))
        y_offset -= 20

    # Write Registered Exam Name
    y_offset -= 20
    c.drawString(50, y_offset, "Registered Exam: {}".format(exam_info["Exam Name"]))
    
    # Write Exam Rules
    y_offset -= 30
    c.drawString(50, y_offset, "Exam Rules:")
    for i, section in enumerate(exam_rules, start=1):
        y_offset -= 20
        c.drawString(70, y_offset, "Section {}:".format(i))
        for j, rule in enumerate(section, start=1):
            y_offset -= 20
            c.drawString(90, y_offset, "{}. {}".format(j, rule))
    
    # Add Student Image
    c.drawImage(student_image_path, 350, 620, width=120, height=120)
    
    if verification_status:
        # Generate barcode
        barcode_value = str(hall_ticket_number)
        barcode128 = code128.Code128(barcode_value, barHeight=20, barWidth=0.5)
        barcode_width, barcode_height = barcode128.width, barcode128.height
        barcode_x = 350  # Same x-coordinate as the student image
        barcode_y = 450  # Below the student image
        barcode128.drawOn(c, barcode_x, barcode_y)

    # Write congratulatory message
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.red)
    c.drawCentredString(300, 300, "Congratulations on your exam!")

    # Save the PDF
    c.save()



@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        dob = request.form['dob']
        phone = request.form['phone']
        email = request.form['email']
        year = request.form['year']
        semester = request.form['semester']

        # Insert user into database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, name, dob, phone, email, year, semester) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (username, password, name, dob, phone, email, year, semester))
        conn.commit()
        conn.close()

        return redirect('/')
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # Check if user exists in the database
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()

    if user and user[2] == password:
        session['username'] = username
        if user[3]:
            #session['is_admin'] = True
            #return redirect('/admin_dashboard')
        #else:
            return redirect('/student_dashboard')
    else:
        return "Invalid username or password"


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('is_admin', None)
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'], is_admin=session.get('is_admin', False))
    else:
        return redirect('/')

@app.route('/update_profile', methods=['POST'])
def update_profile():
    # Update profile logic here
    return redirect('/dashboard')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the provided credentials match the fixed admin credentials
        if username == "admin" and password == "a":
            session['username'] = username
            session['is_admin'] = True
            return redirect('/admin_dashboard')
        else:
            return "Invalid admin credentials"

    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'username' in session and session.get('is_admin', False):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Fetch subjects
        c.execute("SELECT * FROM subjects")
        subjects = c.fetchall()
        
        # Fetch registered students' data
        c.execute('''SELECT  users.username, users.name, users.email, users.year, subjects.name, exam_registrations.id, exam_registrations.status
                     FROM users 
                     JOIN exam_registrations ON users.id = exam_registrations.user_id 
                     JOIN subjects ON exam_registrations.subject_id = subjects.id''')
        registered_students = c.fetchall()

        conn.close()

        return render_template('admin_dashboard.html', username=session['username'], subjects=subjects, registered_students=registered_students)
    else:
        return redirect('/admin_login')

@app.route('/verify_registration/<int:registration_id>', methods=['POST'])
def verify_registration(registration_id):
    if 'username' in session and session.get('is_admin', False):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Update the status of the registration to "Verified"
        c.execute("UPDATE exam_registrations SET status='Verified' WHERE id=?", (registration_id,))
        conn.commit()
        conn.close()
        flash('Registration verified successfully!', 'success')
    return redirect('/admin_dashboard')

@app.route('/add_subject', methods=['POST'])
def add_subject():
    if 'username' in session and session.get('is_admin', False):
        name = request.form['name']
        credits = request.form['credits']
        code = request.form['code']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO subjects (name, credits, code) VALUES (?, ?, ?)", (name, credits, code))
        conn.commit()
        conn.close()

        flash('Subject successfully added!', 'success')

        return redirect('/admin_dashboard')
    else:
        return redirect('/admin_login')


@app.route('/student_dashboard')
def student_dashboard():
    if 'username' in session:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Fetch available subjects
        c.execute("SELECT * FROM subjects")
        subjects = c.fetchall()
        
        # Fetch registered subjects for the logged-in user
        c.execute('''SELECT subjects.id, subjects.name, subjects.credits, subjects.code, exam_registrations.status
                     FROM exam_registrations 
                     JOIN subjects ON exam_registrations.subject_id = subjects.id
                     JOIN users ON exam_registrations.user_id = users.id
                     WHERE users.username = ?''', (session['username'],))
        registered_subjects = c.fetchall()
        
        conn.close()

        # Check if any registration is verified
        verification_status = any(reg[4] == 'Verified' for reg in registered_subjects)

        return render_template('student_dashboard.html', username=session['username'], subjects=subjects, registered_subjects=registered_subjects, verification_status=verification_status)
    else:
        return redirect('/')




@app.route('/register_exam', methods=['POST'])
def register_exam():
    if 'username' in session:
        # Retrieve user ID from the session
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username=?", (session['username'],))
        user = c.fetchone()
        conn.close()

        if user is None:
            flash('User not found.', 'error')
            return redirect('/student_dashboard')

        user_id = user[0]
        subject_id = request.form.get('subject_id')

        if subject_id is None:
            flash('Please select a subject to register for the exam.', 'error')
            return redirect('/student_dashboard')

        # Insert registration into the database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO exam_registrations (user_id, subject_id) VALUES (?, ?)", (user_id, subject_id))
        conn.commit()
        conn.close()

        flash('Successfully registered for the exam!', 'success')
        return redirect('/student_dashboard')
    else:
        return redirect('/')



@app.route('/download_hall_ticket')
def download_hall_ticket():
    if 'username' in session:
        # Check if the user's exam registration is verified
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''SELECT exam_registrations.status, users.name, users.id, subjects.name
                     FROM exam_registrations 
                     JOIN users ON exam_registrations.user_id = users.id
                     JOIN subjects ON exam_registrations.subject_id = subjects.id
                     WHERE users.username = ? AND exam_registrations.status = 'Verified' ''', (session['username'],))
        registration_info = c.fetchone()
        conn.close()

        if registration_info:
            registration_status, student_name, student_id, exam_name = registration_info
            # Define student_info based on the fetched data
            student_info = {
                'Name': student_name,
                'ID': student_id
                # Add more fields as needed
            }
            # Define other necessary information for the hall ticket
            exam_info = {
               'Exam Name': exam_name,
               'Exam Date': 'May 10, 2024',
               'Exam Time': '10:00 AM to 1:00 PM',
               'Exam Location': 'JACSICE,TUTICORIN',
    # Add more exam information as needed
}

            university_name = "Akka University"
            exam_rules = [
    [
        "No student will be allowed to bring his/her mobile phones to the examination hall.",
        "All students must carry with them their Identity Card during the examinations and produce the same for verification, if required.",
        "The students should ensure that they bring with them all the concerned material that is allowed by the concerned course instructor, which would be needed to take the examination.",
        "The students are expected to take their respective seats 5 minutes prior to the scheduled commencement of the examination.",
        "Students should ensure that they are not carrying on their person any material, other than that allowed by the course instructor for the particular examination, before they take their seats in the exam hall. Any such material found on their person during the examination would be construed as a deliberate attempt to use unfair means and would be dealt with accordingly."
    ],
    [
        "The doors of the examination hall would be closed 5 minutes before the commencement of the examination, for the distribution of the exam material to the students already seated in the room. The door will be opened, to allow latecomers, after the last student already seated in the room in time has received his/her exam material.",
        "The latecomers should proceed take their seats and wait for the exam material to be given to them.",
        "No student will be allowed to enter the examination hall 15 minutes after the commencement of the examination for in-semester examinations and 30 minutes after the commencement of the examination for end-semester examinations."
    ],
    [
        "Exchange (borrowing or lending) of any material during the examination is not allowed.",
        "No student will resort to any unfair means of any nature while taking their examinations. If any student were found to be involved in using unfair means during an examination, the said student would be immediately expelled from the exam hall for that examination and the matter would be reported to the respective course instructor and the Dean (AP) for further action.",
        "In case a student is found to be copying from his/her fellow student, then both the parties, the one providing the assistance and the one seeking the same, would be punished for the same.",
        "In case a student has to leave his/her seat for whatever reason, he/she has to seek the permission of the concerned invigilator(s) of that exam hall before doing so. For visiting the rest room, he/she has to seek the permission of the concerned faculty invigilator of that examination hall before doing so.",
        "No supplement(s) would be given to the students in the last 5 minutes of the examination."
    ],
    [
        "No student will be allowed to leave the room in the first 15 minutes of the in semester examination (typical duration 1 hour) or first 30 minutes of the end-semester examination (typical duration of 3 hours) and in the last 5 minutes of the examination.",
        "Students who are present in the last 5 minutes of the examination will have to wait till the exam material is collected from all the students by the invigilators and they are permitted to leave by the faculty invigilator of that exam hall.",
        "While leaving the examination hall the students should not hang around to discuss the paper. As there may be other examinations still in progress, quietly leave the building to ensure that you do not disturb them."
    ]
]


            student_image_path = 'static/images/student_image.jpg'
            logo_path = 'static/images/logo.png'
            
            # Generate the hall ticket PDF
            generate_hall_ticket(student_info, exam_info, university_name, exam_rules, student_image_path, logo_path, verification_status=True)
            # Send the hall ticket PDF as a file download
            return send_file("hall_ticket.pdf", as_attachment=True)
        else:
            flash('Your exam registration is not verified yet.', 'error')
            return redirect('/student_dashboard')
    else:
        return redirect('/')



@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    if 'username' in session and session.get('is_admin', False):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
        conn.commit()
        conn.close()
        flash('Subject successfully deleted!', 'success')
    return redirect('/admin_dashboard')


if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from functools import wraps
import random
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:omega@localhost:5432/flask_database'
db = SQLAlchemy(app)
app.secret_key = 'secret_key'

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'johnDoe18262117@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'avsj hgzp mxfc yxxz'  # Replace with your app password
mail = Mail(app)

class Student(db.Model):
    __tablename__ = 'student'

    name = db.Column(db.String(100), nullable=False)  # Full name of the student
    email = db.Column(db.String(100), primary_key=True, unique=True, nullable=False)  # Email (primary key)
    password = db.Column(db.String(255), nullable=False)  # Password
    verified = db.Column(db.Boolean, default=False, nullable=False)  # Verification status

    def __repr__(self):
        return f"<Student {self.email}>"

class Instructor(db.Model):
    __tablename__ = 'instructor'

    name = db.Column(db.String(100), nullable=False)  # Full name of the instructor
    email = db.Column(db.String(100), primary_key=True, unique=True, nullable=False)  # Email (primary key)
    department = db.Column(db.String(100), nullable=False)  # Department
    designation = db.Column(db.String(100), nullable=False)  # Designation
    password = db.Column(db.String(255), nullable=False)  # Password
    verified = db.Column(db.Boolean, default=False, nullable=False)  # Verification status

    def __repr__(self):
        return f"<Instructor {self.email}>"

class Admin(db.Model):
    __tablename__ = 'admin'

    name = db.Column(db.String(100), nullable=False)  # Full name of the admin
    email = db.Column(db.String(100), primary_key=True, unique=True, nullable=False)  # Email (primary key)
    password = db.Column(db.String(255), nullable=False)  # Password

    def __repr__(self):
        return f"<Admin {self.email}>"
    
class Course(db.Model):
    __tablename__ = 'course'

    course_id = db.Column(db.String(10), primary_key=True)   # Alphanumeric course ID (e.g., MA101, CS533)
    course_name = db.Column(db.String(255), nullable=False)  # Course name
    course_description = db.Column(db.Text, nullable=False)  # Course description
    instructor_email = db.Column(db.String(100), db.ForeignKey('instructor.email'), nullable=False)  # FK to Instructor table
    current_enrollments = db.Column(db.Integer, default=0, nullable=False)  # Current enrollments (starts at 0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # Timestamp when the course was created

    instructor = db.relationship('Instructor', backref=db.backref('courses', lazy=True))

    def __repr__(self):
        return f"<Course {self.course_id} - {self.course_name}>"

class Enrollment(db.Model):
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Unique enrollment ID
    course_id = db.Column(db.String(10), db.ForeignKey('course.course_id'), nullable=False)  # FK to Course table
    student_email = db.Column(db.String(100), db.ForeignKey('student.email'), nullable=False)  # FK to Student table
    status = db.Column(db.Boolean, default=False, nullable=False)  # Enrollment status (True = enrolled, False = not enrolled)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # Timestamp when enrollment was created

    course = db.relationship('Course', backref=db.backref('enrollments', lazy=True))
    student = db.relationship('Student', backref=db.backref('enrollments', lazy=True))

    def __repr__(self):
        return f"<Enrollment {self.id} - Course: {self.course_id}, Student: {self.student_email}>"

with app.app_context():
    db.create_all()

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if role == "admin" and "admin_email" not in session:
                flash("You need to log in as an admin to access this page.", "warning")
                return redirect("/admin_login")
            elif role == "instructor" and "instructor_email" not in session:
                flash("You need to log in as an instructor to access this page.", "warning")
                return redirect("/instructor_login")
            elif role == "student" and "student_email" not in session:
                flash("You need to log in as a student to access this page.", "warning")
                return redirect("/student_login")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/student_register", methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        # Check if OTP verification step
        if 'student_registration_otp_sent' in session:
            entered_otp = request.form['otp']
            if entered_otp == session.get('student_registration_otp'):
                # OTP matched
                new_user = Student(
                    name=session['student_registration_data']['name'],
                    email=session['student_registration_data']['email'],
                    password=session['student_registration_data']['password'],
                    verified=False
                )
                db.session.add(new_user)
                db.session.commit()

                # Notify user about verification requirement
                msg = Message(
                    'Registration Successful - Verification Pending',
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[session['student_registration_data']['email']]
                )
                msg.body = (
                    f"Hello {session['student_registration_data']['name']},\n\n"
                    "Your registration is successful. Your profile will be reviewed by the admin. "
                    "You will receive an email notification once your profile is verified."
                )
                mail.send(msg)

                # Clear session and redirect to home
                session.pop('student_registration_otp', None)
                session.pop('student_registration_otp_sent', None)
                session.pop('student_registration_data', None)
                flash('Registration complete! You will be notified once verified.', 'success')
                return redirect('/')

            else:
                flash('Invalid OTP. Please try again.', 'danger')
        else:
            # First step: Collect form data and send OTP
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            # Validate that passwords match
            if password != confirm_password:
                flash('Password and Confirm Password do not match.', 'danger')
                return redirect('/student_register')

            # Check if email already exists
            if Student.query.filter_by(email=email).first():
                flash('Email already registered.', 'danger')
                return redirect('/student_register')

            otp = str(random.randint(100000, 999999))
            session['student_registration_otp'] = otp
            session['student_registration_otp_sent'] = True
            session['student_registration_data'] = {
                'name': name,
                'email': email,
                'password': password
            }

            # Send OTP via email
            msg = Message('Your Registration OTP', sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"Your OTP for registration is {otp}. It is valid for 5 minutes."
            mail.send(msg)

            flash('OTP sent to your email. Please check your inbox.', 'info')
    return render_template('student_register.html', student_registration_otp_sent=session.get('student_registration_otp_sent'))


@app.route("/student_register_cancel", methods=["GET"])
def student_register_cancel():
    # Clear any session variables related to the registration process
    session.pop("student_registration_otp", None)
    session.pop("student_registration_otp_sent", None)
    session.pop("student_registration_data", None)
    flash("Registration process has been canceled.", "info")
    return redirect("/student_register")


@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Validate email and password
        user = Student.query.filter_by(email=email).first()
        if user and user.password == password:
            if not user.verified:
                flash('Your account is not yet verified. Please contact the admin.', 'warning')
                return redirect('/student_login')

            session['student_email'] = email
            flash('Login successful!', 'success')
            return redirect('/student_home')
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('student_login.html')


@app.route('/student_home')
@login_required(role="student")
def student_home():
    return render_template('student_home.html', email=session['student_email'])

@app.route('/student_course', methods=['GET', 'POST'])
@login_required(role="student")
def student_course():
    if request.method == 'POST':
        # Student applies for a course
        course_id = request.form['course_id']
        student_email = session.get('student_email')  # Ensure student is logged in

        # Check if the student is already enrolled or has a pending application
        existing_enrollment = Enrollment.query.filter_by(course_id=course_id, student_email=student_email).first()
        if existing_enrollment:
            flash("You have already applied for or are enrolled in this course.", "info")
            return redirect('/student_course')

        # Create a new enrollment record
        new_enrollment = Enrollment(
            course_id=course_id,
            student_email=student_email,
            status=False  # Pending approval
        )
        db.session.add(new_enrollment)
        db.session.commit()

        flash("Enrollment request submitted successfully!", "success")
        return redirect('/student_course')

    # GET request: Fetch all courses (optional search filter)
    search_query = request.args.get('search', '').strip()
    if search_query:
        courses = Course.query.filter(Course.course_id.ilike(f"%{search_query}%")).all()
    else:
        courses = Course.query.all()

    return render_template('student_course.html', courses=courses, search_query=search_query)

@app.route('/student_logout')
def student_logout():
    session.pop('student_email', None)
    flash('You have been logged out successfully.', 'info')
    return redirect('/')  

@app.route("/instructor_register", methods=['GET', 'POST'])
def instructor_register():
    if request.method == 'POST':
        # Check if OTP verification step
        if 'instructor_registration_otp_sent' in session:
            entered_otp = request.form['otp']
            if entered_otp == session.get('instructor_registration_otp'):
                # OTP matched
                new_user = Instructor(
                    name=session['instructor_registration_data']['name'],
                    email=session['instructor_registration_data']['email'],
                    department=session['instructor_registration_data']['department'],
                    designation=session['instructor_registration_data']['designation'],
                    password=session['instructor_registration_data']['password'],
                    verified=False  # By default, newly registered instructors are not verified
                )
                db.session.add(new_user)
                db.session.commit()

                # Notify the instructor about verification
                msg = Message(
                    'Registration Successful - Verification Pending',
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[session['instructor_registration_data']['email']]
                )
                msg.body = (
                    f"Hello {session['instructor_registration_data']['name']},\n\n"
                    "Your registration is successful. Your profile will be reviewed by the admin. "
                    "You will receive an email notification once your profile is verified."
                )
                mail.send(msg)

                # Clear session and redirect to home
                session.pop('instructor_registration_otp', None)
                session.pop('instructor_registration_otp_sent', None)
                session.pop('instructor_registration_data', None)
                flash('Registration complete! You will be notified once verified.', 'success')
                return redirect('/')

            else:
                flash('Invalid OTP. Please try again.', 'danger')
        else:
            # First step: Collect form data and send OTP
            name = request.form['full_name']
            email = request.form['email']
            department = request.form['department']
            designation = request.form['designation']
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            # Validate that passwords match
            if password != confirm_password:
                flash('Password and Confirm Password do not match.', 'danger')
                return redirect('/instructor_register')

            # Check if email already exists
            if Instructor.query.filter_by(email=email).first():
                flash('Email already registered.', 'danger')
                return redirect('/instructor_register')

            otp = str(random.randint(100000, 999999))
            session['instructor_registration_otp'] = otp
            session['instructor_registration_otp_sent'] = True
            session['instructor_registration_data'] = {
                'name': name,
                'email': email,
                'department': department,
                'designation': designation,
                'password': password
            }

            # Send OTP via email
            msg = Message('Your Registration OTP', sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"Your OTP for registration is {otp}. It is valid for 5 minutes."
            mail.send(msg)

            flash('OTP sent to your email. Please check your inbox.', 'info')
    return render_template('instructor_register.html', instructor_registration_otp_sent=session.get('instructor_registration_otp_sent'))


@app.route("/instructor_register/cancel", methods=["GET"])
def instructor_register_cancel():
    # Clear any session variables related to the registration process
    session.pop("instructor_registration_otp", None)
    session.pop("instructor_registration_otp_sent", None)
    session.pop("instructor_registration_data", None)
    flash("Registration process has been canceled.", "info")
    return redirect("/instructor_register")


@app.route('/instructor_login', methods=['GET', 'POST'])
def instructor_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Fetch user and validate credentials
        user = Instructor.query.filter_by(email=email).first()
        if user and user.password == password:
            if not user.verified:
                flash('Your account is not yet verified. Please contact the admin.', 'warning')
                return redirect('/instructor_login')

            # Store session and redirect to dashboard
            session['instructor_email'] = email
            flash('Login successful!', 'success')
            return redirect('/instructor_home')
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('instructor_login.html')


@app.route('/instructor_home')
@login_required(role="instructor")
def instructor_home():
    return render_template('instructor_home.html', email=session['instructor_email'])

@app.route('/instructor_float', methods=['GET', 'POST'])
@login_required(role="instructor")
def instructor_float():
    if request.method == 'POST':
        # Get form data
        course_id = request.form['course_id']
        course_name = request.form['course_name']
        course_description = request.form['course_description']
        instructor_email = session.get('instructor_email')  # Ensure the instructor is logged in

        # Check if the course ID is already used
        if Course.query.filter_by(course_id=course_id).first():
            flash("Course ID already exists. Please use a unique ID.", "danger")
            return redirect('/instructor_float')

        # Create a new course
        new_course = Course(
            course_id=course_id,
            course_name=course_name,
            course_description=course_description,
            instructor_email=instructor_email
        )
        db.session.add(new_course)
        db.session.commit()

        flash("Course successfully floated!", "success")
        return redirect('/instructor_float')

    return render_template('instructor_float.html')

from flask_mail import Message

@app.route('/instructor_enroll', methods=['GET', 'POST'])
@login_required(role="instructor")
def instructor_enroll():
    instructor_email = session.get('instructor_email')  # Ensure the instructor is logged in

    if request.method == 'POST':
        # Process approval or rejection
        enrollment_id = request.form['enrollment_id']
        action = request.form['action']  # 'approve' or 'reject'

        # Fetch the enrollment record
        enrollment = Enrollment.query.get(enrollment_id)
        if not enrollment:
            flash("Invalid enrollment ID.", "danger")
            return redirect('/instructor_enroll')

        student_email = enrollment.student_email
        student_name = enrollment.student.name  # Fetch student's name before deleting
        course = enrollment.course

        if action == 'approve':
            enrollment.status = True
            db.session.commit()

            # Send approval email
            msg = Message(
                'Course Enrollment Approved',
                sender=app.config['MAIL_USERNAME'],
                recipients=[student_email]
            )
            msg.body = (
                f"Hello {student_name},\n\n"
                f"Your enrollment for the course '{course.course_name}' (ID: {course.course_id}) has been approved by the instructor.\n\n"
                "You can now access the course through your dashboard.\n\nThank you!"
            )
            mail.send(msg)

            flash(f"Enrollment for '{course.course_name}' approved.", "success")
        elif action == 'reject':
            # Fetch student name and email before deleting the enrollment record
            db.session.delete(enrollment)
            db.session.commit()

            # Send rejection email
            msg = Message(
                'Course Enrollment Rejected',
                sender=app.config['MAIL_USERNAME'],
                recipients=[student_email]
            )
            msg.body = (
                f"Hello {student_name},\n\n"
                f"Your enrollment for the course '{course.course_name}' (ID: {course.course_id}) has been rejected by the instructor.\n\n"
                "Please contact your instructor for further details.\n\nThank you!"
            )
            mail.send(msg)

            flash(f"Enrollment for '{course.course_name}' rejected.", "info")

        return redirect('/instructor_enroll')

    # Fetch pending enrollments for the instructor's courses
    pending_enrollments = Enrollment.query.join(Course).filter(
        Course.instructor_email == instructor_email,
        Enrollment.status == False
    ).all()

    return render_template('instructor_enroll.html', pending_enrollments=pending_enrollments)

@app.route('/instructor_logout')
def instructor_logout():
    session.pop('instructor_email', None)
    flash('You have been logged out successfully.', 'info')
    return redirect('/')  

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        # Check if OTP verification step is ongoing
        if 'admin_login_otp_sent' not in session:
            # Step 1: Validate email and password
            email = request.form['email']
            password = request.form['password']

            # Fetch admin details from the database
            user = Admin.query.filter_by(email=email).first()
            if user and user.password == password:
                # Generate OTP and store it in the session
                otp = str(random.randint(100000, 999999))
                session['admin_login_otp'] = otp
                session['admin_login_otp_sent'] = True
                session['admin_login_email'] = email

                # Send OTP via email
                msg = Message('Your Login OTP', sender=app.config['MAIL_USERNAME'], recipients=[email])
                msg.body = f"Your OTP for login is {otp}. It is valid for 5 minutes."
                mail.send(msg)

                flash('OTP sent to your email. Please check your inbox.', 'info')
            else:
                flash('Invalid email or password.', 'danger')
        else:
            # Step 2: Verify OTP
            entered_otp = request.form['otp']
            if entered_otp == session.get('admin_login_otp'):
                # OTP verified, log the admin in
                session['admin_email'] = session['admin_login_email']
                # Clear OTP-related session variables
                session.pop('admin_login_otp', None)
                session.pop('admin_login_otp_sent', None)
                session.pop('admin_login_email', None)
                flash('Login successful!', 'success')
                return redirect('/admin_home')
            else:
                flash('Invalid OTP. Please try again.', 'danger')

    return render_template('admin_login.html', otp_sent=session.get('admin_login_otp_sent'))


@app.route("/admin_login_cancel", methods=["GET"])
def admin_login_cancel():
    # Clear session variables related to login
    session.pop("admin_login_otp", None)
    session.pop("admin_login_otp_sent", None)
    session.pop("admin_login_email", None)
    flash("Login process has been canceled.", "info")
    return redirect("/admin_login")


@app.route('/admin_home')
@login_required(role="admin")
def admin_home():
    return render_template('admin_home.html', email=session['admin_email'])

@app.route('/admin_verify', methods=['GET', 'POST'])
@login_required(role="admin")
def admin_verify():
    if request.method == 'POST':
        # Extract data from the form submission
        action = request.form.get('action')
        email = request.form.get('email')
        user_type = request.form.get('user_type')

        # Fetch the appropriate user based on user type
        if user_type == 'student':
            user = Student.query.filter_by(email=email).first()
        elif user_type == 'instructor':
            user = Instructor.query.filter_by(email=email).first()
        else:
            flash('Invalid user type.', 'danger')
            return redirect('/admin_verify')

        if not user:
            flash(f'{user_type.capitalize()} not found.', 'danger')
            return redirect('/admin_verify')

        if action == 'approve':
            user.verified = True
            db.session.commit()

            # Send email notification
            msg = Message(
                'Account Verified',
                sender=app.config['MAIL_USERNAME'],
                recipients=[user.email]
            )
            msg.body = (
                f"Hello {user.name},\n\n"
                "Your account has been verified by the admin. You can now log in to the portal.\n\n"
                "Thank you!"
            )
            mail.send(msg)

            flash(f"{user_type.capitalize()} '{user.email}' approved successfully.", 'success')
        elif action == 'reject':
            # Optionally delete the user or just notify rejection
            db.session.delete(user)
            db.session.commit()
            flash(f"{user_type.capitalize()} '{user.email}' rejected and removed successfully.", 'danger')

        return redirect('/admin_verify')

    # Fetch unverified students and instructors
    unverified_students = Student.query.filter_by(verified=False).all()
    unverified_instructors = Instructor.query.filter_by(verified=False).all()

    return render_template('admin_verify.html', unverified_students=unverified_students, unverified_instructors=unverified_instructors)

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_email', None)
    flash('You have been logged out successfully.', 'info')
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
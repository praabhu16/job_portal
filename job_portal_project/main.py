# app.py - Complete features but optimized
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session, send_file
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import json
import bcrypt
from werkzeug.utils import secure_filename
import time
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

# Upload settings
UPLOAD_FOLDER = 'static/resumes'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

class Database:
    def __init__(self):
        self.host = os.getenv('DB_HOST')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_NAME')
    
    def connect(self):
        try:
            return mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
        except Error as e:
            print(f"Database error: {e}")
            return None

# Helper functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password.encode('utf-8'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or session.get('role') != required_role:
                flash('Access denied.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Auth Routes
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = Database()
        conn = db.connect()
        
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user and check_password(user['password_hash'], password):
                session['user_id'] = user['user_id']
                session['email'] = user['email']
                session['role'] = user['role']
                
                cursor.execute("SELECT full_name, location FROM User_Profiles WHERE user_id = %s", (user['user_id'],))
                profile = cursor.fetchone()
                
                if profile:
                    session['full_name'] = profile['full_name']
                    session['location'] = profile['location']
                
                cursor.close()
                conn.close()
                flash(f'Welcome back, {session.get("full_name", session["email"])}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials.', 'error')
        
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']
        full_name = request.form['full_name']
        location = request.form['location']
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        db = Database()
        conn = db.connect()
        
        if conn:
            cursor = conn.cursor()
            
            # Check existing email
            cursor.execute("SELECT user_id FROM Users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('Email already registered.', 'error')
                return render_template('register.html')
            
            # Create user
            hashed_password = hash_password(password)
            cursor.execute("INSERT INTO Users (email, password_hash, role) VALUES (%s, %s, %s)", 
                         (email, hashed_password, role))
            
            user_id = cursor.lastrowid
            
            # Create profile
            cursor.execute("INSERT INTO User_Profiles (user_id, full_name, location) VALUES (%s, %s, %s)", 
                         (user_id, full_name, location))
            
            # Role-specific setup
            if role == 'job_seeker':
                cursor.execute("INSERT INTO Job_Seekers (user_id, skills) VALUES (%s, %s)", 
                             (user_id, json.dumps([])))
            elif role == 'employer':
                company_name = request.form.get('company_name', 'My Company')
                cursor.execute("INSERT INTO Employers (user_id, company_name) VALUES (%s, %s)", 
                             (user_id, company_name))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    db = Database()
    conn = db.connect()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Get counts
        counts = {}
        cursor.execute("SELECT COUNT(*) as count FROM Users")
        counts['users'] = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM Jobs WHERE status='active'")
        counts['jobs'] = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM Employers")
        counts['employers'] = cursor.fetchone()['count']
        
        try:
            cursor.execute("SELECT COUNT(*) as count FROM Applications")
            counts['applications'] = cursor.fetchone()['count']
        except:
            counts['applications'] = 0
        
        # User-specific data
        user_data = {}
        if session['role'] == 'job_seeker':
            cursor.execute("""
                SELECT j.job_id, j.title, a.status, a.applied_date
                FROM Applications a
                JOIN Jobs j ON a.job_id = j.job_id
                WHERE a.seeker_id = (SELECT seeker_id FROM Job_Seekers WHERE user_id = %s)
                ORDER BY a.applied_date DESC LIMIT 5
            """, (session['user_id'],))
            user_data['applications'] = cursor.fetchall()
        elif session['role'] == 'employer':
            cursor.execute("""
                SELECT j.job_id, j.title, j.posted_date, COUNT(a.application_id) as applicant_count
                FROM Jobs j
                LEFT JOIN Applications a ON j.job_id = a.job_id
                WHERE j.employer_id = (SELECT employer_id FROM Employers WHERE user_id = %s)
                GROUP BY j.job_id ORDER BY j.posted_date DESC LIMIT 5
            """, (session['user_id'],))
            user_data['jobs'] = cursor.fetchall()
        
        # Recent jobs
        cursor.execute("""
            SELECT j.job_id, j.title, j.location, j.job_type, e.company_name 
            FROM Jobs j JOIN Employers e ON j.employer_id = e.employer_id 
            WHERE j.status = 'active' ORDER BY j.posted_date DESC LIMIT 5
        """)
        recent_jobs = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('dashboard.html', counts=counts, recent_jobs=recent_jobs, user_data=user_data)
    
    return "Could not connect to database."

# Job Seeker Profile Routes
@app.route('/my-profile', methods=['GET', 'POST'])
@login_required
@role_required('job_seeker')
def my_profile():
    db = Database()
    conn = db.connect()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            phone = request.form.get('phone')
            bio = request.form.get('bio')
            current_job_title = request.form.get('current_job_title')
            total_experience_years = request.form.get('total_experience_years')
            expected_salary = request.form.get('expected_salary')
            skills = request.form.get('skills')
            
            skills_list = [s.strip() for s in skills.split(',')] if skills else []
            
            cursor.execute("UPDATE User_Profiles SET phone = %s, bio = %s WHERE user_id = %s", 
                         (phone, bio, session['user_id']))
            
            cursor.execute("""
                UPDATE Job_Seekers SET current_job_title = %s, total_experience_years = %s,
                expected_salary = %s, skills = %s WHERE user_id = %s
            """, (current_job_title, total_experience_years, expected_salary, json.dumps(skills_list), session['user_id']))
            
            conn.commit()
            flash('Profile updated!', 'success')
            return redirect(url_for('my_profile'))
        
        # Get profile data
        cursor.execute("""
            SELECT up.*, js.*, u.email FROM User_Profiles up
            JOIN Job_Seekers js ON up.user_id = js.user_id
            JOIN Users u ON up.user_id = u.user_id
            WHERE up.user_id = %s
        """, (session['user_id'],))
        
        profile = cursor.fetchone()
        if profile and profile['skills']:
            try:
                profile['skills_list'] = json.loads(profile['skills'])
            except:
                profile['skills_list'] = []
        else:
            profile['skills_list'] = []
        
        # Get experiences
        experiences = []
        try:
            cursor.execute("""
                SELECT e.* FROM Experience e
                JOIN Job_Seekers js ON e.seeker_id = js.seeker_id
                WHERE js.user_id = %s ORDER BY e.start_date DESC
            """, (session['user_id'],))
            experiences = cursor.fetchall()
        except:
            pass
        
        cursor.close()
        conn.close()
        return render_template('job_seeker_profile.html', profile=profile, experiences=experiences)

@app.route('/add-experience', methods=['POST'])
@login_required
@role_required('job_seeker')
def add_experience():
    company = request.form.get('company')
    job_title = request.form.get('job_title')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    description = request.form.get('description')
    is_current = 1 if request.form.get('is_current') else 0
    
    db = Database()
    conn = db.connect()
    
    if conn:
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Experience (
                experience_id INT AUTO_INCREMENT PRIMARY KEY,
                seeker_id INT NOT NULL,
                company VARCHAR(255) NOT NULL,
                job_title VARCHAR(255) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NULL,
                description TEXT,
                is_current BOOLEAN DEFAULT FALSE,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (seeker_id) REFERENCES Job_Seekers(seeker_id)
            )
        """)
        
        cursor.execute("SELECT seeker_id FROM Job_Seekers WHERE user_id = %s", (session['user_id'],))
        seeker = cursor.fetchone()
        
        if seeker:
            cursor.execute("""
                INSERT INTO Experience (seeker_id, company, job_title, start_date, end_date, description, is_current)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (seeker[0], company, job_title, start_date, end_date, description, is_current))
            
            conn.commit()
            flash('Experience added!', 'success')
        
        cursor.close()
        conn.close()
    
    return redirect(url_for('my_profile'))

@app.route('/delete-experience/<int:experience_id>')
@login_required
@role_required('job_seeker')
def delete_experience(experience_id):
    db = Database()
    conn = db.connect()
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE e FROM Experience e
            JOIN Job_Seekers js ON e.seeker_id = js.seeker_id
            WHERE e.experience_id = %s AND js.user_id = %s
        """, (experience_id, session['user_id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        flash('Experience deleted!', 'success')
    
    return redirect(url_for('my_profile'))

# Company Reviews
@app.route('/company/<int:company_id>/reviews')
@login_required
def company_reviews(company_id):
    db = Database()
    conn = db.connect()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT e.*, up.full_name as contact_person
            FROM Employers e 
            JOIN Users u ON e.user_id = u.user_id
            JOIN User_Profiles up ON u.user_id = up.user_id
            WHERE e.employer_id = %s
        """, (company_id,))
        company = cursor.fetchone()
        
        cursor.execute("""
            SELECT cr.*, CASE WHEN cr.is_anonymous = 1 THEN 'Anonymous' ELSE up.full_name END as display_name
            FROM Company_Reviews cr
            JOIN Users u ON cr.user_id = u.user_id
            JOIN User_Profiles up ON u.user_id = up.user_id
            WHERE cr.company_id = %s AND cr.is_approved = 1
            ORDER BY cr.created_date DESC
        """, (company_id,))
        reviews = cursor.fetchall()
        
        user_has_reviewed = False
        if session['role'] == 'job_seeker':
            cursor.execute("SELECT review_id FROM Company_Reviews WHERE company_id = %s AND user_id = %s", (company_id, session['user_id']))
            user_has_reviewed = cursor.fetchone() is not None
        
        cursor.close()
        conn.close()
        return render_template('company_reviews.html', company=company, reviews=reviews, user_has_reviewed=user_has_reviewed)

@app.route('/company/<int:company_id>/add-review', methods=['GET', 'POST'])
@login_required
@role_required('job_seeker')
def add_review(company_id):
    if request.method == 'POST':
        rating = request.form['rating']
        review_title = request.form['review_title']
        review_text = request.form['review_text']
        pros = request.form['pros']
        cons = request.form['cons']
        job_title = request.form.get('job_title', '')
        is_anonymous = 1 if 'is_anonymous' in request.form else 0
        
        db = Database()
        conn = db.connect()
        
        if conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT review_id FROM Company_Reviews WHERE company_id = %s AND user_id = %s", (company_id, session['user_id']))
            if cursor.fetchone():
                flash('Already reviewed!', 'error')
                return redirect(url_for('company_reviews', company_id=company_id))
            
            cursor.execute("""
                INSERT INTO Company_Reviews 
                (company_id, user_id, job_title, rating, review_title, review_text, pros, cons, is_anonymous, is_approved)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (company_id, session['user_id'], job_title, rating, review_title, review_text, pros, cons, is_anonymous, 1))
            
            cursor.execute("""
                UPDATE Employers SET avg_rating = (
                    SELECT AVG(rating) FROM Company_Reviews WHERE company_id = %s AND is_approved = 1
                ), review_count = (
                    SELECT COUNT(*) FROM Company_Reviews WHERE company_id = %s AND is_approved = 1
                ) WHERE employer_id = %s
            """, (company_id, company_id, company_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            flash('Review submitted!', 'success')
            return redirect(url_for('company_reviews', company_id=company_id))
    
    return render_template('add_review.html', company_id=company_id)

# Interview Scheduling
@app.route('/schedule-interview/<int:application_id>', methods=['GET', 'POST'])
@login_required
@role_required('employer')
def schedule_interview(application_id):
    if request.method == 'POST':
        interview_date = request.form['interview_date']
        duration = request.form.get('duration', 60)
        interview_type = request.form.get('interview_type', 'video')
        meeting_link = request.form.get('meeting_link', '')
        location = request.form.get('location', '')
        notes = request.form.get('notes', '')
        job_id = request.form['job_id']
        
        db = Database()
        conn = db.connect()
        
        if conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                INSERT INTO Interviews 
                (application_id, interview_date, duration_minutes, interview_type, meeting_link, location, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (application_id, interview_date, duration, interview_type, meeting_link, location, notes, session['user_id']))
            
            cursor.execute("UPDATE Applications SET status = 'under_review' WHERE application_id = %s", (application_id,))
            
            # Create notification
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Notifications (
                    notification_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES Users(user_id)
                )
            """)
            
            cursor.execute("""
                SELECT js.user_id, j.title, e.company_name
                FROM Applications a
                JOIN Job_Seekers js ON a.seeker_id = js.seeker_id
                JOIN Jobs j ON a.job_id = j.job_id
                JOIN Employers e ON j.employer_id = e.employer_id
                WHERE a.application_id = %s
            """, (application_id,))
            applicant_info = cursor.fetchone()
            
            if applicant_info:
                notification_msg = f"Interview scheduled for '{applicant_info['title']}' at {applicant_info['company_name']}. Date: {interview_date}"
                cursor.execute("INSERT INTO Notifications (user_id, title, message) VALUES (%s, %s, %s)", 
                             (applicant_info['user_id'], "Interview Scheduled", notification_msg))
            
            conn.commit()
            cursor.close()
            conn.close()
            flash('Interview scheduled!', 'success')
            return redirect(url_for('job_applicants', job_id=job_id))
    
    # GET request
    db = Database()
    conn = db.connect()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.*, j.title, j.job_id, p.full_name
        FROM Applications a
        JOIN Jobs j ON a.job_id = j.job_id
        JOIN Job_Seekers js ON a.seeker_id = js.seeker_id
        JOIN User_Profiles p ON js.user_id = p.user_id
        WHERE a.application_id = %s
    """, (application_id,))
    application = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('schedule_interview.html', application=application)

@app.route('/my-interviews')
@login_required
def my_interviews():
    db = Database()
    conn = db.connect()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        if session['role'] == 'job_seeker':
            cursor.execute("""
                SELECT i.*, j.title, e.company_name, up.full_name as employer_name, a.status as application_status
                FROM Interviews i
                JOIN Applications a ON i.application_id = a.application_id
                JOIN Jobs j ON a.job_id = j.job_id
                JOIN Employers e ON j.employer_id = e.employer_id
                JOIN Users u ON e.user_id = u.user_id
                JOIN User_Profiles up ON u.user_id = up.user_id
                WHERE a.seeker_id = (SELECT seeker_id FROM Job_Seekers WHERE user_id = %s)
                ORDER BY i.interview_date DESC
            """, (session['user_id'],))
        else:
            cursor.execute("""
                SELECT i.*, j.title, up.full_name as candidate_name, a.status as application_status
                FROM Interviews i
                JOIN Applications a ON i.application_id = a.application_id
                JOIN Jobs j ON a.job_id = j.job_id
                JOIN Job_Seekers js ON a.seeker_id = js.seeker_id
                JOIN User_Profiles up ON js.user_id = up.user_id
                WHERE i.created_by = %s
                ORDER BY i.interview_date DESC
            """, (session['user_id'],))
        
        interviews = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('my_interviews.html', interviews=interviews)

@app.route('/notifications')
@login_required
def notifications():
    db = Database()
    conn = db.connect()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Notifications (
                notification_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(user_id)
            )
        """)
        
        cursor.execute("SELECT * FROM Notifications WHERE user_id = %s ORDER BY created_date DESC", (session['user_id'],))
        notifications = cursor.fetchall()
        
        cursor.execute("UPDATE Notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0", (session['user_id'],))
        
        conn.commit()
        cursor.close()
        conn.close()
        return render_template('notifications.html', notifications=notifications)
    
    return redirect(url_for('dashboard'))

# Resume Management
@app.route('/upload-resume', methods=['GET', 'POST'])
@login_required
@role_required('job_seeker')
def upload_resume():
    if request.method == 'POST':
        if 'resume' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['resume']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"resume_{session['user_id']}_{int(time.time())}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(file_path)
            
            db = Database()
            conn = db.connect()
            
            if conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE Job_Seekers SET resume_file_path = %s, resume_original_filename = %s WHERE user_id = %s", 
                             (file_path, filename, session['user_id']))
                
                conn.commit()
                cursor.close()
                conn.close()
                flash('Resume uploaded!', 'success')
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid file type.', 'error')
    
    return render_template('upload_resume.html')

@app.route('/download-resume/<int:seeker_id>')
@login_required
def download_resume(seeker_id):
    db = Database()
    conn = db.connect()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT resume_file_path, resume_original_filename FROM Job_Seekers WHERE seeker_id = %s", (seeker_id,))
        resume_info = cursor.fetchone()
        
        if not resume_info or not resume_info['resume_file_path']:
            flash('Resume not found.', 'error')
            return redirect(request.referrer or url_for('dashboard'))
        
        # Check permissions
        if session['role'] == 'employer':
            cursor.execute("""
                SELECT a.application_id 
                FROM Applications a
                JOIN Jobs j ON a.job_id = j.job_id
                JOIN Employers e ON j.employer_id = e.employer_id
                WHERE a.seeker_id = %s AND e.user_id = %s
                LIMIT 1
            """, (seeker_id, session['user_id']))
            if not cursor.fetchone():
                flash('Access denied.', 'error')
                return redirect(url_for('dashboard'))
        elif session['role'] == 'job_seeker':
            cursor.execute("SELECT seeker_id FROM Job_Seekers WHERE seeker_id = %s AND user_id = %s", (seeker_id, session['user_id']))
            if not cursor.fetchone():
                flash('Access denied.', 'error')
                return redirect(url_for('dashboard'))
        
        cursor.close()
        conn.close()
        
        if os.path.exists(resume_info['resume_file_path']):
            return send_file(
                resume_info['resume_file_path'],
                as_attachment=True,
                download_name=resume_info['resume_original_filename'] or 'resume.pdf'
            )
        else:
            flash('File not found.', 'error')
    
    return redirect(url_for('dashboard'))

# Job Management
@app.route('/jobs')
@login_required
def jobs_list():
    db = Database()
    conn = db.connect()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        search_query = request.args.get('search', '')
        company_query = request.args.get('company', '')
        location_query = request.args.get('location', '')
        job_types = request.args.getlist('job_type')
        
        query = """
            SELECT j.*, e.company_name, e.avg_rating, e.review_count
            FROM Jobs j JOIN Employers e ON j.employer_id = e.employer_id 
            WHERE j.status = 'active'
        """
        params = []
        
        if search_query:
            query += " AND (j.title LIKE %s OR j.description LIKE %s)"
            params.extend([f'%{search_query}%', f'%{search_query}%'])
        
        if company_query:
            query += " AND e.company_name LIKE %s"
            params.append(f'%{company_query}%')
        
        if location_query:
            query += " AND j.location LIKE %s"
            params.append(f'%{location_query}%')
        
        if job_types:
            placeholders = ', '.join(['%s'] * len(job_types))
            query += f" AND j.job_type IN ({placeholders})"
            params.extend(job_types)
        
        query += " ORDER BY j.posted_date DESC"
        cursor.execute(query, params)
        jobs = cursor.fetchall()
        
        if session['role'] == 'job_seeker':
            cursor.execute("SELECT job_id FROM Applications WHERE seeker_id = (SELECT seeker_id FROM Job_Seekers WHERE user_id = %s)", (session['user_id'],))
            applied_jobs = [row['job_id'] for row in cursor.fetchall()]
            for job in jobs:
                job['has_applied'] = job['job_id'] in applied_jobs
        
        cursor.close()
        conn.close()
        return render_template('jobs_list.html', jobs=jobs)

@app.route('/apply-job/<int:job_id>', methods=['GET', 'POST'])
@login_required
@role_required('job_seeker')
def apply_job(job_id):
    if request.method == 'POST':
        cover_letter = request.form['cover_letter']
        
        db = Database()
        conn = db.connect()
        
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT seeker_id FROM Job_Seekers WHERE user_id = %s", (session['user_id'],))
            seeker = cursor.fetchone()
            
            if seeker:
                cursor.execute("SELECT application_id FROM Applications WHERE job_id = %s AND seeker_id = %s", (job_id, seeker['seeker_id']))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO Applications (job_id, seeker_id, cover_letter) VALUES (%s, %s, %s)", 
                                 (job_id, seeker['seeker_id'], cover_letter))
                    conn.commit()
                    flash('Application submitted!', 'success')
                    return redirect(url_for('my_applications'))
                else:
                    flash('Already applied!', 'error')
            
            cursor.close()
            conn.close()
    
    return render_template('apply_job.html', job_id=job_id)

@app.route('/add-job', methods=['GET', 'POST'])
@login_required
@role_required('employer')
def add_job():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        requirements = request.form['requirements']
        location = request.form['location']
        job_type = request.form['job_type']
        salary_min = request.form.get('salary_min')
        salary_max = request.form.get('salary_max')
        skills = request.form['skills']
        
        db = Database()
        conn = db.connect()
        
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT employer_id FROM Employers WHERE user_id = %s", (session['user_id'],))
            employer = cursor.fetchone()
            
            if employer:
                skills_list = [s.strip() for s in skills.split(',')] if skills else []
                cursor.execute("""
                    INSERT INTO Jobs (employer_id, title, description, requirements, location, job_type, salary_range_min, salary_range_max, skills_required)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (employer[0], title, description, requirements, location, job_type, salary_min, salary_max, json.dumps(skills_list)))
                
                conn.commit()
                cursor.close()
                conn.close()
                flash('Job posted!', 'success')
                return redirect(url_for('my_jobs'))
    
    return render_template('add_job.html')

@app.route('/my-jobs')
@login_required
@role_required('employer')
def my_jobs():
    db = Database()
    conn = db.connect()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT j.*, e.company_name, COUNT(a.application_id) as applicant_count
            FROM Jobs j JOIN Employers e ON j.employer_id = e.employer_id 
            LEFT JOIN Applications a ON j.job_id = a.job_id
            WHERE e.user_id = %s GROUP BY j.job_id ORDER BY j.posted_date DESC
        """, (session['user_id'],))
        jobs = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('my_jobs.html', jobs=jobs)

@app.route('/job-applicants/<int:job_id>')
@login_required
@role_required('employer')
def job_applicants(job_id):
    db = Database()
    conn = db.connect()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT j.job_id, j.title, j.description, e.company_name
            FROM Jobs j
            JOIN Employers e ON j.employer_id = e.employer_id
            WHERE j.job_id = %s AND e.user_id = %s
        """, (job_id, session['user_id']))
        job = cursor.fetchone()
        
        if not job:
            flash('Job not found.', 'error')
            return redirect(url_for('my_jobs'))
        
        cursor.execute("""
            SELECT a.*, p.full_name, u.email, p.phone, p.location, js.resume_file_path, js.skills, js.seeker_id
            FROM Applications a
            JOIN Job_Seekers js ON a.seeker_id = js.seeker_id
            JOIN Users u ON js.user_id = u.user_id
            JOIN User_Profiles p ON u.user_id = p.user_id
            WHERE a.job_id = %s
            ORDER BY a.applied_date DESC
        """, (job_id,))
        applicants = cursor.fetchall()
        
        for applicant in applicants:
            if applicant['skills']:
                try:
                    applicant['skills_list'] = json.loads(applicant['skills'])
                except:
                    applicant['skills_list'] = []
        
        cursor.close()
        conn.close()
        return render_template('job_applicants.html', job=job, applicants=applicants)
    
    return redirect(url_for('my_jobs'))

@app.route('/my-applications')
@login_required
@role_required('job_seeker')
def my_applications():
    db = Database()
    conn = db.connect()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, j.title, j.location, e.company_name, j.job_type
            FROM Applications a
            JOIN Jobs j ON a.job_id = j.job_id
            JOIN Employers e ON j.employer_id = e.employer_id
            WHERE a.seeker_id = (SELECT seeker_id FROM Job_Seekers WHERE user_id = %s)
            ORDER BY a.applied_date DESC
        """, (session['user_id'],))
        applications = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('my_applications.html', applications=applications)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out!', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("🚀 Advanced Job Portal Started...")
    app.run(debug=True, host='0.0.0.0', port=5000)
import mysql.connector

# Connect to MySQL
conn = mysql.connector.connect(
    host='127.0.0.1',
    user='root',
    password='Pj16032006@',
    database='job_portal'
)

cursor = conn.cursor()

print('Creating missing tables...')

# 1. Users table (already exists)
# 2. User_Profiles table (already exists)
# 3. Job_Seekers table (already exists)
# 4. Employers table (already exists)
# 5. Jobs table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Jobs (
        job_id INT AUTO_INCREMENT PRIMARY KEY,
        employer_id INT NOT NULL,
        title VARCHAR(255) NOT NULL,
        description TEXT NOT NULL,
        requirements TEXT,
        location VARCHAR(255),
        job_type VARCHAR(50),
        salary_range_min DECIMAL(10, 2),
        salary_range_max DECIMAL(10, 2),
        skills_required TEXT,
        status VARCHAR(50) DEFAULT 'active',
        posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
print('? Jobs table created')

# 6. Applications table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Applications (
        application_id INT AUTO_INCREMENT PRIMARY KEY,
        job_id INT NOT NULL,
        seeker_id INT NOT NULL,
        cover_letter TEXT,
        status VARCHAR(50) DEFAULT 'pending',
        applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
print('? Applications table created')

# 7. Experience table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Experience (
        experience_id INT AUTO_INCREMENT PRIMARY KEY,
        seeker_id INT NOT NULL,
        company VARCHAR(255) NOT NULL,
        job_title VARCHAR(255) NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NULL,
        description TEXT,
        is_current BOOLEAN DEFAULT FALSE,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
print('? Experience table created')

# 8. Company_Reviews table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Company_Reviews (
        review_id INT AUTO_INCREMENT PRIMARY KEY,
        company_id INT NOT NULL,
        user_id INT NOT NULL,
        job_title VARCHAR(255),
        rating INT,
        review_title VARCHAR(255),
        review_text TEXT NOT NULL,
        pros TEXT,
        cons TEXT,
        is_anonymous BOOLEAN DEFAULT FALSE,
        is_approved BOOLEAN DEFAULT TRUE,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
print('? Company_Reviews table created')

# 9. Interviews table (THIS IS THE MISSING ONE!)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Interviews (
        interview_id INT AUTO_INCREMENT PRIMARY KEY,
        application_id INT NOT NULL,
        interview_date DATETIME NOT NULL,
        duration_minutes INT DEFAULT 60,
        interview_type VARCHAR(50),
        meeting_link VARCHAR(500),
        location VARCHAR(255),
        notes TEXT,
        created_by INT,
        status VARCHAR(50) DEFAULT 'scheduled',
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
print('? Interviews table created')

# 10. Notifications table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Notifications (
        notification_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        title VARCHAR(255) NOT NULL,
        message TEXT NOT NULL,
        is_read BOOLEAN DEFAULT FALSE,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
print('? Notifications table created')

conn.commit()

# Show all tables
cursor.execute('SHOW TABLES')
tables = cursor.fetchall()
print(f'\n?? All tables ({len(tables)} total):')
for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {table[0]}')
    count = cursor.fetchone()[0]
    print(f'   - {table[0]} ({count} rows)')

cursor.close()
conn.close()
print('\n?? All tables created successfully!')

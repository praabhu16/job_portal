import mysql.connector

# Connect to MySQL
conn = mysql.connector.connect(
    host='127.0.0.1',
    user='root',
    password='Pj16032006@',
    database='job_portal'
)

cursor = conn.cursor()

# Create tables
tables = [
    '''CREATE TABLE IF NOT EXISTS User_Profiles (
        profile_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        full_name VARCHAR(255),
        location VARCHAR(255),
        phone VARCHAR(20),
        bio TEXT,
        FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    )''',
    
    '''CREATE TABLE IF NOT EXISTS Job_Seekers (
        seeker_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        current_job_title VARCHAR(255),
        total_experience_years INT,
        expected_salary DECIMAL(10, 2),
        skills TEXT,
        resume_file_path VARCHAR(500),
        resume_original_filename VARCHAR(255),
        resume_text TEXT,
        FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    )''',
    
    '''CREATE TABLE IF NOT EXISTS Employers (
        employer_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        company_name VARCHAR(255),
        industry VARCHAR(255),
        avg_rating DECIMAL(3, 2) DEFAULT 0,
        review_count INT DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    )''',
    
    '''CREATE TABLE IF NOT EXISTS Jobs (
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
        posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employer_id) REFERENCES Employers(employer_id) ON DELETE CASCADE
    )''',
    
    '''CREATE TABLE IF NOT EXISTS Applications (
        application_id INT AUTO_INCREMENT PRIMARY KEY,
        job_id INT NOT NULL,
        seeker_id INT NOT NULL,
        cover_letter TEXT,
        status VARCHAR(50) DEFAULT 'pending',
        applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES Jobs(job_id) ON DELETE CASCADE,
        FOREIGN KEY (seeker_id) REFERENCES Job_Seekers(seeker_id) ON DELETE CASCADE
    )'''
]

print('Creating tables...')
for i, table in enumerate(tables, 1):
    try:
        cursor.execute(table)
        table_name = table.split('CREATE TABLE IF NOT EXISTS ')[1].split(' (')[0]
        print(f'? {i}. Table created: {table_name}')
    except Exception as e:
        print(f'? Error creating table {i}: {e}')

conn.commit()
cursor.close()
conn.close()

print('\n?? All tables created!')

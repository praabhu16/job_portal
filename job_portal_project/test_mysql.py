# test_mysql.py
import mysql.connector
from mysql.connector import Error

def test_connection():
    try:
        # Connect to MySQL
        connection = mysql.connector.connect(
            host='127.0.0.1',
            user='root',  # Using root user since we have the password
            password='Pj16032006@',  # Your MySQL root password
            database='job_portal'
        )
        
        if connection.is_connected():
            print("✅ SUCCESS! Connected to MySQL database!")
            
            # Get database info
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()
            print(f"📊 Database: {db_name[0]}")
            
            # Show all tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print("📋 Tables in database:")
            for table in tables:
                print(f"   - {table[0]}")
            
            # Count records in each table
            tables_to_check = ['Users', 'User_Profiles', 'Job_Seekers', 'Employers', 'Jobs']
            print("\n📈 Record Counts:")
            for table in tables_to_check:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   - {table}: {count} records")
            
            # Show sample data from Users table
            print("\n👥 Sample Users:")
            cursor.execute("SELECT user_id, email, role FROM Users")
            users = cursor.fetchall()
            for user in users:
                print(f"   - ID: {user[0]}, Email: {user[1]}, Role: {user[2]}")
            
            # Show sample jobs
            print("\n💼 Sample Jobs:")
            cursor.execute("SELECT job_id, title, location FROM Jobs")
            jobs = cursor.fetchall()
            for job in jobs:
                print(f"   - ID: {job[0]}, Title: {job[1]}, Location: {job[2]}")
            
            cursor.close()
            connection.close()
            print("\n🎉 All tests passed! Database is ready for Flask app!")
            
    except Error as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_connection()
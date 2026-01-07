# fix_admin.py
import mysql.connector
from werkzeug.security import generate_password_hash

def create_admin_account():
    try:
        # Connect to database
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="feizen_haven"
        )
        
        cursor = db.cursor(dictionary=True)
        
        # Delete existing admin if exists
        cursor.execute("DELETE FROM users WHERE email = 'admin@feizenhaven.com'")
        print("🗑️  Old admin removed if existed")
        
        # Create new admin
        password = "admin123"
        hashed_password = generate_password_hash(password)
        
        cursor.execute("""
            INSERT INTO users (first_name, last_name, email, phone, password, role) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            "Admin", 
            "Feizen", 
            "admin@feizenhaven.com", 
            "081234567890",
            hashed_password,
            "admin"
        ))
        
        db.commit()
        
        # Verify the admin
        cursor.execute("SELECT * FROM users WHERE role = 'admin'")
        admins = cursor.fetchall()
        
        print(f"\n✅ Admin account created successfully!")
        print(f"📧 Email: admin@feizenhaven.com")
        print(f"🔑 Password: admin123")
        print(f"👑 Role: admin")
        print(f"\n📊 Total admin accounts: {len(admins)}")
        
        for admin in admins:
            print(f"   - {admin['email']} ({admin['first_name']} {admin['last_name']})")
        
        cursor.close()
        db.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    create_admin_account()
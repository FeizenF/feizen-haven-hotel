import mysql.connector
from mysql.connector import Error
import hashlib
from werkzeug.security import generate_password_hash

def create_connection():
    """Membuat koneksi ke database feizen_haven"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',  
            password='',  
            database='feizen_haven'
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def hash_password(password):
    """Hash password menggunakan Werkzeug (sama dengan aplikasi)"""
    return generate_password_hash(password)

def create_tables():
    """Membuat semua tabel di database feizen_haven"""
    connection = create_connection()
    if connection is None:
        print("❌ Gagal terkoneksi ke database!")
        return False
    
    cursor = connection.cursor()
    
    try:
        print("=" * 50)
        print("MEMBUAT TABEL DATABASE")
        print("=" * 50)
        
        # SQL untuk membuat tabel users
        users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INT PRIMARY KEY AUTO_INCREMENT,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            phone VARCHAR(20),
            password VARCHAR(255) NOT NULL,
            role ENUM('user', 'admin') DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_email (email),
            INDEX idx_role (role)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        # SQL untuk membuat tabel rooms
        rooms_table = """
        CREATE TABLE IF NOT EXISTS rooms (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            size VARCHAR(20),
            capacity INT DEFAULT 2,
            view_type VARCHAR(50),
            amenities TEXT,
            images TEXT,
            is_available INT DEFAULT 1,
            room_count INT DEFAULT 1,
            room_type ENUM('hotel_room', 'meeting_room', 'facility', 'restaurant', 'spa') DEFAULT 'hotel_room',
            available_count INT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_room_type (room_type),
            INDEX idx_is_available (is_available),
            INDEX idx_price (price)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        # SQL untuk membuat tabel payments
        payments_table = """
        CREATE TABLE IF NOT EXISTS payments (
            id INT PRIMARY KEY AUTO_INCREMENT,
            booking_id INT NOT NULL,
            facility_booking_id INT,
            amount DECIMAL(10,2) NOT NULL,
            payment_method ENUM('qris', 'bank_transfer', 'credit_card', 'ovo', 'gopay', 'dana') NOT NULL,
            status ENUM('pending', 'processing', 'completed', 'failed', 'expired') DEFAULT 'pending',
            proof_image VARCHAR(255),
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expiration_date TIMESTAMP NULL,
            admin_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_booking_id (booking_id),
            INDEX idx_status (status),
            INDEX idx_payment_date (payment_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        # SQL untuk membuat tabel bookings 
        bookings_table = """
        CREATE TABLE IF NOT EXISTS bookings (
            id INT PRIMARY KEY AUTO_INCREMENT,
            booking_code VARCHAR(20) UNIQUE,
            user_id INT NOT NULL,
            room_id INT NOT NULL,
            check_in DATE NOT NULL,
            check_out DATE NOT NULL,
            guests INT DEFAULT 2,
            total_price DECIMAL(10,2) NOT NULL,
            subtotal DECIMAL(10,2) DEFAULT 0.00,
            tax_amount DECIMAL(10,2) DEFAULT 0.00,
            service_charge DECIMAL(10,2) DEFAULT 0.00,
            special_requests TEXT,
            status ENUM('pending', 'waiting_payment', 'confirmed', 'cancelled', 'completed') DEFAULT 'pending',
            admin_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            payment_id INT NULL,
            payment_status ENUM('pending', 'waiting_payment', 'paid', 'failed') DEFAULT 'pending',
            guest_name VARCHAR(255),
            guest_email VARCHAR(255),
            guest_phone VARCHAR(20),
            guest_country VARCHAR(100),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL ON UPDATE CASCADE,
            INDEX idx_user_id (user_id),
            INDEX idx_room_id (room_id),
            INDEX idx_status (status),
            INDEX idx_check_in (check_in),
            INDEX idx_check_out (check_out),
            INDEX idx_booking_code (booking_code),
            INDEX idx_payment_status (payment_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        # SQL untuk membuat tabel venues
        venues_table = """
        CREATE TABLE IF NOT EXISTS venues (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            icon_class VARCHAR(50),
            image_url VARCHAR(255),
            opening_hours VARCHAR(100),
            is_available BOOLEAN DEFAULT TRUE,
            type ENUM('meeting_room', 'restaurant', 'spa', 'pool', 'gym', 'business_center', 'event_space', 'other') DEFAULT 'other',
            price_per_hour DECIMAL(10,2) DEFAULT 0.00,
            price_per_day DECIMAL(10,2) DEFAULT 0.00,
            capacity INT DEFAULT 10,
            size VARCHAR(50),
            amenities TEXT,
            booking_type ENUM('hourly', 'daily', 'per_person', 'package') DEFAULT 'hourly',
            min_booking_hours INT DEFAULT 1,
            max_advance_days INT DEFAULT 30,
            location VARCHAR(100),
            contact_person VARCHAR(100),
            contact_phone VARCHAR(20),
            features TEXT,
            notes TEXT,
            INDEX idx_type (type),
            INDEX idx_is_available (is_available),
            INDEX idx_booking_type (booking_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        # SQL untuk membuat tabel contact_inquiries
        contact_inquiries_table = """
        CREATE TABLE IF NOT EXISTS contact_inquiries (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL,
            phone VARCHAR(20),
            message TEXT NOT NULL,
            status ENUM('new', 'read', 'replied') DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_status (status),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        # CREATE TABELS DALAM URUTAN YANG BENAR
        print("Membuat tabel users...")
        cursor.execute(users_table)
        
        print("Membuat tabel rooms...")
        cursor.execute(rooms_table)
        
        print("Membuat tabel payments...")
        cursor.execute(payments_table)
        
        print("Membuat tabel bookings...")
        cursor.execute(bookings_table)
        
        print("Membuat tabel venues...")
        cursor.execute(venues_table)
        
        print("Membuat tabel contact_inquiries...")
        cursor.execute(contact_inquiries_table)
        
        print("\n✅ Semua tabel berhasil dibuat!")
        
        connection.commit()
        return True
        
    except Error as e:
        print(f"❌ Error saat membuat tabel: {e}")
        print(f"SQL State: {e.sqlstate}")
        print(f"Error Number: {e.errno}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()

def insert_sample_data():
    """Menyisipkan data contoh ke dalam tabel"""
    connection = create_connection()
    if connection is None:
        print("❌ Gagal terkoneksi ke database!")
        return False
    
    cursor = connection.cursor()
    
    try:
        print("\n" + "=" * 50)
        print("MEMASUKKAN DATA CONTOH")
        print("=" * 50)
        
        # 1. DATA USERS (dengan password yang sudah di-hash)
        print("👤 Menambahkan data users...")
        users_data = [
            ("Fernanda", "Brian", "fernanda@xyz.com", "081234567890", generate_password_hash("fernanda123"), "admin"),
            ("Egacor", "Arda", "arda@xyz.com", "081298765432", generate_password_hash("egacor123"), "user"),
            ("Ajixx", "Suep", "ajizz@xyz.com", "081112223333", generate_password_hash("ajizz122"), "user"),
            ("John", "Doe", "john.doe@example.com", "081223344556", generate_password_hash("john123"), "user"),
            ("Jane", "Smith", "jane.smith@example.com", "081334455667", generate_password_hash("jane123"), "user")
        ]
        
        for user in users_data:
            cursor.execute("""
                INSERT INTO users (first_name, last_name, email, phone, password, role) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, user)
        
        # 2. DATA ROOMS (Hotel Rooms)
        print("🏨 Menambahkan data rooms...")
        rooms_data = [
            # Hotel Rooms
            ("Deluxe Room", "Kamar mewah dengan pemandangan kota, dilengkapi dengan fasilitas modern untuk kenyamanan maksimal", 
             500000, "30m²", 2, "City View", 
             '["WiFi Gratis", "AC", "TV LED 32\\\"", "Mini Bar", "Bathub", "Coffee Maker", "Safe Deposit Box"]', 
             '["static/images/rooms/deluxe1.jpg", "static/images/rooms/deluxe2.jpg"]', 
             1, 8, "hotel_room", 8),
            
            ("Executive Suite", "Suite eksekutif dengan ruang tamu terpisah dan pemandangan laut yang menakjubkan", 
             800000, "50m²", 4, "Sea View",
             '["WiFi Gratis", "AC", "TV LED 55\\\"", "Kitchenette", "Jacuzzi", "Living Room", "Working Desk", "Nespresso Machine"]', 
             '["static/images/rooms/executive1.jpg", "static/images/rooms/executive2.jpg"]', 
             1, 4, "hotel_room", 4),
            
            ("Presidential Suite", "Kamar terbaik hotel dengan fasilitas mewah dan layanan butler pribadi", 
             1500000, "80m²", 6, "Panoramic View",
             '["WiFi Gratis", "AC", "TV LED 65\\\"", "Private Kitchen", "Private Jacuzzi", "Butler Service", "Dining Area", "Private Bar", "Home Theater"]', 
             '["static/images/rooms/presidential1.jpg", "static/images/rooms/presidential2.jpg", "static/images/rooms/presidential3.jpg"]', 
             1, 2, "hotel_room", 2),
            
            ("Standard Room", "Kamar nyaman dengan harga terjangkau untuk tamu bisnis dan wisatawan", 
             350000, "25m²", 2, "Garden View",
             '["WiFi Gratis", "AC", "TV LED 32\\\"", "Coffee/Tea Maker", "Shower", "Work Desk"]', 
             '["static/images/rooms/standard1.jpg", "static/images/rooms/standard2.jpg"]', 
             1, 12, "hotel_room", 12),
            
            ("Family Room", "Kamar luas dengan 2 kamar tidur untuk keluarga, lengkap dengan fasilitas anak-anak", 
             950000, "65m²", 4, "Pool View",
             '["WiFi Gratis", "AC", "TV LED 55\\\"", "Kitchenette", "Living Area", "Baby Cot", "Children Amenities", "Game Console"]', 
             '["static/images/rooms/family1.jpg", "static/images/rooms/family2.jpg"]', 
             1, 6, "hotel_room", 6),
            
            # Meeting Rooms (dalam tabel rooms juga)
            ("Meeting Room A", "Ruang meeting kecil untuk 8-10 orang", 
             250000, "30m²", 10, "City View",
             '["Projector", "Whiteboard", "WiFi", "AC", "Flip Chart", "Conference Phone"]', 
             '["static/images/meetings/rooma1.jpg"]', 
             1, 2, "meeting_room", 2),
            
            ("Boardroom", "Ruang rapat eksekutif untuk 12 orang", 
             500000, "45m²", 12, "City View",
             '["Smart TV 75\\\"", "Video Conferencing", "WiFi High-Speed", "AC", "Executive Chairs", "Catering Service"]', 
             '["static/images/meetings/boardroom1.jpg"]', 
             1, 1, "meeting_room", 1)
        ]
        
        for room in rooms_data:
            cursor.execute("""
                INSERT INTO rooms (name, description, price, size, capacity, view_type, 
                                 amenities, images, is_available, room_count, room_type, available_count) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, room)
        
        # 3. DATA VENUES (Fasilitas Hotel)
        print("📍 Menambahkan data venues...")
        venues_data = [
            # MEETING & EVENT SPACES
            ("Grand Ballroom", 
             "Ballroom mewah dengan kapasitas besar untuk acara formal, pernikahan, dan konferensi. Dilengkapi dengan sistem audio-visual canggih dan pencahayaan yang dapat disesuaikan.",
             "fas fa-users", 
             "static/images/venues/ballroom.jpg",
             "07:00 - 23:00", 
             True, 
             "event_space", 
             0,
             25000000,
             500,
             "800m²", 
             '["Sistem Audio Profesional", "Panggung Besar", "LED Screen 8x4m", "Soundproofing", "AC Sentral", "Toilet Eksklusif", "Ruang Persiapan", "Parkir Valet", "Catering Service"]',
             "package", 
             8,
             365,
             "Lantai 1 - West Wing", 
             "Mr. Andre Wijaya", 
             "+62 812-3456-7890",
             '["Parkir untuk 200 mobil", "4 ruang ganti", "2 ruang VIP", "generator cadangan"]',
             ""),
            
            ("Meeting Room B", 
             "Ruang meeting medium untuk 15-20 orang, ideal untuk training dan workshop.",
             "fas fa-presentation", 
             "static/images/venues/meeting2.jpg",
             "08:00 - 22:00", 
             True, 
             "meeting_room", 
             250000,
             1750000,
             20,
             "40m²", 
             '["Smart TV 65\\\"", "Sound System", "Whiteboard", "WiFi High-Speed", "Flip Chart", "Coffee Break Service"]',
             "hourly", 
             2,
             60,
             "Lantai 2 - Business Center", 
             "Ms. Sarah Chandra", 
             "+62 813-9876-5432",
             '["Video conferencing", "standing desk option"]',
             ""),
            
            # WELLNESS FACILITIES
            ("Infinity Pool & Sky Lounge", 
             "Kolam renang infinity dengan pemandangan kota Yogyakarta yang menakjubkan, dilengkapi lounge area yang nyaman.",
             "fas fa-swimming-pool", 
             "static/images/venues/pool.jpg",
             "06:00 - 22:00", 
             True, 
             "pool", 
             0,
             0,
             50,
             "300m²", 
             '["Pool Bar", "Sunbed Premium", "Towel Service", "Safety Lifeguard", "Changing Room", "Shower Facilities"]',
             "per_person", 
             1,
             7,
             "Rooftop Level", 
             "Pool Manager", 
             "+62 811-2233-4455",
             '["Hanya untuk hotel guest", "kids pool terpisah", "pool heater tersedia"]',
             ""),
            
            ("Feizen Spa & Wellness", 
             "Spa premium dengan berbagai perawatan tradisional dan modern untuk relaksasi dan rejuvenasi.",
             "fas fa-spa", 
             "static/images/venues/spa.jpg",
             "09:00 - 21:00", 
             True, 
             "spa", 
             250000,
             1800000,
             10,
             "200m²", 
             '["Massage Room", "Sauna", "Steam Room", "Jacuzzi", "Treatment Room", "Relaxation Area", "Aromatherapy"]',
             "per_person", 
             1,
             30,
             "Lantai 3 - East Wing", 
             "Spa Director", 
             "+62 812-9988-7766",
             '["Therapist bersertifikat", "produk premium", "paket couple treatment"]',
             ""),
            
            ("Fitness Center", 
             "Gym lengkap dengan peralatan modern dan pelatih bersertifikat untuk menjaga kebugaran selama menginap.",
             "fas fa-dumbbell", 
             "static/images/venues/gym.jpg",
             "24 Hours", 
             True, 
             "gym", 
             0,
             0,
             15,
             "150m²", 
             '["Cardio Machines", "Weight Training", "Free Weights", "Yoga Studio", "Personal Trainer", "Water Station", "Towel Service"]',
             "per_person", 
             1,
             1,
             "Lantai 3 - West Wing", 
             "Fitness Manager", 
             "+62 811-3344-5566",
             '["24/7 access untuk hotel guest", "kelas grup harian", "health monitoring"]',
             ""),
            
            # DINING & RESTAURANTS
            ("Aura Fine Dining Restaurant", 
             "Restoran fine dining dengan menu internasional dan pemandangan kota yang spektakuler.",
             "fas fa-utensils", 
             "static/images/venues/dining.jpg",
             "18:00 - 23:00", 
             True, 
             "restaurant", 
             0,
             0,
             100,
             "400m²", 
             '["Live Cooking Station", "Wine Cellar", "Private Dining Room", "Chefs Table", "Outdoor Terrace", "Piano Lounge"]',
             "per_person", 
             2,
             30,
             "Lantai 5 - Rooftop", 
             "Restaurant Manager", 
             "+62 812-5566-7788",
             '["Dress code berlaku", "reservations recommended", "wine pairing available"]',
             ""),
            
            ("Zen Garden Cafe", 
             "Kafe all-day dining dengan konsep garden untuk sarapan, makan siang, dan coffee break yang nyaman.",
             "fas fa-coffee", 
             "static/images/venues/cafe.jpg",
             "06:00 - 23:00", 
             True, 
             "restaurant", 
             0,
             0,
             80,
             "250m²", 
             '["Buffet Station", "Pastry Corner", "Coffee Bar", "Outdoor Seating", "Free WiFi", "Power Outlets"]',
             "per_person", 
             1,
             14,
             "Lantai 1 - Garden Area", 
             "Cafe Supervisor", 
             "+62 813-4455-6677",
             '["Breakfast buffet 06:00-10:30", "live music weekend", "kids corner"]',
             ""),
            
            ("Sky Bar & Lounge", 
             "Rooftop bar dengan cocktail kreatif dan pemandangan 360 derajat kota Yogyakarta.",
             "fas fa-glass-cheers", 
             "static/images/venues/bar.jpg",
             "16:00 - 01:00", 
             True, 
             "restaurant", 
             0,
             0,
             60,
             "180m²", 
             '["Cocktail Bar", "Live Music", "DJ Booth", "Smoking Area", "VIP Section", "Fire Pit"]',
             "per_person", 
             1,
             7,
             "Rooftop - North Wing", 
             "Bar Manager", 
             "+62 811-6677-8899",
             '["Age 21+", "dress code smart casual", "happy hour 17:00-19:00"]',
             ""),
            
            # BUSINESS FACILITIES
            ("Business Center", 
             "Fasilitas bisnis lengkap untuk para profesional yang membutuhkan akses kerja selama perjalanan.",
             "fas fa-business-time", 
             "static/images/venues/business.jpg",
             "08:00 - 20:00", 
             True, 
             "business_center", 
             0,
             0,
             20,
             "100m²", 
             '["Computer Workstations", "Printer/Scanner/Fax", "Conference Phone", "Private Booths", "Secretarial Service", "High-Speed WiFi"]',
             "hourly", 
             1,
             1,
             "Lantai 2 - Main Lobby", 
             "Business Center Manager", 
             "+62 812-7788-9900",
             '["Gratis untuk hotel guest", "printing limited free pages", "meeting room booking available"]',
             "")
        ]
        
        for venue in venues_data:
            cursor.execute("""
                INSERT INTO venues (name, description, icon_class, image_url, opening_hours, is_available,
                                  type, price_per_hour, price_per_day, capacity, size, amenities,
                                  booking_type, min_booking_hours, max_advance_days, location, contact_person, contact_phone, features, notes) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, venue)
        
        # 4. DATA BOOKINGS (Sample Bookings)
        print("Menambahkan data bookings...")
        
        cursor.execute("SELECT id FROM users LIMIT 3")
        user_ids = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT id FROM rooms WHERE room_type = 'hotel_room' LIMIT 3")
        room_ids = [row[0] for row in cursor.fetchall()]
        
        bookings_data = [
            ("BK-202401-001", user_ids[0], room_ids[0], "2024-03-15", "2024-03-18", 2, 1500000, 
             1304347.83, 130434.78, 65217.39, "Mohon tambahkan extra bed", "confirmed", 
             None, "paid", "Fernanda Brian", "fernanda@xyz.com", "081234567890", "Indonesia"),
            
            ("BK-202401-002", user_ids[1], room_ids[1], "2024-03-20", "2024-03-22", 1, 1600000, 
             1391304.35, 139130.43, 69565.22, "Saya vegetarian", "waiting_payment", 
             None, "pending", "Egacor Arda", "arda@xyz.com", "081298765432", "Indonesia"),
            
            ("BK-202401-003", user_ids[2], room_ids[2], "2024-04-01", "2024-04-05", 4, 6000000, 
             5217391.30, 521739.13, 260869.57, "Membawa anak-anak", "pending", 
             None, "pending", "Ajixx Suep", "ajizz@xyz.com", "081112223333", "Indonesia")
        ]
        
        for booking in bookings_data:
            cursor.execute("""
                INSERT INTO bookings (booking_code, user_id, room_id, check_in, check_out, guests, total_price, 
                                     subtotal, tax_amount, service_charge, special_requests, status, 
                                     admin_notes, payment_status, guest_name, guest_email, guest_phone, guest_country) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, booking)
        
        # 5. DATA PAYMENTS (Sample Payments)
        print("Menambahkan data payments...")
        
        # Ambil booking_id dari data yang sudah dimasukkan
        cursor.execute("SELECT id FROM bookings LIMIT 3")
        booking_ids = [row[0] for row in cursor.fetchall()]
        
        payments_data = [
            (booking_ids[0], None, 1500000, "bank_transfer", "completed", 
             "static/images/payments/proof1.jpg", "2024-03-10 14:30:00", "2024-03-11 14:30:00", "Pembayaran diterima"),
            
            (booking_ids[1], None, 1600000, "qris", "pending", 
             None, None, "2024-03-20 23:59:59", "Menunggu pembayaran"),
        ]
        
        for payment in payments_data:
            cursor.execute("""
                INSERT INTO payments (booking_id, facility_booking_id, amount, payment_method, status, 
                                     proof_image, payment_date, expiration_date, admin_notes) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, payment)
        
        # 6. DATA CONTACT INQUIRIES
        print("Menambahkan data contact inquiries...")
        inquiries_data = [
            ("Alice Johnson", "alice@example.com", "081556677889", 
             "Apakah ada promo untuk menginap di akhir pekan? Saya tertarik untuk booking 2 malam.", "new"),
            
            ("Charlie Brown", "charlie@example.com", "081667788990", 
             "Saya ingin booking meeting room untuk 15 orang pada tanggal 25 Maret 2024. Apakah tersedia?", "read"),
            
            ("David Wilson", "david@example.com", "081778899001", 
             "Untuk reservasi restaurant, apakah perlu booking sebelumnya atau bisa walk-in?", "replied")
        ]
        
        for inquiry in inquiries_data:
            cursor.execute("""
                INSERT INTO contact_inquiries (name, email, phone, message, status) 
                VALUES (%s, %s, %s, %s, %s)
            """, inquiry)
        
        connection.commit()
        print("\n" + "=" * 50)
        print("✅ SEMUA DATA CONTOH BERHASIL DITAMBAHKAN!")
        print("=" * 50)
        return True
        
    except Error as e:
        print(f"❌ Error saat menambahkan data: {e}")
        print(f"SQL State: {e.sqlstate}")
        print(f"Error Number: {e.errno}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()

def verify_database():
    """Verifikasi struktur database dan data"""
    connection = create_connection()
    if connection is None:
        return
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        print("\n" + "=" * 50)
        print("VERIFIKASI DATABASE")
        print("=" * 50)
        
        # Cek tabel
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"📊 Jumlah tabel: {len(tables)}")
        for table in tables:
            print(f"  - {list(table.values())[0]}")
        
        # Cek jumlah data per tabel
        table_counts = {
            'users': 'Users',
            'rooms': 'Rooms',
            'bookings': 'Bookings',
            'payments': 'Payments',
            'venues': '📍 Venues',
            'contact_inquiries': 'Contact Inquiries'
        }
        
        for table, label in table_counts.items():
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            print(f"{label}: {count} records")
        
        print("\n✅ Database siap digunakan!")
        
    except Error as e:
        print(f"❌ Error verifikasi: {e}")
    finally:
        cursor.close()
        connection.close()

def main():
    """Fungsi utama"""
    print("=" * 60)
    print("SETUP DATABASE FEIZEN HAVEN - MySQLdb VERSION")
    print("=" * 60)
    
    # 1. Membuat tabel
    if not create_tables():
        print("Gagal membuat tabel. Proses dihentikan.")
        return
    
    # 2. Tanya apakah mau insert sample data
    print("\n" + "-" * 50)
    add_sample = input("Tambahkan data contoh? (y/n): ").lower().strip()
    
    if add_sample == 'y' or add_sample == '':
        if insert_sample_data():
            # 3. Verifikasi database
            verify_database()
        else:
            print("Gagal menambahkan data contoh.")
    else:
        print("ℹData contoh tidak ditambahkan.")
        verify_database()
    
    print("\n" + "=" * 60)
    print("SETUP DATABASE SELESAI!")
    print("=" * 60)


if __name__ == "__main__":
    main()
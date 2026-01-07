# Feizen Haven Hotel Booking System

A comprehensive hotel booking system built with Python Flask featuring room booking, user management, admin dashboard, and payment processing.

## 📁 Project Structure
FEIZEN_HAVEN/
│
├── .gitignore                  # Ignore env, cache, uploads
├── README.md                   # Project documentation
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
│
├── app.py                      # Main Flask application
├── config.py                   # Application configuration
├── extensions.py               # Flask extensions initialization
├── helpers.py                  # Utility helper functions
├── models.py                   # Database models (SQLAlchemy)
├── database_models.py          # Additional database models
├── setup_database.py           # Database setup & seeding
│
├── routes/                     # Flask Blueprints
│   ├── __init__.py
│   ├── admin_routes.py         # Admin management routes
│   ├── api_routes.py           # REST API endpoints
│   ├── auth_routes.py          # Authentication routes
│   ├── booking_routes.py       # Booking routes
│   ├── main_routes.py          # Main website routes
│   └── user_routes.py          # User profile routes
│
├── templates/                  # Jinja2 templates
│   ├── base.html               # Base layout
│   │
│   ├── admin/                  # Admin panel pages
│   │   ├── dashboard.html
│   │   ├── bookings.html
│   │   ├── manage_rooms.html
│   │   ├── add_room.html
│   │   ├── edit_room.html
│   │   ├── payments.html
│   │   ├── rooms.html
│   │   ├── users.html
│   │   ├── create_user.html
│   │   └── user_profile.html
│   │
│   ├── auth/                   # Authentication pages
│   │   ├── login.html
│   │   └── register.html
│   │
│   ├── booking/                # Booking process pages
│   │   ├── book.html
│   │   ├── payment.html
│   │   └── success.html
│   │
│   ├── main/                   # Public website pages
│   │   ├── index.html
│   │   ├── about.html
│   │   ├── contact.html
│   │   ├── rooms.html
│   │   ├── venues.html
│   │   └── contact_support.html
│   │
│   └── user/                   # User dashboard pages
│       ├── profile.html
│       └── bookings.html
│
├── static/                     # Static assets
│   ├── css/
│   │   ├── style.css
│   │   └── booking.css
│   │
│   ├── js/
│   │   ├── main.js
│   │   ├── index.js
│   │   └── book.js
│   │
│   ├── images/
│   │   ├── rooms/
│   │   │   ├── deluxe.jpg
│   │   │   ├── executive.jpg
│   │   │   ├── presidential.jpg
│   │   │   └── default.jpg
│   │   │
│   │   ├── venues/
│   │   │   ├── venue1.jpg
│   │   │   ├── venue2.jpg
│   │   │   └── venue3.jpg
│   │   │
│   │   ├── payment/
│   │   │   ├── qris.png
│   │   │   ├── bank-transfer.png
│   │   │   └── credit-card.png
│   │   │
│   │   └── icons/
│   │       ├── favicon.ico
│   │       └── logo.png
│
└── uploads/                    # User uploads (ignored by Git)
    ├── payments/
    └── rooms/

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/feizen-haven-hotel.git
   cd feizen-haven-hotel
Create virtual environment


python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
Install dependencies

pip install -r requirements.txt
Configure environment variables

# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# nano .env  # or use your favorite editor
Initialize the database

python setup_database.py
Run the application


# Development mode
python app.py

# Or using Flask CLI
flask run
The application will be available at http://localhost:5000

⚙️ Configuration
Environment Variables (.env)
Create a .env file with the following variables:

# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-this-in-production
DATABASE_URL=sqlite:///hotel.db
DEBUG=True

# Optional: Database (for production)
# DATABASE_URL=postgresql://user:password@localhost/hotel_db

# Optional: Email Configuration
# MAIL_SERVER=smtp.gmail.com
# MAIL_PORT=587
# MAIL_USE_TLS=True
# MAIL_USERNAME=your-email@gmail.com
# MAIL_PASSWORD=your-password

# Optional: Payment Gateway
# STRIPE_SECRET_KEY=sk_test_...
# STRIPE_PUBLISHABLE_KEY=pk_test_...
📋 Features
User Features
✅ User registration and authentication
✅ Browse available rooms and venues
✅ Room booking with date selection
✅ Multiple payment methods (QRIS, Bank Transfer, Credit Card)
✅ Booking history and management
✅ User profile management

Admin Features
✅ Admin dashboard with statistics
✅ Room management (add, edit, delete)
✅ Booking management and approval
✅ User management
✅ Payment verification
✅ Revenue reporting

System Features
✅ Responsive web design
✅ Secure authentication
✅ Database management
✅ File upload handling
✅ Email notifications (optional)
✅ REST API endpoints

🛠️ Technologies Used
Backend: Python, Flask, SQLAlchemy
Frontend: HTML5, CSS3, JavaScript, Jinja2 Templates
Database: SQLite (development), PostgreSQL (production ready)
Authentication: Flask-Login, Werkzeug Security
Forms: Flask-WTF, WTForms
File Handling: Flask-Uploads (optional)
Styling: Custom CSS, Bootstrap (recommended)

📊 Database Schema
Key Models:
User: Customers and administrators
Room: Room types and details
Booking: Reservation records
Payment: Transaction records
Venue: Event venues

🔧 Development
Running in Development Mode

export FLASK_ENV=development
export FLASK_DEBUG=1
flask run
Creating Database Migrations

# If using Flask-Migrate
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
Testing

# Run tests
python -m pytest

# With coverage
python -m pytest --cov=app tests/

📁 File Uploads
The system supports file uploads for:
Payment proof images
Room images
User profile pictures

Uploaded files are stored in:
uploads/payments/ - Payment proofs (git-ignored)
static/images/rooms/ - Room images (git-kept)
static/images/venues/ - Venue images (git-kept)

🔒 Security Notes
Never commit sensitive data to version control
Always use environment variables for secrets
Keep .env in .gitignore
Use strong passwords and API keys
Enable HTTPS in production

🤝 Contributing
Fork the repository
Create a feature branch (git checkout -b feature/AmazingFeature)
Commit your changes (git commit -m 'Add some AmazingFeature')
Push to the branch (git push origin feature/AmazingFeature)
Open a Pull Request

📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

👥 Authors
FeizenFernanda - Initial work

🙏 Acknowledgments
Flask documentation and community
All contributors and testers


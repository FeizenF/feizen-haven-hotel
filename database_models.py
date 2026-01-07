from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('user', 'admin'), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    bookings = db.relationship('Booking', backref='user', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False) 
    size = db.Column(db.String(20))
    capacity = db.Column(db.Integer, default=2)
    view_type = db.Column(db.String(50))
    amenities = db.Column(db.Text)
    images = db.Column(db.Text)
    is_available = db.Column(db.Integer, default=1)
    room_count = db.Column(db.Integer, default=1)
    room_type = db.Column(db.Enum('hotel_room', 'meeting_room', 'facility', 'restaurant', 'spa'), default='hotel_room')
    available_count = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bookings = db.relationship('Booking', backref='room', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Room {self.name}>'
    
    @property
    def is_active(self):
        return bool(self.is_available)
    
    @property
    def images_list(self):
        import json
        if self.images:
            try:
                return json.loads(self.images)
            except:
                return [img.strip() for img in self.images.split(',') if img.strip()]
        return []
    
    @property
    def amenities_list(self):
        import json
        if self.amenities:
            try:
                return json.loads(self.amenities)
            except:
                return [amenity.strip() for amenity in self.amenities.split(',') if amenity.strip()]
        return []
    
    @property
    def formatted_price(self):
        """Format price for display"""
        return f"Rp{self.price:,.0f}".replace(',', '.')
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price) if self.price else 0,
            'size': self.size,
            'capacity': self.capacity,
            'view_type': self.view_type,
            'amenities': self.amenities,
            'images': self.images,
            'is_available': bool(self.is_available),
            'room_count': self.room_count,
            'room_type': self.room_type,
            'available_count': self.available_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_code = db.Column(db.String(20), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    guests = db.Column(db.Integer, default=2)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), default=0.00)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00)
    service_charge = db.Column(db.Numeric(10, 2), default=0.00)
    special_requests = db.Column(db.Text)
    status = db.Column(db.Enum('pending', 'waiting_payment', 'confirmed', 'cancelled', 'completed'), default='pending')
    admin_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    payment_status = db.Column(db.Enum('pending', 'waiting_payment', 'paid', 'failed'), default='pending')
    guest_name = db.Column(db.String(255))
    guest_email = db.Column(db.String(255))
    guest_phone = db.Column(db.String(20))
    guest_country = db.Column(db.String(100))
    
    payment = db.relationship('Payment', backref='booking', uselist=False, foreign_keys=[payment_id])
    
    def __repr__(self):
        return f'<Booking {self.booking_code}>'
    
    @property
    def nights(self):
        if self.check_in and self.check_out:
            return (self.check_out - self.check_in).days
        return 0
    
    @property
    def is_expired(self):
        if self.status == 'waiting_payment' and self.created_at:
            from datetime import timedelta
            expiry_time = self.created_at + timedelta(hours=24)
            return datetime.utcnow() > expiry_time
        return False
    
    @property
    def formatted_price(self):
        """Format total price for display"""
        return f"Rp{self.total_price:,.0f}".replace(',', '.')
    
    @property
    def price_breakdown(self):
        """Return price breakdown dictionary"""
        return {
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'tax_amount': float(self.tax_amount) if self.tax_amount else 0,
            'service_charge': float(self.service_charge) if self.service_charge else 0,
            'total': float(self.total_price) if self.total_price else 0
        }
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'booking_code': self.booking_code,
            'user_id': self.user_id,
            'room_id': self.room_id,
            'check_in': self.check_in.isoformat() if self.check_in else None,
            'check_out': self.check_out.isoformat() if self.check_out else None,
            'guests': self.guests,
            'total_price': float(self.total_price) if self.total_price else 0,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'tax_amount': float(self.tax_amount) if self.tax_amount else 0,
            'service_charge': float(self.service_charge) if self.service_charge else 0,
            'nights': self.nights,
            'status': self.status,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    facility_booking_id = db.Column(db.Integer, nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.Enum('qris', 'bank_transfer', 'credit_card', 'ovo', 'gopay', 'dana'), nullable=False)
    status = db.Column(db.Enum('pending', 'processing', 'completed', 'failed', 'expired'), default='pending')
    proof_image = db.Column(db.String(255))
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiration_date = db.Column(db.DateTime)
    admin_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payment {self.id} - {self.status}>'
    
    @property
    def is_expired(self):
        if self.expiration_date:
            return datetime.utcnow() > self.expiration_date
        return False
    
    @property
    def formatted_amount(self):
        """Format amount for display"""
        return f"Rp{self.amount:,.0f}".replace(',', '.')
    
    @property
    def payment_method_display(self):
        """Get display name for payment method"""
        display_names = {
            'qris': 'QRIS',
            'bank_transfer': 'Bank Transfer',
            'credit_card': 'Credit Card',
            'ovo': 'OVO',
            'gopay': 'GoPay',
            'dana': 'DANA'
        }
        return display_names.get(self.payment_method, self.payment_method)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'amount': float(self.amount) if self.amount else 0,
            'payment_method': self.payment_method,
            'payment_method_display': self.payment_method_display,
            'status': self.status,
            'proof_image': self.proof_image,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Venue(db.Model):
    __tablename__ = 'venues'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon_class = db.Column(db.String(50))
    image_url = db.Column(db.String(255))
    opening_hours = db.Column(db.String(100))
    is_available = db.Column(db.Boolean, default=True)
    type = db.Column(db.Enum('meeting_room', 'restaurant', 'spa', 'pool', 'gym', 'business_center', 'event_space', 'other'), default='other')
    price_per_hour = db.Column(db.Numeric(10, 2), default=0.00)
    price_per_day = db.Column(db.Numeric(10, 2), default=0.00)
    capacity = db.Column(db.Integer, default=10)
    size = db.Column(db.String(50))
    amenities = db.Column(db.Text)
    booking_type = db.Column(db.Enum('hourly', 'daily', 'per_person', 'package'), default='hourly')
    min_booking_hours = db.Column(db.Integer, default=1)
    max_advance_days = db.Column(db.Integer, default=30)
    location = db.Column(db.String(100))
    contact_person = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))
    features = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Venue {self.name}>'
    
    @property
    def amenities_list(self):
        import json
        if self.amenities:
            try:
                return json.loads(self.amenities)
            except:
                return [amenity.strip() for amenity in self.amenities.split(',') if amenity.strip()]
        return []
    
    @property
    def features_list(self):
        import json
        if self.features:
            try:
                return json.loads(self.features)
            except:
                return [feature.strip() for feature in self.features.split(',') if feature.strip()]
        return []
    
    @property
    def formatted_price_per_hour(self):
        """Format price per hour for display"""
        return f"Rp{self.price_per_hour:,.0f}/hour".replace(',', '.') if self.price_per_hour else "Free"
    
    @property
    def formatted_price_per_day(self):
        """Format price per day for display"""
        return f"Rp{self.price_per_day:,.0f}/day".replace(',', '.') if self.price_per_day else "Free"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'image_url': self.image_url,
            'opening_hours': self.opening_hours,
            'is_available': self.is_available,
            'type': self.type,
            'price_per_hour': float(self.price_per_hour) if self.price_per_hour else 0,
            'price_per_day': float(self.price_per_day) if self.price_per_day else 0,
            'capacity': self.capacity,
            'size': self.size,
            'amenities': self.amenities,
            'booking_type': self.booking_type,
            'location': self.location,
            'contact_person': self.contact_person,
            'contact_phone': self.contact_phone
        }

class ContactInquiry(db.Model):
    __tablename__ = 'contact_inquiries'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum('new', 'read', 'replied'), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ContactInquiry {self.name}>'
    
    @property
    def status_display(self):
        """Get display name for status"""
        display_names = {
            'new': 'New',
            'read': 'Read',
            'replied': 'Replied'
        }
        return display_names.get(self.status, self.status)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'message': self.message,
            'status': self.status,
            'status_display': self.status_display,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

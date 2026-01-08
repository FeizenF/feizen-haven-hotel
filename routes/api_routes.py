from flask import jsonify, send_file, url_for, session, make_response, request, g
from config import app, mysql, csrf
from models import login_required, admin_required
from werkzeug.security import check_password_hash
import os
import json
from datetime import datetime, timedelta
import uuid

# =============== HELPER FUNCTIONS ===============
def format_datetime(value):
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value

# =============== PUBLIC API ROUTES ===============
@app.route('/api/room/<int:room_id>/details')
def room_details_api(room_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id, name, description, size, capacity, price, 
                   available_count, room_count, view_type, room_type,
                   amenities, images, is_available
            FROM rooms WHERE id = %s
        """, (room_id,))
        room = cur.fetchone()
        cur.close()
        
        if not room:
            return jsonify({'success': False, 'error': 'Room not found', 'code': 404}), 404

        images = []
        if room['images']:
            try:
                if isinstance(room['images'], str):
                    try:
                        images = json.loads(room['images'])
                    except:
                        images = [img.strip() for img in room['images'].split(',') if img.strip()]
            except:
                images = []
        
        amenities = []
        if room['amenities']:
            if isinstance(room['amenities'], str):
                try:
                    amenities = json.loads(room['amenities'])
                except:
                    amenities = [a.strip() for a in room['amenities'].split(',') if a.strip()]
        
        return jsonify({
            'success': True,
            'data': {
                'id': room['id'],
                'name': room['name'],
                'description': room['description'],
                'size': room['size'],
                'capacity': room['capacity'],
                'price': float(room['price']),
                'available_count': room['available_count'],
                'room_count': room['room_count'],
                'view_type': room['view_type'],
                'room_type': room['room_type'],
                'is_available': bool(room['is_available']),
                'amenities': amenities,
                'images': images
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}', 'code': 500}), 500

@app.route('/api/rooms')
def rooms_list_api():
    try:
        room_type = request.args.get('type')
        min_price = request.args.get('min_price')
        max_price = request.args.get('max_price')
        capacity = request.args.get('capacity')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        cur = mysql.connection.cursor()
        query = """
            SELECT id, name, description, price, capacity, size, 
                   available_count, room_count, view_type, room_type,
                   amenities, images, is_available
            FROM rooms WHERE is_available = 1 AND available_count > 0
        """
        params = []
        
        if room_type:
            query += " AND room_type = %s"
            params.append(room_type)
        if min_price:
            query += " AND price >= %s"
            params.append(float(min_price))
        if max_price:
            query += " AND price <= %s"
            params.append(float(max_price))
        if capacity:
            query += " AND capacity >= %s"
            params.append(int(capacity))
        
        count_query = f"SELECT COUNT(*) as total FROM ({query}) as filtered"
        cur.execute(count_query, tuple(params))
        total_count = cur.fetchone()['total']
        
        query += " ORDER BY price ASC LIMIT %s OFFSET %s"
        offset = (page - 1) * per_page
        params.extend([per_page, offset])
        cur.execute(query, tuple(params))
        rooms = cur.fetchall()
        cur.close()
        
        processed_rooms = []
        for room in rooms:
            room_data = dict(room)
            
            images = []
            if room_data['images']:
                try:
                    if isinstance(room_data['images'], str):
                        try:
                            images = json.loads(room_data['images'])
                        except:
                            images = [img.strip() for img in room_data['images'].split(',') if img.strip()]
                except:
                    images = []
            
            room_data['images'] = images
            room_data['price'] = float(room_data['price'])
            room_data['is_available'] = bool(room_data['is_available'])
            processed_rooms.append(room_data)
        
        return jsonify({
            'success': True,
            'data': {
                'rooms': processed_rooms,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                }
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}', 'code': 500}), 500

@app.route('/api/check-availability')
def check_availability_api():
    try:
        room_id = request.args.get('room_id')
        check_in = request.args.get('check_in')
        check_out = request.args.get('check_out')
        
        if not all([room_id, check_in, check_out]):
            return jsonify({'success': False, 'error': 'Missing required parameters', 'code': 400}), 400
        
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id, name, available_count, room_count, price, capacity
            FROM rooms WHERE id = %s AND is_available = 1
        """, (room_id,))
        room = cur.fetchone()
        
        if not room:
            return jsonify({'success': False, 'error': 'Room not available', 'code': 404}), 404
        
        cur.execute("""
            SELECT COUNT(*) as overlapping_bookings
            FROM bookings 
            WHERE room_id = %s 
            AND status IN ('confirmed', 'pending', 'waiting_payment')
            AND (
                (check_in <= %s AND check_out >= %s) OR
                (check_in <= %s AND check_out >= %s) OR
                (check_in >= %s AND check_out <= %s)
            )
        """, (room_id, check_out, check_in, check_in, check_out, check_in, check_out))
        
        overlap_result = cur.fetchone()
        overlapping_bookings = overlap_result['overlapping_bookings'] if overlap_result else 0
        cur.close()
        
        available_count = room['available_count']
        is_available = available_count > overlapping_bookings
        
        return jsonify({
            'success': True,
            'data': {
                'room_id': room['id'],
                'room_name': room['name'],
                'is_available': is_available,
                'available_count': available_count,
                'overlapping_bookings': overlapping_bookings,
                'max_capacity': room['capacity'],
                'price_per_night': float(room['price'])
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}', 'code': 500}), 500

# =============== AUTH API ROUTES ===============
@app.route('/api/login', methods=['POST'])
@csrf.exempt
def api_login():
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json', 'code': 400}), 400
        
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required', 'code': 400}), 400
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        
        if not user:
            return jsonify({'success': False, 'error': 'Invalid email or password', 'code': 401}), 401
        
        if not check_password_hash(user['password'], password):
            return jsonify({'success': False, 'error': 'Invalid email or password', 'code': 401}), 401
        
        session_id = str(uuid.uuid4())
        session['user_id'] = user['id']
        session['email'] = user['email']
        session['name'] = f"{user['first_name']} {user['last_name']}"
        session['role'] = user['role']
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': f"{user['first_name']} {user['last_name']}",
                'role': user['role'],
                'phone': user.get('phone', '')
            },
            'session': {
                'session_id': session_id,
                'expires_in': 3600,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}', 'code': 500}), 500

@app.route('/api/logout', methods=['POST'])
@csrf.exempt
def api_logout():
    try:
        session.clear()
        return jsonify({'success': True, 'message': 'Logout successful'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 500}), 500

# =============== USER API ROUTES ===============
@app.route('/api/user/profile')
@login_required
def user_profile_api():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated', 'code': 401}), 401
        
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id, first_name, last_name, email, phone, role, created_at
            FROM users WHERE id = %s
        """, (user_id,))
        user = cur.fetchone()
        cur.close()
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found', 'code': 404}), 404
        
        user_data = dict(user)
        if user_data.get('created_at'):
            user_data['created_at'] = format_datetime(user_data['created_at'])
        
        return jsonify({'success': True, 'data': user_data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 500}), 500
@app.route('/api/user/profile', methods=['PUT'])
@login_required
@csrf.exempt
def update_user_profile():
    """Update user profile"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated', 'code': 401}), 401
        
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json', 'code': 400}), 400
        
        data = request.get_json()
        
        # Validasi field yang boleh diupdate
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        phone = data.get('phone')
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        cur = mysql.connection.cursor()
        
        # Jika ingin ganti password
        if new_password:
            if not current_password:
                return jsonify({'success': False, 'error': 'Current password required to change password', 'code': 400}), 400
            
            if new_password != confirm_password:
                return jsonify({'success': False, 'error': 'New password and confirmation do not match', 'code': 400}), 400
            
            if len(new_password) < 6:
                return jsonify({'success': False, 'error': 'Password must be at least 6 characters', 'code': 400}), 400
            
            # Verifikasi password lama
            cur.execute("SELECT password FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            
            if not check_password_hash(user['password'], current_password):
                return jsonify({'success': False, 'error': 'Current password is incorrect', 'code': 400}), 400
            
            # Hash password baru
            from werkzeug.security import generate_password_hash
            hashed_password = generate_password_hash(new_password)
            
            # Update dengan password baru
            cur.execute("""
                UPDATE users 
                SET first_name = COALESCE(%s, first_name),
                    last_name = COALESCE(%s, last_name),
                    phone = COALESCE(%s, phone),
                    password = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                first_name if first_name is not None else None,
                last_name if last_name is not None else None,
                phone if phone is not None else None,
                hashed_password,
                user_id
            ))
        else:
            # Update tanpa ganti password
            cur.execute("""
                UPDATE users 
                SET first_name = COALESCE(%s, first_name),
                    last_name = COALESCE(%s, last_name),
                    phone = COALESCE(%s, phone),
                    updated_at = NOW()
                WHERE id = %s
            """, (
                first_name if first_name is not None else None,
                last_name if last_name is not None else None,
                phone if phone is not None else None,
                user_id
            ))
        
        mysql.connection.commit()
        
        # Ambil data terbaru
        cur.execute("""
            SELECT id, first_name, last_name, email, phone, role, created_at, updated_at
            FROM users WHERE id = %s
        """, (user_id,))
        updated_user = cur.fetchone()
        cur.close()
        
        user_data = dict(updated_user)
        for date_field in ['created_at', 'updated_at']:
            if user_data.get(date_field):
                user_data[date_field] = format_datetime(user_data[date_field])
        
        # Update session name jika nama berubah
        if first_name or last_name:
            session['name'] = f"{user_data['first_name']} {user_data['last_name']}"
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'data': user_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 500}), 500
    
@app.route('/api/user/bookings')
@login_required
def user_bookings_api():
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT b.*, r.name as room_name
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            WHERE b.user_id = %s
            ORDER BY b.created_at DESC
        """, (session['user_id'],))
        bookings = cur.fetchall()
        cur.close()
        
        processed_bookings = []
        for booking in bookings:
            booking_data = dict(booking)
            
            for date_field in ['check_in', 'check_out', 'created_at']:
                if booking_data.get(date_field):
                    booking_data[date_field] = format_datetime(booking_data[date_field])
            
            if booking_data.get('total_price'):
                booking_data['total_price'] = float(booking_data['total_price'])
            
            processed_bookings.append(booking_data)
        
        return jsonify({'success': True, 'data': processed_bookings})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 500}), 500

@app.route('/api/user/booking/<int:booking_id>')
@login_required
def user_booking_detail_api(booking_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT b.*, r.name as room_name, r.description as room_description,
                   r.capacity as room_capacity, r.images as room_images,
                   p.status as payment_status
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            LEFT JOIN payments p ON b.id = p.booking_id
            WHERE b.id = %s AND b.user_id = %s
        """, (booking_id, session['user_id']))
        booking = cur.fetchone()
        cur.close()
        
        if not booking:
            return jsonify({'success': False, 'error': 'Booking not found', 'code': 404}), 404
        
        booking_data = dict(booking)
        
        for date_field in ['check_in', 'check_out', 'created_at']:
            if booking_data.get(date_field):
                booking_data[date_field] = format_datetime(booking_data[date_field])
        
        price_fields = ['total_price', 'subtotal', 'tax_amount', 'service_charge']
        for field in price_fields:
            if booking_data.get(field):
                booking_data[field] = float(booking_data[field])
        
        return jsonify({'success': True, 'data': booking_data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 500}), 500

@app.route('/api/user/create-booking', methods=['POST'])
@login_required
@csrf.exempt
def create_booking_api():
    try:
        data = request.get_json()
        required_fields = ['room_id', 'check_in', 'check_out', 'guests']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}', 'code': 400}), 400
        
        room_id = data['room_id']
        check_in = data['check_in']
        check_out = data['check_out']
        guests = int(data['guests'])
        special_requests = data.get('special_requests', '')
        
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT * FROM rooms 
            WHERE id = %s AND is_available = 1 AND available_count > 0
        """, (room_id,))
        room = cur.fetchone()
        
        if not room:
            return jsonify({'success': False, 'error': 'Room not available', 'code': 400}), 400
        
        if guests > room['capacity']:
            return jsonify({'success': False, 'error': f'Maximum capacity is {room["capacity"]}', 'code': 400}), 400
        
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
        nights = (check_out_date - check_in_date).days
        
        room_price = float(room['price'])
        subtotal = room_price * nights
        tax_amount = subtotal * 0.10
        service_charge = subtotal * 0.11
        total_price = subtotal + tax_amount + service_charge
        
        import random, string
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        numbers = ''.join(random.choices(string.digits, k=6))
        booking_code = f"FH-{letters}-{numbers}"
        
        cur.execute("START TRANSACTION")
        try:
            cur.execute("""
                INSERT INTO bookings 
                (user_id, room_id, check_in, check_out, guests, 
                total_price, subtotal, tax_amount, service_charge, 
                special_requests, status, booking_code)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'waiting_payment', %s)
            """, (session['user_id'], room_id, check_in, check_out, guests,
                  total_price, subtotal, tax_amount, service_charge, 
                  special_requests, booking_code))
            
            booking_id = cur.lastrowid
            
            new_available = room['available_count'] - 1
            cur.execute("""
                UPDATE rooms 
                SET available_count = %s,
                    is_available = CASE WHEN %s > 0 THEN 1 ELSE 0 END
                WHERE id = %s
            """, (new_available, new_available, room_id))
            
            expiration_date = datetime.now() + timedelta(hours=24)
            cur.execute("""
                INSERT INTO payments 
                (booking_id, amount, payment_method, status, expiration_date)
                VALUES (%s, %s, 'pending', 'pending', %s)
            """, (booking_id, total_price, expiration_date))
            
            cur.execute("COMMIT")
            
            return jsonify({
                'success': True,
                'data': {
                    'booking_id': booking_id,
                    'booking_code': booking_code,
                    'total_price': total_price,
                    'status': 'waiting_payment'
                }
            })
            
        except Exception as e:
            cur.execute("ROLLBACK")
            raise e
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 500}), 500
    finally:
        cur.close()
@app.route('/api/user/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
@csrf.exempt
def cancel_user_booking(booking_id):
    """User cancels their own booking"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated', 'code': 401}), 401
        
        data = request.get_json(silent=True) or {}
        cancellation_reason = data.get('cancellation_reason', '')
        
        cur = mysql.connection.cursor()
        
        # 1. Cek booking exists dan milik user
        cur.execute("""
            SELECT b.*, r.available_count, r.room_count
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            WHERE b.id = %s AND b.user_id = %s
        """, (booking_id, user_id))
        
        booking = cur.fetchone()
        
        if not booking:
            return jsonify({'success': False, 'error': 'Booking not found', 'code': 404}), 404
        
        # 2. Cek apakah bisa dicancel
        current_status = booking['status']
        if current_status in ['cancelled', 'completed']:
            return jsonify({
                'success': False, 
                'error': f'Booking already {current_status}',
                'code': 400
            }), 400
        
        # 3. Start transaction
        cur.execute("START TRANSACTION")
        
        try:
            # Update booking dengan kolom baru
            cur.execute("""
                UPDATE bookings 
                SET status = 'cancelled',
                    cancelled_at = NOW(),
                    cancellation_reason = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (cancellation_reason, booking_id))
            
            # Update room availability
            room_id = booking['room_id']
            new_available = booking['available_count'] + 1
            cur.execute("""
                UPDATE rooms 
                SET available_count = LEAST(room_count, %s),
                    is_available = CASE 
                        WHEN %s > 0 THEN 1 
                        ELSE 0 
                    END
                WHERE id = %s
            """, (new_available, new_available, room_id))
            
            # Update payment_status di tabel bookings
            cur.execute("""
                UPDATE bookings 
                SET payment_status = 'cancelled'
                WHERE id = %s
            """, (booking_id,))
            
            cur.execute("COMMIT")
            
            # Ambil data terbaru
            cur.execute("""
                SELECT id, booking_code, status, cancelled_at, cancellation_reason,
                       check_in, check_out, total_price
                FROM bookings WHERE id = %s
            """, (booking_id,))
            updated_booking = cur.fetchone()
            cur.close()
            
            # Format response
            response_data = dict(updated_booking)
            for date_field in ['check_in', 'check_out', 'cancelled_at']:
                if response_data.get(date_field):
                    response_data[date_field] = format_datetime(response_data[date_field])
            
            if response_data.get('total_price'):
                response_data['total_price'] = float(response_data['total_price'])
            
            return jsonify({
                'success': True,
                'message': 'Booking cancelled successfully',
                'data': response_data
            })
            
        except Exception as e:
            cur.execute("ROLLBACK")
            raise e
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 500}), 500
    finally:
        cur.close()
        
# =============== ADMIN API ROUTES ===============
@app.route('/api/admin/bookings')
@admin_required
def admin_bookings_api():
    try:
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        cur = mysql.connection.cursor()
        query = """
            SELECT b.*, u.first_name, u.last_name, u.email, r.name as room_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN rooms r ON b.room_id = r.id
            WHERE 1=1
        """
        params = []
        
        if status and status != 'all':
            query += " AND b.status = %s"
            params.append(status)
        
        count_query = f"SELECT COUNT(*) as total FROM ({query}) as filtered"
        cur.execute(count_query, tuple(params))
        total_count = cur.fetchone()['total']
        
        query += " ORDER BY b.created_at DESC LIMIT %s OFFSET %s"
        offset = (page - 1) * per_page
        params.extend([per_page, offset])
        cur.execute(query, tuple(params))
        bookings = cur.fetchall()
        cur.close()
        
        processed_bookings = []
        for booking in bookings:
            booking_data = dict(booking)
            
            for date_field in ['check_in', 'check_out', 'created_at']:
                if booking_data.get(date_field):
                    booking_data[date_field] = format_datetime(booking_data[date_field])
            
            if booking_data.get('total_price'):
                booking_data['total_price'] = float(booking_data['total_price'])
            
            processed_bookings.append(booking_data)
        
        return jsonify({
            'success': True,
            'data': {
                'bookings': processed_bookings,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                }
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 500}), 500

@app.route('/api/admin/booking/<int:booking_id>', methods=['GET', 'PUT'])
@admin_required
def admin_booking_detail_api(booking_id):
    if request.method == 'GET':
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT b.*, u.first_name, u.last_name, u.email, u.phone,
                       r.name as room_name, r.price as room_price
                FROM bookings b
                JOIN users u ON b.user_id = u.id
                JOIN rooms r ON b.room_id = r.id
                WHERE b.id = %s
            """, (booking_id,))
            booking = cur.fetchone()
            cur.close()
            
            if not booking:
                return jsonify({'success': False, 'error': 'Booking not found', 'code': 404}), 404
            
            booking_data = dict(booking)
            
            for date_field in ['check_in', 'check_out', 'created_at']:
                if booking_data.get(date_field):
                    booking_data[date_field] = format_datetime(booking_data[date_field])
            
            if booking_data.get('total_price'):
                booking_data['total_price'] = float(booking_data['total_price'])
            if booking_data.get('room_price'):
                booking_data['room_price'] = float(booking_data['room_price'])
            
            return jsonify({'success': True, 'data': booking_data})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e), 'code': 500}), 500
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            new_status = data.get('status')
            admin_notes = data.get('admin_notes', '')
            
            if not new_status:
                return jsonify({'success': False, 'error': 'Status is required', 'code': 400}), 400
            
            valid_statuses = ['pending', 'waiting_payment', 'confirmed', 'cancelled', 'completed']
            if new_status not in valid_statuses:
                return jsonify({'success': False, 'error': f'Invalid status', 'code': 400}), 400
            
            cur = mysql.connection.cursor()
            cur.execute("SELECT room_id, status as old_status FROM bookings WHERE id = %s", (booking_id,))
            booking = cur.fetchone()
            
            if not booking:
                return jsonify({'success': False, 'error': 'Booking not found', 'code': 404}), 404
            
            cur.execute("""
                UPDATE bookings 
                SET status = %s, admin_notes = %s, updated_at = NOW()
                WHERE id = %s
            """, (new_status, admin_notes, booking_id))
            
            mysql.connection.commit()
            cur.close()
            
            return jsonify({
                'success': True,
                'message': 'Booking status updated',
                'data': {
                    'booking_id': booking_id,
                    'old_status': booking['old_status'],
                    'new_status': new_status
                }
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e), 'code': 500}), 500

# =============== HEALTH CHECK ===============
@app.route('/api/health')
def health_check():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'database': 'disconnected'
        }), 500

# =============== DEBUG ROUTES ===============
@app.route('/api/debug-csrf', methods=['GET', 'POST'])
def debug_csrf():
    return jsonify({
        'success': True,
        'method': request.method,
        'is_json': request.is_json,
        'headers': dict(request.headers)
    })

@app.route('/api/session-test', methods=['GET'])
def session_test():
    return jsonify({
        'success': True,
        'session_data': dict(session),
        'has_user': 'user_id' in session
    })
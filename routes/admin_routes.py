from flask import render_template, request, redirect, url_for, flash, session, jsonify
from config import app, mysql
from models import login_required, admin_required, allowed_file
import os
import time
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import re
from functools import wraps
from helpers import process_room_images

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ADMIN ROUTES
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    cur = mysql.connection.cursor()
    
    try:
        # Get statistics
        cur.execute("SELECT COUNT(*) as total FROM rooms")
        total_rooms = cur.fetchone()['total'] or 0
        
        cur.execute("SELECT COUNT(*) as total FROM bookings")
        total_bookings = cur.fetchone()['total'] or 0
        
        cur.execute("SELECT COUNT(*) as total FROM users")
        total_users = cur.fetchone()['total'] or 0
        
        cur.execute("SELECT SUM(total_price) as total FROM bookings WHERE status = 'completed'")
        revenue_result = cur.fetchone()
        total_revenue = revenue_result['total'] if revenue_result and revenue_result['total'] else 0
        
        # Available rooms
        cur.execute("SELECT SUM(available_count) as available FROM rooms WHERE is_available = 1")
        available_result = cur.fetchone()
        available_rooms = available_result['available'] if available_result and available_result['available'] else 0
        
        # Pending bookings count
        cur.execute("SELECT COUNT(*) as pending FROM bookings WHERE status = 'pending'")
        pending_bookings = cur.fetchone()['pending'] or 0
        
        # Today's bookings
        today = datetime.now().date()
        cur.execute("SELECT COUNT(*) as today FROM bookings WHERE DATE(created_at) = %s", (today,))
        today_bookings = cur.fetchone()['today'] or 0
        
        # Recent bookings
        cur.execute("""
            SELECT 
                b.id, b.booking_code, b.status, b.total_price, b.guests,
                b.check_in, b.check_out, b.created_at,
                r.name as room_name,
                u.first_name, u.last_name, u.email
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            LEFT JOIN users u ON b.user_id = u.id
            ORDER BY b.created_at DESC
            LIMIT 8
        """)
        recent_bookings = cur.fetchall()
        
        # Recent users
        cur.execute("""
            SELECT id, first_name, last_name, email, created_at 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        recent_users = cur.fetchall()
        
    except Exception as e:
        print(f"Error fetching dashboard data: {e}")
        total_rooms = total_bookings = total_users = total_revenue = 0
        available_rooms = pending_bookings = today_bookings = 0
        recent_bookings = []
        recent_users = []
    
    finally:
        cur.close()
    
    return render_template('admin/dashboard.html',
                         total_rooms=total_rooms,
                         total_bookings=total_bookings,
                         total_users=total_users,
                         total_revenue=total_revenue,
                         available_rooms=available_rooms,
                         pending_bookings=pending_bookings,
                         today_bookings=today_bookings,
                         recent_bookings=recent_bookings,
                         recent_users=recent_users)

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validasi
    if not current_password or not new_password or not confirm_password:
        flash('All password fields are required', 'error')
        return redirect(url_for('profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('profile'))
    
    # Check current password
    cur = mysql.connection.cursor()
    cur.execute("SELECT password FROM users WHERE id = %s", (session['user_id'],))
    user = cur.fetchone()
    
    if not check_password_hash(user['password'], current_password):
        flash('Current password is incorrect', 'error')
        cur.close()
        return redirect(url_for('profile'))
    
    # Update password
    hashed_password = generate_password_hash(new_password)
    cur.execute("UPDATE users SET password = %s WHERE id = %s", 
                (hashed_password, session['user_id']))
    
    mysql.connection.commit()
    cur.close()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/admin/bookings')
@login_required
@admin_required
def admin_bookings():
    status_filter = request.args.get('status', 'all')
    cur = mysql.connection.cursor()
    
    if status_filter == 'all':
        cur.execute("""
            SELECT 
                b.id, 
                b.booking_code, 
                b.status, 
                b.total_price, 
                b.guests,
                b.check_in,
                b.check_out,
                b.created_at,
                b.special_requests,
                b.admin_notes,
                b.payment_status as booking_payment_status,
                u.first_name, 
                u.last_name, 
                u.email, 
                u.phone,
                r.name as room_name,
                p.status as payment_table_status,
                p.proof_image,
                p.payment_method,
                COALESCE(p.status, b.payment_status, 'pending') as final_payment_status,
                p.id as payment_id
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN rooms r ON b.room_id = r.id
            LEFT JOIN payments p ON b.id = p.booking_id
            ORDER BY b.created_at DESC
        """)
    else:
        cur.execute("""
            SELECT 
                b.id, 
                b.booking_code, 
                b.status, 
                b.total_price, 
                b.guests,
                b.check_in,
                b.check_out,
                b.created_at,
                b.special_requests,
                b.admin_notes,
                b.payment_status as booking_payment_status,
                u.first_name, 
                u.last_name, 
                u.email, 
                u.phone,
                r.name as room_name,
                p.status as payment_table_status,
                p.proof_image,
                p.payment_method,
                COALESCE(p.status, b.payment_status, 'pending') as final_payment_status,
                p.id as payment_id
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN rooms r ON b.room_id = r.id
            LEFT JOIN payments p ON b.id = p.booking_id
            WHERE b.status = %s
            ORDER BY b.created_at DESC
        """, (status_filter,))
        
    bookings = cur.fetchall()
    cur.close()
    
    return render_template('admin/bookings.html', bookings=bookings, status_filter=status_filter)

@app.route('/admin/booking/<int:booking_id>/update', methods=['POST'])
@admin_required
def update_booking_status(booking_id):
    new_status = request.form.get('status')
    admin_notes = request.form.get('admin_notes', '')
    
    valid_statuses = ['pending', 'waiting_payment', 'confirmed', 'cancelled', 'completed']
    
    if new_status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin_bookings'))
    
    cur = mysql.connection.cursor()
    
    # Dapatkan data booking dan room
    cur.execute("""
        SELECT b.room_id, b.status as old_status, 
               r.available_count, r.room_count
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE b.id = %s
    """, (booking_id,))
    
    booking = cur.fetchone()
    if not booking:
        flash('Booking not found.', 'danger')
        cur.close()
        return redirect(url_for('admin_bookings'))
    
    old_status = booking['old_status']
    room_id = booking['room_id']
    
    # 2. Update status booking
    cur.execute("""
        UPDATE bookings 
        SET status = %s, admin_notes = %s, updated_at = NOW()
        WHERE id = %s
    """, (new_status, admin_notes, booking_id))

    try:
        if new_status == 'confirmed' and old_status != 'confirmed':
            cur.execute("""
                UPDATE rooms 
                SET is_available = CASE 
                    WHEN available_count <= 0 THEN 0 
                    ELSE 1 
                END
                WHERE id = %s
            """, (room_id,))
            print(f"✅ Booking {booking_id} confirmed. Updated is_available based on available_count")
            
        elif new_status in ['cancelled'] and old_status in ['confirmed', 'pending', 'waiting_payment']:

            cur.execute("""
                UPDATE rooms 
                SET available_count = LEAST(room_count, available_count + 1),
                    is_available = CASE 
                        WHEN available_count + 1 > 0 THEN 1 
                        ELSE 0 
                    END
                WHERE id = %s
            """, (room_id,))
            print(f"✅ Booking {booking_id} cancelled. Incremented available_count")
            
        elif new_status == 'completed':

            cur.execute("""
                UPDATE rooms 
                SET available_count = LEAST(room_count, available_count + 1),
                    is_available = CASE 
                        WHEN available_count + 1 > 0 THEN 1 
                        ELSE 0 
                    END
                WHERE id = %s
            """, (room_id,))
            print(f"✅ Booking {booking_id} completed. Incremented available_count")
            
        elif new_status == 'waiting_payment' and old_status == 'pending':
            print(f"⚠️ Booking {booking_id} waiting payment. No room availability change.")
            
        mysql.connection.commit()
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error updating room availability: {str(e)}', 'danger')
        cur.close()
        return redirect(url_for('admin_bookings'))
    
    cur.close()
    flash('Booking status updated successfully!', 'success')
    return redirect(url_for('admin_bookings'))

@app.route('/admin/users')
@admin_required
def admin_users():
    cur = mysql.connection.cursor()
    
    cur.execute("""
        SELECT u.id, u.first_name, u.last_name, u.email, u.phone, u.role, 
               u.created_at,
               COALESCE(COUNT(b.id), 0) as total_bookings
        FROM users u
        LEFT JOIN bookings b ON u.id = b.user_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """)
    
    users = cur.fetchall()
    cur.close()
    
    processed_users = []
    for user in users:
        processed_user = {
            'id': user['id'],
            'first_name': user['first_name'] or '',
            'last_name': user['last_name'] or '',
            'email': user['email'] or '',
            'phone': user['phone'] or '',
            'role': user['role'] or 'user',
            'created_at': user['created_at'],
            'total_bookings': int(user['total_bookings']) if user['total_bookings'] is not None else 0
        }
        processed_users.append(processed_user)
    
    return render_template('admin/users.html', users=processed_users)

@app.route('/admin/user/<int:user_id>/promote', methods=['POST'])
@login_required
@admin_required
def promote_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET role = 'admin' WHERE id = %s", (user_id,))
    mysql.connection.commit()
    cur.close()
    flash('User promoted to Admin successfully', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/demote', methods=['POST'])
@login_required
@admin_required
def demote_user(user_id):
    if session['user_id'] == user_id:
        flash('You cannot demote yourself', 'error')
        return redirect(url_for('admin_users'))
    
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET role = 'user' WHERE id = %s", (user_id,))
    mysql.connection.commit()
    cur.close()
    flash('Admin demoted to User successfully', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_manage_user(user_id):
    cur = mysql.connection.cursor()
    
    cur.execute("""
        SELECT 
            COUNT(*) as total_bookings,
            SUM(total_price) as total_spent
        FROM bookings 
        WHERE user_id = %s
    """, (user_id,))
    stats = cur.fetchone()
    
    cur.execute("""
        SELECT room_name, check_in, check_out, created_at
        FROM bookings 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT 5
    """, (user_id,))
    recent_bookings = cur.fetchall()
    
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        role = request.form.get('role')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        cur.execute("""
            UPDATE users 
            SET first_name = %s, last_name = %s, phone = %s, role = %s
            WHERE id = %s
        """, (first_name, last_name, phone, role, user_id))
        
        if new_password and confirm_password and new_password == confirm_password:
            hashed_password = generate_password_hash(new_password)
            cur.execute("UPDATE users SET password = %s WHERE id = %s", 
                       (hashed_password, user_id))
            flash('Password updated successfully', 'success')
        
        mysql.connection.commit()
        flash('User updated successfully!', 'success')
    
    cur.close()
    return render_template('admin/user_profile.html', 
                         user=user, 
                         stats=stats, 
                         recent_bookings=recent_bookings)

@app.route('/admin/user/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_user():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = request.form.get('role', 'user')
        password = request.form.get('password')
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            flash('Email already exists', 'error')
            cur.close()
            return redirect(url_for('admin_create_user'))
        
        hashed_password = generate_password_hash(password)
        cur.execute("""
            INSERT INTO users (first_name, last_name, email, phone, role, password)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (first_name, last_name, email, phone, role, hashed_password))
        
        mysql.connection.commit()
        cur.close()
        flash('User created successfully', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/create_user.html')

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    if session['user_id'] == user_id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin_users'))
    
    cur = mysql.connection.cursor()
    
    cur.execute("DELETE FROM bookings WHERE user_id = %s", (user_id,))
    
    # Delete user
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    
    mysql.connection.commit()
    cur.close()
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/rooms/manage')
@login_required
@admin_required
def manage_rooms():
    room_type_filter = request.args.get('type', None)
    
    cur = mysql.connection.cursor()
    
    if room_type_filter:
        cur.execute("""
            SELECT r.*, 
                   (SELECT COUNT(*) FROM bookings b WHERE b.room_id = r.id AND b.status NOT IN ('cancelled', 'expired')) as booking_count
            FROM rooms r 
            WHERE r.room_type = %s
            ORDER BY r.created_at DESC
        """, (room_type_filter,))
    else:
        cur.execute("""
            SELECT r.*, 
                   (SELECT COUNT(*) FROM bookings b WHERE b.room_id = r.id AND b.status NOT IN ('cancelled', 'expired')) as booking_count
            FROM rooms r 
            ORDER BY r.created_at DESC
        """)
    
    raw_rooms = cur.fetchall()
    cur.close()
    
    processed_rooms = process_room_images(raw_rooms)
        
    # TAMBAHKAN booking_count ke hasil processing
    for i, room in enumerate(processed_rooms):
        room['booking_count'] = raw_rooms[i].get('booking_count', 0)
    
    return render_template('admin/manage_rooms.html',
                        rooms=processed_rooms, 
                        room_type_filter=room_type_filter)

@app.route('/admin/room/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_room():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        capacity = int(request.form['capacity'])
        size = request.form['size']
        view_type = request.form.get('view_type', '')
        amenities = request.form.getlist('amenities')
        room_type = request.form.get('room_type', 'hotel_room')
        is_available = 1 if request.form.get('is_available') == 'on' else 0
        available_count = int(request.form.get('available_count', 1))
        
        image_files = request.files.getlist('images')
        image_filenames = []
        
        # Create uploads directory if not exists
        upload_dir = 'static/uploads/rooms'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        for image in image_files:
            if image and image.filename != '':
                filename = secure_filename(f"{int(time.time())}_{image.filename}")
                image_path = os.path.join(upload_dir, filename)
                image.save(image_path)
                image_filenames.append(f"static/uploads/rooms/{filename}")
        
        images_str = ','.join(image_filenames) if image_filenames else None
        
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO rooms (name, description, price, capacity, size, view_type, 
                                 amenities, images, is_available, room_type, available_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, description, price, capacity, size, view_type, 
                  ', '.join(amenities), images_str, is_available, room_type, available_count))
            
            mysql.connection.commit()
            flash('Room added successfully!', 'success')
            return redirect(url_for('manage_rooms'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error adding room: {str(e)}', 'danger')
            return redirect(url_for('add_room'))
        finally:
            cur.close()
    
    return render_template('admin/add_room.html')

@app.route('/admin/room/edit/<int:room_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_room(room_id):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        capacity = int(request.form['capacity'])
        size = request.form['size']
        view_type = request.form.get('view_type', '')
        amenities = request.form.getlist('amenities')
        room_type = request.form.get('room_type', 'hotel_room')
        is_available = 1 if request.form.get('is_available') == 'on' else 0
        available_count = int(request.form.get('available_count', 1))
        
        # Handle images
        existing_images_input = request.form.get('existing_images', '')
        existing_images = []
        if existing_images_input:
            existing_images = [img.strip() for img in existing_images_input.split(',') if img.strip()]
        
        image_files = request.files.getlist('images')
        new_image_filenames = []
        
        # Upload new images
        upload_dir = 'static/uploads/rooms'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        for image in image_files:
            if image and image.filename != '':
                filename = secure_filename(f"{int(time.time())}_{image.filename}")
                image_path = os.path.join(upload_dir, filename)
                image.save(image_path)
                new_image_filenames.append(f"static/uploads/rooms/{filename}")
        
        # Combine existing and new images
        all_images = existing_images + new_image_filenames
        images_str = ','.join(all_images) if all_images else None
        
        try:
            cur.execute("""
                UPDATE rooms 
                SET name=%s, description=%s, price=%s, capacity=%s, size=%s, 
                    view_type=%s, amenities=%s, images=%s, is_available=%s,
                    room_type=%s, available_count=%s, updated_at=NOW()
                WHERE id=%s
            """, (name, description, price, capacity, size, view_type, 
                  ', '.join(amenities), images_str, is_available,
                  room_type, available_count, room_id))
            
            mysql.connection.commit()
            flash('Room updated successfully!', 'success')
            return redirect(url_for('manage_rooms'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error updating room: {str(e)}', 'danger')
            return redirect(url_for('edit_room', room_id=room_id))
    
    # GET request - fetch room data
    cur.execute("SELECT * FROM rooms WHERE id = %s", (room_id,))
    room = cur.fetchone()
    cur.close()
    
    if not room:
        flash('Room not found!', 'danger')
        return redirect(url_for('manage_rooms'))
    
    return render_template('admin/edit_room.html', room=room)

@app.route('/admin/room/<int:room_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_room_status(room_id):
    """Toggle room availability status (enable/disable)"""
    try:
        data = request.get_json()
        new_status = int(data.get('status', 0))  # 1 for available, 0 for unavailable
        
        cur = mysql.connection.cursor()
        
        # Cek apakah room ada
        cur.execute("SELECT id, name FROM rooms WHERE id = %s", (room_id,))
        room = cur.fetchone()
        
        if not room:
            return jsonify({
                'success': False,
                'error': 'Room not found'
            }), 404
        
        # Update status
        cur.execute("""
            UPDATE rooms 
            SET is_available = %s
            WHERE id = %s
        """, (new_status, room_id))
        
        mysql.connection.commit()
        cur.close()
        
        status_text = "enabled" if new_status == 1 else "disabled"
        return jsonify({
            'success': True,
            'message': f'Room "{room["name"]}" {status_text} successfully',
            'new_status': new_status
        })
        
    except Exception as e:
        print(f"Error toggling room status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@app.route('/admin/room/delete/<int:room_id>', methods=['POST'])
@login_required
@admin_required
def delete_room(room_id):
    from flask_wtf.csrf import validate_csrf
    
    try:
        validate_csrf(request.form.get('csrf_token'))
    except:
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('manage_rooms'))
    
    cur = mysql.connection.cursor()
    
    try:
        # Check for active bookings
        cur.execute("""
            SELECT COUNT(*) as booking_count 
            FROM bookings 
            WHERE room_id = %s AND status IN ('pending', 'confirmed', 'waiting_payment')
        """, (room_id,))
        booking_count = cur.fetchone()['booking_count']
        
        if booking_count > 0:
            flash('Cannot delete room with active bookings!', 'danger')
            return redirect(url_for('manage_rooms'))
        
        # Delete the room
        cur.execute("DELETE FROM rooms WHERE id = %s", (room_id,))
        mysql.connection.commit()
        
        flash('Room deleted successfully!', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error deleting room: {str(e)}', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('manage_rooms'))

@app.route('/admin/room/<int:room_id>')
@login_required
@admin_required
def room_details(room_id):
    """View room details"""
    cur = mysql.connection.cursor()
    
    # Get room details
    cur.execute("""
        SELECT r.*,
               (SELECT COUNT(*) FROM bookings b 
                WHERE b.room_id = r.id 
                AND b.status NOT IN ('cancelled', 'expired')) as booking_count,
               (SELECT SUM(total_price) FROM bookings b 
                WHERE b.room_id = r.id 
                AND b.status = 'completed') as total_revenue
        FROM rooms r
        WHERE r.id = %s
    """, (room_id,))
    
    room = cur.fetchone()
    
    if not room:
        flash('Room not found!', 'danger')
        return redirect(url_for('manage_rooms'))
    
    # Get recent bookings
    cur.execute("""
        SELECT b.*, 
               u.first_name, u.last_name, u.email,
               r.name as room_name
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN rooms r ON b.room_id = r.id
        WHERE b.room_id = %s
        ORDER BY b.created_at DESC
        LIMIT 10
    """, (room_id,))
    
    recent_bookings = cur.fetchall()
    
    # Get booking statistics
    cur.execute("""
        SELECT 
            COUNT(*) as total_bookings,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_bookings,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_bookings,
            SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_bookings,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_bookings
        FROM bookings
        WHERE room_id = %s
    """, (room_id,))
    
    booking_stats = cur.fetchone()
    
    cur.close()
    
    # Process room images
    if room['images']:
        if isinstance(room['images'], str):
            try:
                # Try to parse as JSON
                import json
                images = json.loads(room['images'].replace("'", '"'))
            except:
                # Fallback to comma-separated
                images = [img.strip() for img in room['images'].split(',') if img.strip()]
        else:
            images = []
    else:
        images = []
    
    # Process amenities
    amenities = []
    if room['amenities']:
        if isinstance(room['amenities'], str):
            amenities = [a.strip() for a in room['amenities'].split(',') if a.strip()]
        else:
            amenities = room['amenities']
    
    return render_template('admin/rooms.html',
                          room=room,
                          images=images,
                          amenities=amenities,
                          recent_bookings=recent_bookings,
                          booking_stats=booking_stats)

@app.route('/admin/payments')
@admin_required
def admin_payments():
    status_filter = request.args.get('status', 'all')
    method_filter = request.args.get('method', 'all')
    
    cur = mysql.connection.cursor()
    
    query = """
        SELECT 
            p.id,
            p.amount, 
            p.payment_method, 
            p.status, 
            p.proof_image, 
            p.created_at,
            b.id as booking_id,
            r.name as room_name,
            CONCAT(u.first_name, ' ', u.last_name) as customer_name,
            u.email as customer_email
        FROM payments p
        JOIN bookings b ON p.booking_id = b.id
        JOIN rooms r ON b.room_id = r.id
        JOIN users u ON b.user_id = u.id
        WHERE 1=1
    """
    
    params = []
    
    if status_filter != 'all':
        query += " AND p.status = %s"
        params.append(status_filter)
    
    if method_filter != 'all':
        query += " AND p.payment_method = %s"
        params.append(method_filter)
    
    query += " ORDER BY p.created_at DESC"
    
    cur.execute(query, params)
    payments = cur.fetchall()
    
    cur.execute("SELECT COUNT(*) as total FROM payments")
    total_payments = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM payments WHERE status = 'pending'")
    pending_payments = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM payments WHERE status = 'completed'")
    completed_payments = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM payments WHERE status = 'processing'")
    processing_payments = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM payments WHERE status = 'failed'")
    failed_payments = cur.fetchone()['total']
    
    cur.close()
    
    return render_template('admin/payments.html',
                         payments=payments,
                         total_payments=total_payments,
                         pending_payments=pending_payments,
                         completed_payments=completed_payments,
                         processing_payments=processing_payments,
                         failed_payments=failed_payments)

@app.route('/admin/payment/<int:payment_id>/details')
@admin_required
def payment_details(payment_id):
    cur = mysql.connection.cursor()
    
    cur.execute("""
        SELECT p.*, 
               b.id as booking_id, b.check_in, b.check_out, b.total_price,
               r.name as room_name,
               CONCAT(u.first_name, ' ', u.last_name) as customer_name,
               u.email as customer_email, u.phone
        FROM payments p
        JOIN bookings b ON p.booking_id = b.id
        JOIN rooms r ON b.room_id = r.id
        JOIN users u ON b.user_id = u.id
        WHERE p.id = %s
    """, (payment_id,))
    
    payment = cur.fetchone()
    cur.close()
    
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    
    status = payment.get("status", "pending")
    
    image_html = ""
    if payment.get('proof_image'):
        if 'qris_simulated' in payment['proof_image']:
            image_html = '<p class="text-sm text-gray-600 mb-2">QRIS Payment (Simulated)</p>'
        else:

            image_url = url_for('uploaded_file', filename=payment['proof_image'], _external=True)
            
            image_html = f'''
            <div class="text-center">
                <img src="{image_url}" 
                     alt="Payment Proof" 
                     class="max-w-full h-64 object-contain mx-auto rounded-lg">
                <a href="{image_url}" 
                   target="_blank" 
                   class="text-sm text-blue-600 hover:text-blue-800 mt-2 inline-block">
                    <i class="fas fa-external-link-alt mr-1"></i>View Full Size
                </a>
            </div>
            '''
    else:
        image_html = '<p class="text-sm text-gray-600">No proof uploaded</p>'
    
    html = f"""
    <div class="grid md:grid-cols-2 gap-6">
        <!-- Left Column -->
        <div>
            <h4 class="font-semibold mb-4">Payment Information</h4>
            <div class="space-y-3">
                <div class="flex justify-between">
                    <span class="text-gray-600">Payment ID:</span>
                    <span class="font-medium">#PAY{payment["id"]:04d}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Booking ID:</span>
                    <span class="font-medium">#FH{payment["booking_id"]:04d}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Payment Method:</span>
                    <span class="font-medium">{payment["payment_method"].upper()}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Amount:</span>
                    <span class="font-bold text-gold">Rp{payment["amount"]:,.0f}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Status:</span>
                    <span class="font-medium">{status.title()}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Payment Date:</span>
                    <span>{payment.get("created_at").strftime('%d %b %Y %H:%M')}</span>
                </div>
            </div>
            
            <h4 class="font-semibold mt-6 mb-4">Customer Information</h4>
            <div class="space-y-3">
                <div class="flex justify-between">
                    <span class="text-gray-600">Name:</span>
                    <span>{payment["customer_name"]}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Email:</span>
                    <span>{payment["customer_email"]}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Phone:</span>
                    <span>{payment.get("phone", "N/A")}</span>
                </div>
            </div>
        </div>
        
        <!-- Right Column -->
        <div>
            <h4 class="font-semibold mb-4">Booking Details</h4>
            <div class="space-y-3">
                <div class="flex justify-between">
                    <span class="text-gray-600">Room:</span>
                    <span>{payment["room_name"]}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Check-in:</span>
                    <span>{payment["check_in"].strftime('%d %b %Y')}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Check-out:</span>
                    <span>{payment["check_out"].strftime('%d %b %Y')}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">Total Amount:</span>
                    <span class="font-bold">Rp{payment["total_price"]:,.0f}</span>
                </div>
            </div>
            
            <h4 class="font-semibold mt-6 mb-4">Payment Proof</h4>
            {image_html}
        </div>
    </div>
    
    <div class="mt-8 pt-6 border-t">
        <h4 class="font-semibold mb-4">Admin Actions</h4>
        <div class="flex space-x-3">
            <button onclick="verifyPayment({payment_id})" 
                    class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
                <i class="fas fa-check mr-2"></i>Verify Payment
            </button>
            <button onclick="rejectPayment({payment_id})" 
                    class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">
                <i class="fas fa-times mr-2"></i>Reject Payment
            </button>
            <button onclick="closePaymentModal()" 
                    class="px-4 py-2 border rounded-lg">
                Cancel
            </button>
        </div>
    </div>
    """
    
    return jsonify({'html': html})

@app.route('/admin/payment/<int:payment_id>/verify', methods=['POST'])
@admin_required
def verify_payment(payment_id):
    """Verify or reject a payment"""
    data = request.get_json()
    action = data.get('action') 
    reason = data.get('reason', '')
    
    cur = mysql.connection.cursor()
    
    cur.execute("""
        SELECT 
            p.booking_id, 
            p.status as payment_status,
            b.room_id, 
            b.status as booking_status,
            r.available_count,
            r.room_count
        FROM payments p
        JOIN bookings b ON p.booking_id = b.id
        JOIN rooms r ON b.room_id = r.id
        WHERE p.id = %s
    """, (payment_id,))
    
    result = cur.fetchone()
    
    if not result:
        return jsonify({'success': False, 'error': 'Payment not found'})
    
    booking_id = result['booking_id']
    room_id = result['room_id']
    current_payment_status = result['payment_status']
    
    if current_payment_status in ['completed', 'failed']:
        return jsonify({'success': False, 'error': f'Payment already {current_payment_status}'})
    
    cur.execute("START TRANSACTION")
    
    try:
        if action == 'verify':
            new_payment_status = 'completed'
            new_booking_status = 'confirmed'
            
            cur.execute("""
                UPDATE rooms 
                SET is_available = CASE 
                    WHEN available_count <= 0 THEN 0 
                    ELSE 1 
                END
                WHERE id = %s
            """, (room_id,))
            
        elif action == 'reject':
            new_payment_status = 'failed'
            new_booking_status = 'cancelled'
            
            cur.execute("""
                UPDATE rooms 
                SET available_count = LEAST(room_count, available_count + 1),
                    is_available = CASE 
                        WHEN available_count + 1 > 0 THEN 1 
                        ELSE 0 
                    END
                WHERE id = %s
            """, (room_id,))
            
        else:
            return jsonify({'success': False, 'error': 'Invalid action'})
        
        cur.execute("""
            UPDATE payments 
            SET status = %s, 
                admin_notes = %s,
                updated_at = NOW(),
                processed_at = NOW()
            WHERE id = %s
        """, (new_payment_status, reason, payment_id))
        
        cur.execute("""
            UPDATE bookings 
            SET status = %s, 
                payment_status = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (new_booking_status, new_payment_status, booking_id))
        
        cur.execute("COMMIT")
        cur.close()
        
        return jsonify({
            'success': True, 
            'message': f'Payment {action}ed successfully'
        })
        
    except Exception as e:
        cur.execute("ROLLBACK")
        cur.close()
        print(f"Payment verification error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
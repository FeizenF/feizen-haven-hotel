from flask import jsonify, send_file, url_for, session, make_response
from config import app, mysql
from models import login_required, admin_required
import os
import mimetypes
import json
import time
from datetime import datetime

# =============== FILE SERVING ROUTES ===============
@app.route('/uploads/payments/<filename>')
@login_required  # 🔒 Security: hanya user login yang bisa akses
def uploaded_file(filename):
    """Serve uploaded payment proof files dengan security check"""
    try:
        print(f"📁 DEBUG - Requested payment proof file: {filename}")
        print(f"📁 DEBUG - Session role: {session.get('role')}")
        
        cur = mysql.connection.cursor()
        
        # 🔒 Security check untuk non-admin users
        if session.get('role') != 'admin':
            print(f"🔒 DEBUG - Checking user permission for file: {filename}")
            cur.execute("""
                SELECT b.user_id 
                FROM payments p
                JOIN bookings b ON p.booking_id = b.id
                WHERE p.proof_image = %s
            """, (filename,))
            
            payment = cur.fetchone()
            print(f"🔒 DEBUG - Payment found: {payment}")
            
            if not payment or payment['user_id'] != session.get('user_id'):
                cur.close()
                print(f"🔒 DEBUG - Unauthorized access attempt for {filename}")
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized access to this file'
                }), 403
        
        cur.close()
        
        # ===== CEK SEMUA KEMUNGKINAN PATH =====
        print(f"🔍 DEBUG - Searching for file: {filename}")
        
        # Semua kemungkinan path yang dicoba
        possible_paths = [
            ('static/uploads/payments', 'static/uploads/payments'),
            ('uploads/payments', 'uploads/payments'),
            ('static/images/uploads/payments', 'static/images/uploads/payments'),
            ('static/images', 'static/images'),  # Fallback
            ('static', 'static'),  # Fallback
        ]
        
        file_found = False
        actual_path = None
        
        for folder_name, relative_path in possible_paths:
            file_path = os.path.join(folder_name, filename)
            abs_path = os.path.abspath(file_path)
            
            print(f"🔍 DEBUG - Checking: {relative_path}/{filename}")
            print(f"🔍 DEBUG - Absolute path: {abs_path}")
            
            if os.path.exists(abs_path):
                file_found = True
                actual_path = abs_path
                print(f"✅ DEBUG - File found at: {relative_path}/{filename}")
                print(f"✅ DEBUG - File size: {os.path.getsize(abs_path)} bytes")
                break
        
        if not file_found:
            # Coba cari di seluruh direktori project
            print(f"🔍 DEBUG - File not found in standard paths. Searching project...")
            for root, dirs, files in os.walk('.'):
                if filename in files:
                    actual_path = os.path.join(root, filename)
                    print(f"✅ DEBUG - File found via walk at: {actual_path}")
                    file_found = True
                    break
        
        if not file_found:
            print(f"❌ DEBUG - File not found anywhere: {filename}")
            print(f"❌ DEBUG - Current working directory: {os.getcwd()}")
            print(f"❌ DEBUG - List of directories:")
            for root, dirs, files in os.walk('.', topdown=True):
                level = root.replace('.', '').count(os.sep)
                indent = ' ' * 2 * level
                print(f'{indent}{os.path.basename(root)}/')
                subindent = ' ' * 2 * (level + 1)
                for file in files[:10]:  # Tampilkan 10 file pertama
                    if 'payment' in file.lower():
                        print(f'{subindent}{file}')
            
            # Return default image
            default_path = os.path.abspath('static/images/default-payment.jpg')
            if os.path.exists(default_path):
                print(f"🔄 DEBUG - Serving default image: {default_path}")
                return send_file(default_path, mimetype='image/jpeg')
            else:
                print(f"❌ DEBUG - Default image not found either")
                return jsonify({
                    'success': False,
                    'error': f'Payment proof file not found: {filename}'
                }), 404
        
        # Security check - pastikan file dalam folder yang diizinkan
        allowed_dirs = [
            os.path.abspath('static/uploads/payments'),
            os.path.abspath('uploads/payments'),
            os.path.abspath('static/images/uploads/payments'),
            os.path.abspath('static/images'),
            os.path.abspath('static'),
        ]
        
        is_safe = False
        file_dir = os.path.dirname(actual_path)
        for allowed_dir in allowed_dirs:
            try:
                if os.path.commonpath([file_dir, allowed_dir]) == allowed_dir:
                    is_safe = True
                    print(f"✅ DEBUG - Path is safe: {actual_path}")
                    break
            except ValueError:
                # Path tidak share common prefix
                continue
        
        if not is_safe:
            print(f"🚨 SECURITY - Attempt to access unsafe path: {actual_path}")
            return jsonify({
                'success': False,
                'error': 'Access denied - security violation'
            }), 403
        
        # Deteksi MIME type
        mime_type, _ = mimetypes.guess_type(actual_path)
        if not mime_type:
            # Default berdasarkan ekstensi
            if filename.lower().endswith(('.jpg', '.jpeg')):
                mime_type = 'image/jpeg'
            elif filename.lower().endswith('.png'):
                mime_type = 'image/png'
            else:
                mime_type = 'application/octet-stream'
        
        print(f"📤 DEBUG - Sending file: {actual_path} (MIME: {mime_type})")
        
        # Kirim file
        response = send_file(
            actual_path,
            mimetype=mime_type,
            as_attachment=False,
            download_name=filename
        )
        
        # Set cache headers
        if mime_type.startswith('image/'):
            cache_time = 3600  # 1 jam untuk gambar
        else:
            cache_time = 300   # 5 menit untuk file lain
        
        response.headers['Cache-Control'] = f'public, max-age={cache_time}'
        
        return response
        
    except Exception as e:
        print(f"💥 ERROR in uploaded_file: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

# =============== API ROUTES ===============
@app.route('/api/room/<int:room_id>/details')
def room_details_api(room_id):
    """API untuk mengambil detail room dengan format response yang konsisten"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id, name, description, size, capacity, price, 
                   available_count, room_count, view_type, room_type,
                   amenities, images
            FROM rooms 
            WHERE id = %s
        """, (room_id,))
        room = cur.fetchone()
        cur.close()
        
        if not room:
            return jsonify({
                'success': False,
                'error': 'Room not found',
                'code': 404
            }), 404

        images = []
        if room['images']:
            try:
                if isinstance(room['images'], str):
                    try:
                        images = json.loads(room['images'])
                    except json.JSONDecodeError:
                        images = [img.strip() for img in room['images'].split(',') if img.strip()]
            except:
                images = []
        
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
                'amenities': room['amenities'],
                'images': images,
                'availability': {
                    'text': f"{room['available_count']} of {room['room_count']} available",
                    'percentage': round((room['available_count'] / room['room_count']) * 100, 1) if room['room_count'] > 0 else 0,
                    'is_available': room['available_count'] > 0
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}',
            'code': 500
        }), 500

@app.route('/api/venue/<int:venue_id>') 
def venue_details_api(venue_id):  
    """API untuk mengambil detail venue dengan format response yang konsisten"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id, name, type, description, price_per_hour, 
                   capacity, operating_hours, amenities, features, image_url
            FROM venues  
            WHERE id = %s
        """, (venue_id,))
        venue = cur.fetchone()
        cur.close()
        
        if not venue:
            return jsonify({
                'success': False,
                'error': 'Venue not found', 
                'code': 404
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'id': venue['id'],
                'name': venue['name'],
                'type': venue['type'],
                'description': venue['description'],
                'price_per_hour': float(venue['price_per_hour']) if venue['price_per_hour'] else 0,
                'capacity': venue['capacity'],
                'operating_hours': venue['operating_hours'],
                'amenities': venue['amenities'] if venue['amenities'] else '',
                'features': venue['features'] if venue['features'] else '',
                'image_url': venue['image_url'] if venue['image_url'] else ''
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}',
            'code': 500
        }), 500

@app.route('/api/stats')
@admin_required
def stats_api():
    """API untuk mengambil statistics dashboard dengan format response yang konsisten"""
    try:
        cur = mysql.connection.cursor()
    
        cur.execute("SELECT COUNT(*) as total FROM users WHERE role = 'user'")
        total_users = cur.fetchone()['total']
        
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                SUM(CASE WHEN status = 'waiting_payment' THEN 1 ELSE 0 END) as waiting_payment
            FROM bookings
        """)
        bookings_stats = cur.fetchone()
        
        cur.execute("SELECT SUM(total_price) as revenue FROM bookings WHERE status = 'confirmed'")
        revenue_result = cur.fetchone()
        revenue = float(revenue_result['revenue']) if revenue_result['revenue'] else 0
        
        cur.execute("""
            SELECT 
                SUM(room_count) as total_rooms,
                SUM(available_count) as available_rooms,
                SUM(room_count - available_count) as occupied_rooms
            FROM rooms 
            WHERE room_type = 'hotel_room'
        """)
        rooms_stats = cur.fetchone()
        
        cur.execute("""
            SELECT b.id, b.booking_code, b.check_in, b.check_out, 
                   b.total_price, b.status, b.created_at,
                   CONCAT(u.first_name, ' ', u.last_name) as customer_name,
                   r.name as room_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN rooms r ON b.room_id = r.id
            ORDER BY b.created_at DESC
            LIMIT 5
        """)
        recent_bookings = cur.fetchall()
        
        cur.close()
        
        formatted_bookings = []
        for booking in recent_bookings:
            booking_dict = dict(booking)
            for date_field in ['check_in', 'check_out', 'created_at']:
                if booking_dict.get(date_field) and hasattr(booking_dict[date_field], 'strftime'):
                    booking_dict[date_field] = booking_dict[date_field].strftime('%Y-%m-%d')
            
            if booking_dict.get('total_price'):
                booking_dict['total_price'] = float(booking_dict['total_price'])
                
            formatted_bookings.append(booking_dict)
        
        return jsonify({
            'success': True,
            'data': {
                'users': {
                    'total': total_users
                },
                'bookings': {
                    'total': bookings_stats['total'],
                    'confirmed': bookings_stats['confirmed'],
                    'pending': bookings_stats['pending'],
                    'cancelled': bookings_stats['cancelled'],
                    'waiting_payment': bookings_stats['waiting_payment']
                },
                'revenue': revenue,
                'rooms': {
                    'total': rooms_stats['total_rooms'] if rooms_stats['total_rooms'] else 0,
                    'available': rooms_stats['available_rooms'] if rooms_stats['available_rooms'] else 0,
                    'occupied': rooms_stats['occupied_rooms'] if rooms_stats['occupied_rooms'] else 0,
                    'occupancy_rate': round((rooms_stats['occupied_rooms'] / rooms_stats['total_rooms'] * 100), 1) 
                        if rooms_stats['total_rooms'] and rooms_stats['total_rooms'] > 0 else 0
                },
                'recent_bookings': formatted_bookings
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}',
            'code': 500
        }), 500

# =============== HELPER & DEBUG ROUTES ===============
@app.route('/api/health')
def health_check():
    """Health check endpoint untuk monitoring"""
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

@app.route('/debug/session')
@login_required
def debug_session():
    """Debug route untuk cek session (hanya user login)"""
    return jsonify({
        'success': True,
        'data': {
            'user_id': session.get('user_id'),
            'email': session.get('email'),
            'name': session.get('name'),
            'role': session.get('role'),
            'session_keys': list(session.keys())
        }
    })

@app.route('/debug/files')
@admin_required  
def debug_files():
    """Debug route untuk check uploaded files (admin only)"""
    try:
        files_info = []
        upload_dir = 'uploads/payments'
        
        if os.path.exists(upload_dir):
            files = os.listdir(upload_dir)
            for f in files:
                file_path = os.path.join(upload_dir, f)
                if os.path.isfile(file_path):
                    files_info.append({
                        'name': f,
                        'size': os.path.getsize(file_path),
                        'modified': time.ctime(os.path.getmtime(file_path)),
                        'url': url_for('uploaded_file', filename=f, _external=True),
                        'accessible': True
                    })
        
        return jsonify({
            'success': True,
            'data': {
                'directory': upload_dir,
                'exists': os.path.exists(upload_dir),
                'file_count': len(files_info),
                'files': files_info
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/debug/check-file/<filename>')
@admin_required  
def debug_check_file(filename):
    """Debug route untuk check file accessibility (admin only)"""
    try:
        file_path = os.path.join('uploads', 'payments', filename)
        abs_path = os.path.abspath(file_path)
        
        exists = os.path.exists(file_path)
        
        info = {
            'filename': filename,
            'file_path': file_path,
            'absolute_path': abs_path,
            'exists': exists,
            'is_file': os.path.isfile(file_path) if exists else False,
            'size': os.path.getsize(file_path) if exists else 0,
            'url': url_for('uploaded_file', filename=filename, _external=True),
            'permissions': oct(os.stat(file_path).st_mode)[-3:] if exists else None,
            'modified': time.ctime(os.path.getmtime(file_path)) if exists else None
        }
        
        return jsonify({
            'success': True,
            'data': info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_booking_code():
    """Generate unique booking code"""
    import random
    import string
    import time
    
    timestamp = int(time.time()) % 1000000
    random_str = ''.join(random.choices(string.ascii_uppercase, k=3))
    return f"FH-{random_str}-{timestamp:06d}"


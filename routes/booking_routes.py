from flask import render_template, request, redirect, url_for, flash, session, jsonify
from config import app, mysql
from models import login_required, allowed_file
import os
from datetime import datetime, timedelta
import json
import time
import uuid
from werkzeug.utils import secure_filename
from helpers import parse_images_data

PAYMENT_UPLOAD_DIR = os.path.join('static', 'uploads', 'payments')
PAYMENT_UPLOAD_PREFIX = 'uploads/payments'

# =============== BOOKING ROUTES ===============
@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    if request.method == 'POST':
        room_id = request.form.get('room_id')
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        try:
            guests = int(request.form.get('guests', 2))
        except (TypeError, ValueError):
            guests = 2
        special_requests = request.form.get('special_requests', '')
        
        cur = mysql.connection.cursor()
        
        try:
            # 1. CEK KAMAR TERSEDIA DENGAN LOCK ROW
            cur.execute("""
                SELECT * FROM rooms 
                WHERE id = %s AND is_available = 1 AND available_count > 0
                FOR UPDATE
            """, (room_id,))
            
            room = cur.fetchone()
            
            if not room:
                flash('Room not available or fully booked.', 'danger')
                cur.close()
                return redirect(url_for('rooms'))
            
            room = dict(room)
            current_available = room['available_count']
            
            # 2. VALIDASI KAPASITAS
            if guests > room['capacity']:
                flash(f'Maximum capacity for this room is {room["capacity"]} guests.', 'danger')
                cur.close()
                return redirect(url_for('book', room_id=room_id))
            
            # 3. VALIDASI TANGGAL
            try:
                check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
                check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
                
                if check_in_date.date() < datetime.now().date():
                    flash('Check-in date cannot be in the past.', 'danger')
                    cur.close()
                    return redirect(url_for('book', room_id=room_id))

                if check_out_date <= check_in_date:
                    flash('Check-out date must be after check-in date.', 'danger')
                    cur.close()
                    return redirect(url_for('book', room_id=room_id))
                
                nights = (check_out_date - check_in_date).days
                if nights <= 0:
                    nights = 1
            except ValueError:
                flash('Invalid date format.', 'danger')
                cur.close()
                return redirect(url_for('book', room_id=room_id))
            
            if current_available <= 0:
                flash('This room is fully booked.', 'danger')
                cur.close()
                return redirect(url_for('rooms'))
            
            # 5. HITUNG HARGA DENGAN PAJAK
            room_price = float(room['price'])
            
            # Hitung sub-total (harga kamar × malam)
            subtotal = room_price * nights
            
            # **HITUNG PAJAK DAN SERVICE CHARGE**
            # Asumsi: Tax 10% dan Service Charge 11% (total 21%)
            tax_rate = 0.10  # 10%
            service_rate = 0.11  # 11%
            
            tax_amount = subtotal * tax_rate
            service_charge = subtotal * service_rate
            
            # **TOTAL HARGA SETELAH PAJAK**
            total_price = subtotal + tax_amount + service_charge
            
            # 6. GENERATE KODE BOOKING
            import random, string
            def generate_booking_code():
                letters = ''.join(random.choices(string.ascii_uppercase, k=3))
                numbers = ''.join(random.choices(string.digits, k=6))
                return f"FH-{letters}-{numbers}"
            
            booking_code = generate_booking_code()
            
            # 7. SIMPAN BOOKING DENGAN HARGA YANG SUDAH PAJAK
            cur.execute("""
                INSERT INTO bookings 
                (user_id, room_id, check_in, check_out, guests, 
                total_price, subtotal, tax_amount, service_charge,
                special_requests, status, booking_code,
                guest_name, guest_email, guest_phone, guest_country)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'waiting_payment', %s, 
                        %s, %s, %s, %s)
            """, (
                session['user_id'], room_id, check_in, check_out, guests,
                total_price, subtotal, tax_amount, service_charge, 
                special_requests, booking_code,
                request.form.get('guest_name', ''),
                request.form.get('guest_email', ''),
                request.form.get('guest_phone', ''),
                request.form.get('guest_country', 'Indonesia')
            ))
            
            booking_id = cur.lastrowid
            
            # 8. BUAT RECORD PAYMENT
            expiration_date = datetime.now() + timedelta(hours=24)
            cur.execute("""
                INSERT INTO payments 
                (booking_id, amount, payment_method, status, expiration_date)
                VALUES (%s, %s, NULL, 'pending', %s)
            """, (booking_id, total_price, expiration_date))
            
            new_available_count = current_available - 1
            
            # 9. UPDATE ROOM AVAILABILITY
            cur.execute("""
                UPDATE rooms 
                SET available_count = %s,
                    is_available = CASE WHEN %s > 0 THEN 1 ELSE 0 END
                WHERE id = %s
            """, (new_available_count, new_available_count, room_id))
            
            mysql.connection.commit()
            cur.close()
            
            flash(f'Booking successful! Please complete payment.', 'success')
            
            return redirect(url_for('booking_success', booking_id=booking_id))
            
        except Exception as e:
            mysql.connection.rollback()
            cur.close()
            app.logger.exception('Booking creation failed for room %s', room_id)
            flash(f'Booking failed. Please try again.', 'danger')
            return redirect(url_for('book', room_id=room_id))
    
    room_id = request.args.get('room_id')
    cur = mysql.connection.cursor()
    
    if room_id:
        cur.execute("""
            SELECT *, 
                   CASE 
                       WHEN available_count <= 0 THEN 'Sold Out'
                       WHEN available_count <= 2 THEN CONCAT('Only ', available_count, ' left')
                       ELSE CONCAT(available_count, ' available')
                   END as availability_text
            FROM rooms 
            WHERE id = %s AND is_available = 1
        """, (room_id,))
    else:
        cur.execute("""
            SELECT *, 
                   CASE 
                       WHEN available_count <= 0 THEN 'Sold Out'
                       WHEN available_count <= 2 THEN CONCAT('Only ', available_count, ' left')
                       ELSE CONCAT(available_count, ' available')
                   END as availability_text
            FROM rooms 
            WHERE is_available = 1 
            LIMIT 1
        """)
    
    room = cur.fetchone()
    cur.close()
    
    if not room:
        flash('Room not available.', 'warning')
        return redirect(url_for('rooms'))
    
    room = dict(room)
    
    if room.get('images'):
        images_raw = room['images']
        if isinstance(images_raw, str):
            if images_raw.startswith('['):
                try:
                    room['images_list'] = json.loads(images_raw.replace("'", '"'))
                except json.JSONDecodeError:
                    room['images_list'] = [img.strip() for img in images_raw.split(',') if img.strip()]
            else:
                room['images_list'] = [images_raw] if images_raw.strip() else []
        else:
            room['images_list'] = []
    else:
        room['images_list'] = []
    
    # Process amenities for room
    if room.get('amenities'):
        amenities_raw = room['amenities']
        if isinstance(amenities_raw, str):
            if amenities_raw.startswith('['):
                try:
                    room['amenities_list'] = json.loads(amenities_raw.replace("'", '"'))
                except json.JSONDecodeError:
                    # Fallback: split by comma
                    room['amenities_list'] = [amenity.strip() for amenity in amenities_raw.split(',') if amenity.strip()]
            else:
                room['amenities_list'] = [amenities_raw] if amenities_raw.strip() else []
        else:
            room['amenities_list'] = []
    else:
        room['amenities_list'] = []
    
    # Add default amenities if empty
    if not room.get('amenities_list'):
        room['amenities_list'] = [
            "Free WiFi", 
            "Air Conditioning", 
            "Flat-screen TV", 
            "Private Bathroom"
        ]
    
    room['price'] = float(room.get('price', 0))
    room['formatted_price'] = f"Rp{room['price']:,.0f}".replace(',', '.')
    
    # Ensure room_type exists
    if not room.get('room_type'):
        room['room_type'] = 'standard'
    
    # Ensure capacity
    if not room.get('capacity'):
        room['capacity'] = 2
    
    # Default dates
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    day_after = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
    
    return render_template('booking/book.html', 
                         room=room,
                         default_checkin=tomorrow,
                         default_checkout=day_after,
                         min_checkin_date=tomorrow,
                         min_checkout_date=(datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
                         max_capacity=room.get('capacity', 4))

@app.route('/booking/success/<int:booking_id>')
@login_required
def booking_success(booking_id):
    cur = mysql.connection.cursor()
    
    cur.execute("""
        SELECT 
            b.*, 
            r.name as room_name, 
            r.images,
            r.price as room_price,
            r.available_count,
            u.first_name, 
            u.last_name, 
            u.email, 
            u.phone,
            p.status as payment_status,
            p.expiration_date as payment_expiry,
            p.id as payment_id
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        JOIN users u ON b.user_id = u.id
        LEFT JOIN payments p ON b.id = p.booking_id
        WHERE b.id = %s AND b.user_id = %s
    """, (booking_id, session['user_id']))
    
    booking = cur.fetchone()
    cur.close()
    
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('my_bookings'))
    
    # Konversi ke dict
    booking = dict(booking)
    
    # Format semua price
    if booking.get('subtotal'):
        booking['formatted_subtotal'] = "Rp{:,.0f}".format(float(booking['subtotal'])).replace(',', '.')
    
    if booking.get('tax_amount'):
        booking['formatted_tax'] = "Rp{:,.0f}".format(float(booking['tax_amount'])).replace(',', '.')
    
    if booking.get('service_charge'):
        booking['formatted_service'] = "Rp{:,.0f}".format(float(booking['service_charge'])).replace(',', '.')
    
    if booking.get('total_price'):
        booking['formatted_price'] = "Rp{:,.0f}".format(float(booking['total_price'])).replace(',', '.')
    
    # Hitung breakdown untuk ditampilkan
    if booking.get('subtotal') and booking.get('total_price'):
        subtotal = float(booking['subtotal'])
        total = float(booking['total_price'])
        
        if not booking.get('tax_amount') or not booking.get('service_charge'):
            tax_amount = subtotal * 0.10
            service_charge = subtotal * 0.11
            booking['tax_amount'] = tax_amount
            booking['service_charge'] = service_charge
            booking['formatted_tax'] = "Rp{:,.0f}".format(tax_amount).replace(',', '.')
            booking['formatted_service'] = "Rp{:,.0f}".format(service_charge).replace(',', '.')
    
    booking_created = booking.get('created_at')
    if isinstance(booking_created, str):
        try:
            booking_created = datetime.strptime(booking_created, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                booking_created = datetime.strptime(booking_created, '%Y-%m-%d')
            except:
                booking_created = datetime.now()

    if not isinstance(booking_created, datetime):
        booking_created = datetime.now()

    expiry_time = booking_created + timedelta(hours=24)
    time_left = expiry_time - datetime.now()

    if time_left.total_seconds() <= 0:
        hours_left = 0
        minutes_left = 0
        seconds_left = 0
        is_expired = True
        total_seconds = 0
        booking['countdown_display'] = "00:00:00"
    else:
        total_seconds = int(time_left.total_seconds())
        hours_left = total_seconds // 3600
        minutes_left = (total_seconds % 3600) // 60
        seconds_left = total_seconds % 60
        is_expired = False
        booking['countdown_display'] = f"{hours_left:02d}:{minutes_left:02d}:{seconds_left:02d}"

    booking['hours_left'] = hours_left
    booking['minutes_left'] = minutes_left
    booking['seconds_left'] = seconds_left
    booking['is_expired'] = is_expired
    booking['expiry_time'] = expiry_time.strftime('%d %b %Y %H:%M')
    booking['countdown_seconds'] = total_seconds if not is_expired else 0
    
    # Format untuk display
    if is_expired:
        booking['time_left_display'] = "EXPIRED"
    elif hours_left < 1:
        booking['time_left_display'] = f"{minutes_left}m left"
    else:
        booking['time_left_display'] = f"{hours_left}h {minutes_left}m left"
    
    return render_template('booking/success.html', booking=booking)

@app.route('/booking/payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def booking_payment(booking_id):
    cur = mysql.connection.cursor()
    
    # Ambil data booking dengan informasi lengkap
    cur.execute("""
        SELECT b.*, 
               r.name as room_name, 
               r.price as room_price,
               r.images as room_images,
               r.capacity as room_capacity
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE b.id = %s AND b.user_id = %s
    """, (booking_id, session['user_id']))
    
    booking_data = cur.fetchone()
    
    if not booking_data:
        flash('Booking not found.', 'danger')
        cur.close()
        return redirect(url_for('my_bookings'))
    
    # Cek apakah sudah ada payment
    cur.execute("SELECT * FROM payments WHERE booking_id = %s", (booking_id,))
    existing_payment = cur.fetchone()
    
    # Convert to dict untuk konsistensi
    booking = dict(booking_data) if booking_data else {}
    
    if booking.get('status') in ['cancelled', 'expired']:
        flash(f'Booking is already {booking.get("status")}. Cannot proceed with payment.', 'warning')
        cur.close()
        return redirect(url_for('my_bookings'))

    if booking.get('status') == 'confirmed':
        flash('Booking already confirmed. No payment needed.', 'info')
        cur.close()
        return redirect(url_for('booking_success', booking_id=booking_id))

    if existing_payment:
        payment_dict = dict(existing_payment) if existing_payment else {}
        payment_status = payment_dict.get('status')
        
        allowed_statuses = ['pending', 'failed', 'expired']
        completed_statuses = ['completed']

        if payment_status in completed_statuses:
            flash('Payment already submitted for this booking.', 'info')
            cur.close()
            return redirect(url_for('booking_success', booking_id=booking_id))
        elif payment_status == 'processing':
            flash('⚠️ Previous payment proof is being verified. Uploading new proof will replace the old one.', 'warning')
        elif payment_status not in allowed_statuses:
            flash(f'Cannot process payment with current status: {payment_status}', 'warning')
            cur.close()
            return redirect(url_for('booking_success', booking_id=booking_id))
    
    if request.method == 'POST':

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return handle_ajax_payment(booking_id, booking, cur)

        return handle_form_payment(booking_id, booking, cur)
    
    return prepare_booking_data_for_template(booking_id, booking, cur)

def handle_ajax_payment(booking_id, booking, cur):
    """Handle AJAX payment submission"""
    try:
        payment_method = request.form.get('payment_method')
        qris_simulated = request.form.get('qris_simulated', 'false')
        
        # Validasi payment method
        valid_methods = ['qris', 'bank_transfer', 'credit_card', 'ovo', 'gopay', 'dana']
        if payment_method not in valid_methods:
            return jsonify({
                'success': False,
                'error': 'Invalid payment method.'
            }), 400
        
        # Validasi file upload
        if 'payment_proof' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file selected.'
            }), 400
        
        proof_file = request.files['payment_proof']
        
        # Check if file is selected
        if proof_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected.'
            }), 400
        
        # Check file extension
        if not allowed_file(proof_file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Please upload JPG, PNG, or PDF.'
            }), 400
        
        # Check file size (max 5MB)
        proof_file.seek(0, os.SEEK_END)
        file_size = proof_file.tell()
        proof_file.seek(0)
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            return jsonify({
                'success': False,
                'error': 'File size must be less than 5MB.'
            }), 400
        
        # Generate unique filename
        filename = generate_payment_filename(booking_id, payment_method, proof_file.filename, qris_simulated)
        
        # Create directory jika belum ada
        os.makedirs(PAYMENT_UPLOAD_DIR, exist_ok=True)

        filepath = os.path.join(PAYMENT_UPLOAD_DIR, filename)
        stored_path = f"{PAYMENT_UPLOAD_PREFIX}/{filename}"
        
        try:
            # Save file
            proof_file.save(filepath)
            
            # Set expiration date (24 hours from now)
            expiration_date = datetime.now() + timedelta(hours=24)
            
            # Gunakan status 'processing'
            payment_status = 'processing'
            booking_status = 'waiting_payment'
            
            # Start transaction
            try:
                cur.execute("START TRANSACTION")
                cur.execute("SELECT id FROM payments WHERE booking_id = %s", (booking_id,))
                existing = cur.fetchone()

                if existing:
                    # Update existing payment
                    cur.execute("""
                        UPDATE payments 
                        SET amount = %s, 
                            payment_method = %s, 
                            proof_image = %s,
                            status = %s,
                            expiration_date = %s,
                            updated_at = NOW()
                        WHERE booking_id = %s
                    """, (booking.get('total_price', 0), payment_method, stored_path, 
                          payment_status, expiration_date, booking_id))
                else:
                    # Insert new payment record
                    cur.execute("""
                        INSERT INTO payments (booking_id, amount, payment_method, proof_image, 
                                            status, expiration_date, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (booking_id, booking.get('total_price', 0), payment_method, stored_path, 
                          payment_status, expiration_date))
                
                # Update booking status
                cur.execute("""
                    UPDATE bookings 
                    SET status = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (booking_status, booking_id))
                
                cur.execute("COMMIT")
                
                cur.close()
                
                return jsonify({
                    'success': True,
                    'message': 'Payment proof uploaded successfully! Admin will verify within 1-2 hours.',
                    'redirect': url_for('booking_success', booking_id=booking_id)
                })
                
            except Exception as db_error:
                cur.execute("ROLLBACK")
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except:
                        pass
                
                app.logger.exception('Payment processing failed for booking %s', booking_id)
                return jsonify({
                    'success': False,
                    'error': 'Payment processing failed. Please try again.'
                }), 500
                
        except Exception as file_error:
            app.logger.exception('Failed to save payment proof for booking %s', booking_id)
            return jsonify({
                'success': False,
                'error': 'Failed to save payment proof. Please try again.'
            }), 500
            
    except Exception as e:
        app.logger.exception('Unexpected error while processing payment for booking %s', booking_id)
        return jsonify({
            'success': False,
            'error': 'Unexpected error. Please try again.'
        }), 500

def handle_form_payment(booking_id, booking, cur):
    """Handle traditional form payment submission"""
    payment_method = request.form.get('payment_method')
    qris_simulated = request.form.get('qris_simulated')
    
    # Validasi payment method
    valid_methods = ['qris', 'bank_transfer', 'credit_card', 'ovo', 'gopay', 'dana']
    if payment_method not in valid_methods:
        flash('Invalid payment method.', 'danger')
        cur.close()
        return redirect(url_for('booking_payment', booking_id=booking_id))
    
    # Validasi file upload
    if 'payment_proof' not in request.files:
        flash('No file selected.', 'danger')
        cur.close()
        return redirect(url_for('booking_payment', booking_id=booking_id))
    
    proof_file = request.files['payment_proof']
    
    # Check if file is selected
    if proof_file.filename == '':
        flash('No file selected.', 'danger')
        cur.close()
        return redirect(url_for('booking_payment', booking_id=booking_id))
    
    # Check file extension
    if not allowed_file(proof_file.filename):
        flash('Invalid file type. Please upload JPG, PNG, or PDF.', 'danger')
        cur.close()
        return redirect(url_for('booking_payment', booking_id=booking_id))
    
    # Check file size (max 5MB)
    proof_file.seek(0, os.SEEK_END)
    file_size = proof_file.tell()
    proof_file.seek(0)
    
    if file_size > 5 * 1024 * 1024:  # 5MB
        flash('File size must be less than 5MB.', 'danger')
        cur.close()
        return redirect(url_for('booking_payment', booking_id=booking_id))
    
    # Generate unique filename
    filename = generate_payment_filename(booking_id, payment_method, proof_file.filename, qris_simulated)
    
    uploads_dir = PAYMENT_UPLOAD_DIR
    os.makedirs(uploads_dir, exist_ok=True)

    filepath = os.path.join(uploads_dir, filename)
    stored_path = f"{PAYMENT_UPLOAD_PREFIX}/{filename}"
    
    try:
        # Save file
        proof_file.save(filepath)
        
        # Set expiration date (24 hours from now)
        expiration_date = datetime.now() + timedelta(hours=24)
        
        # Gunakan status 'processing'
        payment_status = 'processing'
        booking_status = 'waiting_payment'
        
        # Start transaction
        try:
            cur.execute("START TRANSACTION")
            cur.execute("SELECT id FROM payments WHERE booking_id = %s", (booking_id,))
            existing = cur.fetchone()

            if existing:
                cur.execute("""
                    UPDATE payments 
                    SET amount = %s, 
                        payment_method = %s, 
                        proof_image = %s,
                        status = %s,
                        expiration_date = %s,
                        updated_at = NOW()
                    WHERE booking_id = %s
                """, (booking.get('total_price', 0), payment_method, stored_path, 
                      payment_status, expiration_date, booking_id))
            else:
                # Insert new payment record
                cur.execute("""
                    INSERT INTO payments (booking_id, amount, payment_method, proof_image, 
                                        status, expiration_date, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (booking_id, booking.get('total_price', 0), payment_method, stored_path, 
                      payment_status, expiration_date))
            
            # Update booking status
            cur.execute("""
                UPDATE bookings 
                SET status = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (booking_status, booking_id))
            
            cur.execute("COMMIT")
            
            flash_messages = {
                'qris': 'QRIS payment proof uploaded! Admin will verify within 1-2 hours.',
                'bank_transfer': 'Bank transfer proof uploaded! Admin will verify within 1-2 hours.',
                'credit_card': 'Credit card payment proof uploaded! Admin will verify your payment.',
                'ovo': 'OVO payment proof uploaded! Admin will verify your payment.',
                'gopay': 'GoPay payment proof uploaded! Admin will verify your payment.',
                'dana': 'DANA payment proof uploaded! Admin will verify your payment.'
            }
            
            flash_message = flash_messages.get(payment_method, 'Payment proof uploaded successfully!')
            flash(flash_message, 'success')
            
            cur.close()
            return redirect(url_for('booking_success', booking_id=booking_id))
            
        except Exception:
            cur.execute("ROLLBACK")
            # Delete uploaded file if database error
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            
            app.logger.exception('Payment processing failed for booking %s', booking_id)
            flash('Payment processing failed. Please try again.', 'danger')
            cur.close()
            return redirect(url_for('booking_payment', booking_id=booking_id))
            
    except Exception:
        app.logger.exception('Failed to save payment proof for booking %s', booking_id)
        flash('Failed to save payment proof. Please try again.', 'danger')
        cur.close()
        return redirect(url_for('booking_payment', booking_id=booking_id))

def generate_payment_filename(booking_id, payment_method, original_filename, qris_simulated):
    """Generate unique filename for payment proof"""
    secure_name = secure_filename(original_filename)
    file_extension = secure_name.rsplit('.', 1)[1].lower() if '.' in secure_name else ''
    unique_id = uuid.uuid4().hex[:8]
    timestamp = int(time.time())
    
    base_name = f"payment_{booking_id}_{payment_method}_{timestamp}_{unique_id}"
    
    # For QRIS simulated, add note to filename
    if payment_method == 'qris' and qris_simulated == 'true':
        base_name = f"qris_simulated_{base_name}"
    
    return f"{base_name}.{file_extension}" if file_extension else base_name

def prepare_booking_data_for_template(booking_id, booking, cur):
    """Prepare booking data for template rendering"""
    # Parse room images
    images_list = parse_images_data(booking.get('room_images'), default_dir='images/rooms')
    booking['room_main_image'] = images_list[0] if images_list else None
    booking['room_images_list'] = images_list
    
    # Format price
    if booking.get('total_price'):
        try:
            booking['formatted_price'] = "Rp{:,.0f}".format(float(booking['total_price']))
        except:
            booking['formatted_price'] = "Rp0"
    else:
        booking['formatted_price'] = "Rp0"
    
    # Ensure room_price exists
    booking['room_price'] = booking.get('room_price', 0)

    
    # Booking code
    if not booking.get('booking_code'):
        booking['booking_code'] = f"FH{booking.get('id', 0):06d}"
    
    # Format dates
    if booking.get('check_in'):
        if isinstance(booking['check_in'], str):
            try:
                check_in_dt = datetime.strptime(booking['check_in'], '%Y-%m-%d')
                booking['check_in_formatted'] = check_in_dt.strftime('%d %b %Y')
            except:
                booking['check_in_formatted'] = booking['check_in']
        else:
            try:
                booking['check_in_formatted'] = booking['check_in'].strftime('%d %b %Y')
            except:
                booking['check_in_formatted'] = 'Not set'
    else:
        booking['check_in_formatted'] = 'Not set'
    
    if booking.get('check_out'):
        if isinstance(booking['check_out'], str):
            try:
                check_out_dt = datetime.strptime(booking['check_out'], '%Y-%m-%d')
                booking['check_out_formatted'] = check_out_dt.strftime('%d %b %Y')
            except:
                booking['check_out_formatted'] = booking['check_out']
        else:
            try:
                booking['check_out_formatted'] = booking['check_out'].strftime('%d %b %Y')
            except:
                booking['check_out_formatted'] = 'Not set'
    else:
        booking['check_out_formatted'] = 'Not set'
    
    # Calculate nights
    try:
        check_in_date = None
        check_out_date = None
        
        # Try to parse check_in
        if booking.get('check_in'):
            if isinstance(booking['check_in'], datetime):
                check_in_date = booking['check_in']
            elif isinstance(booking['check_in'], str):
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d %b %Y', '%Y/%m/%d']:
                    try:
                        check_in_date = datetime.strptime(booking['check_in'], fmt)
                        break
                    except:
                        continue
        
        # Try to parse check_out
        if booking.get('check_out'):
            if isinstance(booking['check_out'], datetime):
                check_out_date = booking['check_out']
            elif isinstance(booking['check_out'], str):
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d %b %Y', '%Y/%m/%d']:
                    try:
                        check_out_date = datetime.strptime(booking['check_out'], fmt)
                        break
                    except:
                        continue
        
        if check_in_date and check_out_date and check_out_date > check_in_date:
            booking['nights'] = (check_out_date - check_in_date).days
            if booking['nights'] <= 0:
                booking['nights'] = 1
        else:
            booking['nights'] = 1
            
    except Exception:
        booking['nights'] = 1
    
    booking_created = booking.get('created_at')
    if isinstance(booking_created, str):
        try:
            booking_created = datetime.strptime(booking_created, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                booking_created = datetime.strptime(booking_created, '%Y-%m-%d')
            except:
                booking_created = datetime.now()
    
    if not isinstance(booking_created, datetime):
        booking_created = datetime.now()
    
    expiry_time = booking_created + timedelta(hours=24)
    time_left = expiry_time - datetime.now()
    
    if time_left.total_seconds() <= 0:
        hours_left = 0
        minutes_left = 0
        seconds_left = 0
        is_expired = True
        total_seconds = 0
    else:
        total_seconds = int(time_left.total_seconds())
        hours_left = total_seconds // 3600
        minutes_left = (total_seconds % 3600) // 60
        seconds_left = total_seconds % 60
        is_expired = False
    
    booking['hours_left'] = hours_left
    booking['minutes_left'] = minutes_left
    booking['seconds_left'] = seconds_left
    booking['is_expired'] = is_expired
    booking['expiry_time'] = expiry_time.strftime('%d %b %Y %H:%M')
    booking['countdown_seconds'] = total_seconds if not is_expired else 0
    booking['countdown_display'] = f"{hours_left:02d}:{minutes_left:02d}:{seconds_left:02d}"
    
    # Ensure room name exists
    if not booking.get('room_name'):
        booking['room_name'] = 'Room'
    
    # Ensure guests exists
    if not booking.get('guests'):
        booking['guests'] = 1
    
    cur.close()
    return render_template('booking/payment.html', booking=booking)
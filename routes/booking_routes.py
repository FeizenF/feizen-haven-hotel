from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, send_file
from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, send_file
from config import app, mysql
from models import login_required, allowed_file
import os
from datetime import datetime, timedelta
import json
import time
import uuid
from werkzeug.utils import secure_filename
from models import allowed_file

# =============== BOOKING ROUTES ===============
@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    if request.method == 'POST':
        room_id = request.form.get('room_id')
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        guests = int(request.form.get('guests', 2))
        special_requests = request.form.get('special_requests', '')
        
        cur = mysql.connection.cursor()
        
        try:
            print(f"\n=== DEBUG: START BOOKING PROCESS ===")
            print(f"Room ID: {room_id}, Dates: {check_in} to {check_out}")
            
            # 1. CEK KAMAR TERSEDIA DENGAN LOCK ROW
            cur.execute("""
                SELECT * FROM rooms 
                WHERE id = %s AND is_available = 1 AND available_count > 0
                FOR UPDATE
            """, (room_id,))
            
            room = cur.fetchone()
            
            if not room:
                print(f"DEBUG: Room {room_id} not available")
                flash('Room not available or fully booked.', 'danger')
                cur.close()
                return redirect(url_for('rooms'))
            
            room = dict(room)
            current_available = room['available_count']
            
            print(f"DEBUG: Room {room['name']}")
            print(f"  - Current available_count: {current_available}")
            print(f"  - Room count: {room['room_count']}")
            
            # 2. VALIDASI KAPASITAS
            if guests > room['capacity']:
                flash(f'Maximum capacity for this room is {room["capacity"]} guests.', 'danger')
                cur.close()
                return redirect(url_for('book', room_id=room_id))
            
            # 3. VALIDASI TANGGAL
            try:
                check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
                check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
                
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
            
            print(f"DEBUG: Price Calculation")
            print(f"  - Room price per night: Rp{room_price:,.0f}")
            print(f"  - Nights: {nights}")
            print(f"  - Subtotal: Rp{subtotal:,.0f}")
            print(f"  - Tax (10%): Rp{tax_amount:,.0f}")
            print(f"  - Service Charge (11%): Rp{service_charge:,.0f}")
            print(f"  - TOTAL: Rp{total_price:,.0f}")
            
            # 6. GENERATE KODE BOOKING
            import random, string
            def generate_booking_code():
                letters = ''.join(random.choices(string.ascii_uppercase, k=3))
                numbers = ''.join(random.choices(string.digits, k=6))
                return f"FH-{letters}-{numbers}"
            
            booking_code = generate_booking_code()
            
            print(f"DEBUG: Creating booking with code {booking_code}")
            
            # 7. SIMPAN BOOKING DENGAN HARGA YANG SUDAH PAJAK
            cur.execute("""
                INSERT INTO bookings 
                (user_id, room_id, check_in, check_out, guests, 
                total_price, subtotal, tax_amount, service_charge,  -- PERHATIKAN URUTAN!
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
                VALUES (%s, %s, 'pending', 'pending', %s)
            """, (booking_id, total_price, expiration_date))
            
            new_available_count = current_available - 1
            
            print(f"DEBUG: Updating room availability")
            print(f"  - From: {current_available}")
            print(f"  - To: {new_available_count}")
            
            # 9. UPDATE ROOM AVAILABILITY
            cur.execute("""
                UPDATE rooms 
                SET available_count = %s,
                    is_available = CASE WHEN %s > 0 THEN 1 ELSE 0 END
                WHERE id = %s
            """, (new_available_count, new_available_count, room_id))
            
            mysql.connection.commit()
            cur.close()
            
            print(f"=== DEBUG: BOOKING SUCCESS ===")
            print(f"Booking ID: {booking_id}")
            print(f"Booking Code: {booking_code}")
            print(f"Total Price (with tax): Rp{total_price:,.0f}")
            print(f"New available_count for room {room_id}: {new_available_count}")
            
            flash(f'Booking successful! Please complete payment.', 'success')
            
            return redirect(url_for('booking_success', booking_id=booking_id))
            
        except Exception as e:
            mysql.connection.rollback()
            cur.close()
            print(f"DEBUG: BOOKING ERROR - {str(e)}")
            flash(f'Booking failed. Please try again.', 'danger')
            return redirect(url_for('book', room_id=room_id))
    
    room_id = request.args.get('room_id')
    cur = mysql.connection.cursor()
    
    print(f"\n=== DEBUG: GET BOOK PAGE ===")
    print(f"Requested room_id: {room_id}")
    
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
        print(f"DEBUG: Room not found or not available")
        flash('Room not available.', 'warning')
        return redirect(url_for('rooms'))
    
    room = dict(room)
    
    print(f"DEBUG: Displaying room {room['name']}")
    print(f"  - Available: {room.get('available_count')}")
    print(f"  - Availability text: {room.get('availability_text')}")
    
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

def fix_payment_paths():
    cur = mysql.connection.cursor()
    
    cur.execute("SELECT id, proof_image FROM payments WHERE proof_image IS NOT NULL")
    payments = cur.fetchall()
    
    for payment in payments:
        old_path = payment['proof_image']
        payment_id = payment['id']
        
        if not old_path:
            continue
        
        if old_path.startswith('static/'):
            print(f"✅ Payment {payment_id}: Path sudah benar - {old_path}")
            continue
        
        if '/' not in old_path:
            new_path = f"images/uploads/payments/{old_path}"
            print(f"🔄 Payment {payment_id}: Update '{old_path}' -> '{new_path}'")
            
            cur.execute("UPDATE payments SET proof_image = %s WHERE id = %s", 
                       (new_path, payment_id))
        
        elif 'static/images/uploads/payments/' in old_path:
            new_path = old_path.replace('static/', '')
            print(f"🔄 Payment {payment_id}: Fix static path '{old_path}' -> '{new_path}'")
            
            cur.execute("UPDATE payments SET proof_image = %s WHERE id = %s", 
                       (new_path, payment_id))
    
    mysql.connection.commit()
    cur.close()
    print("Migration completed!")

@app.route('/booking/payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def booking_payment(booking_id):
    cur = mysql.connection.cursor()
    
    print(f"=== DEBUG booking_payment for booking_id={booking_id} ===")
    
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
        completed_statuses = ['completed', 'processing']
        
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
        uploads_dir = os.path.join('uploads', 'payments')
        os.makedirs(uploads_dir, exist_ok=True)
        
        filepath = os.path.join(uploads_dir, filename)
        
        try:
            # Save file
            proof_file.save(filepath)
            print(f"DEBUG: Payment proof saved: {filepath}")
            
            # Set expiration date (24 hours from now)
            expiration_date = datetime.now() + timedelta(hours=24)
            
            # Gunakan status 'processing'
            payment_status = 'processing'
            booking_status = 'waiting_payment'
            
            # Start transaction
            try:
                cur.execute("START TRANSACTION")
                if cur.execute("SELECT id FROM payments WHERE booking_id = %s", (booking_id,)):
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
                    """, (booking.get('total_price', 0), payment_method, filename, 
                          payment_status, expiration_date, booking_id))
                else:
                    # Insert new payment record
                    cur.execute("""
                        INSERT INTO payments (booking_id, amount, payment_method, proof_image, 
                                            status, expiration_date, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (booking_id, booking.get('total_price', 0), payment_method, filename, 
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
                
                print(f"Database error: {db_error}")
                return jsonify({
                    'success': False,
                    'error': f'Payment processing failed: {str(db_error)}'
                }), 500
                
        except Exception as file_error:
            print(f"File save error: {file_error}")
            return jsonify({
                'success': False,
                'error': f'Failed to save payment proof: {str(file_error)}'
            }), 500
            
    except Exception as e:
        print(f"General error: {e}")
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
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
        return render_template('booking/payment.html', booking=booking)
    
    # Validasi file upload
    if 'payment_proof' not in request.files:
        flash('No file selected.', 'danger')
        cur.close()
        return render_template('booking/payment.html', booking=booking)
    
    proof_file = request.files['payment_proof']
    
    # Check if file is selected
    if proof_file.filename == '':
        flash('No file selected.', 'danger')
        cur.close()
        return render_template('booking/payment.html', booking=booking)
    
    # Check file extension
    if not allowed_file(proof_file.filename):
        flash('Invalid file type. Please upload JPG, PNG, or PDF.', 'danger')
        cur.close()
        return render_template('booking/payment.html', booking=booking)
    
    # Check file size (max 5MB)
    proof_file.seek(0, os.SEEK_END)
    file_size = proof_file.tell()
    proof_file.seek(0)
    
    if file_size > 5 * 1024 * 1024:  # 5MB
        flash('File size must be less than 5MB.', 'danger')
        cur.close()
        return render_template('booking/payment.html', booking=booking)
    
    # Generate unique filename
    filename = generate_payment_filename(booking_id, payment_method, proof_file.filename, qris_simulated)
    
    uploads_dir = os.path.join('uploads', 'payments')
    os.makedirs(uploads_dir, exist_ok=True)
    
    filepath = os.path.join(uploads_dir, filename)
    
    try:
        # Save file
        proof_file.save(filepath)
        print(f"DEBUG: Payment proof saved: {filepath}")
        
        # Set expiration date (24 hours from now)
        expiration_date = datetime.now() + timedelta(hours=24)
        
        # Gunakan status 'processing'
        payment_status = 'processing'
        booking_status = 'waiting_payment'
        
        # Start transaction
        try:
            cur.execute("START TRANSACTION")

            if cur.execute("SELECT id FROM payments WHERE booking_id = %s", (booking_id,)):
                cur.execute("""
                    UPDATE payments 
                    SET amount = %s, 
                        payment_method = %s, 
                        proof_image = %s,
                        status = %s,
                        expiration_date = %s,
                        updated_at = NOW()
                    WHERE booking_id = %s
                """, (booking.get('total_price', 0), payment_method, filename, 
                      payment_status, expiration_date, booking_id))
            else:
                # Insert new payment record
                cur.execute("""
                    INSERT INTO payments (booking_id, amount, payment_method, proof_image, 
                                        status, expiration_date, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (booking_id, booking.get('total_price', 0), payment_method, filename, 
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
            
        except Exception as db_error:
            cur.execute("ROLLBACK")
            # Delete uploaded file if database error
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            
            print(f"Database error: {db_error}")
            flash(f'Payment processing failed: {str(db_error)}', 'danger')
            cur.close()
            return render_template('booking/payment.html', booking=booking)
            
    except Exception as file_error:
        print(f"File save error: {file_error}")
        flash(f' Failed to save payment proof: {str(file_error)}', 'danger')
        cur.close()
        return render_template('booking/payment.html', booking=booking)

def generate_payment_filename(booking_id, payment_method, original_filename, qris_simulated):
    """Generate unique filename for payment proof"""
    secure_name = secure_filename(original_filename)
    file_extension = secure_name.rsplit('.', 1)[1].lower() if '.' in secure_name else ''
    unique_id = uuid.uuid4().hex[:8]
    timestamp = int(time.time())
    
    if file_extension:
        base_name = f"payment_{booking_id}_{payment_method}_{timestamp}_{unique_id}"
    else:
        base_name = f"payment_{booking_id}_{payment_method}_{timestamp}_{unique_id}"
    
    # For QRIS simulated, add note to filename
    if payment_method == 'qris' and qris_simulated == 'true':
        base_name = f"qris_simulated_{base_name}"
    
    return f"{base_name}.{file_extension}" if file_extension else base_name

def prepare_booking_data_for_template(booking_id, booking, cur):
    """Prepare booking data for template rendering"""
    # Parse room images
    if booking.get('room_images'):
        try:
            if isinstance(booking['room_images'], str):
                try:
                    images_list = json.loads(booking['room_images'])
                except json.JSONDecodeError:
                    images_list = [img.strip() for img in booking['room_images'].split(',') if img.strip()]
            else:
                images_list = []
            
            if images_list and len(images_list) > 0:
                # Ensure the path is correct
                first_image = images_list[0]
                if not first_image.startswith(('http', '/static', '/')):
                    booking['room_main_image'] = url_for('static', filename=f'images/rooms/{first_image}')
                else:
                    booking['room_main_image'] = first_image
            else:
                booking['room_main_image'] = None
        except Exception as e:
            print(f"Error parsing room images: {e}")
            booking['room_main_image'] = None
    else:
        booking['room_main_image'] = None
    
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
            
    except Exception as e:
        print(f"Error calculating nights: {e}")
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
    
    print(f"DEBUG - Booking {booking_id}: {hours_left}h {minutes_left}m {seconds_left}s left")
    
    # Ensure room name exists
    if not booking.get('room_name'):
        booking['room_name'] = 'Room'
    
    # Ensure guests exists
    if not booking.get('guests'):
        booking['guests'] = 1
    
    cur.close()
    return render_template('booking/payment.html', booking=booking)
from flask import render_template, request, redirect, url_for, flash, session
from config import app, mysql
from models import login_required
import json
from datetime import datetime, timedelta

@app.route('/profile')
@login_required
def profile():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cur.fetchone()
    
    cur.execute("""
        SELECT 
            COUNT(*) as total_bookings,
            SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_bookings,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_bookings,
            SUM(total_price) as total_spent
        FROM bookings 
        WHERE user_id = %s
    """, (session['user_id'],))
    
    stats = cur.fetchone()
    cur.close()
    
    return render_template('user/profile.html', user=user, stats=stats)

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    phone = request.form.get('phone')
    
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE users 
        SET first_name = %s, last_name = %s, phone = %s
        WHERE id = %s
    """, (first_name, last_name, phone, session['user_id']))
    
    mysql.connection.commit()
    cur.close()
    
    session['name'] = f"{first_name} {last_name}"
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))


@app.route('/my_bookings')
@login_required
def my_bookings():
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            b.*, 
            r.name as room_name, 
            r.images,
            r.price as room_price,
            p.status as payment_status,
            p.payment_method,
            p.proof_image,
            p.created_at as payment_date,
            p.expiration_date as payment_expiry,
            p.updated_at as payment_updated
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        LEFT JOIN payments p ON b.id = p.booking_id
        WHERE b.user_id = %s
        ORDER BY b.created_at DESC
    """, (session['user_id'],))
    
    bookings = cur.fetchall()
    cur.close()
    
    processed_bookings = []
    for booking in bookings:
        booking_dict = dict(booking)
        
        from datetime import datetime, timedelta
        
        if booking_dict.get('check_in'):
            if isinstance(booking_dict['check_in'], str):
                booking_dict['check_in_formatted'] = booking_dict['check_in']
            else:
                try:
                    booking_dict['check_in_formatted'] = booking_dict['check_in'].strftime('%d %b %Y')
                except:
                    booking_dict['check_in_formatted'] = 'N/A'
        

        if booking_dict.get('check_out'):
            if isinstance(booking_dict['check_out'], str):
                booking_dict['check_out_formatted'] = booking_dict['check_out']
            else:
                try:
                    booking_dict['check_out_formatted'] = booking_dict['check_out'].strftime('%d %b %Y')
                except:
                    booking_dict['check_out_formatted'] = 'N/A'
        
        if booking_dict.get('created_at'):
            if isinstance(booking_dict['created_at'], str):
                booking_dict['created_formatted'] = booking_dict['created_at']
            else:
                try:
                    booking_dict['created_formatted'] = booking_dict['created_at'].strftime('%d %b %Y %H:%M')
                except:
                    booking_dict['created_formatted'] = 'N/A'
        
        try:
            check_in = None
            check_out = None
            
            if booking_dict.get('check_in'):
                if isinstance(booking_dict['check_in'], datetime):
                    check_in = booking_dict['check_in']
                elif isinstance(booking_dict['check_in'], str):
                    try:
                        check_in = datetime.strptime(booking_dict['check_in'], '%Y-%m-%d')
                    except:
             
                        try:
                            check_in = datetime.strptime(booking_dict['check_in'], '%d %b %Y')
                        except:
                            pass
            

            if booking_dict.get('check_out'):
                if isinstance(booking_dict['check_out'], datetime):
                    check_out = booking_dict['check_out']
                elif isinstance(booking_dict['check_out'], str):
                    try:
                        check_out = datetime.strptime(booking_dict['check_out'], '%Y-%m-%d')
                    except:
                   
                        try:
                            check_out = datetime.strptime(booking_dict['check_out'], '%d %b %Y')
                        except:
                            pass
            
            if check_in and check_out and check_out > check_in:
                booking_dict['nights'] = (check_out - check_in).days
            else:
                booking_dict['nights'] = 1
        except Exception as e:
            print(f"Error calculating nights: {e}")
            booking_dict['nights'] = 1
        
        if booking_dict.get('total_price'):
            try:
                price = float(booking_dict['total_price'])
                booking_dict['formatted_price'] = f"Rp{price:,.0f}".replace(',', '.')
            except:
                booking_dict['formatted_price'] = "Rp0"
        else:
            booking_dict['formatted_price'] = "Rp0"
        
        if not booking_dict.get('booking_code'):
            booking_dict['booking_code'] = f"FH{booking_dict.get('id', '00000'):06d}"
        
        booking_created = booking_dict.get('created_at')
        current_time = datetime.now()
        
        if isinstance(booking_created, str):
            try:

                booking_created = datetime.strptime(booking_created, '%Y-%m-%d %H:%M:%S')
            except:
                try:

                    booking_created = datetime.strptime(booking_created, '%Y-%m-%d')
                except:
                    try:

                        booking_created = datetime.strptime(booking_created, '%d %b %Y %H:%M')
                    except:
                        booking_created = current_time
        
        if not isinstance(booking_created, datetime):
            booking_created = current_time
        
        expiry_time = booking_created + timedelta(hours=24)
        time_left = expiry_time - current_time
        
        if time_left.total_seconds() <= 0:
            booking_dict['hours_left'] = 0
            booking_dict['minutes_left'] = 0
            booking_dict['is_expired'] = True
            booking_dict['time_left_display'] = "EXPIRED"
            
            if booking_dict.get('status') == 'waiting_payment':
                try:
                    cur2 = mysql.connection.cursor()
                    cur2.execute("""
                        UPDATE bookings 
                        SET status = 'expired', updated_at = NOW() 
                        WHERE id = %s AND status = 'waiting_payment'
                    """, (booking_dict['id'],))
                    
                    if booking_dict.get('payment_status') in ['pending', 'processing']:
                        cur2.execute("""
                            UPDATE payments 
                            SET status = 'expired', updated_at = NOW() 
                            WHERE booking_id = %s AND status IN ('pending', 'processing')
                        """, (booking_dict['id'],))
                    
                    mysql.connection.commit()
                    cur2.close()
                    
                    booking_dict['status'] = 'expired'
                    booking_dict['payment_status'] = 'expired'
                    
                except Exception as e:
                    print(f"Error auto-expiring booking {booking_dict['id']}: {e}")
        else:
            total_seconds = int(time_left.total_seconds())
            booking_dict['hours_left'] = total_seconds // 3600
            booking_dict['minutes_left'] = (total_seconds % 3600) // 60
            
            booking_dict['is_expired'] = False
            
            if booking_dict['hours_left'] < 1:
                booking_dict['time_left_display'] = f"{booking_dict['minutes_left']}m left"
            else:
                booking_dict['time_left_display'] = f"{booking_dict['hours_left']}h {booking_dict['minutes_left']}m left"
        
        if booking_dict.get('payment_method'):
            payment_method_display = {
                'qris': 'QRIS',
                'bank_transfer': 'Bank Transfer',
                'credit_card': 'Credit Card',
                'ovo': 'OVO',
                'gopay': 'GoPay',
                'dana': 'DANA',
                'pending': 'Not Selected'
            }
            booking_dict['payment_method_display'] = payment_method_display.get(
                booking_dict['payment_method'],
                booking_dict['payment_method'].replace('_', ' ').title()
            )
        else:
            booking_dict['payment_method_display'] = 'Not Selected'
        
        booking_status = booking_dict.get('status', '')
        payment_status = booking_dict.get('payment_status', '')
        
        if booking_status == 'confirmed':
            booking_dict['status_bg_color'] = 'bg-green-100'
            booking_dict['status_text_color'] = 'text-green-800'
        elif booking_status == 'waiting_payment':
            booking_dict['status_bg_color'] = 'bg-yellow-100'
            booking_dict['status_text_color'] = 'text-yellow-800'
        elif booking_status == 'pending':
            booking_dict['status_bg_color'] = 'bg-blue-100'
            booking_dict['status_text_color'] = 'text-blue-800'
        elif booking_status in ['cancelled', 'expired']:
            booking_dict['status_bg_color'] = 'bg-red-100'
            booking_dict['status_text_color'] = 'text-red-800'
        else:
            booking_dict['status_bg_color'] = 'bg-gray-100'
            booking_dict['status_text_color'] = 'text-gray-800'
        
        if payment_status == 'completed':
            booking_dict['payment_status_bg_color'] = 'bg-green-100'
            booking_dict['payment_status_text_color'] = 'text-green-800'
        elif payment_status == 'processing':
            booking_dict['payment_status_bg_color'] = 'bg-yellow-100'
            booking_dict['payment_status_text_color'] = 'text-yellow-800'
        elif payment_status in ['failed', 'expired']:
            booking_dict['payment_status_bg_color'] = 'bg-red-100'
            booking_dict['payment_status_text_color'] = 'text-red-800'
        elif payment_status == 'pending':
            booking_dict['payment_status_bg_color'] = 'bg-blue-100'
            booking_dict['payment_status_text_color'] = 'text-blue-800'
        else:
            booking_dict['payment_status_bg_color'] = 'bg-gray-100'
            booking_dict['payment_status_text_color'] = 'text-gray-800'
        
        processed_bookings.append(booking_dict)
    
    return render_template('user/bookings.html', bookings=processed_bookings)

@app.route('/booking/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    cur = mysql.connection.cursor()
    
    try:
        print(f"\n=== DEBUG: CANCEL BOOKING {booking_id} ===")
        
        cur.execute("""
            SELECT b.*, r.available_count as room_available
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            WHERE b.id = %s AND b.user_id = %s
        """, (booking_id, session['user_id']))
        
        booking = cur.fetchone()
        
        if not booking:
            flash('Booking not found.', 'danger')
            cur.close()
            return redirect(url_for('my_bookings'))
        
        booking = dict(booking)
        
        print(f"DEBUG: Found booking {booking.get('booking_code')}")
        print(f"  - Status: {booking.get('status')}")
        print(f"  - Room ID: {booking.get('room_id')}")
        print(f"  - Room current available: {booking.get('room_available')}")
        
        if booking['status'] not in ['pending', 'waiting_payment']:
            flash(f'Cannot cancel booking with status: {booking["status"]}', 'warning')
            cur.close()
            return redirect(url_for('my_bookings'))
        
        current_available = booking.get('room_available', 0)
        new_available = current_available + 1
        
        print(f"DEBUG: Updating room availability")
        print(f"  - From: {current_available}")
        print(f"  - To: {new_available}")
        
        # Update booking status
        cur.execute("""
            UPDATE bookings 
            SET status = 'cancelled',
                payment_status = 'failed'
            WHERE id = %s
        """, (booking_id,))
        
        # Update room availability
        room_id = booking['room_id']
        cur.execute("""
            UPDATE rooms 
            SET available_count = %s,
                is_available = CASE WHEN %s > 0 THEN 1 ELSE 0 END
            WHERE id = %s
        """, (new_available, new_available, room_id))
        
        # Update payment jika ada
        cur.execute("""
            UPDATE payments 
            SET status = 'failed'
            WHERE booking_id = %s
        """, (booking_id,))
        
        mysql.connection.commit()
        
        print(f"DEBUG: Cancellation successful")
        
        flash(f'✅ Booking {booking.get("booking_code", f"#{booking_id}")} cancelled successfully.', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        print(f"DEBUG: CANCEL ERROR - {str(e)}")
        flash('❌ Failed to cancel booking.', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('my_bookings'))

@app.route('/users')
def get_users():
    """Get all users - pure JSON response (like SQLAlchemy but with MySQLdb)"""
    try:

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
        cur.close()
        
        return {
            'users': users,
            'count': len(users),
            'message': 'Data fetched successfully using MySQLdb',
            'technology': 'Flask-MySQLdb',
            'format': 'JSON (no HTML)'
        }
    except Exception as e:
        return {'error': str(e)}, 500
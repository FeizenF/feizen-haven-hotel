from flask import render_template, request, redirect, url_for, flash
from config import app, mysql
from helpers import (
    process_room_data,
    process_facility_data
)

# PUBLIC ROUTES 
@app.route('/')
def index():
    cur = mysql.connection.cursor()
    
    cur.execute("""
        SELECT * FROM rooms 
        WHERE is_available = 1 
        ORDER BY price ASC 
        LIMIT 3
    """)
    featured_rooms_data = cur.fetchall()
    
    featured_rooms = [process_room_data(room) for room in featured_rooms_data]
    
    cur.execute("SELECT * FROM venues WHERE is_available = 1 LIMIT 6")
    venues_data = cur.fetchall()
    
    venues_list = [process_facility_data(venue) for venue in venues_data]
    
    cur.close()
    
    return render_template('main/index.html', 
                         featured_rooms=featured_rooms,
                         venues=venues_list)

@app.route('/about')
def about():
    return render_template('main/about.html')

@app.route('/rooms')
def rooms():
    cur = mysql.connection.cursor()
    

    cur.execute("""
        SELECT * FROM rooms 
        WHERE room_type = 'hotel_room' 
        AND available_count > 0 
        AND is_available = 1
        ORDER BY price ASC
    """)
    
    raw_rooms = cur.fetchall()
    cur.close()

    rooms = []
    for raw_room in raw_rooms:
        room = process_room_data(raw_room)
        room['capacity_text'] = room['capacity_display']

        available = int(room.get('available_count') or 0)
        if available <= 0:
            room['availability'] = {'text': 'Sold Out', 'color': 'red', 'class': 'bg-red-100 text-red-800'}
        elif available <= 2:
            room['availability'] = {'text': f'Only {available} left', 'color': 'yellow', 'class': 'bg-yellow-100 text-yellow-800'}
        else:
            room['availability'] = {'text': f'{available} available', 'color': 'green', 'class': 'bg-green-100 text-green-800'}

        rooms.append(room)

    deluxe_rooms = [r for r in rooms if 'deluxe' in r['name'].lower()]
    executive_rooms = [r for r in rooms if 'executive' in r['name'].lower()]
    presidential_rooms = [r for r in rooms if 'presidential' in r['name'].lower()]

    return render_template('main/rooms.html', 
                        rooms=rooms,
                        deluxe_rooms=deluxe_rooms,
                        executive_rooms=executive_rooms,
                        presidential_rooms=presidential_rooms)

# Sudah diganti menjadi Venue (Hanya untuk compability)
@app.route('/facilities')
def facilities():
    """Redirect ke halaman venues untuk backward compatibility"""
    flash('Facilities page has moved to <a href="/venues" class="underline font-semibold">Venues</a>', 'info')
    return redirect(url_for('venues'))

@app.route('/facilities-list')
def facilities_list():
    """Redirect ke venues untuk kompatibilitas"""
    flash('Please visit our Venues page for all facilities information.', 'info')
    return redirect(url_for('venues'))

@app.route('/venues')
def venues():
    """Halaman venues (gabungan meeting, facilities, dining)"""
    cur = mysql.connection.cursor()
    
    cur.execute("""
        SELECT * FROM venues 
        WHERE is_available = 1 
        ORDER BY 
            CASE type 
                WHEN 'meeting_room' THEN 1
                WHEN 'conference_room' THEN 2
                WHEN 'ballroom' THEN 3
                WHEN 'pool' THEN 4
                WHEN 'spa' THEN 5
                WHEN 'gym' THEN 6
                WHEN 'fitness_center' THEN 7
                WHEN 'restaurant' THEN 8
                WHEN 'cafe' THEN 9
                WHEN 'bar' THEN 10
                WHEN 'lounge' THEN 11
                ELSE 12
            END,
            name
    """)
    
    venues_data = cur.fetchall()
    cur.close()
    
    meeting_rooms = []
    hotel_facilities = []
    dining = []
    
    for venue in venues_data:
        venue_dict = process_facility_data(venue)
        venue_type = str(venue_dict.get('type', '')).lower()

        if 'meeting' in venue_type or 'conference' in venue_type or 'ballroom' in venue_type:
            meeting_rooms.append(venue_dict)
        elif 'restaurant' in venue_type or 'dining' in venue_type or 'cafe' in venue_type or 'bar' in venue_type or 'lounge' in venue_type:
            dining.append(venue_dict)
        else:
            hotel_facilities.append(venue_dict)
    
    return render_template('main/venues.html',
                         meeting_rooms=meeting_rooms,
                         hotel_facilities=hotel_facilities,
                         dining=dining)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        
        name = f"{first_name} {last_name}".strip()
        
        # Validasi
        if not all([first_name, last_name, email, message]):
            flash('Please fill in all required fields', 'danger')
        else:
            cur = mysql.connection.cursor()
            try:
                cur.execute("""
                    INSERT INTO contact_inquiries (name, email, message)
                    VALUES (%s, %s, %s)
                """, (name, email, message))
                
                mysql.connection.commit()
                flash('Your message has been sent successfully! We will contact you soon.', 'success')
                
            except Exception:
                mysql.connection.rollback()
                app.logger.exception('Failed to save contact inquiry')
                flash('Failed to send message. Please try again.', 'danger')
            finally:
                cur.close()
        
        return redirect(url_for('contact'))
    
    return render_template('main/contact.html')

@app.route('/support')
def support():
    """Support page for password reset and other issues"""
    return render_template('main/contact_support.html')


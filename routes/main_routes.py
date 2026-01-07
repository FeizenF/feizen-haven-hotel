from flask import render_template, request, redirect, url_for, flash, session
from config import app, mysql
import json
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from helpers import (
    process_room_data,
    process_facility_data,
    parse_images_data,
    parse_amenities_data,
    format_price,
    get_availability_info,
    process_room_images
)

def process_room_images(rooms):
    """Process room images sama seperti di rooms() route"""
    processed = []
    
    for raw_room in rooms:
        room = dict(raw_room)
        
        main_image = None
        
        if room.get('images'):
            img = str(room['images']).strip()
            if img and img.lower() not in ['null', 'none', '']:
                main_image = img
        
        # Fallback
        if not main_image:
            room_name = str(room.get('name', '')).lower()
            if 'deluxe' in room_name:
                main_image = '/static/images/rooms/deluxe.jpg'
            elif 'executive' in room_name:
                main_image = '/static/images/rooms/executive.jpg'
            elif 'presidential' in room_name:
                main_image = '/static/images/rooms/presidential.jpg'
            else:
                main_image = '/static/images/rooms/default.jpg'
        
        # Fix path
        if main_image and not main_image.startswith(('http', '/static', '/')):
            if main_image.startswith('static/'):
                main_image = '/' + main_image
            else:
                main_image = '/static/images/rooms/' + main_image
        
        room['main_image'] = main_image
        processed.append(room)
    
    return processed
    
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
    
    featured_rooms = []
    for room in featured_rooms_data:
        room_dict = dict(room)
        
        images_raw = room_dict.get('images')
        room_dict['images_list'] = parse_images_data(images_raw)
        
        if not room_dict['images_list']:
            room_name = str(room_dict.get('name', '')).lower()
            if 'deluxe' in room_name:
                room_dict['images_list'] = ['/static/images/rooms/deluxe.jpg']
            elif 'executive' in room_name:
                room_dict['images_list'] = ['/static/images/rooms/executive.jpg']
            elif 'presidential' in room_name:
                room_dict['images_list'] = ['/static/images/rooms/presidential.jpg']
            else:
                room_dict['images_list'] = ['/static/images/rooms/default.jpg']
        
        amenities_raw = room_dict.get('amenities')
        if amenities_raw:
            if isinstance(amenities_raw, str):
                if amenities_raw.startswith('['):
                    try:
                        room_dict['amenities_list'] = json.loads(amenities_raw.replace("'", '"'))
                    except:
                        room_dict['amenities_list'] = [a.strip() for a in amenities_raw.split(',')]
                else:
                    room_dict['amenities_list'] = [a.strip() for a in amenities_raw.split(',')]
            else:
                room_dict['amenities_list'] = []
        else:
            room_dict['amenities_list'] = []
        

        try:
            room_dict['price'] = float(room_dict.get('price', 1500000))
        except:
            room_dict['price'] = 1500000.0
        
        featured_rooms.append(room_dict)
    
    cur.execute("SELECT * FROM venues WHERE is_available = 1 LIMIT 6")
    venues_data = cur.fetchall()
    
    venues_list = []
    for venue in venues_data:
        venue_dict = dict(venue)
        
        images_raw = venue_dict.get('image_url') or venue_dict.get('images')
        venue_dict['images_list'] = parse_images_data(images_raw)
        
        if not venue_dict['images_list']:
            venue_type = str(venue_dict.get('type', '')).lower()
            if 'meeting' in venue_type or 'conference' in venue_type:
                venue_dict['images_list'] = ['/static/images/venues/meeting.jpg']
            elif 'pool' in venue_type or 'swimming' in venue_type:
                venue_dict['images_list'] = ['/static/images/venues/pool.jpg']
            elif 'spa' in venue_type or 'wellness' in venue_type:
                venue_dict['images_list'] = ['/static/images/venues/spa.jpg']
            elif 'gym' in venue_type or 'fitness' in venue_type:
                venue_dict['images_list'] = ['/static/images/venues/gym.jpg']
            elif 'restaurant' in venue_type or 'dining' in venue_type or 'cafe' in venue_type:
                venue_dict['images_list'] = ['/static/images/venues/restaurant.jpg']
            else:
                venue_dict['images_list'] = ['/static/images/venues/default.jpg']
        
        venues_list.append(venue_dict)
    
    cur.close()
    
    return render_template('main/index.html', 
                         featured_rooms=featured_rooms,
                         venues=venues_list)

@app.route('/about')
def about():
    return render_template('main/about.html')

def parse_images_data(images_str):
    """Parse images data dari berbagai format - SUPPORT LOCAL STATIC PATHS"""
    if not images_str:
        return []
    
    print(f"DEBUG parse_images_data INPUT: '{images_str}'")
    
    try:
        if isinstance(images_str, str):
            images_str = images_str.strip()
            
            if not images_str or images_str.lower() in ['null', 'none', '[]', '{}']:
                print("DEBUG: Empty string, returning []")
                return []
            
            if images_str.startswith('/static/'):
                print(f"DEBUG: Detected local static path: {images_str}")
                return [images_str]

            if images_str.startswith('[') and images_str.endswith(']'):
                print("DEBUG: Detected JSON array format")
                try:

                    cleaned = images_str.replace("'", '"')
                    parsed = json.loads(cleaned)
                    
                    if isinstance(parsed, list):
                        print(f"DEBUG: Parsed as list: {parsed}")
                        valid_paths = []
                        for item in parsed:
                            if isinstance(item, str) and item:

                                if item.startswith('http') or item.startswith('/static/'):
                                    valid_paths.append(item.strip())
                                else:
                                    valid_paths.append(str(item).strip())
                        
                        print(f"DEBUG: Valid paths found: {valid_paths}")
                        return valid_paths
                    else:

                        print(f"DEBUG: Parsed as non-list, converting: {parsed}")
                        return [str(parsed)] if parsed else []
                        
                except json.JSONDecodeError as e:
                    print(f"DEBUG: JSON decode error: {e}")

                    content = images_str[1:-1].strip()
                    if content:
                        print(f"DEBUG: Extracted content: {content}")
                        return [content]
                    return []
            
            elif images_str.startswith('http'):
                print(f"DEBUG: Detected plain URL: {images_str}")
                return [images_str]
            
            elif ',' in images_str:
                print(f"DEBUG: Detected comma-separated: {images_str}")
                paths = []
                for part in images_str.split(','):
                    part = part.strip().strip('"').strip("'").strip()
                    if part:  
                        paths.append(part)
                print(f"DEBUG: Extracted paths: {paths}")
                return paths
            
            else:
                print(f"DEBUG: Single string: {images_str}")
                return [images_str] if images_str else []
        
        print(f"DEBUG: Not a string, returning []")
        return []
        
    except Exception as e:
        print(f"ERROR in parse_images_data: {e}")
        import traceback
        traceback.print_exc()
        return []
    
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
    rooms = []

    for raw_room in raw_rooms:
        room = dict(raw_room)
        
        # Format harga
        room['formatted_price'] = f"Rp{float(room.get('price', 0)):,.0f}".replace(',', '.')
        
        # Format kapasitas
        room['capacity_text'] = f"{room.get('capacity', 2)} people"
        
        # Cek ketersediaan
        available = room.get('available_count', 0)
        if available <= 0:
            room['availability'] = {'text': 'Sold Out', 'color': 'red', 'class': 'bg-red-100 text-red-800'}
        elif available <= 2:
            room['availability'] = {'text': f'Only {available} left', 'color': 'yellow', 'class': 'bg-yellow-100 text-yellow-800'}
        else:
            room['availability'] = {'text': f'{available} available', 'color': 'green', 'class': 'bg-green-100 text-green-800'}
        
        main_image = None

        if room.get('images'):
            img = str(room['images']).strip()
            if img and img.lower() not in ['null', 'none', '']:
                main_image = img
                print(f"DEBUG Room '{room.get('name')}': Found image: {main_image}")
        
        # Fallback
        if not main_image:
            room_name = str(room.get('name', '')).lower()
            if 'deluxe' in room_name:
                main_image = '/static/images/rooms/deluxe.jpg'
            elif 'executive' in room_name:
                main_image = '/static/images/rooms/executive.jpg'
            elif 'presidential' in room_name:
                main_image = '/static/images/rooms/presidential.jpg'
            else:
                main_image = '/static/images/rooms/default.jpg'
            print(f"DEBUG Room '{room.get('name')}': Using fallback: {main_image}")
        
        room['main_image'] = main_image
        rooms.append(room)

    deluxe_rooms = [r for r in rooms if 'deluxe' in r['name'].lower()]
    executive_rooms = [r for r in rooms if 'executive' in r['name'].lower()]
    presidential_rooms = [r for r in rooms if 'presidential' in r['name'].lower()]
    processed_rooms = process_room_images(raw_rooms)

    return render_template('main/rooms.html', 
                        rooms=processed_rooms,
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
        venue_dict = dict(venue)
        venue_type = str(venue_dict.get('type', '')).lower()
        
        if venue_dict.get('image_url'):
            venue_dict['main_image'] = venue_dict['image_url']
        elif venue_dict.get('main_image'):
            venue_dict['main_image'] = venue_dict['main_image']
        elif venue_dict.get('image'):
            venue_dict['main_image'] = venue_dict['image']
        elif venue_dict.get('photo_url'):
            venue_dict['main_image'] = venue_dict['photo_url']
        else:

            if 'meeting' in venue_type or 'conference' in venue_type or 'ballroom' in venue_type:
                venue_dict['main_image'] = '/static/images/venues/meeting.jpg'
            elif 'pool' in venue_type or 'swimming' in venue_type:
                venue_dict['main_image'] = '/static/images/venues/pool.jpg'
            elif 'spa' in venue_type or 'wellness' in venue_type:
                venue_dict['main_image'] = '/static/images/venues/spa.jpg'
            elif 'gym' in venue_type or 'fitness' in venue_type:
                venue_dict['main_image'] = '/static/images/venues/gym.jpg'
            elif 'restaurant' in venue_type or 'dining' in venue_type or 'cafe' in venue_type or 'bar' in venue_type or 'lounge' in venue_type:
                venue_dict['main_image'] = '/static/images/venues/restaurant.jpg'
            else:
                venue_dict['main_image'] = '/static/images/venues/default.jpg'
        
        if venue_dict.get('price_per_hour'):
            try:
                price = float(venue_dict['price_per_hour'])
                venue_dict['formatted_price'] = f"Rp{price:,.0f}/hour"
            except:
                venue_dict['formatted_price'] = f"Rp{venue_dict['price_per_hour']}/hour"
        
        venue_type_lower = venue_type.lower()
        
        if 'meeting' in venue_type_lower or 'conference' in venue_type_lower or 'ballroom' in venue_type_lower:
            meeting_rooms.append(venue_dict)
        elif 'restaurant' in venue_type_lower or 'dining' in venue_type_lower or 'cafe' in venue_type_lower or 'bar' in venue_type_lower or 'lounge' in venue_type_lower:
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
        phone = request.form.get('phone', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        
        name = f"{first_name} {last_name}".strip()
        
        # Validasi
        if not all([first_name, last_name, email, message]):
            flash('Please fill in all required fields', 'danger')
        else:
            cur = mysql.connection.cursor()
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS contact_inquiries (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        email VARCHAR(100) NOT NULL,
                        phone VARCHAR(20),
                        subject VARCHAR(100),
                        message TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status ENUM('new', 'read', 'replied') DEFAULT 'new'
                    )
                """)
                
                cur.execute("""
                    INSERT INTO contact_inquiries (name, email, phone, subject, message)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, email, phone, subject, message))
                
                mysql.connection.commit()
                flash('Your message has been sent successfully! We will contact you soon.', 'success')
                
            except Exception as e:
                mysql.connection.rollback()
                print(f"Error: {e}")
                flash('Failed to send message. Please try again.', 'danger')
            finally:
                cur.close()
        
        return redirect(url_for('contact'))
    
    return render_template('main/contact.html')

import re  # Import regex untuk validasi
from werkzeug.security import generate_password_hash

@app.route('/support')
def support():
    """Support page for password reset and other issues"""
    return render_template('main/contact_support.html')


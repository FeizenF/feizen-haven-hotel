import json
from datetime import datetime

# PARSE FUNCTIONS
def parse_images_data(images_raw):
    """Parse images data from database (JSON string or comma-separated)"""
    if not images_raw:
        return []
    
    try:
        if isinstance(images_raw, str):
            # Try to parse as JSON
            try:
                images_list = json.loads(images_raw)
            except json.JSONDecodeError:
                # If not JSON, treat as comma-separated string
                images_list = [img.strip() for img in images_raw.split(',') if img.strip()]
        else:
            images_list = []
        
        # Ensure it's a list
        if not isinstance(images_list, list):
            images_list = [images_list]
        
        return images_list
    except Exception as e:
        print(f"Error parsing images: {e}")
        return []

def parse_amenities_data(amenities_raw):
    """Parse amenities data from database"""
    if not amenities_raw:
        return []
    
    try:
        if isinstance(amenities_raw, str):
            if amenities_raw.startswith('['):
                try:
                    amenities_list = json.loads(amenities_raw.replace("'", '"'))
                except:
                    amenities_list = [a.strip() for a in amenities_raw.split(',')]
            else:
                amenities_list = [a.strip() for a in amenities_raw.split(',')]
        else:
            amenities_list = []
        
        return amenities_list
    except Exception as e:
        print(f"Error parsing amenities: {e}")
        return []

# FORMAT FUNCTIONS
def format_price(price):
    """Format price to Indonesian Rupiah"""
    try:
        price_float = float(price)
        return f"Rp{price_float:,.0f}".replace(',', '.')
    except:
        return "Rp0"

def format_capacity(capacity):
    """Format capacity display"""
    capacity = int(capacity) if capacity else 2
    return f"{capacity} { 'person' if capacity == 1 else 'people' }"

def format_size(size):
    """Format size display"""
    if size:
        return f"{size} m²"
    return "Standard size"

# AVAILABILITY FUNCTIONS
def get_availability_info(room_dict):
    """Generate availability information for a room"""
    available_count = room_dict.get('available_count', 0)
    room_count = room_dict.get('room_count', 0)
    
    # Calculate availability percentage
    if room_count > 0:
        availability_percent = (available_count / room_count) * 100
    else:
        availability_percent = 0
    
    # Determine availability status
    if available_count <= 0:
        return {
            'text': "Sold Out",
            'color': "red",
            'badge_class': "bg-red-100 text-red-800",
            'is_available': False,
            'available_count': available_count,
            'percent': round(availability_percent, 1)
        }
    elif available_count <= 2:
        return {
            'text': f"Only {available_count} left",
            'color': "yellow",
            'badge_class': "bg-yellow-100 text-yellow-800",
            'is_available': True,
            'available_count': available_count,
            'percent': round(availability_percent, 1)
        }
    else:
        return {
            'text': f"{available_count} available",
            'color': "green",
            'badge_class': "bg-green-100 text-green-800",
            'is_available': True,
            'available_count': available_count,
            'percent': round(availability_percent, 1)
        }

# ROOM PROCESSING 
def process_room_data(room):
    """Process raw room data from database for template use"""
    room_dict = dict(room)
    
    # Parse images
    images_raw = room_dict.get('images')
    room_dict['images_list'] = parse_images_data(images_raw)
    
    # Get main image for card
    if room_dict['images_list'] and len(room_dict['images_list']) > 0:
        room_dict['main_image'] = room_dict['images_list'][0]
    else:
        room_dict['main_image'] = None
    
    # Parse amenities
    amenities_raw = room_dict.get('amenities')
    room_dict['amenities_list'] = parse_amenities_data(amenities_raw)
    
    # Format price
    try:
        room_dict['price'] = float(room_dict.get('price', 0))
    except:
        room_dict['price'] = 0
    
    room_dict['formatted_price'] = format_price(room_dict['price'])
    room_dict['per_night_price'] = f"{format_price(room_dict['price'])}/night"
    
    # Format capacity and size
    room_dict['capacity_display'] = format_capacity(room_dict.get('capacity'))
    room_dict['size_display'] = format_size(room_dict.get('size'))
    
    # Get availability info
    room_dict['availability_info'] = get_availability_info(room_dict)
    
    return room_dict

def process_facility_data(facility):
    """Process raw facility data from database for template use"""
    facility_dict = dict(facility)
    
    # Get images from image_url or images column
    images_raw = facility_dict.get('image_url') or facility_dict.get('images')
    facility_dict['images_list'] = parse_images_data(images_raw)
    
    # Add fallback image if no images
    if not facility_dict['images_list']:
        facility_dict['images_list'] = get_venue_fallback_image(facility_dict)
    
    # Parse amenities
    amenities_raw = facility_dict.get('amenities')
    facility_dict['amenities_list'] = parse_amenities_data(amenities_raw)
    
    # Format price
    if facility_dict.get('price_per_hour'):
        try:
            price = float(facility_dict['price_per_hour'])
            facility_dict['formatted_price'] = f"{format_price(price)}/hour"
        except:
            facility_dict['formatted_price'] = "Contact for pricing"
    
    return facility_dict

def get_venue_fallback_image(venue_dict):
    """Get fallback image based on venue type (renamed from facility)"""
    venue_type = str(venue_dict.get('type', '')).lower()
    
    fallback_images = {
        'meeting': '/static/images/venues/meeting.jpg',
        'conference': '/static/images/venues/meeting.jpg',
        'ballroom': '/static/images/venues/meeting.jpg',
        'pool': '/static/images/venues/pool.jpg',
        'swimming': '/static/images/venues/pool.jpg',
        'spa': '/static/images/venues/spa.jpg',
        'wellness': '/static/images/venues/spa.jpg',
        'gym': '/static/images/venues/gym.jpg',
        'fitness': '/static/images/venues/gym.jpg',
        'restaurant': '/static/images/venues/restaurant.jpg',
        'dining': '/static/images/venues/restaurant.jpg',
        'cafe': '/static/images/venues/restaurant.jpg',
        'bar': '/static/images/venues/restaurant.jpg',
        'lounge': '/static/images/venues/restaurant.jpg',
        'library': '/static/images/venues/default.jpg',
        'business': '/static/images/venues/meeting.jpg'
    }
    
    for key, image_path in fallback_images.items():
        if key in venue_type:
            return [image_path]
    
    return ['/static/images/venues/default.jpg']
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
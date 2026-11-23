import json
import logging
import os

logger = logging.getLogger(__name__)

# ============================================================
# IMAGE / PATH HELPERS
# ============================================================
def normalize_image_path(path, default_dir='images/rooms'):
    """Normalize a stored image value into a browser-friendly URL.

    Handles the different formats found in the database:
      - absolute URLs (http/https)
      - already-normalized paths (/static/...)
      - project-relative paths (static/...)
      - static-relative paths (images/rooms/foo.jpg)
      - bare filenames (foo.jpg)
    """
    if path is None:
        return ''

    value = str(path).strip().strip('"').strip("'")

    if not value or value.lower() in ('null', 'none', '[]', '{}'):
        return ''

    if value.startswith(('http://', 'https://')):
        return value

    if value.startswith('/static/'):
        return value

    if value.startswith('static/'):
        return '/' + value

    if value.startswith('/'):
        return value

    if '/' in value:
        return '/static/' + value.lstrip('/')

    return '/static/' + default_dir.strip('/') + '/' + value


def parse_images_data(images_raw, default_dir='images/rooms'):
    """Parse images data from the database (JSON array, comma list or single value)."""
    if not images_raw:
        return []

    parsed = []

    try:
        if isinstance(images_raw, (list, tuple)):
            parsed = list(images_raw)
        elif isinstance(images_raw, str):
            value = images_raw.strip()

            if not value or value.lower() in ('null', 'none', '[]', '{}'):
                return []

            if value.startswith('[') and value.endswith(']'):
                try:
                    decoded = json.loads(value.replace("'", '"'))
                    parsed = decoded if isinstance(decoded, list) else [decoded]
                except (json.JSONDecodeError, TypeError):
                    # Malformed JSON array: strip the brackets and split.
                    parsed = [part for part in value[1:-1].split(',')]
            elif ',' in value:
                parsed = value.split(',')
            else:
                parsed = [value]
        else:
            return []

        images = []
        for item in parsed:
            normalized = normalize_image_path(item, default_dir=default_dir)
            if normalized and normalized not in images:
                images.append(normalized)

        return images
    except Exception:
        logger.exception('Error parsing images')
        return []


def parse_amenities_data(amenities_raw):
    """Parse amenities data from the database."""
    if not amenities_raw:
        return []

    try:
        if isinstance(amenities_raw, (list, tuple)):
            return [str(a).strip() for a in amenities_raw if str(a).strip()]

        if isinstance(amenities_raw, str):
            value = amenities_raw.strip()

            if value.startswith('[') and value.endswith(']'):
                try:
                    decoded = json.loads(value.replace("'", '"'))
                    if isinstance(decoded, list):
                        return [str(a).strip() for a in decoded if str(a).strip()]
                except (json.JSONDecodeError, TypeError):
                    pass
                value = value[1:-1]

            return [a.strip() for a in value.split(',') if a.strip()]

        return []
    except Exception:
        logger.exception('Error parsing amenities')
        return []


def payment_proof_url(proof_image):
    """Return a browser URL for a stored payment proof path."""
    if not proof_image:
        return ''

    value = str(proof_image).strip()

    if value.startswith(('http://', 'https://')):
        return value

    if value.startswith('/static/'):
        return value

    if value.startswith('static/'):
        return '/' + value

    if value.startswith('/'):
        return value

    if value.startswith('uploads/'):
        return '/static/' + value

    # Legacy values may include a nested folder such as images/uploads/payments/x.jpg
    if value.startswith('images/'):
        return '/static/' + value

    return '/static/uploads/payments/' + value


# ============================================================
# FORMAT HELPERS
# ============================================================
def format_price(price):
    """Format price to Indonesian Rupiah."""
    try:
        return f"Rp{float(price):,.0f}".replace(',', '.')
    except (TypeError, ValueError):
        return "Rp0"


def format_capacity(capacity):
    """Format capacity display."""
    try:
        capacity = int(capacity)
    except (TypeError, ValueError):
        capacity = 2
    return f"{capacity} {'person' if capacity == 1 else 'people'}"


def format_size(size):
    """Format size display."""
    if size:
        return f"{size} m²"
    return "Standard size"


# ============================================================
# AVAILABILITY
# ============================================================
def get_availability_info(room_dict):
    """Generate availability information for a room."""
    try:
        available_count = int(room_dict.get('available_count') or 0)
    except (TypeError, ValueError):
        available_count = 0

    try:
        room_count = int(room_dict.get('room_count') or 0)
    except (TypeError, ValueError):
        room_count = 0

    availability_percent = (available_count / room_count * 100) if room_count > 0 else 0

    if available_count <= 0:
        return {
            'text': "Sold Out",
            'color': "red",
            'badge_class': "bg-red-100 text-red-800",
            'is_available': False,
            'available_count': available_count,
            'percent': round(availability_percent, 1)
        }

    if available_count <= 2:
        return {
            'text': f"Only {available_count} left",
            'color': "yellow",
            'badge_class': "bg-yellow-100 text-yellow-800",
            'is_available': True,
            'available_count': available_count,
            'percent': round(availability_percent, 1)
        }

    return {
        'text': f"{available_count} available",
        'color': "green",
        'badge_class': "bg-green-100 text-green-800",
        'is_available': True,
        'available_count': available_count,
        'percent': round(availability_percent, 1)
    }


# ============================================================
# ROOM / VENUE PROCESSING
# ============================================================
def get_room_fallback_image(room_name):
    """Return an existing fallback image for a room."""
    name = str(room_name or '').lower()

    if 'deluxe' in name:
        return '/static/images/rooms/deluxe.jpg'
    if 'executive' in name:
        return '/static/images/rooms/executive.jpg'
    if 'presidential' in name:
        return '/static/images/rooms/presidential.jpg'
    if 'meeting' in name or 'boardroom' in name:
        return '/static/images/venues/meeting.jpg'
    return '/static/images/rooms/default.jpg'


def process_room_data(room):
    """Process raw room data from the database for template use."""
    room_dict = dict(room)

    images_list = parse_images_data(room_dict.get('images'), default_dir='images/rooms')
    if not images_list:
        images_list = [get_room_fallback_image(room_dict.get('name'))]

    room_dict['images_list'] = images_list
    room_dict['main_image'] = images_list[0]

    room_dict['amenities_list'] = parse_amenities_data(room_dict.get('amenities'))

    try:
        room_dict['price'] = float(room_dict.get('price') or 0)
    except (TypeError, ValueError):
        room_dict['price'] = 0

    room_dict['formatted_price'] = format_price(room_dict['price'])
    room_dict['per_night_price'] = f"{format_price(room_dict['price'])}/night"
    room_dict['capacity_display'] = format_capacity(room_dict.get('capacity'))
    room_dict['size_display'] = format_size(room_dict.get('size'))
    room_dict['availability_info'] = get_availability_info(room_dict)

    return room_dict


def process_room_images(rooms):
    """Process room images for list/card templates."""
    processed = []

    for raw_room in rooms:
        room = dict(raw_room)

        images_list = parse_images_data(room.get('images'), default_dir='images/rooms')
        if not images_list:
            images_list = [get_room_fallback_image(room.get('name'))]

        room['images_list'] = images_list
        room['main_image'] = images_list[0]
        processed.append(room)

    return processed


def get_venue_fallback_image(venue_dict):
    """Return an existing fallback image based on venue type."""
    venue_type = str(venue_dict.get('type', '')).lower()

    if 'meeting' in venue_type or 'conference' in venue_type:
        return ['/static/images/venues/meeting.jpg']
    if 'ballroom' in venue_type or 'event' in venue_type:
        return ['/static/images/venues/ballroom.jpg']
    if 'pool' in venue_type or 'swimming' in venue_type:
        return ['/static/images/venues/pool.jpg']
    if 'spa' in venue_type or 'wellness' in venue_type:
        return ['/static/images/venues/spa.jpg']
    if 'gym' in venue_type or 'fitness' in venue_type:
        return ['/static/images/venues/gym.jpg']
    if 'restaurant' in venue_type or 'dining' in venue_type or 'cafe' in venue_type:
        return ['/static/images/venues/dining.jpg']
    if 'bar' in venue_type or 'lounge' in venue_type:
        return ['/static/images/venues/bar.jpg']
    if 'business' in venue_type:
        return ['/static/images/venues/business.jpg']

    return ['/static/images/venues/pavilion.jpg']


def process_facility_data(facility):
    """Process raw venue/facility data from the database for template use."""
    facility_dict = dict(facility)

    images_raw = facility_dict.get('image_url') or facility_dict.get('images')
    images_list = parse_images_data(images_raw, default_dir='images/venues')

    if not images_list:
        images_list = get_venue_fallback_image(facility_dict)

    facility_dict['images_list'] = images_list
    facility_dict['main_image'] = images_list[0]
    facility_dict['amenities_list'] = parse_amenities_data(facility_dict.get('amenities'))

    if facility_dict.get('price_per_hour'):
        try:
            price = float(facility_dict['price_per_hour'])
            facility_dict['formatted_price'] = f"{format_price(price)}/hour"
        except (TypeError, ValueError):
            facility_dict['formatted_price'] = "Contact for pricing"

    return facility_dict

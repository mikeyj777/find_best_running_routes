# utils/geo_utils.py
from math import radians, sin, cos, sqrt, atan2, asin, degrees

# Earth's radius in miles
EARTH_RADIUS_MILES = 3958.8

def get_destination_point(lat, lon, bearing, distance_miles):
    """
    Calculates a new GPS coordinate given a starting point, bearing, and distance.
    """
    lat_rad = radians(lat)
    lon_rad = radians(lon)
    bearing_rad = radians(bearing)

    lat2_rad = asin(sin(lat_rad) * cos(distance_miles / EARTH_RADIUS_MILES) +
                    cos(lat_rad) * sin(distance_miles / EARTH_RADIUS_MILES) * cos(bearing_rad))

    lon2_rad = lon_rad + atan2(sin(bearing_rad) * sin(distance_miles / EARTH_RADIUS_MILES) * cos(lat_rad),
                               cos(distance_miles / EARTH_RADIUS_MILES) - sin(lat_rad) * sin(lat2_rad))

    return degrees(lat2_rad), degrees(lon2_rad)

def get_bounding_box(origin_lat, origin_lon, total_radius_miles):
    """
    Calculates a square bounding box around a central point.

    Args:
        origin_lat (float): Latitude of the center point.
        origin_lon (float): Longitude of the center point.
        total_radius_miles (float): The total radius (e.g., search radius + path distance) in miles.

    Returns:
        tuple: A tuple of (min_lat, min_lon, max_lat, max_lon).
    """
    # Calculate the four corner points of the box using the total radius
    north_lat, _ = get_destination_point(origin_lat, origin_lon, 0, total_radius_miles)
    _, east_lon = get_destination_point(origin_lat, origin_lon, 90, total_radius_miles)
    south_lat, _ = get_destination_point(origin_lat, origin_lon, 180, total_radius_miles)
    _, west_lon = get_destination_point(origin_lat, origin_lon, 270, total_radius_miles)

    return south_lat, west_lon, north_lat, east_lon

def haversine_distance(p1, p2):
    """Calculates the distance between two GPS coordinates in miles."""
    lat1, lon1 = radians(p1['lat']), radians(p1['lon'])
    lat2, lon2 = radians(p2['lat']), radians(p2['lon'])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return EARTH_RADIUS_MILES * c

def interpolate_point(p1, p2, fraction):
    """Calculates an intermediate GPS point between two points."""
    lat1, lon1 = radians(p1['lat']), radians(p1['lon'])
    lat2, lon2 = radians(p2['lat']), radians(p2['lon'])
    d = 2 * asin(sqrt(sin((lat1 - lat2) / 2)**2 + cos(lat1) * cos(lat2) * sin((lon1 - lon2) / 2)**2))
    A = sin((1 - fraction) * d) / sin(d)
    B = sin(fraction * d) / sin(d)
    x = A * cos(lat1) * cos(lon1) + B * cos(lat2) * cos(lon2)
    y = A * cos(lat1) * sin(lon1) + B * cos(lat2) * sin(lon2)
    z = A * sin(lat1) + B * sin(lat2)
    lat = atan2(z, sqrt(x**2 + y**2))
    lon = atan2(y, x)
    return {'lat': degrees(lat), 'lon': degrees(lon)}
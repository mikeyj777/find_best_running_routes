# utils/geo_utils.py
from math import radians, sin, cos, sqrt, atan2

def haversine_distance(p1, p2):
    """
    Calculates the distance between two GPS coordinates in miles.
    
    Args:
        p1 (dict): The first point, with 'lat' and 'lon' keys.
        p2 (dict): The second point, with 'lat' and 'lon' keys.
        
    Returns:
        float: The distance in miles.
    """
    R = 3958.8  # Earth's radius in miles

    lat1, lon1 = radians(p1['lat']), radians(p1['lon'])
    lat2, lon2 = radians(p2['lat']), radians(p2['lon'])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c
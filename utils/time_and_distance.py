import concurrent.futures
import math

walk_speed = 1.34 #m/s

def haversine_distance_and_time(lat1, lon1, lat2, lon2):
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    radius = 6371  # Earth's radius in kilometers

    distance = radius * c
    return int(distance * 1000), max(1, int(distance*1000 / walk_speed)), ''


def get_multiple_calls_response_haversine(coordinates):
    results = {}

    def compute_distance(coord):
        (lat1, lon1), (lat2, lon2), stop_id = coord
        try:
            distance_m, _, _ = haversine_distance_and_time(lat1, lon1, lat2, lon2)
            return int(stop_id), distance_m / 1000
        except Exception as e:
            return stop_id, str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_coord = {executor.submit(compute_distance, coord): coord for coord in coordinates}
        for future in concurrent.futures.as_completed(future_to_coord):
            stop_id, result = future.result()
            results[stop_id] = result

    return results
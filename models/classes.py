class Route:
    def __init__(self):
        self.route = ''
        self.routes = []
        self.type = ''
        self.short_name = ''
        self.long_name = ''
        self.agency = ''
        self.vehicle_id = ''
        self.occupancy = ''
        self.departure_time = ''
        self.ending_time = ''
        self.color = ''
        self.description = ''
        self.trip_time = -1
        self.fare = 0
        self.available_options = []
        self.stops = []
        self.polyline = ''
        self.frequency = 0
        self.distance = 0
        self.meta_info = {}

    def to_dict(self):
        return {
            'route': self.route,
            'routes': self.routes,
            'type': self.type,
            'short_name': self.short_name,
            'long_name': self.long_name,
            'agency': self.agency,
            'vehicle_id': self.vehicle_id,
            'occupancy': self.occupancy,
            'departure_time': self.departure_time,
            'ending_time': self.ending_time,
            'color': self.color,
            'description': self.description,
            'trip_time': self.trip_time,
            'fare': self.fare,
            'available_options': self.available_options,
            'stops': self.stops,
            'polyline': self.polyline,
            'frequency': self.frequency,
            'distance': self.distance,
            'meta_info': self.meta_info
        }

    def __str__(self):
        return f"Route(route={self.route}, routes={self.routes}, type={self.type}, short_name={self.short_name}, " \
               f"long_name={self.long_name}, agency={self.agency}, vehicle_id={self.vehicle_id}, occupancy={self.occupancy}, " \
               f"departure_time={self.departure_time}, ending_time={self.ending_time}, color={self.color}, " \
               f"description={self.description}, trip_time={self.trip_time}, fare={self.fare}, " \
               f"available_options={self.available_options}, stops={self.stops}, polyline={self.polyline}, " \
               f"distance={self.distance}, frequency={self.frequency}, meta_info={self.meta_info})"


class NearestStop:
    def __init__(self, stop_id, stop_name, stop_type, geometry, distance, travel_time, source_name):
        self.stop_id = stop_id
        self.stop_name = stop_name
        self.stop_type = stop_type
        self.geometry = geometry
        self.distance = distance
        self.travel_time = travel_time
        self.source_name = source_name

    def to_dict(self):
        return {
            'stop_id': self.stop_id,
            'stop_name': self.stop_name,
            'stop_type': self.stop_type,
            'geometry': self.geometry,
            'distance': self.distance,
            'travel_time': self.travel_time,
            'source_name': self.source_name
        }


    def __str__(self):
        return f"NearestStop(stop_id={self.stop_id}, stop_name='{self.stop_name}', stop_type='{self.stop_type}'," \
               f"geometry={self.geometry}, distance={self.distance}, travel_time={self.travel_time}, " \
               f"source_name={self.source_name})"

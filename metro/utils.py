import datetime

import pandas as pd

from models.classes import Route

# routes_df = pd.read_csv('static/GTFS/metro/routes.txt')
# stops_df = pd.read_csv('static/GTFS/metro/stops.txt')
# metro_stops = pd.read_csv('static/meta/metro_stops.csv')


metro_routes_df = pd.read_csv('static/GTFS/metro/routes.txt')
metro_routes_df['idx'] = metro_routes_df.loc[:, 'route_id']
metro_routes_dict = metro_routes_df[['idx', 'route_short_name', 'route_long_name', 'route_type', 'route_id']].set_index(
    'idx').T.to_dict('list')
del metro_routes_df

metro_stops_df = pd.read_csv('static/GTFS/metro/stops.txt')
metro_stops_df.rename(columns={'stop_id': 'id', 'stop_name': 'name', 'stop_lat': 'lat', 'stop_lon': 'lon'},
                      inplace=True)
metro_stops_df['idx'] = metro_stops_df.loc[:, 'id']
metro_stops_dict = metro_stops_df[['idx', 'id', 'name', 'lat', 'lon']].set_index('idx').T.to_dict()
del metro_stops_df

def get_current_frequency(route_id, time=None):
    return -1


def get_ranked_results(route_ids):
    ranked = {}
    for r in route_ids:
        ranked[r] = get_current_frequency(r)
    print(ranked)
    v = dict(sorted(ranked.items(), key=lambda x: x[1]))
    resp = [x for x in (list(v.keys())[:3] if len(v.keys()) > 3 else list(v.keys())) if v[x] != -1]
    return resp if len(resp) > 0 else list(v.keys())[:3] if len(v.keys()) > 3 else list(v.keys())
#     3 because we want to show only top 3 results in grouped state


def make_resp_easy(g):
    print(f'g : {g}')
    rts = []
    for a in g:
        rt = []
        idx = 0
        for i in range(1, len(a)):
            if a[i][2] == a[i - 1][2]:
                rt[idx].append(a[i])
            else:
                if i == 1:
                    rt.append([a[0]])
                else:
                    rt.append([a[i - 1]])
                    idx += 1
                rt[idx].append(a[i])
        rts.append(rt)
    return rts


def generate_response_metro_new(g, src, dest, src_name, dest_name):
    rts = make_resp_easy(g)
    print(f'rts : {rts}')
    possible_directions = []
    for res in rts:  # All routes
        total_fare = 0
        total_trip_time = 0
        directions = {'routes': []}
        routes = []
        for rt_idx, rt in enumerate(res):  # individual route
            stops = []
            try:
                route = get_route(rt[1][2][0], rt[1][4])
                # routes.append(get_route_grouped(r[1][2], r[1][8], r[1][4]))
            except Exception as e:
                print(e)
                continue
            geometry = rt[-1][-1]
            distance = round(rt[-1][-2] * 1000) if rt[-1][-2] != '' else 0
            trip_time = round(rt[-1][6] / 60)

            for leg_idx, leg in enumerate(rt):
                if leg_idx == 0:
                    continue
                if len(stops) == 0:
                    if rt_idx == 0 and leg[2] == [-1]:
                        stops.append({'id': -1, 'name': src_name, 'lat': src[0], 'lon': src[1]})
                    else:
                        stops.append(get_stops(leg[1]))
                if leg_idx == len(rt) - 1:
                    if leg[0] < 0:
                        if len(dest) == 1:
                            stops.append(get_stops(dest[0]))
                        else:
                            stops.append({'name': dest_name, 'lat': dest[0], 'lon': dest[1]})
                    else:
                        stops.append(get_stops(leg[0]))
                else:
                    stops.append(get_stops(leg[0]))
            route.fare = 0
            route.trip_time = max(1, trip_time)
            route.stops = stops
            route.polyline = geometry
            route.distance = distance
            total_fare = 0
            routes.append(route.to_dict())
            directions['routes'] = routes

        response_type = 'static'
        print(f' total_trip_time : {total_trip_time}')
        total_trip_time = ((datetime.datetime.strptime(res[-1][-1][3], "%H:%M:%S") -
                            datetime.datetime.strptime(res[0][0][3], "%H:%M:%S")).seconds // 60)
        print(f' total_trip_time : {total_trip_time}')
        possible_directions.append(
            {'directions': directions, 'fare_unit': '₹', 'trip_time': total_trip_time, 'total_fare': total_fare,
             'response_type': response_type, 'reach_by': res[-1][-1][3], "time_unit": "min", "route_description": ""})
    return possible_directions


def get_stops(stop_id, loc=None, name=''):
    if loc is None:
        loc = [0.0, 0.0]
    if stop_id == -1:
        stops = {'id': -1, 'name': name, 'lat': loc[0], 'lon': loc[1]}
        return stops
    elif stop_id == -2:
        stops = {'id': -2, 'name': name, 'lat': loc[0], 'lon': loc[1]}
        return stops

    print(stop_id)
    try:
        val = metro_stops_dict[stop_id[0]]
    except:
        val = metro_stops_dict[stop_id]
    # print(stops)
    return val


def get_route(route_id, departure_time=None):
    route = Route()
    if route_id == -1:
        route.route = 'walk'
        route.routes = ['walk']
        route.type = 'walk'
        route.short_name = ''
        route.long_name = f" towards "
        route.agency = ''
        route.vehicle_id = ''
        route.occupancy = ''
        route.departure_time = departure_time
        route.ending_time = ''
        # route.color = '#53BDC0'
        route.color = '#4D4D4D'
        route.description = ''
        route.trip_time = ''
        route.fare = 0
        route.available_options = []
        route.stops = []
        route.polyline = ''
        route.frequency = -1
        route.meta_info = {}
    else:
        val = metro_routes_dict[route_id]
        route.route = val[1].split('_')[0]
        route.routes = [val[1].split('_')[0]]
        route.type = 'metro'
        route.short_name = val[0]
        route.long_name = f" towards {val[1].split(' to ')[1]}"
        route.agency = "DMRC"
        route.vehicle_id = ''
        route.occupancy = ''
        route.departure_time = departure_time
        route.ending_time = ''
        route.color = get_color(route.route.lower())
        route.description = ''
        route.trip_time = ''
        route.fare = 0
        route.available_options = []
        route.stops = []
        route.polyline = ''
        route.frequency = -1
        route.meta_info = {}
    return route


def get_route_name(long_name):
    if 'DOWN' in long_name.upper():
        long_name = long_name.upper().replace('DOWN', '')
    if 'UP' in long_name.upper():
        long_name = long_name.upper().replace('UP', '')
    if 'DN' in long_name.upper():
        long_name = long_name.upper().replace('DN', '')
    if '_' in long_name.upper():
        long_name = long_name.upper().replace('_', '')

    return long_name


def get_stop_details(nearest_stops, stop_id):
    for stop in nearest_stops:
        if stop.stop_id == stop_id:
            return stop


def get_color(route):
    metro_color_dict = {'green': '#20B2AA', 'red': '#FF4040', 'yellow': '#FFDF00', 'blue': '#4169E1',
                        'violet': '#553592', 'pink': '#FC8EAC', 'magenta': '#CC338B', 'orange/airport': '#FF4500',
                        'rapid': '#87CEEB', 'grey': '#838996'}
    if route in metro_color_dict:
        return metro_color_dict[route]
    else:
        return '#000000'


def get_trip_time(start_time, end_time):
    end_time = datetime.datetime.strptime(end_time, '%H:%M:%S')
    start_time = datetime.datetime.strptime(start_time, '%H:%M:%S')
    new_time = datetime.datetime.strptime('00:00:00', '%H:%M:%S')
    if end_time < start_time:
        if end_time.hour < 2 and start_time.hour <= 23:
            tt = 0
            tt += ((new_time + datetime.timedelta(seconds=86399.0) - start_time).total_seconds())
            tt += (end_time - new_time).total_seconds()
            return round(tt / 60)
    else:
        return max(1, round((end_time - start_time).total_seconds() / 60))


if __name__ == '__main__':
    pass

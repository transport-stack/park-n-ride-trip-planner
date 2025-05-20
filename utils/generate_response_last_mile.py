import datetime
import math
import pickle
import pandas as pd

from last_mile_pt.algorithm.Parameter_file import parking_fare_flat
from utils import metro_misc
from last_mile_pt.algorithm.add_schedule import get_waiting_time
from utils.time_and_distance import haversine_distance_and_time

routes_df = pd.read_csv('static/GTFS/metro/routes.txt')
stops_df = pd.read_csv('static/GTFS/metro/stops.txt')

total_fare = 0
total_trip_time = 0

with open('static/meta/metro/metro_mapping_updated.pkl', 'rb') as file:
    id_map = pickle.load(file)


def make_resp_easy(g):
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
        # print(rts)
        rts.append(rt)
    return rts


# Used for last mile - ptx
def generate_response_metro_updated(g, src, dest, src_name, dest_name, query_time, parking_resp, id_dict, parking_dist):
    rts = make_resp_easy(g)
    # print(f'rts : {rts}')
    fastest_rt = 0
    fastest_time = 1000000
    possible_directions = []
    route_description = "Alternate option"
    for rt_idx, res in enumerate(rts):
        metro_legs = 0
        metro_fare = 0
        total_fare = 0
        max_total_fare = 0
        total_trip_time = 0
        directions = {'routes': []}
        routes = []
        meta_info = {}
        with_last_mile = False
        for i, r in enumerate(res):
            stops = []
            if not with_last_mile and (r[1][2] == -50 or r[-1][2] == -50):
                with_last_mile = True
            if len(res) == 1:
                routes.append(
                    get_route(r[1][2], r[1][5], query_time, r[len(r) - 1][3], i, pr=parking_resp, id=id_dict,
                              s_id=r[1][0], pd=parking_dist))
            else:
                routes.append(
                    get_route(r[1][2], r[1][5], query_time, r[len(r) - 1][3], i, pr=parking_resp, id=id_dict,
                              s_id=r[1][0], pd=parking_dist))
            cur_rt_idx = len(routes) - 1
            for idx, v in enumerate(r):
                if idx == 0:
                    continue
                stop = get_stops(v[1])
                if idx == 1 and r[1][2] != -1 and r[1][2] != -50:
                    meta_info = {'platform': metro_misc.get_platform_info_details(stop['name'],
                                                                                  routes[cur_rt_idx]['long_name'].split(
                                                                                      'towards ')[1])}
                    metro_legs += 1
                    metro_fare += int(r[-1][9])
                if len(stops) == 0:
                    if v[1] > 0:
                        stops.append(stop)
                    else:
                        stops.append({'name': src_name, 'lat': src[0], 'lon': src[1]})
                if idx == len(r) - 1:
                    if v[0] < 0:
                        stops.append({'name': dest_name, 'lat': dest[0], 'lon': dest[1]})
                    else:
                        stops.append(get_stops(v[0]))
                else:
                    stops.append(get_stops(v[0]))

            trip_time = math.ceil(r[-1][6] / 60)
            fare = int(r[-1][9])
            if rt_idx == 0:
                direct_rt_fare = fare
            if res[cur_rt_idx][-1][2] > 0:
                if int(res[-1][-1][2]) < 0:
                    if cur_rt_idx == len(res) - 2:
                        routes[cur_rt_idx]['fare'] = fare
                    else:
                        routes[cur_rt_idx]['fare'] = -1
                else:
                    routes[cur_rt_idx]['fare'] = -1
            else:
                routes[cur_rt_idx]['fare'] = fare

            if routes[cur_rt_idx]['routes'][0] == 'walk':
                routes[cur_rt_idx]['meta_info'] = {}
                walk_info = haversine_distance_and_time(stops[0]['lat'], stops[0]['lon'], stops[-1]['lat'], stops[-1]['lon'])
                routes[cur_rt_idx]['distance'] = walk_info[0]
                routes[cur_rt_idx]['trip_time'] = math.floor(walk_info[1] / 60)
                routes[cur_rt_idx]['polyline'] = walk_info[2]
            else:
                drive_info = haversine_distance_and_time(stops[0]['lat'], stops[0]['lon'], stops[-1]['lat'],
                                                         stops[-1]['lon'])
                if routes[cur_rt_idx]['route'] != 'Parking':
                    routes[cur_rt_idx]['meta_info'] = meta_info
                    routes[cur_rt_idx]['polyline'] = ''
                else:
                    routes[cur_rt_idx]['polyline'] = drive_info[2]
                routes[cur_rt_idx]['distance'] = drive_info[0]
                try:
                    if drive_info[0] < 1000:
                        routes[cur_rt_idx]['routes'].append('walk')
                except Exception as e:
                    print('Error in adding walk', e)
                routes[cur_rt_idx]['trip_time'] = trip_time
            routes[cur_rt_idx]['stops'] = stops

            total_trip_time += trip_time
            total_fare += fare
            directions['routes'] = routes
        total_trip_time = ((datetime.datetime.strptime(res[-1][-1][3], "%H:%M:%S") -
                            datetime.datetime.strptime(res[0][0][3], "%H:%M:%S")).seconds // 60)
        if total_trip_time < fastest_time:
            fastest_time = total_trip_time
            fastest_rt = rt_idx

        try:
            # get_fare_range(routes)
            for i, x in enumerate(routes):
                max_total_fare += x['fare'] if x['fare'] >= 0 else 0
        except:
            max_total_fare = 0

        metro_legs = 1 if metro_legs == 0 else metro_legs
        metro_fare = metro_fare / metro_legs if metro_legs > 1 else metro_fare
        if with_last_mile:
            if metro_legs > 1:
                total_fare = total_fare - metro_fare
        else:
            total_fare = metro_fare
        total_fare_range = f'₹{float(total_fare)}' if not with_last_mile else f'₹{float(total_fare)} - ₹{float(max_total_fare)}'

        possible_directions.append(
            {'directions': directions, 'fare_unit': '₹', 'trip_time': total_trip_time, 'total_fare': float(total_fare),
             'response_type': 'static', 'reach_by': res[-1][-1][3],
             "time_unit": "min", "with_last_mile": with_last_mile, 'request_time': query_time,
             'created_at': datetime.datetime.now(), "route_description": route_description
            if with_last_mile else "Only metro option", 'total_fare_range': total_fare_range})
    possible_directions[fastest_rt]['route_description'] = "Fastest option"
    return possible_directions



def get_trip_time(g, idx):
    try:
        for i in range(0, idx):
            if g[i][5] != '':
                departure_time = pd.to_datetime(g[i][5])
        trip_time = round((pd.to_datetime(g[idx][5]) - departure_time).seconds / 60)
    except:
        trip_time = 0
    print(trip_time)
    return trip_time


def get_key_from_value(_dict, _value):
    for key, value in _dict.items():
        if value == _value:
            return key


def get_parking_on_stop(idx, resp):
    try:
        return [resp['results'][x]['id'] for x in idx]
    except Exception as e:
        print(f'get_parking_on_stop : {e}')


def get_route(route_id, departure_time, query_time=None, ending_time=None, idx=0, pr=None, id=None, s_id=None, pd=None):
    routes = {}
    if route_id == -50:
        parkings = get_parking_on_stop([k for k, v in id.items() if v == s_id], pr)
        meta_info = dict()
        try:
            min_value = min({x: pd[x] for x in parkings}.values())
            selected_key = [key for key, value in pd.items() if value == min_value][0]
            selected_p_id = [idx for idx, x in enumerate(pr['results']) if x['id'] == selected_key][0]
            # print(f'get route 2, selected_p_id : {selected_p_id}')
        except KeyError as ke:
            selected_p_id = 0
            print(f'get route 2, KeyError: {ke}, parkings: {parkings}, pd keys: {pd.keys()}')
        except Exception as e:
            selected_p_id = 0
            print(f'Unexpected error: {e}, parkings: {parkings}, pd keys: {pd.keys()}')
        meta_info['parking_id'] = pr['results'][selected_p_id]['id']
        meta_info['parking_name'] = pr['results'][selected_p_id]['location']['name'] + ' ' + \
                                    pr['results'][selected_p_id]['location']['type']
        meta_info['parking_gate'] = pr['results'][selected_p_id]['floor_name']
        routes['route'] = 'Parking'
        routes['routes'] = ['Drive / Ride']
        routes['type'] = 'parking'
        routes['short_name'] = ''
        routes['long_name'] = ' '
        routes['agency'] = ''
        routes['vehicle_id'] = ''
        routes['occupancy'] = ''
        routes['departure_time'] = departure_time
        routes['ending_time'] = ending_time if ending_time is not None else ""
        routes['color'] = '#219653'
        routes['meta_info'] = meta_info
        routes['available_options'] = []
        routes['description'] = ''
        if idx == 0:
            map_dict = {}
            for item in pr['results'][selected_p_id]['rate']:
                if item['vehicle_type'] == "BICYCLE":
                    map_dict['bicycle'] = [item['rate_card'][0]['hourly_rate'], item['rate_card'][0]['max_rate']]
                elif item['vehicle_type'] == 'TWO_WHEELER':
                    map_dict['bike'] = [item['rate_card'][0]['hourly_rate'], item['rate_card'][0]['max_rate']]
                elif item['vehicle_type'] == 'CAR_JEEP_VAN':
                    map_dict['car'] = [item['rate_card'][0]['hourly_rate'], item['rate_card'][0]['max_rate']]
            psa = {}
            # TODO : Replace available with total in 1st parameter
            for item in pr['results'][selected_p_id]['parking_spot_availability']:
                if item['vehicle_type'] == "BICYCLE":
                    psa['bicycle'] = [item['available'], item['available']]
                elif item['vehicle_type'] == 'TWO_WHEELER':
                    psa['bike'] = [item['available'], item['available']]
                elif item['vehicle_type'] == 'CAR_JEEP_VAN':
                    psa['car'] = [item['available'], item['available']]
            try:
                routes['trip_time'] = get_waiting_time(ending_time,
                                                       departure_time)  #math.ceil(estimate_l1[0]['biketaxi']['data']['data']['rideTime'])
                routes['fare'] = map_dict['car'][
                    0]  #estimate_l1[0]['biketaxi']['data']['data']['quotes'][0]['totalAmount']
                # noinspection PyTypedDict
                routes['available_options'] = [
                    {
                        "name": "bicycle",
                        "fare": int(map_dict['bicycle'][0]) if 'bicycle' in map_dict else 0,
                        "max_fare": map_dict['bicycle'][1] if 'bicycle' in map_dict else 0,
                        "time": 0,  # max(1, estimate_l1[0]['biketaxi']['data']['data']['quotes'][0]['eta'])
                        "total": psa['bicycle'][0] if 'bicycle' in psa else 0,
                        "available": psa['bicycle'][0] if 'bicycle' in psa else 0
                    },
                    {
                        "name": "bike",
                        "fare": int(map_dict['bike'][0]) if 'bike' in map_dict else 0,
                        "max_fare": map_dict['bike'][1] if 'bike' in map_dict else 0,
                        "time": 0,  #max(1, estimate_l1[0]['biketaxi']['data']['data']['quotes'][0]['eta'])
                        "total": psa['bike'][0] if 'bike' in psa else 0,
                        "available": psa['bike'][1] if 'bike' in psa else 0
                    },
                    {
                        "name": "car",
                        "fare": int(map_dict['car'][0]) if 'car' in map_dict else 0,
                        "max_fare": map_dict['car'][1] if 'car' in map_dict else 0,
                        "time": 0,
                        "total": psa['car'][0] if 'car' in psa else 0,
                        "available": psa['car'][1] if 'car' in psa else 0
                    }
                ]
            except Exception as e:
                print(f'get route {e}')
                routes['trip_time'] = -1
                routes['fare'] = -1
                routes['available_options'] = []
        else:
            try:
                routes['trip_time'] = get_waiting_time(ending_time,
                                                       departure_time)
                routes[
                    'fare'] = parking_fare_flat
                routes['available_options'] = [
                    {
                        "name": "bicycle",
                        "fare": parking_fare_flat,
                        "time": 0
                    },
                    {
                        "name": "bike",
                        "fare": parking_fare_flat,
                        "time": 0
                    },
                    {
                        "name": "car",
                        "fare": parking_fare_flat,
                        "time": 0
                    }
                ]
            except Exception as e:
                routes['trip_time'] = -1
                routes['fare'] = -1
                print(f'get route 1 {e}')
        routes['stops'] = []
        routes['polyline'] = ''

    elif route_id == -1:
        routes['routes'] = ['walk']
        routes['route'] = 'walk'
        routes['type'] = 'walk'
        routes['short_name'] = ''
        routes['long_name'] = f" towards "
        routes['agency'] = ''
        routes['vehicle_id'] = ''
        routes['occupancy'] = ''
        routes['frequency'] = 0
        routes['fare'] = 0
        routes['departure_time'] = departure_time
        routes['ending_time'] = ending_time if ending_time is not None else ""
        routes['description'] = ''
        routes['trip_time'] = -1
        routes['stops'] = []
        routes['color'] = '#4D4D4D'
        routes['polyline'] = ''
    else:
        val = routes_df[routes_df.route_id == route_id].values
        routes['routes'] = [val[0][3].split('_')[0].capitalize()]
        routes['route'] = val[0][3].split('_')[0].capitalize()
        routes['type'] = 'metro'
        routes['short_name'] = ''
        routes['long_name'] = f" towards {val[0][3].split(' to ')[1]}"
        routes['agency'] = 'dmrc'
        routes['vehicle_id'] = ''
        routes['occupancy'] = ''
        routes['fare'] = 0
        routes['departure_time'] = departure_time
        routes['ending_time'] = ending_time if ending_time is not None else ""
        routes['color'] = get_color(routes['route'].lower())
        routes['description'] = ''
        routes['trip_time'] = -1
        routes['stops'] = []
        routes['polyline'] = ''
        routes['frequency'] = metro_misc.get_frequency(route_id, query_time)
        routes['meta_info'] = {}
    return routes


def get_stops(stop_id):
    stops = {}
    try:
        val = stops_df[stops_df.stop_id == stop_id].values
        stops['name'] = val[0][2]
        stops['lat'] = val[0][4]
        stops['lon'] = val[0][5]
        stops['id'] = stop_id
        if stop_id in id_map.keys():
            stops['ticketing_stop_id'] = id_map[stop_id]
        else:
            stops['ticketing_stop_id'] = None
    except Exception as e:
        print(f'get_stops {e} and {stop_id}')
    return stops


def get_color(route):
    metro_color_dict = {'green': '#20B2AA', 'red': '#FF4040', 'yellow': '#FFDF00', 'blue': '#4169E1',
                        'violet': '#553592', 'pink': '#FC8EAC', 'magenta': '#CC338B', 'orange/airport': '#FF4500',
                        'rapid': '#87CEEB', 'grey': '#838996'}
    if route in metro_color_dict:
        return metro_color_dict[route]
    else:
        return '#000000'


def get_metro_stops():
    return stops_df.to_dict('records')

import datetime
import json
import math
import os
import sqlite3

import numpy as np
import pandas as pd
import requests
from flask.cli import load_dotenv
from geopy.distance import distance

import last_mile_pt.algorithm.Parameter_file as pm
import last_mile_pt.algorithm.k_shortest_path as ksp
from last_mile_pt.algorithm.add_schedule import add_schedule
from utils.time_and_distance import get_multiple_calls_response_haversine

load_dotenv()

parking_url = os.getenv('parking_url')
FMT = '%H:%M:%S'
root_path = "static/GTFS/metro/"
conn = sqlite3.connect(root_path + 'dmrcSqlite.sqlite')
df_fare = pd.read_sql('select * from tbl_fare', con=conn)

dic = np.load("static/results_numpy_files/transfers_between_stops.npy", allow_pickle=True)
res = dic.item()
dic = np.load("static/results_numpy_files/stop_sequence.npy", allow_pickle=True)
dbmetro = sqlite3.connect('file:static/meta/metro/metro_response2.db?mode=ro', uri=True, check_same_thread=False)
dfa = dic.item()
one_hop_penalty = pm.hopOnePenalty
rang = pm._range
#maxfare = pm.Max_Fare


def get_static(path):
    stops = pd.read_csv(path + 'stops.txt')
    routes = pd.read_csv(path + 'routes.txt')
    trips = pd.read_csv(path + 'trips.txt')
    stop_times = pd.read_csv(path + 'stop_times.txt')
    return stops, routes, trips, stop_times


stops, routes, trips, stop_times = get_static(root_path)


def lm_dir_distance(loc, lat, lon):
    return distance(loc, [lat, lon]).km


def lm_fare(dist):
    if dist > pm.metro_only_walk:  #pm.min_walk:
        return pm.parking_fare_flat
    else:
        return 0

def lm_time(dist):
    if dist > pm.min_walk:
        return (dist / pm.Speed) * 60. + pm.flat_eta / 60.
    else:
        return max(0.1, (dist / 5) * 60.)


def m_path_list(source, destination):
    return dfa[(source, destination)][0]


def metro_distance(source, destination):
    res_path = m_path_list(source, destination)
    l = len(res_path)
    total_dist = 0
    # #print(res_path)
    for i in range(0, l - 1):
        a = list(stops[stops.stop_id == res_path[i]][["stop_lat", "stop_lon"]].values[0])
        b = list(stops[stops.stop_id == res_path[i + 1]][["stop_lat", "stop_lon"]].values[0])
        total_dist += distance(a, b).km
    return total_dist


def find_buses_within_radius(query_coords, df, radius):
    # radius in kilometers
    """
    given the query coordinates, realtime data df and radius (in km), the function returns the dataframe of vehicles
    within radius of the queried coordinates
    :param query_coords: tuple of lat, long
    :param df: stops data dataframe
    :param radius: distance threshold in km
    :return: dataframe of stops records within radius of given query coords
    """
    q_lat = query_coords[0]
    q_lng = query_coords[1]

    vehicle_lats = df['stop_lat'].values.astype(float)
    vehicle_lngs = df['stop_lon'].values.astype(float)

    stst = 6367 * 2 * np.arcsin(np.sqrt(
        np.sin((np.radians(vehicle_lats) - math.radians(q_lat)) / 2) ** 2 + math.cos(
            math.radians(q_lat)) * np.cos(np.radians(vehicle_lats)) * np.sin(
            (np.radians(vehicle_lngs) - math.radians(q_lng)) / 2) ** 2))
    df['distance'] = stst
    bus_record_indices_within_radius = np.where(stst <= radius)[0]
    return df.iloc[bus_record_indices_within_radius].sort_values('distance')


def get_ids(resp: object, df: object) -> object:
    return find_buses_within_radius((float(resp['location']['latitude']), float(resp['location']['longitude'])), df,
                                    pm._range).iloc[0, 0]


def get_fare(resp, dic, s_id):
    return resp['results'][dic[s_id]]['rate'][2]['rate_card'][0]['hourly_rate']


def src_and_dest_stops(src, dest):
    srcstop = stops.copy()
    deststop = stops.copy()
    srcstop.loc[:, 'dir_distance'] = srcstop.apply(lambda x: lm_dir_distance(src, x['stop_lat'], x['stop_lon']), axis=1)
    deststop.loc[:, 'dir_distance'] = deststop.apply(lambda x: lm_dir_distance(dest, x['stop_lat'], x['stop_lon']),
                                                     axis=1)
    srcs = 0
    dests = 0
    x = 0
    while srcs == 0:
        x += rang
        srcs = len(srcstop[srcstop.dir_distance < x])
    srcstop = srcstop[srcstop.dir_distance < x]
    x = 0
    while dests == 0:
        x += rang
        dests = len(deststop[deststop.dir_distance < x])
    deststop = deststop[deststop.dir_distance < x]

    #calculate distance
    src_coords = [(src, [x[0], x[1]], x[2]) for x in srcstop[['stop_lat', 'stop_lon', 'stop_id']].values]
    haversine_res = get_multiple_calls_response_haversine(src_coords)
    srcstop['distance'] = srcstop['stop_id'].map(haversine_res)
    dest_coords = [([x[0], x[1]], dest, x[2]) for x in deststop[['stop_lat', 'stop_lon', 'stop_id']].values]
    haversine_res = get_multiple_calls_response_haversine(dest_coords)
    deststop['distance'] = deststop['stop_id'].map(haversine_res)

    srcs = 0
    dests = 0
    x = 0
    while srcs == 0:
        x += rang
        srcs = len(srcstop[srcstop.distance < x])
    srcstop = srcstop[srcstop.distance < x]
    x = 0
    while dests == 0:
        x += rang
        dests = len(deststop[deststop.distance < x])
    deststop = deststop[deststop.distance < x]
    # filter out the stops that have parking.
    '''
    How:
    1. Get the api result.
    2. Match every result to a stop
    '''
    url = f'{parking_url}?distance={pm._range}&latitude={src[0]}&longitude={src[1]}'
    resp = requests.get(url).json()  # api call
    # ids = {get_ids(x, srcstop.copy()): i for i, x in enumerate(resp['results'])}
    ids = {i: get_ids(x, srcstop.copy()) for i, x in enumerate(resp['results'])}
    parking_dist = get_multiple_calls_response_haversine(
        [[src, [float(x['latitude']), float(x['longitude'])], x['id']] for i, x in enumerate(resp['results'])])
    srcstop = srcstop[(srcstop.stop_id.isin(ids.values()))]

    srcstop.loc[:,
    'fare'] = pm.parking_fare_flat  #srcstop['stop_id'].apply(lambda x: get_fare(resp, ids, x))#pm.parking_fare_flat #TODO: changes when real-time parking data
    deststop.loc[:, 'fare'] = deststop['distance'].apply(lm_fare)

    srcstop.loc[:, 'time(mins)'] = srcstop['distance'].apply(lm_time)
    deststop.loc[:, 'time(mins)'] = deststop['distance'].apply(lm_time)
    deststop = deststop[deststop.fare == 0]
    return srcstop, deststop, resp, ids, parking_dist


def shortest_route(srcstop, deststop, src, dest, k, maxfare, metro_only=False):  # ,current_time):
    if len(srcstop) == 0 or len(deststop) == 0:
        return []
    if metro_only:
        srcstop['time(mins)'] = srcstop['distance'].apply(lambda x: max(0.1, (x / 5) * 60.))
        deststop['time(mins)'] = deststop['distance'].apply(lambda x: max(0.1, (x / 5) * 60.))
    #### Add api calls here or do offline estimate here
    src_stops_edge = np.array(srcstop[["stop_id", "fare", "time(mins)"]])
    dest_stops_edge = np.array(deststop[["stop_id", "fare", "time(mins)"]])
    gr = ksp.Subgraph()
    gr.graph.add_nodes_from([0, -1])
    if metro_only:
        for sstop in src_stops_edge:
            gr.graph.add_edge(0, int(sstop[0]), weight=(0, round(sstop[2]), 0))
        for dstop in dest_stops_edge:
            gr.graph.add_edge(int(dstop[0]), -1, weight=(0, round(dstop[2]), 0))
    else:
        for sstop in src_stops_edge:
            gr.graph.add_edge(0, int(sstop[0]), weight=(sstop[1], round(sstop[2]), 0))
        for dstop in dest_stops_edge:
            gr.graph.add_edge(int(dstop[0]), -1, weight=(dstop[1], round(dstop[2]), 0))
    result = gr.dijkstra(0, -1, k, maxfare, one_hop_penalty)
    gr.graph.remove_nodes_from([0, -1])

    return result


def func4(TSTR):
    val = TSTR.split('.')
    val = val[0].split(':')
    h, m, s = int(val[0]), int(val[1]), int(val[2])
    dt = datetime.datetime(1900, 1, 1, h, m, s)
    return dt


# Given a time dept_time in "HH:MM:SS", add "timediff" seconds to dept_time
# Each response from graph consists of - [next_stop, current_stop, route_id, arrival_time, cost,
# departure_time, transit_time, transfer, vehicle_id]
def convAdd(dept_time, timediff):
    x = func4(dept_time)
    x += datetime.timedelta(seconds=int(timediff))
    return str(x.time())


def find_path(src, dest, current_time, maxfare=500):
    cur = dbmetro.cursor()
    k = pm.k
    srcstop, deststop, parking_resp, id_dict, parking_dist = src_and_dest_stops(src, dest)
    final_path = []
    estimate_l1 = []
    estimate_l2 = []
    result = shortest_route(srcstop, deststop, src, dest, k, maxfare)
    result_nolm = []
    _ = [result.append(x) for x in result_nolm if x not in result and len(x) == 3]
    if len(result) == 0:
        return [], [], []
    else:
        for temp in result:
            indx = []
            if dfa[(temp[0][1], temp[0][-2])] == []:
                continue
            else:
                resp = cur.execute(
                    f'select response from metro_response where source is {temp[0][1]} and destination is {temp[0][-2]}').fetchall()[
                    0][0]
                if len(resp) == 0:
                    continue
                path = json.loads(resp)[0]
                lm1dist = srcstop[srcstop.stop_id == temp[0][1]]['distance'].values[0]
                lm2dist = deststop[deststop.stop_id == temp[0][-2]]['distance'].values[0]
                lm1fare = srcstop[srcstop.stop_id == temp[0][1]].fare.values[0]
                lm2fare = deststop[deststop.stop_id == temp[0][-2]].fare.values[0]
                lm1time = srcstop[srcstop.stop_id == temp[0][1]]['time(mins)'].values[0] * 60
                lm2time = deststop[deststop.stop_id == temp[0][-2]]['time(mins)'].values[0] * 60
                met_fare = temp[1] - lm1fare - lm2fare
                path = [x + [''] for x in path]
                st_time = convAdd(current_time, lm1time)
                for i in range(1, len(path) - 1):
                    if path[i][2] != path[i + 1][2]:
                        indx.append(i)
                    if path[i][6] == '' and isinstance(path[i][5], int):
                        path[i][6] = path[i][5]
                        path[i][5] = ''
                if indx != []:
                    for i in indx:
                        path[i][-1] = met_fare
                path[-1][-1] = met_fare
                path[-1][3] = path[-1][5] = convAdd(st_time, path[-1][6])
                path = [[-1, -1, None, current_time, '', current_time, '', '', '', '']] + path + [
                    [-2, path[-1][0], -50, '', '', '', '', '', '', lm2fare]]
                path[1][3] = path[1][5] = st_time
                if lm1fare == 0:
                    path[1][2] = -1
                else:
                    path[1][2] = -50
                if lm2fare == 0:
                    path[-1][2] = -1
                else:
                    path[-1][2] = -50
                path[1][1] = -1
                path[1][-1] = lm1fare
                path[-1][3] = path[-1][5] = convAdd(path[-2][5], lm2time)
                path, est_fl, est_sl = add_schedule(path, 'metro', lm1time // 60, lm1fare)
                if not path:
                    continue
                if lm1dist <= 0.06:
                    path = [path[0]] + path[2:]
                    path[0][0] = path[0][1] = path[1][1]
                if lm2dist <= 0.06:
                    path = path[:-1]
                final_path.append(path)
                estimate_l1.append(est_fl)
                estimate_l2.append(est_sl)
    return final_path, parking_resp, id_dict, parking_dist  #[dir_path]

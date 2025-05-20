import datetime
import json
import os
import sqlite3

import numpy as np
import pandas as pd
from flask.cli import load_dotenv

from metro.algo.add_schedule import add_schedule
from metro.utils import get_trip_time

load_dotenv()
STATIC_FOLDER = os.getenv('STATIC_FOLDER')

routes_df = pd.read_csv(f'{STATIC_FOLDER}/GTFS/metro/routes.txt')
stops_df = pd.read_csv(f'{STATIC_FOLDER}/GTFS/metro/stops.txt')
metro_stops = pd.read_csv(f'{STATIC_FOLDER}/meta/metro_stops.csv')
con = sqlite3.connect(f'file:{STATIC_FOLDER}/meta/metro/metro_response2.db?mode=ro', uri=True, check_same_thread=False)
metro_fare = np.load(f'{STATIC_FOLDER}/meta/metro/metro_fare.npy', allow_pickle=True).item()


def func4(TSTR):
    val = TSTR.split('.')
    val = val[0].split(':')
    h, m, s = int(val[0]), int(val[1]), int(val[2])
    dt = datetime.datetime(1900, 1, 1, h, m, s)
    return dt


def convAdd(dept_time, timediff):
    x = func4(dept_time)
    x += datetime.timedelta(seconds=int(timediff))
    return str(x.time())


def get_resp_metro(src, dest, time):
    cur = con.cursor()
    cur.execute(f'select response from metro_response where source is \'{src}\' and destination is \'{dest}\'')
    try:
        res = json.loads(cur.fetchall()[0][0])
    except IndexError:
        res = []
    p = []
    for pth in res:
        pth[0][3] = pth[0][5] = time
        temp = 0
        count = 0
        for i in range(len(pth)):
            pth[i][2] = [pth[i][2]]
            if pth[i][6] != '':
                count += 1
                if count > 1:
                    pth[i][6] -= 4 * 120
                # temp += pth[i][6]
                # pth[i][6] = temp
                pth[i][3] = convAdd(time, pth[i][6])
                if i == len(pth):
                    pth[i][5] = pth[i][3]
                else:
                    pth[i][5] = convAdd(pth[i][3], 480)
                pth[i] += ['']
        x = add_schedule(pth)
        if x:
            x[-1][7] = metro_fare[x[0][0]][x[-1][0]]
            for ed in x:
                tx = ed[3]
                ed[3] = ed[5]
                ed[5] = ''
                ed[4] = tx
            x[-1][4] = x[-1][3]
            p.append(x)

    cur.close()
    # G_GTFS = nx.read_gpickle('static/meta/metro/metro_static_graph.gpickle')
    # dod_G = nx.to_dict_of_dicts(G_GTFS)
    # g = Graph(len(list(dod_G.keys())))
    #
    # g.graph = dod_G
    # g.dijkstra(src, dest, time)

    return p


def generate_response_metro(g):
    possible_directions = []
    # total_routes_added = []
    # flag = 0
    for all_ in g:
        directions = {'routes': []}
        routes = []
        routes_added = []
        # tt = 0
        reach_by = ''
        last_stop = {}
        for i in range(1, len(all_)):
            # Each response from graph consists of - [next_stop, current_stop, route_id, arrival_time, cost,departure_time,
            # transit_time, transfer, vehicle_id]
            if all_[i][3] != '':
                start_time = all_[i][3]
            if all_[i][5] != '':
                end_time = all_[i][5]
            if all_[i][2] not in routes_added:
                routes_added.append(all_[i][2])
                routes.append(get_route(all_[i][2]))
                if i == 1:
                    routes[len(routes_added) - 1]['stops'].append(get_stops(all_[0][0]))
                    routes[-1]['departure_time'] = all_[0][3]
                else:
                    routes[len(routes_added) - 1]['stops'].append(last_stop)
                    routes[-1]['departure_time'] = all_[i][3]
                routes[len(routes_added) - 1]['stops'].append(get_stops(all_[i][0]))
            else:
                routes[len(routes_added) - 1]['stops'].append(get_stops(all_[i][0]))

            try:
                trip_time = get_trip_time(start_time, end_time)
                routes[len(routes_added) - 1]['trip_time'] = trip_time
            except Exception as e:
                print(e)

            last_stop = get_stops(all_[i][0])
            # tt += all_[i][5]

        directions['routes'] = routes
        tt = all_[len(all_) - 1][6]
        possible_directions.append(
            {'directions': directions, 'trip_time': round(tt / 60.0), 'total_fare': 0,
             'reach_by': all_[len(all_) - 1][5]})
        # print(possible_directions)
    return possible_directions


def get_route(route_id):
    routes = {}
    val = routes_df[routes_df.route_id == route_id][
        ['route_short_name', 'route_long_name', 'route_type', 'route_id']].values
    # print(val)
    routes['route'] = val[0][1].split('_')[0]
    routes['routes'] = [val[0][1].split('_')[0]]
    routes['type'] = 'metro'
    routes['short_name'] = val[0][0]
    routes['long_name'] = f" towards {val[0][1].split(' to ')[1]}"
    routes['agency'] = 'DMRC'
    routes['vehicle_id'] = ''
    routes['occupancy'] = ''
    routes['fare'] = 0
    routes['departure_time'] = ''
    routes['color'] = get_color(routes['routes'][0].lower())
    routes['stops'] = []
    routes['trip_time'] = ''
    routes['polyline'] = ''
    return routes


def get_stops(stop_id):
    stops = {}
    val = stops_df[stops_df.stop_id == stop_id][['stop_id', 'stop_code', 'stop_name', 'stop_lat', 'stop_lon']].values
    stops['name'] = val[0][2]
    stops['lat'] = val[0][3]
    stops['lon'] = val[0][4]
    # print(stops)
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
    return metro_stops.to_dict('records')


if __name__ == '__main__':
    t = get_resp_metro(44, 132, '14:15:00')

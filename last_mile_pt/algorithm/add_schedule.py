import sqlite3
from datetime import datetime, timedelta
from functools import lru_cache

import pandas as pd

from last_mile_pt.algorithm.Parameter_file import lm2met_trans, met2met_trans, flat_eta, time_thresh

conn = sqlite3.connect('file:static/meta/schedule.db?mode=ro', uri=True, check_same_thread=False)
mstops = pd.read_csv('static/GTFS/metro/stops.txt')


def get_waiting_time(time1, time2):
    time1, time2 = str(time1).split(':'), str(time2).split(':')
    hours_2_sec2, min_2_sec2, hours_2_sec1, min_2_sec1 = (int(time2[0]) % 24) * 60 * 60, int(time2[1]) * 60, (
            int(time1[0]) % 24) * 60 * 60, int(time1[1]) * 60
    tot_sec1 = hours_2_sec1 + min_2_sec1 + int(float(time1[2]))
    tot_sec2 = hours_2_sec2 + min_2_sec2 + int(float(time2[2]))
    if tot_sec2 - tot_sec1 < 0:
        return tot_sec2 - tot_sec1 + (24 * 3600)
    return tot_sec2 - tot_sec1


def func4(TSTR):
    val = TSTR.split('.')
    val = val[0].split(':')
    h, m, s = int(val[0]), int(val[1]), int(val[2])
    dt = datetime(1900, 1, 1, h, m, s)
    return dt


def convAdd(dept_time, timediff):
    x = func4(dept_time)
    x += timedelta(seconds=timediff)
    return str(x.time())


def get_legs(path):
    leg_st = [0]
    for i in range(1, len(path) - 1):
        if compare_elements(path[i][2], path[i + 1][2]):
            leg_st.append(i + 1)
        else:
            path[i][5] = ''
    return leg_st


def get_dept_time(stop_id, route_id, departure_time, mode):
    c = conn.cursor()
    if mode == 'bus':
        if len(route_id) == 1:
            route_id = f"('{route_id[0]}')"
        else:
            route_id = tuple(route_id)
        t_ = c.execute(f"""select min(departure_time) from bus_schedule 
                        where stop_id is {stop_id} and route_id in {route_id} 
                        and departure_time > '{departure_time}';""").fetchall()[0][0]
        if t_ is None or get_waiting_time(departure_time, t_) > time_thresh:
            return None
    elif mode == 'metro':
        t_ = c.execute(f"""select min(departure_time) from metro_schedule 
                        where stop_id is {stop_id} and route_id is {route_id} 
                        and departure_time > '{departure_time}';""").fetchall()[0][0]
        if t_ is None or get_waiting_time(departure_time, t_) > time_thresh:
            return None
    else:
        t_ = departure_time
    return t_


def modify_init_leg(t, mode):
    t_ = get_dept_time(t[1][1], t[1][2], t[0][3], mode)
    if t_ is None:
        return -1
    t[0][5] = t_
    if t[1][2] != -1:
        t[1][5] = t_
        t[1][3] = t[0][3]
    if t_ > '23:59:59':
        return -1
    t[-1][3] = convAdd(t_, t[-1][5])
    return t


def modify_middle_leg(t, dept_time, init_cost, mode):
    t_ = get_dept_time(t[0][1], t[0][2], dept_time, mode)
    if t_ is None or t_ > '23:59:59':
        return -1
    if t_ == dept_time:
        t[-1][3] = t[-1][5] = convAdd(t_, t[-1][5])
    else:
        t[0][5] = t_
        t[-1][3] = convAdd(t_, t[-1][6])
        if len(t)>1:
            t[-1][5] = ''
    return t


def compare_elements(a, b):
    if isinstance(a, int) and isinstance(b, int):
        return a != b
    elif isinstance(a, list) and isinstance(b, list):
        return sorted(a) != sorted(b)
    else:
        return True

@lru_cache(maxsize = None)
def get_loc(id, mode = 'metro'):
    return mstops[mstops.stop_id == id][['stop_lat', 'stop_lon']].values[0]


def add_schedule(path, mode='metro', ridetime=None, fare=None):
    leg_st = get_legs(path)
    if len(leg_st) > 7 or len(path) == 0:
        return [], [], []
    if len(leg_st) == 1:
        return modify_init_leg(path, mode)
    t = path[leg_st[0]: leg_st[1]]
    if t[1][2] not in [-1, -50]:
        t = modify_init_leg(t, mode)
        if t == -1:
            return [], [], []
    elif t[1][2] == -1:
        t[1][6] = get_waiting_time(t[0][3], t[1][3])
        t[1][5] = t[0][5]
    else:
        eta = 0
        if eta == -1:
            t[1][5] = convAdd(t[0][5], flat_eta)
        else:
            t[1][5] = convAdd(t[0][5], eta * 60)  # eta in minutes
        t[-1][-1] = fare
        t[1][3] = convAdd(t[1][5], ridetime * 60)
        t[-1][6] = get_waiting_time(t[0][3], t[1][3])
    init_time = convAdd(t[-1][3], lm2met_trans)
    t = path[leg_st[-1]:]
    if t[0][2] == -1:
        t[0][6] = get_waiting_time(path[leg_st[-1] - 1][3], t[0][3])
    for i in range(1, len(leg_st) - 1):
        t = path[leg_st[i]: leg_st[i + 1]]
        t = modify_middle_leg(t, init_time, path[leg_st[i] - 1][6], mode)
        if t == -1:
            return [], [], []
        init_time = convAdd(t[-1][3], met2met_trans)
    #     print()
    t = path[leg_st[-1]:]
    if t[0][2] not in [-1, -50]:
        t = modify_middle_leg(t, init_time, path[leg_st[-1] - 1][6], mode)
        dat = {}
        if t == -1:
            return [], [], []
    else:
        t[0][5] = init_time  # path[leg_st[-1]-1][3]
        t[0][3] = convAdd(t[0][5], t[0][6])
    return path, {}, {}

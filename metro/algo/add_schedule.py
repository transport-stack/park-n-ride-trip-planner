from datetime import datetime, timedelta
import sqlite3

conn = sqlite3.connect('file:static/meta/schedule.db?mode=ro', uri=True, check_same_thread=False)


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


def get_dept_time(stop_id, route_id, departure_time, mode='metro', init = True):
    c = conn.cursor()
    if init == False:
        departure_time = convAdd(departure_time, 420)
    if mode == 'bus':
        if len(route_id) == 1:
            route_id = f"('{route_id[0]}')"
        else:
            route_id = tuple(route_id)
        t_ = c.execute(f"""select min(departure_time) from bus_schedule 
                        where stop_id is {stop_id} and route_id in {route_id} 
                        and departure_time > '{departure_time}';""").fetchall()[0][0]
    elif mode == 'metro':
        t_ = c.execute(f"""select min(departure_time) from metro_schedule 
                        where stop_id is {stop_id} and route_id is {route_id[0]} 
                        and departure_time > '{departure_time}';""").fetchall()[0][0]
    else:
        t_ = departure_time
    return t_


def modify_init_leg(t):
    if t[1][-1] == "":
        t_ = get_dept_time(t[1][1], t[1][2], t[0][5], 'metro')
    else:
        t_ = get_dept_time(t[1][1], t[1][2], t[0][5], t[1][-1])
    if t_ is None:
        return -1
    t[0][3] = t[1][3] = t_
    # t[1][3] = t[0][3]
    if t_ > '23:59:59':
        return -1
    t[-1][5] = convAdd(t_, t[-1][6])
    if len(t) > 2:
        t[-1][3] = ''
    return t


def modify_middle_leg(t, dept_time, init_cost):
    if t[0][-1] == '':
        t_ = get_dept_time(t[0][1], t[0][2], dept_time, 'metro', init = False)
    else:
        t_ = get_dept_time(t[0][1], t[0][2], dept_time, t[0][-1], init = False)
    if t_ is None or t_ > '23:59:59':
        return -1
    if t_ == dept_time:
        t[-1][5] = t[-1][3] = convAdd(t_, t[-1][6])
    else:
        t[0][3] = t_
        t[-1][5] = convAdd(t_, t[-1][6])
        if len(t) > 1:
            t[-1][3] = t[0][5] = ''
    return t


def compare_elements(a, b):
    if isinstance(a, int) and isinstance(b, int):
        return a != b
    elif (isinstance(a, list) and isinstance(b, list)) or (isinstance(a, tuple) and isinstance(b, tuple)):
        return sorted(a) != sorted(b)
    else:
        return True


def add_schedule(path):
    leg_st = get_legs(path)
    if len(leg_st) > 5 or len(path) == 0:
        return []
    if len(leg_st) == 1:
        t = modify_init_leg(path)
        if t == -1:
            return []
        else:
            return t
    t = path[leg_st[0]: leg_st[1]]
    t = modify_init_leg(t)
    if t == -1:
        return []
    for i in range(1, len(leg_st) - 1):
        t = path[leg_st[i]: leg_st[i + 1]]
        t = modify_middle_leg(t, path[leg_st[i] - 1][5], path[leg_st[i] - 1][6])
        if t == -1:
            return []
    #     print()
    t = path[leg_st[-1]:]
    t = modify_middle_leg(t, path[leg_st[-1] - 1][5], path[leg_st[-1] - 1][6])
    if t == -1:
        return []
    if len(t) > 1:
        t[-1][3] = t[-1][5]

    if t[-1][2] == [-1]:
        t[-1][3] = path[leg_st[-1] - 1][5]
    return path


if __name__ == '__main__':
    import pprint as pp

    test_path = [[132, 132, None, '12:00:00', '', '', '', '', '', 'metro', 'metro', 'metro'],
                 [1233, 132, -1, '', '', 1002, '', '', '', 'bus', 'metro', 'walk'],
                 [1701, 1233, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [1702, 1701, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [1703, 1702, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [1704, 1703, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [15613, 1704, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [459, 15613, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [1088, 459, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [1089, 1088, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [1090, 1089, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [323, 1090, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [325, 323, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [326, 325, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [327, 326, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [1092, 327, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [1093, 1092, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [347, 1093, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [348, 347, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [3505, 348, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [351, 3505, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [2980, 351, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [2981, 2980, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [353, 2981, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [354, 353, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [355, 354, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [3394, 355, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [3395, 3394, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [3396, 3395, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [3005, 3396, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [3571, 3005, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [2795, 3571, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [15344, 2795, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [15345, 15344, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [15346, 15345, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [203, 15346, [5647], '', '', '', '', '', '', 'bus', 'bus', 'bus'],
                 [2134, 203, [5647], '13:51:44', '', 6704, '', '', '', 'bus', 'bus', 'bus']]
    pp.pprint(add_schedule(test_path))

# algo modified for tracking
import bisect
import operator
import time as tx

import networkx as nx
import numpy as np

import last_mile_pt.algorithm.Parameter_file as pm
import pickle

root_path = "static/GTFS/metro/"
# conn = sqlite3.connect(root_path + 'dmrcSqlite.sqlite')
# df_fare = pd.read_sql('select * from tbl_fare', con = conn)import os
dic = np.load("static/results_numpy_files/stop_sequence.npy", allow_pickle=True)
dfa = dic.item()
dic = np.load("static/results_numpy_files/routes.npy", allow_pickle=True)
routes = dic.item()
with open("static/metro_static_time_and_cost_graph.pkl", 'rb') as file:
    shortest_G = pickle.load(file)

def update_record(time, current_stop, temp_record, record):
    if (time[current_stop][0] > temp_record[2]) or (
            time[current_stop][0] == temp_record[2] and time[current_stop][1] > temp_record[1]):
        time[current_stop][0] = temp_record[2]
        time[current_stop][1] = temp_record[1]
        record[current_stop] = temp_record


def not_same(candidate, list):
    if len(candidate) == 0 or len(candidate[0]) == 3 or dfa[(candidate[0][1], candidate[0][-2])] == []:
        return False
    cand_sseq = routes[(candidate[0][1], candidate[0][-2])]
    for temp in list:
        temp_sseq = routes[(temp[0][1], temp[0][-2])]
        if len(temp_sseq.intersection(cand_sseq)) == 0:
            return False
    return True


class Graph():
    def __init__(self, g=None):
        self.graph = shortest_G
        # self.V = np.array(self.graph.nodes())
        self.record = {}
        self.timeQ = []
    def short_penalty(self, time):
        return time

    def dijkstra(self, src, trgt, k, maxfare, one_hop_penalty):
        time = {}
        for i in self.graph.nodes():
            time[i] = [np.inf, np.inf]
        temp_record = [[src], 0, 0, 0]
        self.timeQ.append((0, 0, temp_record))
        self.timeQ = sorted(self.timeQ, key=operator.itemgetter(0, 1))
        self.path_count = 0
        self.res_path = []
        countx = 0
        while (self.timeQ):
            qNode = self.timeQ[0]
            self.timeQ = self.timeQ[1:]
            temp_record = qNode[-1]
            current_stop = temp_record[0][-1]
            update_record(time, current_stop, temp_record, self.record)

            if trgt == current_stop:
                if not_same(temp_record, self.res_path):
                    self.res_path.append(temp_record)
                    self.path_count += 1
                    if self.path_count >= k:
                        return self.res_path

            x = temp_record[0]
            if (len(x) > 3):
                continue
            for v in list(self.graph[current_stop].keys()):
                if v in x:
                    continue
                if current_stop != src and v != trgt and (
                        self.graph.has_edge(src, current_stop) == False or self.graph.has_edge(v, trgt) == False):
                    continue
                if (len(temp_record[0]) == 3 and v != trgt):
                    continue

                rec0 = [x for x in temp_record[0]]
                rec = [rec0]+[x for x in temp_record[1:]]
                if current_stop != src and v != trgt:
                    par_fare, par_time = self.graph[src][current_stop][0]['weight'][0], self.graph[src][current_stop][0]['weight'][1]
                    cur_fare, cur_time = self.graph[current_stop][v][0]['weight'][0], self.graph[current_stop][v][0]['weight'][1]
                    tot_fare = cur_fare + par_fare
                    # if par_fare == 0:
                    #     lmp = 0
                    #     mp = 1
                    # else:
                    lmp = pm.lmPenalty
                    mp = pm.metroPenalty
                    tot_time = round(mp * cur_time + lmp * par_time)
                    tot_time += round(self.graph[current_stop][v][0]['weight'][2]*one_hop_penalty)
                    if par_fare != 0:
                        tot_time += pm.lmtrans
                    # if self.graph[current_stop][v][0]['weight'][2] == 1:
                    #     tot_time += round(one_hop_penalty)
                    # elif self.graph[current_stop][v][0]['weight'][2] == 2:
                    #     tot_time += round(pm.hopTwoPenalty)
                    if tot_fare + self.graph[current_stop][v][0]['weight'][0] <= maxfare:
                        if (time[v][0] > tot_time) or (time[v][0] == tot_time and time[v][1] > tot_fare):
                            rec = [rec[0] + [v], tot_fare, tot_time]
                            if rec in self.timeQ:
                                continue
                            bisect.insort_left(self.timeQ, (tot_time, tot_fare, rec))
                    continue
                tot_time = 0
                tot_fare = 0
                if (current_stop == src):
                    tot_fare += self.graph[current_stop][v][0]['weight'][0]
                    tot_time = round(pm.lmPenalty * self.graph[current_stop][v][0]['weight'][1])
                    if tot_fare != 0:
                        tot_time += pm.lmtrans
                elif len(temp_record[0]) == 2:
                    if v == -1:
                        continue
                    else:
                        tot_fare += self.graph[current_stop][v][0]['weight'][0] + \
                               self.graph[src][temp_record[0][1]][0]['weight'][0]

                        tot_time = round(pm.lmPenalty * self.graph[current_stop][v][0]['weight'][1] + pm.metroPenalty * \
                                    self.graph[src][temp_record[0][1]][0]['weight'][1])
                        if self.graph[src][temp_record[0][1]][0]['weight'][0] != 0:
                            tot_time += pm.lmtrans
                else:
                    tot_fare += self.graph[current_stop][v][0]['weight'][0] + \
                                self.graph[temp_record[0][1]][temp_record[0][2]][0]['weight'][0] + \
                                self.graph[src][temp_record[0][1]][0]['weight'][0]
                    tot_time = round(pm.lmPenalty * self.graph[current_stop][v][0]['weight'][1] + pm.metroPenalty * \
                                self.graph[temp_record[0][1]][temp_record[0][2]][0]['weight'][1] + pm.lmPenalty * \
                                self.graph[src][temp_record[0][1]][0]['weight'][1])
                    if  self.graph[current_stop][v][0]['weight'][0] != 0:
                        tot_time += pm.lmtrans
                    if self.graph[src][temp_record[0][1]][0]['weight'][0] != 0:
                        tot_time += pm.lmtrans
                    # if self.graph[temp_record[0][1]][temp_record[0][2]][0]['weight'][2] == 1:
                    #     tot_time += round(one_hop_penalty)
                    # elif self.graph[temp_record[0][1]][temp_record[0][2]][0]['weight'][2] == 2:
                    #     tot_time += round(pm.hopTwoPenalty)
                    tot_time += round(self.graph[temp_record[0][1]][temp_record[0][2]][0]['weight'][2]*pm.hopOnePenalty)
                if tot_fare <= maxfare:
                    if (time[v][0] > tot_time) or (tot_time - time[v][0] <= pm.path_diff and time[v][1] >= tot_fare):
                        rec = [rec[0] + [v], tot_fare, tot_time]
                        if rec in self.timeQ:
                            continue
                        bisect.insort_left(self.timeQ, (tot_time, tot_fare, rec))

        return self.res_path

class Subgraph(Graph):
    def __init__(self, networkx_graph=None):
        super().__init__(networkx_graph)


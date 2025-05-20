import ast
import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from exts import db
from last_mile_pt.algorithm.lm_pt_best_k_path import find_path
from modules.time_helpers import convert_to_24h
from utils.generate_response_last_mile import get_stops, generate_response_metro_updated


def register_extensions(app):
    db.init_app(app)


def create_app():
    app = Flask(__name__)

    CORS(app)
    load_dotenv()

    app.config.from_pyfile('config.cfg')
    register_extensions(app)

    return app


app = create_app()
from db_operations.add_data import add_user_activity
from metro.main import get_metro_stops


@app.route('/')
def main():
    return 'Welcome to Directions home.'


@app.route('/v1/get_parknride_response', methods=['GET'])
def get_park_n_ride_response():
    res = {'message': '', 'description': ''}
    data = request.values

    src = ast.literal_eval(data['src'])
    dest = ast.literal_eval(data['dest'])
    src_name = data['src_name'] if 'src_name' in data else 'My location'
    dest_name = data['dest_name'] if 'dest_name' in data else 'Destination'
    query_time = convert_to_24h(data['time']) if 'time' in data else datetime.datetime.now().time().strftime("%H:%M:%S")
    maxfare = int(data['maxfare']) if 'maxfare' in data else 500
    src_type = data['src_type']
    dest_type = data['dest_type']

    if src_type == 'place' and dest_type == 'place':
        g, parking_resp, id_dict, parking_dist = find_path(src, dest, query_time, maxfare=maxfare)
    else:
        if src_type == 'metro':
            src = get_stops(src[0])
            src = (src['lat'], src['lon'])
        else:
            src = src
        if dest_type == 'metro':
            dest = get_stops(dest[0])
            dest = (dest['lat'], dest['lon'])
        else:
            dest = dest

        g, parking_resp, id_dict, parking_dist = find_path(src, dest, query_time)
    if g:
        generated_resp = generate_response_metro_updated(g, src, dest, src_name, dest_name, query_time,
                                                                     parking_resp, id_dict, parking_dist)
        res['message'] = 'success'
        res['description'] = 'route found'
        res['response_type'] = 'realtime'
        res['possible_directions'] = generated_resp
        res['data'] = generated_resp
        return jsonify(res), 200
    else:
        res['message'] = 'failed'
        res['description'] = 'no route found'
        res['response_type'] = 'failed'
        res['possible_directions'] = []
        res['data'] = []
        return jsonify(res), 400


@app.route('/get_stops_metro', methods=['GET'])
def get_stops_metro():
    try:
        add_user_activity(device_id='', end_point=request.endpoint, src='-1', dest='-1', type='Metro')
    except Exception:
        pass
    res = {'message': 'success', 'description': '', 'stops': get_metro_stops()}
    return jsonify(res), 200



if __name__ == '__main__':
    app.run()

    # Example api end call
    # /v1/get_parknride_response?src=[28.542995316734967,77.26967461296249]&src_name=Govind%20Puri&dest=[28.567433394054476,77.24136269458242]&dest_name=Moolchand&time=12:18:42&src_type=place&dest_type=place
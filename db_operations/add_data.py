import datetime

import pandas as pd

from app import create_app
from exts import db

metro_stops = pd.read_csv('static/meta/metro_stops.csv')
metro_stops.rename(columns={'lng': 'lon'}, inplace=True)

app = create_app()

from db_operations.models_file import UsersActivity, BusClusters, MetroStops


def add_user_activity(device_id, end_point, src=None, dest=None, type='Bus'):
    user_activity = UsersActivity(device_id=device_id, time_stamp=datetime.datetime.now(), end_point=end_point,
                                  src=src, dest=dest, type=type)
    db.session.add(user_activity)
    db.session.commit()


def add_metro_stops():
    val = metro_stops.to_dict('records')
    db.engine.execute(MetroStops.__table__.insert(), val)
    print("Added metro stops")


def set_data():
    with app.app_context():
        add_metro_stops()
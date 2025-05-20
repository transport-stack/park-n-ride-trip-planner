from exts import db
# from app import create_app

# app = create_app()


class BusClusters(db.Model):
    __bind_key__ = 'data-db'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    stop_type = db.Column(db.String(100))
    next_stop_name = db.Column(db.String(100))

    def __repr__(self):
        return f"BusCluster {self.device_id}, {self.end_point}>"


class MetroStops(db.Model):
    __bind_key__ = 'data-db'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    stop_type = db.Column(db.String(100))

    def __repr__(self):
        return f"MetroStops {self.device_id}, {self.end_point}>"


# User models
class UsersActivity(db.Model):
    __bind_key__ = 'user-db'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(100))
#    app_version = db.Column(db.Integer)
#    entry_point = db.Column(db.String(1))
    time_stamp = db.Column(db.DateTime)
    end_point = db.Column(db.String(24))
    src = db.Column(db.String(100))
    dest = db.Column(db.String(100))
    type = db.Column(db.String(10))

    def __repr__(self):
        return f"UsersActivity {self.device_id}, {self.end_point}>"


def create_db():
    # with app.app_context():
    db.create_all()

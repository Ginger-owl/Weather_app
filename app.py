import string
import os
import sys
import requests
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather.db'
key = os.urandom(24)
app.config['SECRET_KEY'] = key


db = SQLAlchemy(app)
url = 'https://api.openweathermap.org/data/2.5/weather'
my_api_key = '11c0d3dc6093f7442898ee49d2430d20'

try:
    api_key = my_api_key
except KeyError:
    sys.exit("Can't find api_key!")


class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    degrees = db.Column(db.Integer)
    state = db.Column(db.String(40), nullable=False)
    state_of_day = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return '<City %r>' % self.name


db.drop_all()
db.create_all()


@app.route('/', methods=['POST', 'GET'])
def index():
    query = City.query.all()
    cities_list = [x for x in query]
    cities_info = []
    for c in cities_list:

        weather_info = {'id': c.id, 'name': c.name, 'degrees': c.degrees, 'state': c.state, 'state_of_day': c.state_of_day}
        cities_info.append(weather_info)

    return render_template('index.html', cities=cities_info)


@app.route('/add', methods=['POST'])
def add():
    city_name = string.capwords(request.form['city_name'])
    exists = db.session.query(City.id).filter_by(name=city_name.title()).first() is not None

    if exists:
        flash("The city has already been added to the list!")
        return redirect(url_for('index'))
    else:
        r = requests.get(url, params={'q': city_name, 'appid': api_key, 'units': 'metric'})
        if r.status_code == 200:
            data = r.json()
        else:
            flash("The city doesn't exist!")
            return redirect(url_for('index'))

        degrees = int(data.get('main').get('temp'))
        state = data.get('weather')[0].get('main')

        offset = int(data.get('timezone'))
        dt = int(data.get('dt')) + offset
        local_hour = get_local_hour(dt, offset)

        day_state = get_state(local_hour)

        db.session.add(City(name=city_name, degrees=degrees, state=state, state_of_day=day_state))
        db.session.commit()

    return redirect(url_for('index'))


@app.route('/delete/<city_id>', methods=['GET', 'POST'])
def delete(city_id):
    city = City.query.filter_by(id=city_id).first()
    db.session.delete(city)
    db.session.commit()
    return redirect(url_for('index'))


def get_local_hour(dt, offset):
    ts = dt + offset
    return int(datetime.utcfromtimestamp(ts).strftime('%H'))


def get_state(hour: int):
    if 17 <= hour <= 23:
        return 'day'
    elif 6 <= hour <= 16:
        return 'evening-morning'
    else:
        return 'night'


# don't change the following way to run flask:
if __name__ == '__main__':
    if len(sys.argv) > 1:
        arg_host, arg_port = sys.argv[1].split(':')
        app.run(host=arg_host, port=arg_port)
    else:
        app.run()

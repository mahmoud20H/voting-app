from flask import Flask, render_template, request, make_response, g, redirect, url_for
from redis import Redis
import os
import socket
import random
import json
import logging

import requests

option_a = os.getenv('OPTION_A', "Cats")
option_b = os.getenv('OPTION_B', "Dogs")
hostname = socket.gethostname()

app = Flask(__name__)

gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.INFO)

def get_redis():
    if not hasattr(g, 'redis'):
        password = os.getenv('REDIS_PASSWORD')
        g.redis = Redis(host="redis", db=0, socket_timeout=5, password=password)
    return g.redis

def verify_auth():
    token = request.cookies.get('auth_token')
    if not token:
        return None
    try:
        resp = requests.get('http://auth:5000/auth/verify', cookies={'auth_token': token}, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        app.logger.error(f"Auth verification failed: {e}")
    return None

@app.route("/health")
def health():
    return "OK", 200

@app.route("/login/")
@app.route("/login")
def login_page():
    return render_template('login.html')

@app.route("/", methods=['POST','GET'])
def hello():
    user = verify_auth()
    if not user:
        from flask import redirect, url_for
        return redirect(url_for('login_page'))

    voter_id = request.cookies.get('voter_id')
    if not voter_id:
        voter_id = hex(random.getrandbits(64))[2:-1]

    vote = None

    if request.method == 'POST':
        redis = get_redis()
        vote = request.form['vote']
        app.logger.info('Received vote for %s from %s', vote, user.get('username'))
        data = json.dumps({'voter_id': voter_id, 'vote': vote})
        redis.rpush('votes', data)

    resp = make_response(render_template(
        'index.html',
        option_a=option_a,
        option_b=option_b,
        hostname=hostname,
        vote=vote,
        user=user
    ))
    resp.set_cookie('voter_id', voter_id)
    return resp


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=False, threaded=True)

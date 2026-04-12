from flask import Flask, request, jsonify, make_response
import jwt
import bcrypt
import psycopg2
import os
import time
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

# Config
DB_HOST = os.getenv('DB_HOST', 'db')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'postgres')
DB_NAME = os.getenv('POSTGRES_DB', 'postgres')
AUTH_SECRET = os.getenv('AUTH_SECRET', 'super-secret-key')
DEFAULT_ADMIN_USER = os.getenv('DEFAULT_ADMIN_USER', 'admin')
DEFAULT_ADMIN_PASSWORD = os.getenv('DEFAULT_ADMIN_PASSWORD', 'admin123')

def get_param_marker():
    if os.getenv('TESTING') == 'true':
        return '?'
    return '%s'

def get_db_connection():
    if os.getenv('TESTING') == 'true':
        import sqlite3
        conn = sqlite3.connect(':memory:', check_same_thread=False)
        return conn
    
    while True:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS
            )
            return conn
        except Exception as e:
            print(f"Waiting for DB... {e}")
            time.sleep(1)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # SQLite compatibility for SERIAL and PRIMARY KEY
    pk_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if os.getenv('TESTING') == 'true' else "SERIAL PRIMARY KEY"
    
    cur.execute(f'''
        CREATE TABLE IF NOT EXISTS users (
            id {pk_type},
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role VARCHAR(10) NOT NULL DEFAULT 'user'
        );
    ''')
    
    # Seed admin
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        hashed = bcrypt.hashpw(DEFAULT_ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        m = get_param_marker()
        cur.execute(
            f"INSERT INTO users (username, password_hash, role) VALUES ({m}, {m}, {m})",
            (DEFAULT_ADMIN_USER, hashed, 'admin')
        )
        print(f"Seeded admin user: {DEFAULT_ADMIN_USER}")
    
    conn.commit()
    cur.close()
    conn.close()

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Missing fields'}), 400
    
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        m = get_param_marker()
        cur.execute(
            f"INSERT INTO users (username, password_hash, role) VALUES ({m}, {m}, {m})",
            (username, hashed, 'user')
        )
        conn.commit()
        return jsonify({'message': 'User registered'}), 201
    except psycopg2.IntegrityError:
        return jsonify({'error': 'Username exists'}), 409
    finally:
        cur.close()
        conn.close()

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    cur = conn.cursor()
    m = get_param_marker()
    cur.execute(f"SELECT id, username, password_hash, role FROM users WHERE username = {m}", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
        payload = {
            'user_id': user[0],
            'username': user[1],
            'role': user[3],
            'exp': datetime.now(timezone.utc) + timedelta(hours=24)
        }
        token = jwt.encode(payload, AUTH_SECRET, algorithm='HS256')
        
        resp = make_response(jsonify({'message': 'Login successful', 'role': user[3]}))
        resp.set_cookie('auth_token', token, httponly=True, samesite='Lax', path='/')
        return resp
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/auth/verify', methods=['GET'])
def verify():
    token = request.cookies.get('auth_token')
    if not token:
        return jsonify({'error': 'No token'}), 401
    
    try:
        data = jwt.decode(token, AUTH_SECRET, algorithms=['HS256'])
        return jsonify(data), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/auth/logout', methods=['POST'])
def logout():
    resp = make_response(jsonify({'message': 'Logged out'}))
    resp.set_cookie('auth_token', '', expires=0, path='/')
    return resp

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

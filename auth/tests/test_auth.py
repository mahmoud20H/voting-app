import pytest
import json
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone

def test_register_success(client):
    response = client.post('/auth/register', json={
        'username': 'newuser',
        'password': 'password123'
    })
    assert response.status_code == 201
    assert b'User registered' in response.data

def test_register_duplicate(client):
    client.post('/auth/register', json={'username': 'dup', 'password': 'p'})
    response = client.post('/auth/register', json={'username': 'dup', 'password': 'p'})
    assert response.status_code == 409
    assert b'Username exists' in response.data

def test_register_missing_fields(client):
    response = client.post('/auth/register', json={'username': 'onlyone'})
    assert response.status_code == 400

def test_login_success(client):
    client.post('/auth/register', json={'username': 'loginuser', 'password': 'correct'})
    response = client.post('/auth/login', json={'username': 'loginuser', 'password': 'correct'})
    assert response.status_code == 200
    assert 'auth_token' in response.headers['Set-Cookie']
    
    data = response.get_json()
    assert data['role'] == 'user'

def test_login_invalid_creds(client):
    client.post('/auth/register', json={'username': 'failuser', 'password': 'p'})
    response = client.post('/auth/login', json={'username': 'failuser', 'password': 'wrong'})
    assert response.status_code == 401

def test_verify_valid_token(client, auth_token):
    client.set_cookie('auth_token', auth_token)
    response = client.get('/auth/verify')
    assert response.status_code == 200
    data = response.get_json()
    assert data['username'] == 'testuser'

def test_verify_no_token(client):
    response = client.get('/auth/verify')
    assert response.status_code == 401

def test_verify_expired_token(client):
    payload = {
        'username': 'old',
        'exp': datetime.now(timezone.utc) - timedelta(hours=1)
    }
    expired_token = jwt.encode(payload, 'test-secret', algorithm='HS256')
    client.set_cookie('auth_token', expired_token)
    response = client.get('/auth/verify')
    assert response.status_code == 401

def test_logout(client, auth_token):
    client.set_cookie('auth_token', auth_token)
    response = client.post('/auth/logout')
    assert response.status_code == 200
    # Check if cookie is cleared (expiry set to past)
    assert 'auth_token=;' in response.headers['Set-Cookie']

def test_admin_seeding(client):
    # In conftest, init_db is called. By default it seeds 'admin'
    response = client.post('/auth/login', json={
        'username': 'admin',
        'password': 'admin123'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['role'] == 'admin'

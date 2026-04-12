import pytest
from unittest.mock import patch, MagicMock
import json

def test_index_unauthenticated_redirect(client):
    response = client.get('/')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

@patch('app.requests.get')
def test_index_authenticated_load(mock_get, client, auth_token):
    # Mock auth service response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'username': 'testuser', 'role': 'user'}
    
    client.set_cookie('auth_token', auth_token)
    response = client.get('/')
    assert response.status_code == 200
    assert b'testuser' in response.data
    assert b'Logout' in response.data

def test_login_page_renders(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data

@patch('app.requests.get')
@patch('app.get_redis')
def test_submit_vote(mock_redis_getter, mock_get, client, auth_token):
    # Mock auth
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'username': 'voteuser', 'role': 'user'}
    
    # Mock redis
    mock_redis = MagicMock()
    mock_redis_getter.return_value = mock_redis
    
    client.set_cookie('auth_token', auth_token)
    response = client.post('/', data={'vote': 'a'})
    assert response.status_code == 200
    assert b'Processed by container' in response.data
    
    # Verify redis call
    mock_redis.rpush.assert_called_once()
    call_args = mock_redis.rpush.call_args[0]
    assert call_args[0] == 'votes'
    vote_data = json.loads(call_args[1])
    assert vote_data['vote'] == 'a'

@patch('app.requests.get')
def test_admin_button_visibility(mock_get, client, admin_token, auth_token):
    # Mock auth for admin
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'username': 'admin', 'role': 'admin'}
    
    client.set_cookie('auth_token', admin_token)
    response = client.get('/')
    assert b'See Results' in response.data
    
    # Mock auth for regular user
    mock_get.return_value.json.return_value = {'username': 'user', 'role': 'user'}
    client.set_cookie('auth_token', auth_token)
    response = client.get('/')
    assert b'See Results' not in response.data

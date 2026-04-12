const request = require('supertest');
const nock = require('nock');
const server = require('../server');

describe('Result App Auth Guard', () => {
  afterAll((done) => {
    server.close(done);
  });

  test('Redirect to login if no token provided', async () => {
    const res = await request(server).get('/');
    expect(res.statusCode).toBe(302);
    expect(res.header.location).toContain('/login');
  });

  test('Access denied if role is user', async () => {
    // Mock the auth service verify call
    nock('http://auth:5000')
      .get('/auth/verify')
      .reply(200, { username: 'normaluser', role: 'user' });

    const res = await request(server)
      .get('/')
      .set('Cookie', ['auth_token=fake-user-token']);

    expect(res.statusCode).toBe(302);
    expect(res.header.location).toBe('/access-denied');
  });

  test('Access granted if role is admin', async () => {
    nock('http://auth:5000')
      .get('/auth/verify')
      .reply(200, { username: 'adminuser', role: 'admin' });

    const res = await request(server)
      .get('/')
      .set('Cookie', ['auth_token=fake-admin-token']);

    expect(res.statusCode).toBe(200);
    // Since it sends a file, we check for html content
    expect(res.type).toBe('text/html');
  });

  test('Redirect if auth service returns error', async () => {
    nock('http://auth:5000')
      .get('/auth/verify')
      .reply(401, { error: 'Invalid token' });

    const res = await request(server)
      .get('/')
      .set('Cookie', ['auth_token=bad-token']);

    expect(res.statusCode).toBe(302);
    expect(res.header.location).toContain('/login');
  });

  test('Access denied page returns 200', async () => {
    const res = await request(server).get('/access-denied');
    expect(res.statusCode).toBe(200);
    expect(res.text).toContain('Access Denied');
  });
});

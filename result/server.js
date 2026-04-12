const express = require('express'),
    async = require('async'),
    { Pool } = require('pg'),
    cookieParser = require('cookie-parser'),
    app = express(),
    server = require('http').Server(app),
    io = require('socket.io')(server),
    http = require('http'),
    path = require('path');

var port = process.env.PORT || 4000;

io.on('connection', function (socket) {
  socket.emit('message', { text : 'Welcome!' });
  socket.on('subscribe', function (data) {
    socket.join(data.channel);
  });
});

var pool = new Pool({
  connectionString: 'postgres://postgres:postgres@db/postgres'
});

function getVotes(client) {
  client.query('SELECT vote, COUNT(id) AS count FROM votes GROUP BY vote', [], function(err, result) {
    if (err) {
      console.error("Error performing query: " + err);
    } else {
      var votes = collectVotesFromResult(result);
      io.sockets.emit("scores", JSON.stringify(votes));
    }

    setTimeout(function() {getVotes(client) }, 1000);
  });
}

function collectVotesFromResult(result) {
  var votes = {a: 0, b: 0};
  result.rows.forEach(function (row) {
    votes[row.vote] = parseInt(row.count);
  });
  return votes;
}

app.use(cookieParser());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(__dirname + '/views'));

// Auth Middleware
app.use(function(req, res, next) {
  if (req.path === '/access-denied') return next();

  const token = req.cookies.auth_token;
  if (!token) return res.redirect('/login?returnTo=/results');

  const options = {
    hostname: 'auth',
    port: 5000,
    path: '/auth/verify',
    method: 'GET',
    headers: { 'Cookie': `auth_token=${token}` }
  };

  const authReq = http.request(options, (authRes) => {
    let data = '';
    authRes.on('data', (chunk) => data += chunk);
    authRes.on('end', () => {
      if (authRes.statusCode === 200) {
        const user = JSON.parse(data);
        if (user.role === 'admin') {
          req.user = user;
          next();
        } else {
          res.redirect('/access-denied');
        }
      } else {
        res.redirect('/login?returnTo=/results');
      }
    });
  });

  authReq.on('error', (err) => {
    console.error('Auth check error:', err);
    res.redirect('/login?returnTo=/results');
  });
  authReq.end();
});

app.get('/', function (req, res) {
  res.sendFile(path.resolve(__dirname + '/views/index.html'));
});

app.get('/access-denied', function (req, res) {
  res.send('<h1>Access Denied</h1><p>You do not have permission to view this page.</p><a href="/">Back to Voting</a>');
});

if (require.main === module) {
  async.retry(
    {times: 1000, interval: 1000},
    function(callback) {
      pool.connect(function(err, client, done) {
        if (err) {
          console.error("Waiting for db");
        }
        callback(err, client);
      });
    },
    function(err, client) {
      if (err) {
        return console.error("Giving up");
      }
      console.log("Connected to db");
      getVotes(client);
    }
  );

  server.listen(port, function () {
    var port = server.address().port;
    console.log('App running on port ' + port);
  });
}

module.exports = server;

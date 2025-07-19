const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');

const app = express();
const port = 3000;

// Middleware
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());
app.use(express.static('public'));

// In-Memory store
const commands = {};   // { client_id: { cmd } }

const CLIENTS = {
  'client1': 'secret-token-123'
};

// Route: HTML page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'views', 'index.html'));
});

// Route: Form submission
app.post('/send-command', (req, res) => {
  const { client_id, token, cmd } = req.body;

  if (CLIENTS[client_id] !== token) {
    return res.status(401).send('Unauthorized: Invalid token for this client.');
  }

  commands[client_id] = { cmd };
  res.send(`✅ Command "${cmd}" queued for client "${client_id}". <a href="/">Back</a>`);
});

// Client polling
app.get('/command', (req, res) => {
  const { client_id, token } = req.query;

  if (CLIENTS[client_id] !== token) return res.status(401).send('Unauthorized');

  const entry = commands[client_id];
  if (entry) {
    delete commands[client_id];
    return res.json({ cmd: entry.cmd });
  }
  res.json({ cmd: null });
});

// Result receiving
app.post('/result', (req, res) => {
  const { client_id, token, output } = req.body;

  if (CLIENTS[client_id] !== token) return res.status(401).send('Unauthorized');

  console.log(`📥 Result from ${client_id}:\n${output}`);
  res.send('Result received');
});

// Start
app.listen(port, () => {
  console.log(`✅ Server running at http://localhost:${port}`);
});

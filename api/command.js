export default function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).send('Method Not Allowed');

  const { client_id, token } = req.query;

  const CLIENTS = { 'client1': 'secret-token-123' };
  if (CLIENTS[client_id] !== token) return res.status(401).send('Unauthorized');

  global.commands = global.commands || {};
  const entry = global.commands[client_id];
  if (entry) {
    delete global.commands[client_id];
    return res.json({ cmd: entry.cmd });
  }
  res.json({ cmd: null });
}

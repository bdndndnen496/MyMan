export default function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');

  const { client_id, token, cmd } = req.body;

  const CLIENTS = { 'client1': 'secret-token-123' };
  if (CLIENTS[client_id] !== token) return res.status(401).send('Unauthorized');

  global.commands = global.commands || {};
  global.commands[client_id] = { cmd };

  res.send(`✅ Command "${cmd}" queued for client "${client_id}".`);
}

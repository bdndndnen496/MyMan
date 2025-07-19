export default function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');

  const { client_id, token, output } = req.body;

  const CLIENTS = { 'client1': 'secret-token-123' };
  if (CLIENTS[client_id] !== token) return res.status(401).send('Unauthorized');

  console.log(`📥 Result from ${client_id}:\n${output}`);
  res.send('Result received');
}

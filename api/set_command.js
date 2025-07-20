export default async function handler(req, res) {
  if (req.method === 'POST') {
    const { client_id, command } = req.body;
    if (global.clients && global.clients[client_id]) {
      global.clients[client_id].command = command;
      res.status(200).json({ message: 'Command set' });
    } else {
      res.status(404).json({ error: 'Client not found' });
    }
  } else {
    res.status(405).end();
  }
}

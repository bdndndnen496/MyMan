export default async function handler(req, res) {
  if (req.method === 'POST') {
    const { client_id, username, status } = req.body;
    if (!global.clients) global.clients = {};
    global.clients[client_id] = { username, status, command: '' };
    res.status(200).json({ message: 'Registered' });
  } else {
    res.status(405).end();
  }
}

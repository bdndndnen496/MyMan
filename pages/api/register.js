import { updateClient } from './clients';

export default function handler(req, res) {
  if (req.method === 'POST') {
    const { client_id, username, status } = req.body;
    updateClient(client_id, username, status);
    res.status(200).json({ message: 'Registered', client_id });
  } else {
    res.status(405).json({ message: 'Method not allowed' });
  }
}

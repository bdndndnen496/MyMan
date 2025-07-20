let clients = [];

export default function handler(req, res) {
  if (req.method === 'POST') {
    const { client_id, username, status } = req.body;
    const existing = clients.find(c => c.client_id === client_id);
    if (!existing) {
      clients.push({ client_id, username, status });
    }
    res.status(200).json({ message: "✅ register ok", client_id });
  } else {
    res.status(405).json({ message: "Method not allowed" });
  }
}

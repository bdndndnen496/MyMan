let clients = {};

export default function handler(req, res) {
  res.status(200).json(clients);
}

export function updateClient(id, username, status) {
  clients[id] = { username, status };
}

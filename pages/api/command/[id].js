let commands = {};

export default function handler(req, res) {
  const { id } = req.query;
  if (req.method === 'POST') {
    const { command } = req.body;
    commands[id] = command;
    res.status(200).json({ message: `Command set for ${id}` });
  } else if (req.method === 'GET') {
    const cmd = commands[id] || '';
    commands[id] = '';
    res.status(200).json({ command: cmd });
  } else {
    res.status(405).json({ message: 'Method not allowed' });
  }
}

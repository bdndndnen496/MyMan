let outputs = {};

export default function handler(req, res) {
  const { id } = req.query;
  if (req.method === 'POST') {
    const { output } = req.body;
    outputs[id] = output;
    res.status(200).json({ message: 'Output received' });
  } else if (req.method === 'GET') {
    const out = outputs[id] || '';
    outputs[id] = '';
    res.status(200).json({ output: out });
  } else {
    res.status(405).json({ message: 'Method not allowed' });
  }
}

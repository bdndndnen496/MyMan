export default function handler(req, res) {
  const { client_id, username, status } = req.body;
  res.status(200).json({
    message: "✅ register works on Netlify",
    client: { client_id, username, status }
  });
}

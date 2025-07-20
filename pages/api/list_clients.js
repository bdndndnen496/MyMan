export default function handler(req, res) {
  res.status(200).json({
    message: "list_clients endpoint works ✅",
    note: "Hier könnte deine Clients-Auflistung implementiert werden."
  });
}

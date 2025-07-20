import { useState, useEffect } from 'react';

export default function Home() {
  const [clients, setClients] = useState([]);

  useEffect(() => {
    fetch('/api/list_clients')
      .then(res => res.json())
      .then(data => setClients(data.clients || []));
  }, []);

  return (
    <main style={{ padding: 20 }}>
      <h1>Next.js Webserver on Netlify 🚀</h1>
      <p>API route available at <code>/api/list_clients</code></p>
      <h2>Registered Clients:</h2>
      <ul>
        {clients.map(c => (
          <li key={c.client_id}>{c.username} ({c.status})</li>
        ))}
      </ul>
    </main>
  );
}

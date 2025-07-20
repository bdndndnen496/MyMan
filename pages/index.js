import { useEffect, useState } from 'react';

export default function Home() {
  const [clients, setClients] = useState({});

  useEffect(() => {
    const fetchClients = async () => {
      const res = await fetch('/api/clients');
      const data = await res.json();
      setClients(data);
    };
    fetchClients();
    const interval = setInterval(fetchClients, 5000);
    return () => clearInterval(interval);
  }, []);

  const sendCommand = async (clientId) => {
    const cmd = document.getElementById(`cmd-${clientId}`).value;
    await fetch(`/api/command/${clientId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd })
    });
    alert('Command sent to ' + clientId);
  };

  return (
    <main style={{ padding: 20 }}>
      <h1>Manager Dashboard on Netlify 🚀</h1>
      <h2>Registered Clients:</h2>
      <ul>
        {Object.keys(clients).map(id => (
          <li key={id}>
            <strong>{clients[id].username}</strong> ({id}) - {clients[id].status}
            <input id={`cmd-${id}`} placeholder="Command" />
            <button onClick={() => sendCommand(id)}>Send</button>
          </li>
        ))}
      </ul>
    </main>
  );
}

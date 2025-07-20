import { useState } from 'react';

export default function Home() {
  const [clientId, setClientId] = useState('');
  const [cmd, setCmd] = useState('');

  const sendCmd = async () => {
    await fetch('/api/set_command', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ client_id: clientId, command: cmd })
    });
    alert('Command sent');
  };

  return (
    <div>
      <h1>Manager Dashboard</h1>
      <p>Client ID: <input value={clientId} onChange={e => setClientId(e.target.value)} /></p>
      <p>Command: <input value={cmd} onChange={e => setCmd(e.target.value)} /></p>
      <button onClick={sendCmd}>Send Command</button>
    </div>
  );
}

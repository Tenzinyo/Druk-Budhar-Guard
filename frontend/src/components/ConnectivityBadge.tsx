import { useEffect, useState } from 'react';
import { checkHealth } from '../lib/api';
import { addNetworkListener, getNetworkStatus } from '../lib/deviceSensors';

type Status = 'online' | 'cached' | 'offline';

export default function ConnectivityBadge() {
  const [status, setStatus] = useState<Status>('offline');

  async function probe() {
    const net = await getNetworkStatus();
    if (!net.connected) { setStatus('offline'); return; }
    const alive = await checkHealth();
    setStatus(alive ? 'online' : 'cached');
  }

  useEffect(() => {
    probe();
    const timer = setInterval(probe, 15_000);
    let removeNet: (() => void) | undefined;
    addNetworkListener((s) => {
      if (!s.connected) setStatus('offline');
      else probe();
    }).then((fn) => { removeNet = fn; });
    return () => {
      clearInterval(timer);
      removeNet?.();
    };
  }, []);

  const label =
    status === 'online'  ? '● ONLINE'  :
    status === 'cached'  ? '◐ CACHED'  :
                           '○ OFFLINE';

  return <span className={`badge badge-${status}`}>{label}</span>;
}

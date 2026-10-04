import { useState } from 'react';
import type { AuditReport, Region, SlopeInput } from '../lib/api';
import { runAudit } from '../lib/api';
import { saveAudit } from '../lib/offlineStorage';
import TiltMeter from './TiltMeter';

interface Props {
  region: Region;
  onResult: (r: AuditReport) => void;
}

export default function AuditForm({ region, onResult }: Props) {
  const [theta,  setTheta]  = useState(35);
  const [z,      setZ]      = useState(1.5);
  const [phi,    setPhi]    = useState(28);
  const [hw,     setHw]     = useState(0);
  const [cp,     setCp]     = useState(0);
  const [gamma,  setGamma]  = useState(18);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const input: SlopeInput = { theta, z, phi, h_w: hw, c_prime: cp, gamma, region };
      const report = await runAudit(input);
      await saveAudit(report).catch(() => {}); // best-effort IndexedDB cache
      onResult(report);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Audit request failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

      {/* Tilt gauge */}
      <div className="card">
        <div style={{ fontSize: '0.78rem', color: 'var(--color-text-dim)', marginBottom: 8, letterSpacing: '0.05em' }}>
          SLOPE ANGLE (&theta;)
        </div>
        <TiltMeter angle={theta} onChange={setTheta} />
      </div>

      {/* Core inputs */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

        <div>
          <label>Depth to failure plane (z, metres)</label>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-dim)', marginBottom: 4 }}>
            One forearm deep &asymp; 0.4 m &nbsp;|&nbsp; knee-deep &asymp; 0.5 m
          </div>
          <input type="number" min="0.1" max="20" step="0.1" value={z}
            onChange={(e) => setZ(Number(e.target.value))} required />
        </div>

        <div>
          <label>Internal friction angle (&phi;, degrees)</label>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-dim)', marginBottom: 4 }}>
            Loose sand &asymp; 30&deg; &nbsp;|&nbsp; stiff clay &asymp; 20&deg; &nbsp;|&nbsp; gravel &asymp; 35&deg;
          </div>
          <input type="number" min="5" max="45" step="1" value={phi}
            onChange={(e) => setPhi(Number(e.target.value))} required />
        </div>

        <div>
          <label>Groundwater height (h_w, metres) &mdash; 0 = dry</label>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-dim)', marginBottom: 4 }}>
            Height of water above failure plane. Must be &le; z.
          </div>
          <input type="number" min="0" max={z} step="0.05" value={hw}
            onChange={(e) => setHw(Number(e.target.value))} />
        </div>
      </div>

      {/* Advanced panel */}
      <details className="card" style={{ padding: '12px 16px' }}>
        <summary style={{ cursor: 'pointer', fontSize: '0.8rem', color: 'var(--color-text-dim)', userSelect: 'none' }}>
          Advanced: soil cohesion &amp; unit weight
        </summary>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
          <div>
            <label>Effective cohesion c&prime; (kPa) &mdash; bare soil &asymp; 0</label>
            <input type="number" min="0" max="50" step="0.5" value={cp}
              onChange={(e) => setCp(Number(e.target.value))} />
          </div>
          <div>
            <label>Bulk unit weight &gamma; (kN/m&sup3;) &mdash; typical 16&ndash;20</label>
            <input type="number" min="10" max="25" step="0.5" value={gamma}
              onChange={(e) => setGamma(Number(e.target.value))} />
          </div>
        </div>
      </details>

      {error && (
        <div style={{
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: 8, padding: '10px 14px', fontSize: '0.85rem', color: 'var(--color-critical)',
        }}>
          {error}
        </div>
      )}

      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? 'Analysing…' : 'Run Slope Audit'}
      </button>
    </form>
  );
}

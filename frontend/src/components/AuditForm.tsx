import { useState } from 'react';
import type { AuditReport, Region, SlopeInput } from '../lib/api';
import { runAudit } from '../lib/api';
import { useT } from '../lib/i18n';
import { saveAudit } from '../lib/offlineStorage';
import { takePhoto } from '../lib/camera';
import TiltMeter from './TiltMeter';

interface Props {
  region: Region;
  language: string;
  onResult: (r: AuditReport) => void;
}

export default function AuditForm({ region, language, onResult }: Props) {
  const tr = useT(language);
  const [theta,  setTheta]  = useState(35);
  const [z,      setZ]      = useState(1.5);
  const [phi,    setPhi]    = useState(28);
  const [hw,     setHw]     = useState(0);
  const [cp,     setCp]     = useState(0);
  const [gamma,  setGamma]  = useState(18);
  const [photo,   setPhoto]   = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const input: SlopeInput = { theta, z, phi, h_w: hw, c_prime: cp, gamma, region, language };
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
          {tr.slopeAngle}
        </div>
        <TiltMeter angle={theta} onChange={setTheta} />
        <div style={{ fontSize: '0.72rem', color: 'var(--color-text-dim)', marginTop: 6 }}>
          {tr.tiltHint}
        </div>
      </div>

      {/* Core inputs */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

        <div>
          <label>{tr.depthLabel}</label>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-dim)', marginBottom: 4 }}>
            {tr.depthHint}
          </div>
          <input type="number" min="0.1" max="20" step="0.1" value={z}
            onChange={(e) => setZ(Number(e.target.value))} required />
        </div>

        <div>
          <label>{tr.frictionLabel}</label>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-dim)', marginBottom: 4 }}>
            {tr.frictionHint}
          </div>
          <input type="number" min="5" max="45" step="1" value={phi}
            onChange={(e) => setPhi(Number(e.target.value))} required />
        </div>

        <div>
          <label>{tr.groundwaterLabel}</label>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-dim)', marginBottom: 4 }}>
            {tr.groundwaterHint}
          </div>
          <input type="number" min="0" max={z} step="0.05" value={hw}
            onChange={(e) => setHw(Number(e.target.value))} />
          <button
            type="button"
            onClick={() => setHw(z)}
            style={{
              marginTop: 6, padding: '5px 12px', fontSize: '0.78rem',
              background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.4)',
              borderRadius: 6, color: '#93c5fd', cursor: 'pointer',
            }}
          >
            &#127783; {tr.saturatedPreset}
          </button>
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-dim)', marginTop: 4 }}>
            {tr.saturatedHint}
          </div>
        </div>
      </div>

      {/* Advanced panel */}
      <details className="card" style={{ padding: '12px 16px' }}>
        <summary style={{ cursor: 'pointer', fontSize: '0.8rem', color: 'var(--color-text-dim)', userSelect: 'none' }}>
          {tr.advanced}
        </summary>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
          <div>
            <label>{tr.cohesionLabel}</label>
            <input type="number" min="0" max="50" step="0.5" value={cp}
              onChange={(e) => setCp(Number(e.target.value))} />
          </div>
          <div>
            <label>{tr.unitWeightLabel}</label>
            <input type="number" min="10" max="25" step="0.5" value={gamma}
              onChange={(e) => setGamma(Number(e.target.value))} />
          </div>
        </div>
      </details>

      {/* Camera capture */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ fontSize: '0.78rem', color: 'var(--color-text-dim)', letterSpacing: '0.05em' }}>
          {tr.slopePhoto}
        </div>
        {photo ? (
          <div style={{ position: 'relative' }}>
            <img
              src={photo}
              alt="Slope capture"
              style={{ width: '100%', borderRadius: 8, display: 'block', maxHeight: 220, objectFit: 'cover' }}
            />
            <button
              type="button"
              onClick={() => setPhoto(null)}
              style={{
                position: 'absolute', top: 6, right: 6,
                background: 'rgba(0,0,0,0.55)', border: 'none', borderRadius: '50%',
                color: '#fff', width: 28, height: 28, cursor: 'pointer', fontSize: '0.85rem',
              }}
            >
              &times;
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={async () => { const p = await takePhoto(); if (p) setPhoto(p); }}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              background: 'rgba(74,154,74,0.12)', border: '1px dashed var(--color-sage)',
              borderRadius: 8, padding: '12px 16px', cursor: 'pointer',
              color: 'var(--color-sage)', fontSize: '0.9rem',
            }}
          >
            <span style={{ fontSize: '1.3rem' }}>&#128247;</span> {tr.takePhoto}
          </button>
        )}
      </div>

      {error && (
        <div style={{
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: 8, padding: '10px 14px', fontSize: '0.85rem', color: 'var(--color-critical)',
        }}>
          {error}
        </div>
      )}

      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? tr.analysing : tr.runAudit}
      </button>
    </form>
  );
}

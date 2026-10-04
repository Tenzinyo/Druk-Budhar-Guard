import { useState } from 'react';
import type { AuditReport, Region } from './lib/api';
import AuditForm from './components/AuditForm';
import AuditResult from './components/AuditResult';
import ConnectivityBadge from './components/ConnectivityBadge';
import RoadBulletin from './components/RoadBulletin';

type Tab = 'audit' | 'roads';

const REGIONS: { value: Region; label: string }[] = [
  { value: 'himalaya',    label: 'Himalaya (Bhutan / Nepal)' },
  { value: 'andes',       label: 'Andes (South America)' },
  { value: 'east_africa', label: 'East Africa' },
];

export default function App() {
  const [tab, setTab] = useState<Tab>(() => {
    const p = new URLSearchParams(window.location.search);
    return p.get('action') === 'roads' ? 'roads' : 'audit';
  });
  const [region, setRegion] = useState<Region>('himalaya');
  const [report, setReport] = useState<AuditReport | null>(null);

  function handleRegionChange(r: Region) {
    setRegion(r);
    setReport(null);
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      maxWidth: 480, margin: '0 auto',
    }}>

      {/* ── Header ── */}
      <header style={{
        padding: 'calc(var(--safe-top) + 12px) 16px 10px',
        background: 'var(--color-canopy)',
        borderBottom: '1px solid rgba(74,154,74,0.2)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexShrink: 0,
      }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--color-mist)' }}>
            BioTerrace Sentinel
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--color-text-dim)' }}>
            Slope auditor &middot; bio-prescriber
          </div>
        </div>
        <ConnectivityBadge />
      </header>

      {/* ── Region selector ── */}
      <div style={{ padding: '10px 16px 0', background: 'var(--color-canopy)', flexShrink: 0 }}>
        <select
          value={region}
          onChange={(e) => handleRegionChange(e.target.value as Region)}
        >
          {REGIONS.map((r) => (
            <option key={r.value} value={r.value}>{r.label}</option>
          ))}
        </select>
      </div>

      {/* ── Tab bar ── */}
      <nav style={{
        display: 'flex',
        background: 'var(--color-canopy)',
        borderBottom: '1px solid rgba(74,154,74,0.2)',
        flexShrink: 0, padding: '0 16px',
      }}>
        {(['audit', 'roads'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              flex: 1, padding: '10px 0',
              background: 'none', border: 'none',
              borderBottom: tab === t ? '2px solid var(--color-sage)' : '2px solid transparent',
              color: tab === t ? 'var(--color-text)' : 'var(--color-text-dim)',
              fontWeight: tab === t ? 600 : 400,
              fontSize: '0.9rem', cursor: 'pointer',
            }}
          >
            {t === 'audit' ? 'Audit' : 'Roads'}
          </button>
        ))}
      </nav>

      {/* ── Scrollable content ── */}
      <main style={{
        flex: 1, overflowY: 'auto',
        padding: '16px',
        paddingBottom: 'calc(var(--safe-bottom) + 24px)',
      }}>
        {tab === 'audit' && (
          report
            ? <AuditResult report={report} region={region} onClear={() => setReport(null)} />
            : <AuditForm region={region} onResult={setReport} />
        )}
        {tab === 'roads' && <RoadBulletin region={region} />}
      </main>
    </div>
  );
}

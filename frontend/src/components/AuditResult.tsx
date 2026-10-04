import type { AuditReport, Region } from '../lib/api';
import VoicePlayer from './VoicePlayer';

interface Props {
  report: AuditReport;
  region: Region;
  onClear: () => void;
}

const RISK_BADGE: Record<string, string> = {
  STABLE:   'badge-stable',
  MARGINAL: 'badge-marginal',
  CRITICAL: 'badge-critical',
};

function FoSBar({ value }: { value: number }) {
  const pct = Math.min(100, (value / 3) * 100);
  const color =
    value >= 1.5 ? 'var(--color-stable)' :
    value >= 1.0 ? 'var(--color-marginal)' :
                   'var(--color-critical)';
  return (
    <div style={{ background: 'rgba(255,255,255,0.07)', borderRadius: 6, height: 7, overflow: 'hidden' }}>
      <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 6, transition: 'width 0.5s ease' }} />
    </div>
  );
}

export default function AuditResult({ report, region, onClear }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* FoS summary card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <span style={{ fontWeight: 700, fontSize: '1rem' }}>Audit Result</span>
          <span className={`badge ${RISK_BADGE[report.risk_level]}`}>{report.risk_level}</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-dim)' }}>FoS — bare slope</span>
              <span style={{ fontWeight: 600 }}>{report.fos_baseline.toFixed(2)}</span>
            </div>
            <FoSBar value={report.fos_baseline} />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-dim)' }}>FoS — after planting</span>
              <span style={{ fontWeight: 600, color: 'var(--color-stable)' }}>{report.fos_post_intervention.toFixed(2)}</span>
            </div>
            <FoSBar value={report.fos_post_intervention} />
          </div>

          <div style={{ fontSize: '0.8rem', color: 'var(--color-text-dim)', marginTop: 2, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <span>Improvement: <strong style={{ color: 'var(--color-sage)' }}>+{report.fos_improvement.toFixed(2)}</strong></span>
            <span>Band: <strong style={{ color: 'var(--color-text)' }}>{report.slope_band}</strong></span>
            <span>Post-risk: <span className={`badge ${RISK_BADGE[report.risk_level_post]}`} style={{ fontSize: '0.68rem' }}>{report.risk_level_post}</span></span>
          </div>
        </div>
      </div>

      {/* Warning flags */}
      {report.warning_flags.length > 0 && (
        <div style={{
          background: 'rgba(245,158,11,0.08)',
          border: '1px solid rgba(245,158,11,0.3)',
          borderRadius: 10, padding: '10px 14px',
        }}>
          {report.warning_flags.map((w, i) => (
            <div key={i} style={{
              fontSize: '0.82rem', color: 'var(--color-marginal)',
              marginBottom: i < report.warning_flags.length - 1 ? 4 : 0,
            }}>
              {w}
            </div>
          ))}
        </div>
      )}

      {/* Prescriptions */}
      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-dim)', fontWeight: 600, letterSpacing: '0.06em' }}>
        BIO-ENGINEERING PRESCRIPTIONS
      </div>

      {report.prescriptions.map((p, i) => (
        <div key={i} className="card" style={{ borderLeft: '3px solid var(--color-sage)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{p.method}</span>
            <span style={{ fontSize: '0.72rem', color: 'var(--color-text-dim)' }}>Priority {p.priority}</span>
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--color-mist)', marginBottom: 6 }}>
            {p.species.join(' · ')}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--color-text-dim)' }}>Spacing: {p.spacing_physical}</span>
            <span style={{ fontSize: '0.78rem', color: 'var(--color-text-dim)' }}>Depth: {p.depth_physical}</span>
          </div>
          {p.notes && (
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-dim)', marginTop: 6, fontStyle: 'italic' }}>
              {p.notes}
            </div>
          )}
        </div>
      ))}

      {/* Vernacular advisory */}
      {report.vernacular_script && (
        <div className="card" style={{ borderLeft: '3px solid var(--color-leaf)' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-dim)', marginBottom: 6, letterSpacing: '0.05em' }}>
            LOCAL ADVISORY
          </div>
          <p style={{ margin: 0, lineHeight: 1.55, fontSize: '0.9rem' }}>{report.vernacular_script}</p>
        </div>
      )}

      {/* Voice player */}
      <VoicePlayer report={report} region={region} />

      {/* Run another */}
      <button
        className="btn-primary"
        onClick={onClear}
        style={{ background: 'transparent', border: '1px solid var(--color-leaf)', color: 'var(--color-sage)' }}
      >
        Run Another Audit
      </button>
    </div>
  );
}

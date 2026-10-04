import { useState } from 'react';
import type { AuditReport, Region } from '../lib/api';
import { resolveAudioUrl, synthesizeVoice, LANGUAGE_NATIVE } from '../lib/api';
import { useT } from '../lib/i18n';

interface Props {
  report: AuditReport;
  region: Region;
  language: string;
}

type State = 'idle' | 'loading' | 'ready' | 'error';

export default function VoicePlayer({ report, region, language }: Props) {
  const tr = useT(language);
  const [state, setState] = useState<State>('idle');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [script, setScript] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSpeak() {
    setState('loading');
    setError(null);
    try {
      const text = report.vernacular_script
        ?? tr.riskFallback[report.risk_level as keyof typeof tr.riskFallback]
        ?? report.risk_level;
      const res = await synthesizeVoice(text, region, report.risk_level, language);
      setScript(res.script);
      if (res.audio_available && res.audio_endpoint) {
        setAudioUrl(resolveAudioUrl(res.audio_endpoint));
      } else {
        setAudioUrl(null);
      }
      setState('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Voice synthesis failed');
      setState('error');
    }
  }

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ fontSize: '0.72rem', color: 'var(--color-text-dim)', letterSpacing: '0.05em' }}>
        {tr.voiceAdvisoryHeader} — {LANGUAGE_NATIVE[language] ?? language}
      </div>

      {state === 'idle' && (
        <button className="btn-primary" onClick={handleSpeak} style={{ padding: '10px' }}>
          {tr.hearAdvisory} {LANGUAGE_NATIVE[language] ?? language}
        </button>
      )}

      {state === 'loading' && (
        <div style={{ textAlign: 'center', color: 'var(--color-text-dim)', fontSize: '0.85rem', padding: '8px 0' }}>
          {tr.synthesizing}
        </div>
      )}

      {state === 'ready' && (
        <>
          {audioUrl ? (
            <audio
              controls
              src={audioUrl}
              style={{ width: '100%', accentColor: 'var(--color-sage)' }}
            />
          ) : (
            <div style={{
              fontSize: '0.85rem',
              background: 'rgba(255,255,255,0.04)',
              padding: '10px 12px',
              borderRadius: 8,
              lineHeight: 1.5,
            }}>
              {script}
            </div>
          )}
          <button
            onClick={handleSpeak}
            style={{
              background: 'none', border: 'none',
              color: 'var(--color-text-dim)', fontSize: '0.78rem',
              cursor: 'pointer', textAlign: 'left', padding: 0,
            }}
          >
            {tr.resynthesize}
          </button>
        </>
      )}

      {state === 'error' && (
        <div style={{ color: 'var(--color-critical)', fontSize: '0.82rem', display: 'flex', gap: 8, alignItems: 'center' }}>
          <span>{error}</span>
          <button
            onClick={handleSpeak}
            style={{ background: 'none', border: 'none', color: 'var(--color-sage)', cursor: 'pointer', fontSize: '0.82rem' }}
          >
            {tr.retry}
          </button>
        </div>
      )}
    </div>
  );
}

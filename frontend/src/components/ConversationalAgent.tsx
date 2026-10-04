/**
 * ConversationalAgent — ElevenLabs real-time voice conversation
 * ==============================================================
 *
 * Connects to ElevenLabs Conversational AI via WebSocket using a
 * signed URL fetched from the backend (keeps API key server-side).
 *
 * Audio pipeline:
 *   Mic → AudioContext (16 kHz) → ScriptProcessor → PCM int16 → base64 → WS → ElevenLabs
 *   ElevenLabs → base64 PCM → AudioContext buffer → scheduled playback
 *
 * The agent is pre-loaded with slope audit context (FoS, risk level,
 * prescription) and responds in the region's local language.
 */

import { useEffect, useRef, useState } from 'react';
import type { AuditReport, Region } from '../lib/api';
import { getConvaiUrl, LANGUAGE_NATIVE } from '../lib/api';
import { useT } from '../lib/i18n';

interface Props {
  report: AuditReport;
  region: Region;
  language: string;
}

type AgentState = 'idle' | 'connecting' | 'listening' | 'thinking' | 'speaking' | 'error';

const STATE_LABEL_KEY: Record<AgentState, keyof import('../lib/i18n').Translations | ''> = {
  idle:       '',
  connecting: 'connecting',
  listening:  'listening',
  thinking:   'thinking',
  speaking:   'agentSpeaking',
  error:      'connecting',
};

const STATE_COLOR: Record<AgentState, string> = {
  idle:       'var(--color-text-dim)',
  connecting: 'var(--color-text-dim)',
  listening:  'var(--color-stable)',
  thinking:   'var(--color-marginal)',
  speaking:   'var(--color-sage)',
  error:      'var(--color-critical)',
};

export default function ConversationalAgent({ report, region, language }: Props) {
  const tr = useT(language);
  const [state, setState]         = useState<AgentState>('idle');
  const [transcript, setTranscript] = useState<{ role: 'user' | 'agent'; text: string }[]>([]);
  const [error, setError]         = useState<string | null>(null);

  const wsRef           = useRef<WebSocket | null>(null);
  const audioCtxRef     = useRef<AudioContext | null>(null);
  const processorRef    = useRef<ScriptProcessorNode | null>(null);
  const sourceRef       = useRef<MediaStreamAudioSourceNode | null>(null);
  const streamRef       = useRef<MediaStream | null>(null);
  const nextPlayRef     = useRef(0);       // scheduled end-time for audio queue
  const stateRef        = useRef<AgentState>('idle');
  const transcriptRef   = useRef<HTMLDivElement | null>(null);

  useEffect(() => { stateRef.current = state; }, [state]);

  // Auto-scroll transcript
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [transcript]);

  useEffect(() => () => { cleanup(); }, []);

  // ── Audio helpers ────────────────────────────────────────────────────────────

  function float32ToPcm16Base64(float32: Float32Array): string {
    const int16 = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      int16[i] = Math.max(-32768, Math.min(32767, Math.round(float32[i] * 32767)));
    }
    const bytes = new Uint8Array(int16.buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i += 8192) {
      binary += String.fromCharCode(...Array.from(bytes.subarray(i, i + 8192)));
    }
    return btoa(binary);
  }

  function scheduleChunk(b64: string, ctx: AudioContext) {
    try {
      const binary = atob(b64);
      const bytes  = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

      const int16  = new Int16Array(bytes.buffer);
      const f32    = new Float32Array(int16.length);
      for (let i = 0; i < int16.length; i++) f32[i] = int16[i] / 32768;

      const buf = ctx.createBuffer(1, f32.length, 16000);
      buf.copyToChannel(f32, 0);

      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(ctx.destination);

      const startAt = Math.max(ctx.currentTime, nextPlayRef.current);
      src.start(startAt);
      nextPlayRef.current = startAt + buf.duration;

      src.onended = () => {
        // Transition back to listening once the audio queue drains
        if (nextPlayRef.current <= ctx.currentTime + 0.05) {
          if (stateRef.current === 'speaking') setState('listening');
        }
      };
    } catch {
      // ignore individual chunk decode errors
    }
  }

  // ── Lifecycle ────────────────────────────────────────────────────────────────

  function cleanup() {
    wsRef.current?.close();
    wsRef.current = null;
    processorRef.current?.disconnect();
    processorRef.current = null;
    sourceRef.current?.disconnect();
    sourceRef.current = null;
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      audioCtxRef.current.close();
    }
    audioCtxRef.current = null;
    nextPlayRef.current = 0;
  }

  // ── Start conversation ───────────────────────────────────────────────────────

  async function startConversation() {
    setState('connecting');
    setError(null);
    setTranscript([]);

    try {
      // 1. Get signed WebSocket URL + context from backend
      const { url, el_code, system_prompt, first_message, context } = await getConvaiUrl(
        region,
        report.risk_level,
        report.fos_baseline,
        report.prescriptions[0]?.method ?? 'bioengineering',
        language,
      );

      // 2. Create 16 kHz AudioContext
      const AudioCtx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx({ sampleRate: 16000 });
      audioCtxRef.current = ctx;
      nextPlayRef.current = 0;

      // 3. Open ElevenLabs ConvAI WebSocket
      const ws = new WebSocket(url as string);
      wsRef.current = ws;

      ws.onopen = async () => {
        // Override agent prompt with slope audit context
        ws.send(JSON.stringify({
          type: 'conversation_initiation_client_data',
          conversation_config_override: {
            agent: {
              prompt:        { prompt: system_prompt as string },
              first_message: first_message as string,
              language:      el_code as string,
            },
          },
        }));

        // 4. Request microphone
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            sampleRate:      16000,
            channelCount:    1,
            echoCancellation: true,
            noiseSuppression: true,
          },
        });
        streamRef.current = stream;

        const source    = ctx.createMediaStreamSource(stream);
        sourceRef.current = source;
        const processor = ctx.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (e) => {
          if (ws.readyState !== WebSocket.OPEN) return;
          const b64 = float32ToPcm16Base64(e.inputBuffer.getChannelData(0));
          ws.send(JSON.stringify({ user_audio_chunk: b64 }));
        };

        source.connect(processor);
        processor.connect(ctx.destination);
        setState('listening');
      };

      ws.onmessage = (event) => {
        let msg: Record<string, unknown>;
        try { msg = JSON.parse(event.data as string); } catch { return; }

        switch (msg.type) {
          case 'ping': {
            const ping = msg.ping_event as { event_id: number };
            ws.send(JSON.stringify({ type: 'pong', event_id: ping?.event_id }));
            break;
          }
          case 'audio': {
            const ae = msg.audio_event as { audio_base_64: string };
            setState('speaking');
            scheduleChunk(ae.audio_base_64, ctx);
            break;
          }
          case 'agent_response': {
            const ar = msg.agent_response_event as { agent_response: string };
            setTranscript(prev => [...prev, { role: 'agent', text: ar.agent_response }]);
            break;
          }
          case 'user_transcript': {
            const ut = msg.user_transcription_event as { user_transcript: string };
            if (ut.user_transcript.trim()) {
              setTranscript(prev => [...prev, { role: 'user', text: ut.user_transcript }]);
              setState('thinking');
            }
            break;
          }
          case 'interruption':
            // User interrupted — reset playback clock
            nextPlayRef.current = ctx.currentTime;
            setState('listening');
            break;
        }
      };

      ws.onerror = () => {
        setError('Connection to ElevenLabs failed');
        setState('error');
        cleanup();
      };

      ws.onclose = () => {
        if (stateRef.current !== 'idle' && stateRef.current !== 'error') {
          setState('idle');
        }
        cleanup();
      };

      void context; // suppress unused warning

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start conversation');
      setState('error');
      cleanup();
    }
  }

  function stopConversation() {
    cleanup();
    setState('idle');
    setTranscript([]);
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  const isActive = state !== 'idle' && state !== 'error';

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: '0.72rem', color: 'var(--color-text-dim)', letterSpacing: '0.05em' }}>
          {tr.voiceAdvisorHeader} — {LANGUAGE_NATIVE[language] ?? language}
        </div>
        {isActive && (
          <button
            onClick={stopConversation}
            style={{
              background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 6, color: 'var(--color-critical)',
              padding: '3px 10px', fontSize: '0.75rem', cursor: 'pointer',
            }}
          >
            {tr.endCall}
          </button>
        )}
      </div>

      {/* Idle / error state — big start button */}
      {!isActive && (
        <>
          <button
            className="btn-primary"
            onClick={startConversation}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, padding: '14px' }}
          >
            <span style={{ fontSize: '1.5rem' }}>&#127897;</span>
            {tr.talkToAdvisor} {LANGUAGE_NATIVE[language] ?? language}
          </button>
          {error && (
            <div style={{ fontSize: '0.82rem', color: 'var(--color-critical)', lineHeight: 1.4 }}>
              {error}
            </div>
          )}
        </>
      )}

      {/* Active state */}
      {isActive && (
        <>
          {/* Status dot + label */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span
              className={state === 'listening' ? 'pulse-dot' : undefined}
              style={{
                display: 'inline-block',
                width: 9, height: 9, borderRadius: '50%',
                background: STATE_COLOR[state],
                flexShrink: 0,
              }}
            />
            <span style={{ fontSize: '0.83rem', color: STATE_COLOR[state] }}>
              {STATE_LABEL_KEY[state] ? tr[STATE_LABEL_KEY[state] as keyof typeof tr] : ''}
            </span>
          </div>

          {/* Transcript bubbles */}
          <div
            ref={transcriptRef}
            style={{
              minHeight: 80, maxHeight: 260, overflowY: 'auto',
              display: 'flex', flexDirection: 'column', gap: 8,
            }}
          >
            {transcript.length === 0 && (
              <div style={{ fontSize: '0.8rem', color: 'var(--color-text-dim)', textAlign: 'center', padding: '12px 0' }}>
                {tr.saySomething} {LANGUAGE_NATIVE[language] ?? language}
              </div>
            )}
            {transcript.map((t, i) => (
              <div
                key={i}
                style={{
                  alignSelf: t.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '88%',
                  background: t.role === 'user'
                    ? 'rgba(74,154,74,0.18)'
                    : 'rgba(255,255,255,0.06)',
                  border: t.role === 'agent'
                    ? '1px solid rgba(74,154,74,0.2)'
                    : 'none',
                  borderRadius: 10,
                  padding: '8px 12px',
                  fontSize: '0.88rem',
                  lineHeight: 1.55,
                }}
              >
                <div style={{ fontSize: '0.65rem', color: 'var(--color-text-dim)', marginBottom: 3 }}>
                  {t.role === 'user' ? tr.you : tr.advisor}
                </div>
                {t.text}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

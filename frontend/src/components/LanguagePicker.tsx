import type { Region, LanguageOption } from '../lib/api';
import { REGION_LANGUAGE_OPTIONS } from '../lib/api';

interface Props {
  region: Region;
  language: string;
  onChange: (language: string) => void;
}

export default function LanguagePicker({ region, language, onChange }: Props) {
  const options: LanguageOption[] = REGION_LANGUAGE_OPTIONS[region];

  return (
    <div style={{ padding: '8px 16px 10px', background: 'var(--color-canopy)', flexShrink: 0 }}>
      <div style={{ fontSize: '0.68rem', color: 'var(--color-text-dim)', letterSpacing: '0.06em', marginBottom: 6 }}>
        LANGUAGE
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {options.map((opt) => {
          const active = opt.value === language;
          return (
            <button
              key={opt.value}
              aria-label={`${opt.label} — ${opt.country}`}
              onClick={() => onChange(opt.value)}
              style={{
                padding: '5px 12px',
                borderRadius: 20,
                border: active
                  ? '1px solid var(--color-sage)'
                  : '1px solid rgba(74,154,74,0.25)',
                background: active
                  ? 'rgba(74,154,74,0.18)'
                  : 'transparent',
                color: active ? 'var(--color-text)' : 'var(--color-text-dim)',
                fontSize: '0.8rem',
                fontWeight: active ? 600 : 400,
                cursor: 'pointer',
                lineHeight: 1.2,
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '0.9rem' }}>{opt.native}</div>
              <div style={{ fontSize: '0.62rem', opacity: 0.65 }}>{opt.country}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

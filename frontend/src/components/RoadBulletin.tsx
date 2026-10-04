import { useEffect, useState } from 'react';
import type { Region, RoadBulletinResponse, RoadStatusItem } from '../lib/api';
import { getRoadBulletin } from '../lib/api';
import { getCachedBulletin, saveRoadBulletin } from '../lib/offlineStorage';

interface Props {
  region: Region;
}

const SEVERITY_BADGE: Record<string, string> = {
  none:     'badge-stable',
  minor:    'badge-stable',
  major:    'badge-marginal',
  critical: 'badge-critical',
};

const STATUS_LABEL: Record<string, string> = {
  open:       'OPEN',
  closed:     'CLOSED',
  restricted: 'LIMITED',
};

const STATUS_COLOR: Record<string, string> = {
  open:       'var(--color-stable)',
  closed:     'var(--color-critical)',
  restricted: 'var(--color-marginal)',
};

function RoadCard({ road }: { road: RoadStatusItem }) {
  const color = STATUS_COLOR[road.status] ?? 'var(--color-text-dim)';
  return (
    <div className="card" style={{ borderLeft: `3px solid ${color}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{road.source_name}</span>
        <span style={{ color, fontSize: '0.82rem', fontWeight: 700 }}>{STATUS_LABEL[road.status]}</span>
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--color-text-dim)' }}>{road.country}</span>
        {road.severity !== 'none' && (
          <span className={`badge ${SEVERITY_BADGE[road.severity]}`}>{road.severity}</span>
        )}
      </div>
      {road.reason && (
        <div style={{ fontSize: '0.78rem', color: 'var(--color-text-dim)', marginTop: 4 }}>
          {road.reason}
        </div>
      )}
      <div style={{ fontSize: '0.72rem', color: 'var(--color-text-dim)', marginTop: 4, opacity: 0.6 }}>
        Updated: {new Date(road.last_updated).toLocaleString()}
      </div>
    </div>
  );
}

export default function RoadBulletin({ region }: Props) {
  const [data, setData]       = useState<RoadBulletinResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  async function fetchBulletin() {
    setLoading(true);
    setError(null);
    try {
      const res = await getRoadBulletin(region);
      await saveRoadBulletin(res).catch(() => {});
      setData(res);
    } catch {
      // Fall back to IndexedDB cache
      const cached = await getCachedBulletin(region);
      if (cached) {
        setData(cached);
      } else {
        setError('Road bulletin unavailable — no cached data for this region.');
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchBulletin(); }, [region]);

  const sourceClass =
    data?.data_source === 'live'    ? 'badge-online'  :
    data?.data_source === 'cache'   ? 'badge-cache'   :
    data?.data_source === 'fixture' ? 'badge-cache'   :
                                      'badge-offline';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 700, fontSize: '1rem' }}>Road Bulletin</span>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {data && (
            <span className={`badge ${sourceClass}`}>
              {data.data_source.toUpperCase()}
            </span>
          )}
          <button
            onClick={fetchBulletin}
            disabled={loading}
            style={{
              background: 'none', border: 'none',
              color: 'var(--color-sage)', cursor: 'pointer',
              fontSize: '1.1rem', padding: '2px 6px', lineHeight: 1,
            }}
            aria-label="Refresh road bulletin"
          >
            {loading ? '…' : '\u21BB'}
          </button>
        </div>
      </div>

      {/* Farmer advisory banner */}
      {data?.advisory && (
        <div style={{
          background: 'rgba(74,154,74,0.1)',
          border: '1px solid rgba(74,154,74,0.25)',
          borderRadius: 10,
          padding: '10px 14px',
          fontSize: '0.85rem',
          lineHeight: 1.45,
        }}>
          {data.advisory}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !data && (
        <div style={{ textAlign: 'center', color: 'var(--color-text-dim)', padding: '32px 0' }}>
          Fetching road status…
        </div>
      )}

      {/* Error state */}
      {error && !data && (
        <div style={{
          color: 'var(--color-critical)', fontSize: '0.85rem',
          background: 'rgba(239,68,68,0.08)', borderRadius: 8, padding: '10px 14px',
        }}>
          {error}
        </div>
      )}

      {/* Road cards */}
      {data && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {data.roads.map((road, i) => <RoadCard key={i} road={road} />)}
        </div>
      )}

      {/* Fetch timestamp */}
      {data && (
        <div style={{ fontSize: '0.72rem', color: 'var(--color-text-dim)', textAlign: 'center', opacity: 0.6 }}>
          Fetched: {new Date(data.fetched_at).toLocaleString()}
        </div>
      )}
    </div>
  );
}

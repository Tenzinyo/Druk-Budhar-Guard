/**
 * BioTerrace Sentinel — TypeScript API Client
 * =============================================
 *
 * All types mirror the backend Pydantic models exactly.
 * Update this file if backend schemas change.
 *
 * Environment variable:
 *   VITE_API_URL  — base URL of the FastAPI backend
 *                   Default: http://localhost:8000
 *                   Production: set to your deployed API URL
 */

// ── Shared types ──────────────────────────────────────────────────────────────

export type Region = 'himalaya' | 'andes' | 'east_africa';
export type RiskLevel = 'STABLE' | 'MARGINAL' | 'CRITICAL';
export type RoadStatus = 'open' | 'closed' | 'restricted';
export type RoadSeverity = 'none' | 'minor' | 'major' | 'critical';
export type DataSource = 'live' | 'cache' | 'fixture';
export type VoiceSource = 'cache' | 'elevenlabs' | 'template' | 'text_only';

// ── Slope audit types ─────────────────────────────────────────────────────────

/** POST /audit/ — request body */
export interface SlopeInput {
  /** Slope angle in degrees. Range: 1–89. */
  theta: number;
  /** Depth to failure plane in metres. Must be > 0. */
  z: number;
  /** Internal friction angle in degrees. Range: 0–45. */
  phi: number;
  /** Height of groundwater above failure plane (m). 0 = dry. Must be ≤ z. */
  h_w?: number;
  /** Effective soil cohesion (kPa). Default 0. */
  c_prime?: number;
  /** Bulk unit weight of soil (kN/m³). Default 18. */
  gamma?: number;
  /** Unit weight of water (kN/m³). Default 9.81. */
  gamma_w?: number;
  /** Region key — selects species palette. Default 'himalaya'. */
  region?: Region;
}

export interface Prescription {
  method: string;
  species: string[];
  /** Low-literacy physical unit string, e.g. "two paces between rows / ~1.5 m" */
  spacing_physical: string;
  /** Low-literacy depth string, e.g. "one forearm deep / ~40 cm" */
  depth_physical: string;
  priority: number;
  notes?: string;
}

/** POST /audit/ — response body */
export interface AuditReport {
  fos_baseline: number;
  fos_post_intervention: number;
  fos_improvement: number;
  risk_level: RiskLevel;
  risk_level_post: RiskLevel;
  slope_band: string;
  prescriptions: Prescription[];
  /** Ollama-generated vernacular advisory (Hindi / Nepali / Spanish / Amharic). Null if offline. */
  vernacular_script?: string;
  region: Region;
  warning_flags: string[];
}

// ── Road bulletin types ───────────────────────────────────────────────────────

export interface RoadStatusItem {
  source_name: string;
  country: string;
  status: RoadStatus;
  reason?: string;
  severity: RoadSeverity;
  last_updated: string;
}

/** GET /road-bulletin/ — response body */
export interface RoadBulletinResponse {
  region: Region;
  roads: RoadStatusItem[];
  data_source: DataSource;
  fetched_at: string;
  /** Single-line farmer advisory string. */
  advisory?: string;
}

// ── Voice types ───────────────────────────────────────────────────────────────

/** POST /voice/synthesize — response body */
export interface VoiceSynthesisResponse {
  script: string;
  cache_key: string;
  audio_available: boolean;
  source: VoiceSource;
  /** Relative URL to GET /voice/audio/{key}. Null if audio unavailable. */
  audio_endpoint?: string;
}

// ── API client ────────────────────────────────────────────────────────────────

const BASE_URL: string =
  (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ??
  'http://localhost:8000';

/** POST /audit/ — run a full slope stability audit */
export async function runAudit(input: SlopeInput): Promise<AuditReport> {
  const resp = await fetch(`${BASE_URL}/audit/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    const detail = body?.detail;
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join('; ')
        : `Audit request failed (HTTP ${resp.status})`;
    throw new Error(message);
  }
  return resp.json() as Promise<AuditReport>;
}

/** GET /road-bulletin/ — fetch road pass status with optional country filter */
export async function getRoadBulletin(
  region: Region = 'himalaya',
  country?: string,
): Promise<RoadBulletinResponse> {
  const params = new URLSearchParams({ region });
  if (country) params.set('country', country);
  const resp = await fetch(`${BASE_URL}/road-bulletin/?${params.toString()}`);
  if (!resp.ok) throw new Error(`Road bulletin request failed (HTTP ${resp.status})`);
  return resp.json() as Promise<RoadBulletinResponse>;
}

/** POST /voice/synthesize — synthesize a vernacular advisory audio note */
export async function synthesizeVoice(
  script: string,
  region: Region = 'himalaya',
  risk_level: string = 'MARGINAL',
): Promise<VoiceSynthesisResponse> {
  const resp = await fetch(`${BASE_URL}/voice/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ script, region, risk_level }),
  });
  if (!resp.ok) throw new Error(`Voice synthesis failed (HTTP ${resp.status})`);
  return resp.json() as Promise<VoiceSynthesisResponse>;
}

/** Resolve a relative audio_endpoint to a full URL. */
export function resolveAudioUrl(endpoint: string): string {
  return `${BASE_URL}${endpoint}`;
}

/** GET /health — liveness probe for connectivity detection */
export async function checkHealth(): Promise<boolean> {
  try {
    const resp = await fetch(`${BASE_URL}/health`, { signal: AbortSignal.timeout(3000) });
    return resp.ok;
  } catch {
    return false;
  }
}

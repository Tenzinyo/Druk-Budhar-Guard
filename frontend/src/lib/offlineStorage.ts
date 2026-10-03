/**
 * Offline Storage — IndexedDB wrapper for edge caching
 * =====================================================
 *
 * Caches the last successful AuditReport and RoadBulletinResponse in
 * IndexedDB so the app remains usable when the backend is unreachable.
 *
 * Storage schema (IndexedDB database: "bioterrace-sentinel" v1):
 *   Store "audits"       — keyed by ISO timestamp; stores AuditReport
 *   Store "road-bulletin"— keyed by region; stores RoadBulletinResponse
 *
 * This is a client-side cache on top of the backend's SQLite edge cache.
 * Together they form a two-layer offline guarantee:
 *   Layer 1 (this file) : browser IndexedDB — survives page reload
 *   Layer 2 (backend)   : SQLite + JSON fixtures — survives network loss
 */

import type { AuditReport, Region, RoadBulletinResponse } from './api';

const DB_NAME = 'bioterrace-sentinel';
const DB_VERSION = 1;

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('audits')) {
        const store = db.createObjectStore('audits', { keyPath: 'id', autoIncrement: true });
        store.createIndex('by_timestamp', 'saved_at', { unique: false });
      }
      if (!db.objectStoreNames.contains('road-bulletin')) {
        db.createObjectStore('road-bulletin', { keyPath: 'region' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// ── Audit cache ───────────────────────────────────────────────────────────────

export interface CachedAudit {
  id?: number;
  saved_at: string;
  report: AuditReport;
}

export async function saveAudit(report: AuditReport): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('audits', 'readwrite');
    tx.objectStore('audits').add({
      saved_at: new Date().toISOString(),
      report,
    });
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

/** Return the most recent N cached audit reports (latest first). */
export async function getRecentAudits(limit = 5): Promise<CachedAudit[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('audits', 'readonly');
    const req = tx.objectStore('audits').index('by_timestamp').getAll();
    req.onsuccess = () => {
      const all: CachedAudit[] = req.result ?? [];
      resolve(all.reverse().slice(0, limit));
    };
    req.onerror = () => reject(req.error);
  });
}

// ── Road bulletin cache ───────────────────────────────────────────────────────

export async function saveRoadBulletin(bulletin: RoadBulletinResponse): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('road-bulletin', 'readwrite');
    tx.objectStore('road-bulletin').put(bulletin);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getCachedBulletin(
  region: Region,
): Promise<RoadBulletinResponse | null> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('road-bulletin', 'readonly');
    const req = tx.objectStore('road-bulletin').get(region);
    req.onsuccess = () => resolve(req.result ?? null);
    req.onerror = () => reject(req.error);
  });
}

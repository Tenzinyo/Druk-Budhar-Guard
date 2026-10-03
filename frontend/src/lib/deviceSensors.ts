/**
 * Device Sensors — Capacitor plugin wrappers
 * ===========================================
 *
 * Provides:
 *  - Accelerometer-based slope angle (degrees) via @capacitor/motion
 *  - Network online/offline status via @capacitor/network
 *  - Haptic feedback via @capacitor/haptics
 *
 * Degrades gracefully to manual input when running in a desktop browser
 * where device motion APIs are unavailable.
 */

import { Motion, type AccelListenerEvent } from '@capacitor/motion';
import { Network } from '@capacitor/network';
import { Haptics, ImpactStyle } from '@capacitor/haptics';

// ── Slope angle from accelerometer ────────────────────────────────────────────

/**
 * Derive slope angle (degrees) from a raw accelerometer reading.
 *
 * The phone is held flat against the slope face, screen outward.
 * The y-axis component (pointing toward the top of the phone) captures
 * the slope angle relative to horizontal.
 *
 * θ = arcsin(clamp(|ay| / g, −1, 1))   where g ≈ 9.81 m/s²
 */
function accelToSlopeAngle(event: AccelListenerEvent): number {
  const { y } = event.acceleration;
  const ratio = Math.min(1, Math.max(-1, Math.abs(y) / 9.81));
  return Math.round(Math.asin(ratio) * (180 / Math.PI));
}

type SlopeAngleCallback = (angleDeg: number) => void;
type RemoveListenerFn = () => void;

/**
 * Start listening to the device accelerometer and call `cb` with the
 * derived slope angle on each reading (typically ~60 Hz).
 *
 * Returns a cleanup function that removes the listener.
 * Returns null if Motion is unavailable in this environment.
 */
export async function startSlopeAngleListener(
  cb: SlopeAngleCallback,
): Promise<RemoveListenerFn | null> {
  try {
    const handle = await Motion.addListener('accel', (event) => {
      cb(accelToSlopeAngle(event));
    });
    return () => handle.remove();
  } catch {
    // Desktop browser or permission denied — caller falls back to manual slider
    return null;
  }
}

// ── Network status ─────────────────────────────────────────────────────────────

export interface NetworkStatus {
  connected: boolean;
  connectionType: string;
}

/** Get the current network status once. */
export async function getNetworkStatus(): Promise<NetworkStatus> {
  try {
    const status = await Network.getStatus();
    return { connected: status.connected, connectionType: status.connectionType };
  } catch {
    // Fallback to navigator.onLine for PWA in desktop browser
    return { connected: navigator.onLine, connectionType: 'unknown' };
  }
}

/** Subscribe to network status changes. Returns a cleanup function. */
export async function addNetworkListener(
  cb: (status: NetworkStatus) => void,
): Promise<RemoveListenerFn> {
  try {
    const handle = await Network.addListener('networkStatusChange', (status) => {
      cb({ connected: status.connected, connectionType: status.connectionType });
    });
    return () => handle.remove();
  } catch {
    // Browser fallback
    const onOnline  = () => cb({ connected: true,  connectionType: 'unknown' });
    const onOffline = () => cb({ connected: false, connectionType: 'none' });
    window.addEventListener('online',  onOnline);
    window.addEventListener('offline', onOffline);
    return () => {
      window.removeEventListener('online',  onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }
}

// ── Haptic feedback ────────────────────────────────────────────────────────────

/** Light tap — used for UI interactions. */
export async function hapticLight(): Promise<void> {
  try { await Haptics.impact({ style: ImpactStyle.Light }); } catch { /* noop */ }
}

/** Heavy thud — used for CRITICAL risk alerts. */
export async function hapticHeavy(): Promise<void> {
  try { await Haptics.impact({ style: ImpactStyle.Heavy }); } catch { /* noop */ }
}

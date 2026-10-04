/**
 * Camera capture — Capacitor wrapper with browser fallback
 * =========================================================
 *
 * On a real device (Android / iOS):  uses @capacitor/camera native plugin.
 * In a desktop / PWA browser:        falls back to <input type=file capture>.
 *
 * Returns a data-URL (base64 JPEG) or null if the user cancelled.
 */

import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';

/** Take a photo and return it as a base64 data-URL (image/jpeg). */
export async function takePhoto(): Promise<string | null> {
  try {
    const photo = await Camera.getPhoto({
      resultType: CameraResultType.DataUrl,
      source: CameraSource.Camera,
      quality: 80,
      width: 1280,
    });
    return photo.dataUrl ?? null;
  } catch {
    // User cancelled or plugin unavailable — fall back to file input
    return browserFilePicker();
  }
}

/** Choose from the photo library instead of the camera. */
export async function pickPhoto(): Promise<string | null> {
  try {
    const photo = await Camera.getPhoto({
      resultType: CameraResultType.DataUrl,
      source: CameraSource.Photos,
      quality: 80,
      width: 1280,
    });
    return photo.dataUrl ?? null;
  } catch {
    return browserFilePicker();
  }
}

// ── Browser fallback ───────────────────────────────────────────────────────────

function browserFilePicker(): Promise<string | null> {
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment'; // rear camera on mobile browsers
    input.onchange = () => {
      const file = input.files?.[0];
      if (!file) { resolve(null); return; }
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => resolve(null);
      reader.readAsDataURL(file);
    };
    input.oncancel = () => resolve(null);
    input.click();
  });
}

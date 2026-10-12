/* Browser implementation of Platform. The ONLY file in packages/core allowed
 * to touch window/document/localStorage/navigator/XMLHttpRequest (the ESLint
 * portability override and src/portability.test.ts both exempt it). Apps
 * import it explicitly: `import { createWebPlatform } from "@gazyar/core/platform.web"`. */

import {
  buildFormData,
  createDeviceIdGetter,
  memoryStorage,
  uuidV4,
  type HapticKind,
  type KeyValueStore,
  type Platform,
  type UploadRequest,
  type UploadResponse,
} from "./platform";

/**
 * localStorage behind the async interface. Every call is guarded: Safari in
 * private mode and browsers with site data blocked throw on access, and a
 * throwing storage must degrade to "not remembered", never to a crashed app.
 */
function webStorage(): KeyValueStore {
  const fallback = memoryStorage();
  const ls = (): Storage | null => {
    try {
      return window.localStorage;
    } catch {
      return null;
    }
  };
  return {
    async get(k) {
      try {
        const s = ls();
        if (s) return s.getItem(k);
      } catch {
        /* fall through */
      }
      return fallback.get(k);
    },
    async set(k, v) {
      try {
        const s = ls();
        if (s) {
          s.setItem(k, v);
          return;
        }
      } catch {
        /* quota exceeded / blocked */
      }
      await fallback.set(k, v);
    },
    async remove(k) {
      try {
        ls()?.removeItem(k);
      } catch {
        /* ignore */
      }
      await fallback.remove(k);
    },
  };
}

const VIBRATION: Record<HapticKind, number | number[]> = {
  selection: 5,
  light: 10,
  medium: 18,
  heavy: 28,
  success: [10, 40, 14],
  warning: [18, 60, 18],
  error: [26, 50, 26, 50, 26],
};

function haptic(kind: HapticKind): void {
  // iOS Safari has no vibrate(); Android Chrome ignores it until the first
  // user gesture. Either way it is a hint, so failures are swallowed.
  try {
    if (typeof navigator !== "undefined" && typeof navigator.vibrate === "function") navigator.vibrate(VIBRATION[kind]);
  } catch {
    /* unsupported */
  }
}

const abortError = () => new DOMException("The upload was aborted.", "AbortError");

/** XHR, not fetch: fetch still has no upload progress events, and the meter
 *  photo / case photo screens show a progress ring. */
function xhrUpload(req: UploadRequest): Promise<UploadResponse> {
  return new Promise<UploadResponse>((resolve, reject) => {
    if (req.signal.aborted) {
      reject(abortError());
      return;
    }
    const xhr = new XMLHttpRequest();
    const onAbort = () => xhr.abort();
    const cleanup = () => req.signal.removeEventListener("abort", onAbort);
    req.signal.addEventListener("abort", onAbort, { once: true });

    xhr.open(req.method, req.url);
    xhr.withCredentials = req.withCredentials;
    for (const [k, v] of Object.entries(req.headers)) xhr.setRequestHeader(k, v);
    xhr.upload.onprogress = (e) => {
      const total = e.lengthComputable ? e.total : 0;
      req.onProgress?.({ loaded: e.loaded, total, fraction: total > 0 ? Math.min(1, e.loaded / total) : null });
    };
    xhr.onload = () => {
      cleanup();
      resolve({ status: xhr.status, body: xhr.responseText });
    };
    xhr.onerror = () => {
      cleanup();
      reject(new TypeError("Network request failed"));
    };
    xhr.onabort = () => {
      cleanup();
      reject(abortError());
    };
    xhr.send(buildFormData(req.file, req.fileField, req.fields));
  });
}

export interface WebPlatformOptions {
  /** Override persistent storage (tests). Defaults to guarded localStorage. */
  storage?: KeyValueStore;
}

export function createWebPlatform(options: WebPlatformOptions = {}): Platform {
  const storage = options.storage ?? webStorage();
  return {
    fetch: window.fetch.bind(window),
    storage,
    // Web keeps no secrets at rest: the refresh token is an httpOnly cookie,
    // and anything in localStorage is readable by any injected script.
    secureStorage: memoryStorage(),
    randomId: uuidV4,
    deviceId: createDeviceIdGetter(storage, uuidV4),
    upload: xhrUpload,
    haptic,
  };
}

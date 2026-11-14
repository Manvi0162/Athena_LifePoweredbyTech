import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { ReceiptItem, UtilityKind } from './types';

export const DEMO_MODE = process.env.EXPO_PUBLIC_USE_MOCKS !== 'false';
const URL = (process.env.EXPO_PUBLIC_API_URL || '').replace(/\/$/, '');
const SESSION_KEY = '@livebetter-session';

// ---- session (login token from POST /auth/login) ----
// Demo-grade storage: AsyncStorage is not encrypted. Use expo-secure-store before a real release.
type Session = { token: string | null; refresh_token?: string | null; email?: string | null; mode?: string };
let session: Session = { token: null };
export const getSession = () => session;
export async function loadSession() {
  try { const raw = await AsyncStorage.getItem(SESSION_KEY); if (raw) session = JSON.parse(raw); } catch {}
  return session;
}
export async function saveSession(s: Session) { session = s; await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(s)); }
export async function clearSession() { session = { token: null }; await AsyncStorage.removeItem(SESSION_KEY); }

export class ApiError extends Error {
  status: number; code?: string; details?: any;
  constructor(message: string, status: number, code?: string, details?: any) {
    super(message); this.status = status; this.code = code; this.details = details;
  }
}

// Messages people can act on (14 Nov). The server already words most errors; this covers the rest, so nobody sees
// "HTTP 500", a JSON dump or a Pydantic list.
const BY_STATUS: Record<number, string> = {
  400: 'Something in the form is not right. Please check it and try again.',
  401: 'Please log in again to continue.',
  403: 'You do not have access to this.',
  404: 'We could not find that. It may have been deleted already.',
  413: 'The photo is too large. Please choose a smaller one.',
  429: 'Too many tries. Please wait a minute and try again.',
  500: 'Something went wrong on our side. Your data is safe: please try again in a moment.',
  502: 'The server is restarting. Please try again in a few seconds.',
  503: 'This service is busy right now. Please try again in a moment.',
  504: 'The server took too long to answer. Please try again.',
};
const TECHNICAL = /traceback|exception|pydantic|sqlstate|postgrest|keyerror|typeerror|nonetype|\bjson\b|http \d{3}|internal server error|\{".*":/i;
export function friendlyMessage(status: number, message?: string): string {
  const m = (message || '').trim();
  if (m && !TECHNICAL.test(m) && m.length < 400) return m;
  return BY_STATUS[status] || (status >= 500 ? BY_STATUS[500] : 'Something did not work. Please try again.');
}
function errorMessage(result: any, status: number, path: string) {
  const d = result?.detail;
  if (d && typeof d === 'object' && !Array.isArray(d)) return { message: friendlyMessage(status, d.message), code: d.code, details: d.details };
  if (Array.isArray(d)) return { message: friendlyMessage(422, d.map((x: any) => String(x.msg || '').replace('Value error, ', '')).join(' ')), code: 'validation_error' };
  return { message: friendlyMessage(status, result?.message || (typeof d === 'string' ? d : '')), code: result?.code };
}

// Supabase access tokens expire after about an hour. On a 401 the app uses the refresh token once, saves the new
// session and repeats the request, so the user is not suddenly "logged out" in the middle of the demo.
let refreshing: Promise<boolean> | null = null;
async function refreshSession(): Promise<boolean> {
  if (!session.refresh_token) return false;
  if (!refreshing) refreshing = (async () => {
    try {
      const r = await fetch(`${URL}/auth/refresh`, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ refresh_token: session.refresh_token }) });
      if (!r.ok) return false;
      const j: any = await r.json();
      if (!j?.token) return false;
      await saveSession({ ...session, token: j.token, refresh_token: j.refresh_token || session.refresh_token });
      return true;
    } catch { return false; } finally { setTimeout(() => { refreshing = null; }, 0); }
  })();
  return refreshing;
}

// Render's free plan sleeps: the first request after a while can take ~50 s, so the timeout is generous.
const TIMEOUT = 60000;

// stepUp = one-time permission from drawing the security pattern (misuse safeguard), sent as X-Step-Up.
export async function request<T>(path: string, method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE' = 'GET', body?: unknown,
  stepUp?: string, retried = false): Promise<T> {
  if (!URL) throw Error('Backend URL missing. Set EXPO_PUBLIC_API_URL in .env.local.');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT);
  let response: Response;
  try {
    const headers: Record<string, string> = { Accept: 'application/json', 'Content-Type': 'application/json' };
    if (session.token) headers.Authorization = `Bearer ${session.token}`;
    if (stepUp) headers['X-Step-Up'] = stepUp;
    response = await fetch(`${URL}${path}`, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal });
  } catch (e) {
    throw Error((e as any)?.name === 'AbortError' ? 'The server is waking up or slow right now. Please try again in a few seconds.'
      : 'We cannot reach LiveBetter right now. Check your internet connection and try again.');
  } finally { clearTimeout(timer); }
  let result: unknown = null;
  try { result = await response.json(); } catch {}
  if (response.status === 401 && !retried && !path.startsWith('/auth/') && await refreshSession())
    return request<T>(path, method, body, stepUp, true);
  if (!response.ok) {
    const e = errorMessage(result, response.status, path);
    throw new ApiError(e.message, response.status, e.code, e.details);
  }
  return result as T;
}

// Photo upload. Android/iOS: XMLHttpRequest with {uri, name, type} (React Native's own networking). Expo's newer fetch
// rejects that object with "Unsupported FormDataPart implementation", which is why receipts, bills and food scans
// failed on the phone. Web: the picker gives a blob URL, sent as a real Blob.
function xhrUpload(url: string, data: FormData, headers: Record<string, string>): Promise<{ status: number; body: any }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    for (const [k, v] of Object.entries(headers)) xhr.setRequestHeader(k, v);
    xhr.timeout = TIMEOUT;
    xhr.onload = () => { let body: any = null; try { body = JSON.parse(xhr.responseText); } catch {} resolve({ status: xhr.status, body }); };
    xhr.onerror = () => reject(Error('We cannot reach LiveBetter right now. Check your internet connection and try again.'));
    xhr.ontimeout = () => reject(Error('The server is waking up or slow right now. Please try again in a few seconds.'));
    xhr.send(data as any);
  });
}

export async function uploadImage<T>(path: string, imageUri: string, fields?: Record<string, string>, retried = false): Promise<T> {
  if (!URL) throw Error('Backend URL missing.');
  const data = new FormData();
  for (const [k, v] of Object.entries(fields || {})) data.append(k, v);
  const lower = imageUri.toLowerCase();
  const type = lower.endsWith('.png') ? 'image/png' : lower.endsWith('.webp') ? 'image/webp' : 'image/jpeg';
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (session.token) headers.Authorization = `Bearer ${session.token}`;
  let res: { status: number; body: any };
  if (Platform.OS === 'web') {
    const blob = await (await fetch(imageUri)).blob();
    data.append('image', blob, blob.type === 'image/png' ? 'photo.png' : 'photo.jpg');
    const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), TIMEOUT);
    try {
      const r = await fetch(`${URL}${path}`, { method: 'POST', body: data, signal: controller.signal, headers });
      res = { status: r.status, body: await r.json().catch(() => null) };
    } finally { clearTimeout(timer); }
  } else {
    data.append('image', { uri: imageUri, name: type === 'image/png' ? 'photo.png' : 'photo.jpg', type } as any);
    res = await xhrUpload(`${URL}${path}`, data, headers);
  }
  if (res.status === 401 && !retried && await refreshSession()) return uploadImage<T>(path, imageUri, fields, true);
  if (res.status < 200 || res.status >= 300) { const e = errorMessage(res.body, res.status, path); throw new ApiError(e.message, res.status, e.code, e.details); }
  return res.body as T;
}

// Contract implemented by backend/integration/gateway.py and the module routers.
export const routes = {
  login: '/auth/login', signup: '/auth/signup', me: '/households/me',
  onboarding: '/households/onboarding', bills: '/bills', forecasts: '/utilities/forecast',
  parse: '/receipts/parse', confirm: '/receipts/confirm', pantry: '/pantry',
  recipes: '/recipes/ranked', insights: '/household/insights', scenario: '/household/scenarios',
  coach: '/household/coach', activity: '/activity', sample: '/demo/sample', reset: '/account/reset',
  mfa: '/auth/mfa', authMe: '/auth/me',
  security: '/security/status', pattern: '/security/pattern', verifyPattern: '/security/pattern/verify',
  authSetup: '/security/authenticator/setup', authConfirm: '/security/authenticator/confirm',
  authDisable: '/security/authenticator/disable', restore: '/account/restore', resetStatus: '/account/reset-status',
  parseBill: '/bills/parse', explain: '/utilities/explain', habits: '/habits', recognize: '/food/recognize',
  describe: '/food/describe', searchRecipes: '/recipes/search', generateRecipe: '/recipes/generate', drafts: '/recipes/drafts',
};
export type ParsedReceipt = {
  items: ReceiptItem[]; receipt_id?: string; status?: string; retailer?: string | null;
  receipt_date?: string | null; total?: number; excluded_non_food?: string[];
};
export function categoryParams(kind: UtilityKind) { return `?category=${kind}`; }
export function newOperationId() {
  // RFC 4122 v4 format; one per "I cooked this" tap so a retry never deducts twice.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0; return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}
// Never put service-role keys, AI credentials or private API tokens in EXPO_PUBLIC_ variables.

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

function errorMessage(result: any, status: number, path: string) {
  const d = result?.detail;
  if (d && typeof d === 'object' && !Array.isArray(d)) return { message: d.message || JSON.stringify(d), code: d.code, details: d.details };
  if (Array.isArray(d)) return { message: d.map((x: any) => x.msg).join('; '), code: 'validation_error' };
  return { message: result?.message || (typeof d === 'string' ? d : `HTTP ${status}: ${path}`), code: result?.code };
}

// stepUp = one-time permission from drawing the security pattern (misuse safeguard), sent as X-Step-Up.
export async function request<T>(path: string, method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE' = 'GET', body?: unknown,
  stepUp?: string): Promise<T> {
  if (!URL) throw Error('Backend URL missing. Set EXPO_PUBLIC_API_URL in .env.local.');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const headers: Record<string, string> = { Accept: 'application/json', 'Content-Type': 'application/json' };
    if (session.token) headers.Authorization = `Bearer ${session.token}`;
    if (stepUp) headers['X-Step-Up'] = stepUp;
    const response = await fetch(`${URL}${path}`, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal });
    let result: unknown = null;
    try { result = await response.json(); } catch {}
    if (!response.ok) {
      const e = errorMessage(result, response.status, path);
      throw new ApiError(e.message, response.status, e.code, e.details);
    }
    return result as T;
  } finally { clearTimeout(timer); }
}

export async function uploadImage<T>(path: string, imageUri: string, fields?: Record<string, string>): Promise<T> {
  if (!URL) throw Error('Backend URL missing.');
  const data = new FormData();
  for (const [k, v] of Object.entries(fields || {})) data.append(k, v);
  // The food backend reads the photo from the `image` field.
  if (Platform.OS === 'web') {
    // In a browser the picker gives a blob:/data: URL; the {uri,name,type} object only works on iOS/Android
    // (on web it was sent as the text "[object Object]" -> "Expected UploadFile, received str").
    const blob = await (await fetch(imageUri)).blob();
    data.append('image', blob, blob.type === 'image/png' ? 'receipt.png' : 'receipt.jpg');
  } else {
    data.append('image', { uri: imageUri, name: 'receipt.jpg', type: 'image/jpeg' } as any);
  }
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 45000);
  try {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (session.token) headers.Authorization = `Bearer ${session.token}`;
    const response = await fetch(`${URL}${path}`, { method: 'POST', body: data, signal: controller.signal, headers });
    const result = await response.json().catch(() => null);
    if (!response.ok) { const e = errorMessage(result, response.status, path); throw new ApiError(e.message, response.status, e.code); }
    return result as T;
  } finally { clearTimeout(timer); }
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

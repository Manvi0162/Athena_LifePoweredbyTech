export type UtilityKind = 'water' | 'electricity';
export type Confidence = 'limited_history' | 'historical_baseline' | 'measured' | 'unavailable';
export type Household = {
  id: string; name: string; members: number; home_type: string;
  water_tariff: string; electricity_tariff: string;
  monthly_target: number; diet: string; allergies: string;
  water_habit: string; appliance_notes: string;
  occupancy?: string | null; main_goal?: string | null; region?: string | null;
};
export type Bill = { id: string; household_id: string; kind: UtilityKind; period_start: string; period_end: string;
  units: number; amount: number; tariff: string; currency: 'MUR'; amount_source?: 'bill' | 'tariff_calculation' };
export type ForecastLine = { label: string; m3?: number; kind: string; source: string };
export type Forecast = { category: UtilityKind; period_start: string | null; period_end: string | null; units: number;
  unit: string; value: number | null; currency: 'MUR'; method: string;
  confidence: Confidence; assumptions: string[]; source_data: string[];
  // Live backend extras (water + electricity engines)
  status?: string; status_message?: string | null; prompts?: string[];
  range?: { low: number; high: number }; cost_range?: { low: number; high: number };
  lines?: ForecastLine[]; bill_breakdown?: { label: string; rs: number; how: string }[] };
export type PantryItem = { id: string; name: string; quantity: number; unit: string; expiry?: string; available: boolean };
export type ReceiptItem = { name: string; quantity: number; unit: string; price: number; original_name?: string; category?: string };
export type Recipe = { id: string; name: string; ingredients: { name: string; quantity: number; unit: string }[];
  missing: string[]; coverage: number; instructions: string; source: string; cook_now?: boolean;
  steps?: string[]; ai_generated?: boolean; verification_status?: string | null };
export type ActivityCategory = 'ai' | 'water' | 'electricity' | 'groceries' | 'security' | 'household';
export type Activity = { id: string; at: string; message: string; kind: string; category?: ActivityCategory;
  event_type?: string; details?: Record<string, unknown> };
export type BigBrainAction = { source: string; module: string; action_id: string; title: string; rank?: number;
  priority_score: number | null; estimated_savings_mur: number | null; confidence?: string; kind?: string;
  evidence: Record<string, unknown>; assumptions?: Record<string, unknown>; explanation?: string | null;
  explanation_source?: string; status?: string | null };
export type Insight = { period_start: string | null; period_end: string | null; currency: 'MUR';
  water: number | null; electricity: number | null; groceries_recorded: number;
  total: number | null; assumptions: string[]; recommendations: string[]; method: string;
  source_data: string[];
  // Big Brain dashboard (live backend)
  actions?: BigBrainAction[]; module_status?: Record<string, string>; outlook?: any;
  // Big Brain v3 (Manvi): plan summary + savings compared per 30 days
  big_brain_summary?: string; savings_30d?: { rank: number; module: string; action_id: string; title: string;
    normalized_savings_30d_mur: number; estimated_savings_mur: number; savings_period: string; ai_explanation?: string }[] };
export type Scenario = { baseline: number | null; adjusted: number | null; delta: number | null;
  unit_change: number | null; message: string; assumptions: string[]; status?: string; unit?: string };
export type CoachReply = { answer: string; intent: string; source: string; suggestions?: string[];
  actions?: { module: string; action_id: string; title: string; estimated_savings_mur: number | null }[] };
export type Snapshot = { household: Household | null; bills: Bill[]; pantry: PantryItem[];
  receipts: { id: string; at: string; total: number }[];
  activity: Activity[]; completed_actions: string[] };

// ---- misuse safeguards (surprise card) ----
export type SensitiveAction = 'reset_account' | 'restore_account' | 'delete_bill' | 'edit_household' | 'security_off';
export type SecurityEvent = { at: string; event: string; action?: string; [k: string]: unknown };
export type SecurityStatus = { pattern_set: boolean; pattern_set_at?: string | null; authenticator_on: boolean;
  recovery_codes_left: number; locks: Record<string, string>;
  alert: { count: number; last_at: string; message: string } | null;
  recent_events: SecurityEvent[]; protected_actions: Record<SensitiveAction, string> };
export type AuthenticatorSetup = { otpauth_uri: string; qr_png: string; manual_key: string; note: string };
export type ResetStatus = { restorable: boolean; reset_at?: string; restore_until?: string };
export type LoginResult = { household: boolean; mfa?: { token: string; message: string } };

// ---- redesign (14 Nov): bill photo, explainable AI, habits, scan-to-cook ----
export type ParsedBill = { kind: UtilityKind; period_start: string | null; period_end: string | null; units: number | null;
  amount: number | null; start_reading: number | null; end_reading: number | null; tariff: string | null;
  uncertain: string[]; message: string };
export type Explanation = { category: UtilityKind; status: string; available: boolean; confidence?: string; headline: string;
  summary: string; summary_source: string; factors: { label: string; value: string; detail: string }[];
  breakdown: { label: string; rs: number; how: string }[]; to_improve: string[]; method?: string; assumptions: string[] };
export type HabitQuestion = { id: string; question: string; multi: boolean; options: { value: string; label: string }[];
  extra?: { id: string; label: string } };
export type Habits = { kind: UtilityKind; questions: HabitQuestion[]; answers: Record<string, any>; note: string };
export type RecognisedItem = { name: string; category: 'fresh' | 'packaged' | 'unknown'; confidence: number;
  label_text: string[]; low_confidence: boolean };
export type RecipeMatch = { recipe_id: string; name: string; verification_status?: string; uses_from_photo: string[];
  already_in_pantry: string[]; still_to_buy: string[] };
export type AIRecipe = { recipe: { name: string; description?: string; servings?: number; prep_minutes?: number;
  cook_minutes?: number; ingredients: { ingredient_name: string; quantity: number | null; unit: string | null; optional?: boolean }[];
  instructions: string[] }; missing: string[]; coverage: number; cook_now: boolean; warning: string };

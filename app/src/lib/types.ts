import type { components } from '@dri/shared-types';

export type ScreeningInput = components['schemas']['ScreeningInput'];
export type ScreeningResult = components['schemas']['ScreeningResult'];
export type ClinicalRule = components['schemas']['ClinicalRule'];
export type MLResult = components['schemas']['MLResult'];
export type FollowupSchedule = components['schemas']['FollowupSchedule'];
export type EmergencyFlag = components['schemas']['EmergencyFlag'];

export interface HistoryItem {
  id: string;
  health_score: number;
  risk_category: string;
  created_at: string;
  pending?: boolean;
}

export interface HistoryResponse {
  screenings: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export type RiskCategory = 'low' | 'medium' | 'high' | 'very_high';

export interface DeviceConnection {
  id: string;
  user_id: string;
  provider: string;
  access_token_encrypted?: string | null;
  refresh_token_encrypted?: string | null;
  token_expires_at?: string | null;
  last_sync_at?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface DeviceConnectionCreate {
  provider: string;
  access_token_encrypted?: string | null;
  refresh_token_encrypted?: string | null;
  token_expires_at?: string | null;
}

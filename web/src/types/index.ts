export interface Destination {
  id: string;
  name: string;
  url: string;
  platform_key: string;
  connector_key: string;
  surface: string;
  category: string;
  audience_tags: string[];
  language: string;
  geo: string;
  est_audience: number;
  rules_url?: string;
  frequency_cap: number;
  self_promo_allowed: boolean;
  link_policy: string;
  disclosure_required: boolean;
  automation_allowed: boolean;
  relevance_score: number;
  relevance_reason: string;
  parameters: Record<string, any>;
  connection?: Record<string, any>;
  level: string; // L0, L1, L2, L3
  created_at: string;
}

export interface ConnectorSurface {
  key: string;
  content_types: string[];
  spec: {
    title_max_chars?: number;
    body_max_chars?: number;
    links_allowed: boolean;
  };
}

export interface ConnectorInfo {
  key: string;
  version: string;
  tier: string;
  auth: string;
  surfaces: ConnectorSurface[];
  rate_limits: {
    per_connection: {
      requests: number;
      per_seconds: number;
    };
  };
  capabilities: string[];
  error_map: Record<string, string>;
  instance_param?: string;
  disabled: boolean;
  health: 'healthy' | 'disabled';
}

export interface Rendition {
  title: string;
  body: string;
  canonical_url?: string;
  tags: string[];
  media: Array<{
    url: string;
    media_type: string;
    size_bytes?: number;
    alt_text?: string;
  }>;
  ai_disclosure?: string;
  custom_fields?: Record<string, any>;
}

export interface RuleDecision {
  action: 'allow' | 'block' | 'reschedule';
  rule?: string;
  reason: string;
  retry_at?: string;
  required_human_action?: string;
  warnings: string[];
}

export interface RuleAudit {
  id: string;
  destination_id: string;
  decision: 'allow' | 'block' | 'reschedule';
  rule_violated?: string;
  reason: string;
  next_allowed_at?: string;
  human_action_required?: string;
  timestamp: string;
}

export interface StepResult {
  step_name: string;
  status: 'pending' | 'running' | 'succeeded' | 'failed';
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  error_message?: string;
  details?: Record<string, any>;
}

export interface CertificationRecord {
  certification_id: string;
  destination_id: string;
  status: 'pending' | 'running' | 'succeeded' | 'failed';
  assigned_level: string;
  is_mock: boolean;
  real_certified: boolean;
  evidence_s3_url?: string;
  step_results: StepResult[];
}

export interface CertificationAlert {
  id: string;
  destination_id: string;
  timestamp: string;
  alert_type: string;
  reason: string;
  previous_level: string;
  demoted_to: string;
  failing_step?: string;
  evidence_s3_url?: string;
}

export interface JobRecord {
  job_id: string;
  idempotency_key?: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  progress: number;
  payload: Record<string, any>;
  result?: Record<string, any>;
  result_links: Record<string, any>;
  manifest?: Record<string, any>;
  callback_url?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface SecurityStatus {
  token: string;
  is_valid: boolean;
  status: 'active' | 'revoked';
  simulation_mode: boolean;
  rate_limits: {
    limit_per_minute: number;
    remaining: number;
    reset_seconds: number;
  };
  webhook_signing_secret?: string;
}

export interface SystemReadiness {
  status: 'ready' | 'not_ready';
  simulation_mode: boolean;
  checks: {
    database: string;
    queue: string;
    storage: string;
  };
}

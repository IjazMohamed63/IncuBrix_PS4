import {
  CertificationAlert,
  CertificationRecord,
  ConnectorInfo,
  Destination,
  JobRecord,
  Rendition,
  RuleAudit,
  RuleDecision,
  SecurityStatus,
  SystemReadiness,
} from '../types';

const DEFAULT_TOKEN = 'incubrix_demo_reviewer_token_2026';

class ApiClient {
  private token: string;
  private onTokenOrRateLimitChange?: (remaining: number, limit: number) => void;

  constructor() {
    this.token = localStorage.getItem('incubrix_token') || DEFAULT_TOKEN;
  }

  public getToken(): string {
    return this.token;
  }

  public setToken(token: string): void {
    this.token = token;
    localStorage.setItem('incubrix_token', token);
  }

  public setRateLimitListener(listener: (remaining: number, limit: number) => void) {
    this.onTokenOrRateLimitChange = listener;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    
    // Always include revocable demo token
    if (!headers.has('X-IncuBrix-Token')) {
      headers.set('X-IncuBrix-Token', this.token);
    }
    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }

    const response = await fetch(endpoint, {
      ...options,
      headers,
    });

    // Capture rate-limit headers
    const remaining = response.headers.get('X-RateLimit-Remaining');
    const limit = response.headers.get('X-RateLimit-Limit');
    if (remaining && limit && this.onTokenOrRateLimitChange) {
      this.onTokenOrRateLimitChange(parseInt(remaining, 10), parseInt(limit, 10));
    }

    if (!response.ok) {
      let errorDetail = `Request failed: ${response.status} ${response.statusText}`;
      try {
        const errorJson = await response.json();
        if (errorJson.error?.message) {
          errorDetail = errorJson.error.message;
        } else if (errorJson.detail) {
          errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // use fallback
      }
      throw new Error(errorDetail);
    }

    return response.json();
  }

  // --- Readiness & Health ---
  public async getReadiness(): Promise<SystemReadiness> {
    return this.request<SystemReadiness>('/ready');
  }

  // --- Destinations ---
  public async getDestinations(): Promise<Destination[]> {
    return this.request<Destination[]>('/api/v1/destinations');
  }

  public async getDestination(id: string): Promise<Destination> {
    return this.request<Destination>(`/api/v1/destinations/${id}`);
  }

  public async createDestination(payload: Partial<Destination>): Promise<Destination> {
    return this.request<Destination>('/api/v1/destinations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async importCsv(csvText: string, safeReachability: boolean = false): Promise<any> {
    return this.request<any>('/api/v1/destinations/import-csv', {
      method: 'POST',
      body: JSON.stringify({
        csv_text: csvText,
        safe_reachability: safeReachability,
      }),
    });
  }

  // --- Connectors ---
  public async getConnectors(): Promise<{ connectors: ConnectorInfo[]; count: number }> {
    return this.request<{ connectors: ConnectorInfo[]; count: number }>('/connector/v1');
  }

  public async toggleConnectorKillSwitch(connectorKey: string): Promise<{ connector_key: string; disabled: boolean; health: string; message: string }> {
    return this.request(`/connector/v1/${connectorKey}/kill-switch`, {
      method: 'POST',
    });
  }

  // --- Rules & Tailoring ---
  public async evaluateRules(destinationId: string, rendition: Rendition): Promise<RuleDecision> {
    return this.request<RuleDecision>('/api/v1/rules/evaluate', {
      method: 'POST',
      body: JSON.stringify({
        destination_id: destinationId,
        rendition,
      }),
    });
  }

  public async tailorRendition(destinationId: string, rendition: Rendition): Promise<{ destination_id: string; tailored_rendition: Rendition; modifications: string[] }> {
    return this.request('/api/v1/rules/tailor', {
      method: 'POST',
      body: JSON.stringify({
        destination_id: destinationId,
        rendition,
      }),
    });
  }

  public async getRuleAudits(destinationId?: string): Promise<RuleAudit[]> {
    const url = destinationId ? `/api/v1/rules/audits?destination_id=${destinationId}` : '/api/v1/rules/audits';
    return this.request<RuleAudit[]>(url);
  }

  public async getRulePolicies(): Promise<Array<{ id: string; name: string; description: string; enforcement: string; default: string }>> {
    return this.request('/api/v1/rules/policies');
  }

  public async proposeRules(destinationId: string, rulesText: string, rulesUrl?: string): Promise<any> {
    return this.request(`/api/v1/destinations/${destinationId}/propose-rules`, {
      method: 'POST',
      body: JSON.stringify({
        rules_text: rulesText,
        rules_url: rulesUrl,
      }),
    });
  }

  public async confirmRules(destinationId: string, proposalId: string, confirmedBy: string = 'human_operator'): Promise<any> {
    return this.request(`/api/v1/destinations/${destinationId}/confirm-rules`, {
      method: 'POST',
      body: JSON.stringify({
        proposal_id: proposalId,
        confirmed_by: confirmedBy,
      }),
    });
  }

  // --- Publishing ---
  public async publishContent(payload: {
    rendition: Rendition;
    destination_ids: string[];
    callback_url?: string;
    async_mode?: boolean;
  }, idempotencyKey: string): Promise<any> {
    return this.request('/api/v1/publish', {
      method: 'POST',
      headers: {
        'Idempotency-Key': idempotencyKey,
      },
      body: JSON.stringify(payload),
    });
  }

  // --- Jobs ---
  public async getJobs(limit: number = 50): Promise<JobRecord[]> {
    return this.request<JobRecord[]>(`/api/v1/jobs?limit=${limit}`);
  }

  public async getJob(jobId: string): Promise<JobRecord> {
    return this.request<JobRecord>(`/api/v1/jobs/${jobId}`);
  }

  // --- Certification ---
  public async runCertification(destinationId: string, isMock: boolean = true): Promise<CertificationRecord> {
    return this.request<CertificationRecord>(`/api/v1/destinations/${destinationId}/certify`, {
      method: 'POST',
      body: JSON.stringify({ is_mock: isMock }),
    });
  }

  public async getCertificationHistory(destinationId: string): Promise<CertificationRecord[]> {
    return this.request<CertificationRecord[]>(`/api/v1/destinations/${destinationId}/certification-history`);
  }

  public async getCertificationAlerts(): Promise<CertificationAlert[]> {
    return this.request<CertificationAlert[]>('/api/v1/certification/alerts');
  }

  // --- Security & Tokens ---
  public async getSecurityStatus(): Promise<SecurityStatus> {
    return this.request<SecurityStatus>('/api/v1/security/token-status');
  }

  public async revokeToken(token: string): Promise<{ token: string; status: string; message: string }> {
    return this.request('/api/v1/security/revoke-token', {
      method: 'POST',
      body: JSON.stringify({ token }),
    });
  }

  public async restoreToken(token: string): Promise<{ token: string; status: string; message: string }> {
    return this.request('/api/v1/security/restore-token', {
      method: 'POST',
      body: JSON.stringify({ token }),
    });
  }

  public async setSimulationMode(enabled: boolean): Promise<{ simulation_mode: boolean; message: string }> {
    return this.request('/api/v1/security/simulation-mode', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    });
  }
}

export const api = new ApiClient();

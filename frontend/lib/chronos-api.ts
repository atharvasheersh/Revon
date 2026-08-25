export type RepositorySummary = {
  name: string;
  head: number | null;
  head_hash: string | null;
  versions: number;
  storage_bytes: number;
  status?: string;
};

export type Commit = {
  version: number;
  commit_hash: string;
  root_hash: string;
  parent: number | null;
  parent_hash: string | null;
  message: string | null;
  timestamp_ns: number;
  timestamp_utc: string;
  changeset_hash: string;
};

export type CommitMetric = {
  version: number;
  changed_keys: number;
  new_nodes: number;
  reused_nodes: number;
  bytes_written: number;
  shared_percent: number;
};

export type OpenRepository = {
  name: string;
  status: string;
  head: number | null;
  head_hash: string | null;
  root_hash: string | null;
  versions: number;
  storage_bytes: number;
  integrity: {
    objects: number;
    nodes: number;
    changesets: number;
    commits: number;
    versions: number;
  };
};

export type History = {
  name: string;
  head: number | null;
  head_hash: string | null;
  count: number;
  commits: Commit[];
};

export type Metrics = {
  name: string;
  head: number | null;
  head_hash: string | null;
  versions: number;
  storage_bytes: number;
  commit_metrics: CommitMetric[];
  comparison?: {
    from_version: number;
    to_version: number;
    strategy_requested: string;
    strategy_selected: string;
    changed_keys: number;
    diff_ms: number;
    work_examined: number;
    work_unit: string;
  };
};

export type Difference = {
  key: string;
  change_type: "added" | "deleted" | "modified";
  old_value: unknown;
  new_value: unknown;
};

export type Comparison = {
  name: string;
  from_version: number;
  to_version: number;
  strategy_requested: string;
  changed_keys: number;
  differences: Difference[];
  diff_ms: number;
  diff_metrics: {
    strategy_selected: string;
    work_examined: number;
    work_unit: string;
    nodes_compared: number;
    matching_subtrees_skipped: number;
    leaf_entries_examined: number;
    log_operations_examined: number;
  };
};

export type Checkout = {
  name: string;
  version: number;
  commit_hash: string;
  root_hash: string;
  total_rows: number;
  returned_rows: number;
  truncated: boolean;
  state: Record<string, unknown>;
};

type RepositoryList = {
  repositories: RepositorySummary[];
  count: number;
};

export class ChronosApi {
  constructor(readonly baseUrl: string) {}

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      const message = payload?.error?.message ?? `Request failed (${response.status})`;
      throw new Error(message);
    }
    return payload as T;
  }

  health() {
    return this.request<{ status: string }>("/health");
  }

  listRepositories() {
    return this.request<RepositoryList>("/repositories");
  }

  createRepository(name: string) {
    return this.request<{ name: string; status: string }>("/repositories", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  }

  openRepository(name: string) {
    return this.request<OpenRepository>(`/repositories/${name}/open`, {
      method: "POST",
    });
  }

  history(name: string) {
    return this.request<History>(`/repositories/${name}/history`);
  }

  metrics(name: string) {
    return this.request<Metrics>(`/repositories/${name}/metrics`);
  }

  compare(name: string, from: number, to: number, strategy: string) {
    const query = new URLSearchParams({
      from: String(from),
      to: String(to),
      strategy,
    });
    return this.request<Comparison>(`/repositories/${name}/compare?${query}`);
  }

  checkout(name: string, version: number, limit = 250) {
    return this.request<Checkout>(
      `/repositories/${name}/versions/${version}?offset=0&limit=${limit}`,
    );
  }

  importJson(
    name: string,
    payload: { state?: Record<string, unknown>; rows?: unknown[]; primary_key?: string; message: string },
  ) {
    return this.request<{ head: number; rows: number }>(
      `/repositories/${name}/import`,
      { method: "POST", body: JSON.stringify(payload) },
    );
  }

  async importCsv(name: string, csv: string, primaryKey: string, message: string) {
    const query = new URLSearchParams({ primary_key: primaryKey, message });
    const response = await fetch(
      `${this.baseUrl}/repositories/${name}/import?${query}`,
      { method: "POST", headers: { "Content-Type": "text/csv" }, body: csv },
    );
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(payload?.error?.message ?? `Import failed (${response.status})`);
    }
    return payload as { head: number; rows: number };
  }

  commit(
    name: string,
    payload: {
      base_version: number;
      puts: Record<string, unknown>;
      deletes: string[];
      message: string;
    },
  ) {
    return this.request<{ head: number; commit_metrics: CommitMetric }>(
      `/repositories/${name}/commits`,
      { method: "POST", body: JSON.stringify(payload) },
    );
  }
}

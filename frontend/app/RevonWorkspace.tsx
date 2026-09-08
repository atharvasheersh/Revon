"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  Checkout,
  RevonApi,
  Comparison,
  History,
  Metrics,
  OpenRepository,
  RepositorySummary,
} from "../lib/revon-api";

type Modal = "create" | "import" | "commit" | "settings" | null;
type Connection = "connecting" | "online" | "offline";

const DEFAULT_API = "http://127.0.0.1:8000/api";
const WORKLOAD_SIZES = [10, 100, 10_000, 100_000, 1_000_000] as const;

function compactCount(value: number) {
  if (value === 1_000_000) return "1M";
  if (value >= 1_000) return `${value / 1_000}K`;
  return String(value);
}

function humanBytes(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(2)} MB`;
}

function compactHash(hash?: string | null) {
  return hash ? hash.slice(0, 8) : "not committed";
}

function displayValue(value: unknown) {
  if (value === undefined) return "-";
  const rendered = typeof value === "string" ? value : JSON.stringify(value);
  return rendered.length > 68 ? `${rendered.slice(0, 65)}...` : rendered;
}

function relativeTime(timestamp: string) {
  const seconds = Math.max(0, (Date.now() - Date.parse(timestamp)) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function RevonWorkspace() {
  const [apiBase, setApiBase] = useState(() =>
    typeof window === "undefined"
      ? DEFAULT_API
      : window.localStorage.getItem("revon-api-url") ?? DEFAULT_API,
  );
  const api = useMemo(() => new RevonApi(apiBase), [apiBase]);
  const [connection, setConnection] = useState<Connection>("connecting");
  const [repositories, setRepositories] = useState<RepositorySummary[]>([]);
  const [activeName, setActiveName] = useState("");
  const [opened, setOpened] = useState<OpenRepository | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [checkout, setCheckout] = useState<Checkout | null>(null);
  const [fromVersion, setFromVersion] = useState(1);
  const [toVersion, setToVersion] = useState(1);
  const [strategy, setStrategy] = useState("hybrid");
  const [workloadSize, setWorkloadSize] = useState<number>(10_000);
  const [modal, setModal] = useState<Modal>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const [newRepository, setNewRepository] = useState("");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [primaryKey, setPrimaryKey] = useState("id");
  const [importMessage, setImportMessage] = useState("Import dataset");
  const [commitMessage, setCommitMessage] = useState("Update records");
  const [putsText, setPutsText] = useState("{\n  \"key\": {\"value\": \"new data\"}\n}");
  const [deletesText, setDeletesText] = useState("");
  const [settingsUrl, setSettingsUrl] = useState(() =>
    typeof window === "undefined"
      ? DEFAULT_API
      : window.localStorage.getItem("revon-api-url") ?? DEFAULT_API,
  );

  const clearFeedback = () => {
    setError("");
    setNotice("");
  };

  const refreshRepository = useCallback(
    async (name: string) => {
      const [repository, repositoryHistory, repositoryMetrics] = await Promise.all([
        api.openRepository(name),
        api.history(name),
        api.metrics(name),
      ]);
      setOpened(repository);
      setHistory(repositoryHistory);
      setMetrics(repositoryMetrics);
      setCheckout(null);
      const versions = repositoryHistory.commits.map((commit) => commit.version);
      const newest = versions[0] ?? 1;
      const previous = versions[1] ?? newest;
      setFromVersion(previous);
      setToVersion(newest);
      if (previous !== newest) {
        setComparison(await api.compare(name, previous, newest, "hybrid"));
      } else {
        setComparison(null);
      }
    },
    [api],
  );

  const loadRepositories = useCallback(
    async (preferred?: string) => {
      const listing = await api.listRepositories();
      setRepositories(listing.repositories);
      const target =
        preferred && listing.repositories.some((repository) => repository.name === preferred)
          ? preferred
          : listing.repositories[0]?.name ?? "";
      setActiveName(target);
      if (target) await refreshRepository(target);
      else {
        setOpened(null);
        setHistory(null);
        setMetrics(null);
        setComparison(null);
      }
    },
    [api, refreshRepository],
  );

  const connect = useCallback(async () => {
    clearFeedback();
    setConnection("connecting");
    try {
      await api.health();
      setConnection("online");
      await loadRepositories(activeName || undefined);
    } catch (caught) {
      setConnection("offline");
      setError(caught instanceof Error ? caught.message : "Could not reach Revon API");
    }
  }, [activeName, api, loadRepositories]);

  useEffect(() => {
    const timer = window.setTimeout(() => void connect(), 0);
    return () => window.clearTimeout(timer);
    // The initial connection is intentionally repeated only when the API URL changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase]);

  const chooseRepository = async (name: string) => {
    clearFeedback();
    setActiveName(name);
    setBusy(true);
    try {
      await refreshRepository(name);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not open repository");
    } finally {
      setBusy(false);
    }
  };

  const submitCreate = async (event: FormEvent) => {
    event.preventDefault();
    clearFeedback();
    setBusy(true);
    try {
      await api.createRepository(newRepository.trim());
      await loadRepositories(newRepository.trim());
      setNotice(`Repository “${newRepository.trim()}” created`);
      setNewRepository("");
      setModal(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not create repository");
    } finally {
      setBusy(false);
    }
  };

  const submitImport = async (event: FormEvent) => {
    event.preventDefault();
    if (!activeName || !importFile) return;
    clearFeedback();
    setBusy(true);
    try {
      const text = await importFile.text();
      if (importFile.name.toLowerCase().endsWith(".csv")) {
        await api.importCsv(activeName, text, primaryKey.trim(), importMessage);
      } else {
        const parsed = JSON.parse(text) as unknown;
        if (Array.isArray(parsed)) {
          await api.importJson(activeName, {
            rows: parsed,
            primary_key: primaryKey.trim(),
            message: importMessage,
          });
        } else {
          await api.importJson(activeName, {
            state: parsed as Record<string, unknown>,
            message: importMessage,
          });
        }
      }
      await loadRepositories(activeName);
      setNotice(`${importFile.name} committed as a new version`);
      setImportFile(null);
      setModal(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not import dataset");
    } finally {
      setBusy(false);
    }
  };

  const submitCommit = async (event: FormEvent) => {
    event.preventDefault();
    if (!activeName || !opened?.head) return;
    clearFeedback();
    setBusy(true);
    try {
      const puts = JSON.parse(putsText) as Record<string, unknown>;
      const deletes = deletesText
        .split(/[\n,]/)
        .map((key) => key.trim())
        .filter(Boolean);
      await api.commit(activeName, {
        base_version: opened.head,
        puts,
        deletes,
        message: commitMessage,
      });
      await loadRepositories(activeName);
      setNotice("Mutation batch committed atomically");
      setModal(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not commit changes");
    } finally {
      setBusy(false);
    }
  };

  const runComparison = async () => {
    if (!activeName) return;
    clearFeedback();
    setBusy(true);
    try {
      setComparison(await api.compare(activeName, fromVersion, toVersion, strategy));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not compare versions");
    } finally {
      setBusy(false);
    }
  };

  const showCheckout = async (version: number) => {
    if (!activeName) return;
    clearFeedback();
    setBusy(true);
    try {
      setCheckout(await api.checkout(activeName, version));
      window.setTimeout(() => document.getElementById("checkout")?.scrollIntoView(), 0);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not checkout version");
    } finally {
      setBusy(false);
    }
  };

  const applySettings = (event: FormEvent) => {
    event.preventDefault();
    const normalized = settingsUrl.trim().replace(/\/$/, "");
    window.localStorage.setItem("revon-api-url", normalized);
    setApiBase(normalized);
    setModal(null);
  };

  const latestMetric = metrics?.commit_metrics.at(-1);
  const versions = history?.commits ?? [];
  const changeCounts = comparison?.differences.reduce(
    (counts, difference) => ({
      ...counts,
      [difference.change_type]: counts[difference.change_type] + 1,
    }),
    { added: 0, modified: 0, deleted: 0 },
  ) ?? { added: 0, modified: 0, deleted: 0 };

  return (
    <main className="app-shell" aria-busy={busy}>
      <aside className="sidebar">
        <div className="wordmark">
          <span className="mark" aria-hidden="true">C</span>
          <div><strong>REVON</strong><small>VERSIONED DATA STORE</small></div>
        </div>

        <div className="repo-control">
          <label htmlFor="repository-select">ACTIVE REPOSITORY</label>
          <div className="repo-select-row">
            <span className={`repo-indicator ${connection}`} aria-hidden="true" />
            <select
              id="repository-select"
              value={activeName}
              onChange={(event) => void chooseRepository(event.target.value)}
              disabled={!repositories.length}
            >
              {!repositories.length && <option value="">No repositories</option>}
              {repositories.map((repository) => (
                <option value={repository.name} key={repository.name}>{repository.name}</option>
              ))}
            </select>
            <button type="button" onClick={() => setModal("create")} aria-label="Create repository">+</button>
          </div>
        </div>

        <nav aria-label="Repository navigation" className="nav-stack">
          <a className="active" href="#workspace">Overview</a>
          <a href="#history">History</a>
          <a href="#compare">Compare</a>
          <a href="#metrics">Metrics</a>
        </nav>

        <div className="sidebar-foot">
          <span className={`status-dot ${connection}`} />
          <span>{connection === "online" ? "Local API connected" : connection === "offline" ? "API offline" : "Connecting"}</span>
          <button type="button" onClick={() => setModal("settings")}>{apiBase.replace(/^https?:\/\//, "")}</button>
        </div>
      </aside>

      <section className="workspace" id="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">REVON / RESEARCH WORKSPACE</p>
            <h1>Versioning metrics</h1>
            <p className="page-summary">Measure repository growth, structural sharing, and version-diff work without mixing configured workload scale with observed results.</p>
          </div>
          <div className="top-actions">
            <button className="button ghost" type="button" disabled={!activeName} onClick={() => setModal("import")}>Import data</button>
            <button className="button primary" type="button" disabled={!opened?.head} onClick={() => setModal("commit")}>New commit</button>
          </div>
        </header>

        <section className="workload-bar" aria-labelledby="workload-title">
          <div className="workload-copy">
            <span id="workload-title">WORKLOAD SIZE</span>
            <strong>{workloadSize.toLocaleString()} records</strong>
          </div>
          <div className="size-toggle" role="group" aria-label="Select benchmark workload size">
            {WORKLOAD_SIZES.map((size) => (
              <button
                type="button"
                key={size}
                aria-pressed={workloadSize === size}
                className={workloadSize === size ? "active" : ""}
                onClick={() => setWorkloadSize(size)}
              >
                {compactCount(size)}
              </button>
            ))}
          </div>
          <p>Selection configures the benchmark view only. Values below remain measured repository data.</p>
        </section>

        {connection === "offline" && (
          <div className="connection-banner" role="alert">
            <div><strong>The Revon API is not running.</strong><span>Start it with <code>python -m revon_api</code>, then reconnect.</span></div>
            <button className="button primary" type="button" onClick={() => void connect()}>Reconnect</button>
          </div>
        )}
        {(error || notice) && (
          <div className={`feedback ${error ? "error" : "success"}`} role="status">
            <span>{error || notice}</span><button type="button" onClick={clearFeedback}>×</button>
          </div>
        )}

        <div className="metric-section-heading">
          <div><span>LIVE REPOSITORY</span><strong>{activeName || "No repository selected"}</strong></div>
          <small>Measured values</small>
        </div>
        <div className="stat-strip" aria-label="Repository metrics">
          <div><span>WORKLOAD</span><strong>{compactCount(workloadSize)}</strong><small>configured records</small></div>
          <div><span>HEAD</span><strong>{opened?.head ? `v${opened.head}` : "-"}</strong><small>{compactHash(opened?.head_hash)}</small></div>
          <div><span>VERSIONS</span><strong>{opened?.versions ?? 0}</strong><small>linear history</small></div>
          <div><span>STORAGE</span><strong>{humanBytes(metrics?.storage_bytes)}</strong><small>{opened?.integrity.objects ?? 0} verified objects</small></div>
          <div><span>NODE REUSE</span><strong>{latestMetric ? `${latestMetric.shared_percent.toFixed(1)}%` : "-"}</strong><small>latest commit</small></div>
        </div>

        {!activeName && connection === "online" ? (
          <section className="empty-repository panel">
            <p className="eyebrow">BEGIN A TIMELINE</p>
            <h2>Create your first repository</h2>
            <p>Revon stores each structured state by content hash and only rewrites paths touched by a commit.</p>
            <button className="button primary" type="button" onClick={() => setModal("create")}>Create repository</button>
          </section>
        ) : (
          <div className="content-grid">
            <section className="panel history-panel" id="history">
              <div className="panel-heading">
                <div><p className="eyebrow">COMMIT GRAPH</p><h2>Recent history</h2></div>
                <button className="icon-button" type="button" aria-label="Refresh repository" onClick={() => activeName && void refreshRepository(activeName)}>↻</button>
              </div>
              <div className="commit-list">
                {versions.length ? versions.slice(0, 7).map((commit, index) => (
                  <button className="commit" key={commit.commit_hash} type="button" onClick={() => void showCheckout(commit.version)}>
                    <span className="commit-node"><span>{index + 1}</span></span>
                    <span className="commit-copy"><strong>{commit.message || "Untitled commit"}</strong><small>v{commit.version} · {relativeTime(commit.timestamp_utc)}</small></span>
                    <code>{compactHash(commit.commit_hash)}</code>
                  </button>
                )) : (
                  <div className="panel-empty"><strong>No commits yet</strong><span>Import a JSON or CSV dataset to create v1.</span></div>
                )}
              </div>
            </section>

            <section className="panel compare-panel" id="compare">
              <div className="panel-heading">
                <div><p className="eyebrow">HASH-PRUNED DIFF</p><h2>Compare versions</h2></div>
                <span className="strategy-pill">{comparison ? `${comparison.diff_metrics.strategy_selected.toUpperCase()} SELECTED` : "AWAITING VERSIONS"}</span>
              </div>
              <div className="compare-controls">
                <label><span>FROM</span><select value={fromVersion} onChange={(event) => setFromVersion(Number(event.target.value))}>{versions.map((commit) => <option value={commit.version} key={`from-${commit.version}`}>v{commit.version}</option>)}</select></label>
                <span className="arrow" aria-hidden="true">→</span>
                <label><span>TO</span><select value={toVersion} onChange={(event) => setToVersion(Number(event.target.value))}>{versions.map((commit) => <option value={commit.version} key={`to-${commit.version}`}>v{commit.version}</option>)}</select></label>
                <label><span>MODE</span><select value={strategy} onChange={(event) => setStrategy(event.target.value)}><option value="hybrid">Revon-H</option><option value="merkle">Forced Merkle</option><option value="log">Forced log</option></select></label>
                <button className="button dark" type="button" disabled={versions.length < 2 || busy} onClick={() => void runComparison()}>Run diff</button>
              </div>
              <div className="diff-summary">
                <div className="change added"><span>+</span><strong>{changeCounts.added}</strong><small>ADDED</small></div>
                <div className="change modified"><span>~</span><strong>{changeCounts.modified}</strong><small>MODIFIED</small></div>
                <div className="change deleted"><span>−</span><strong>{changeCounts.deleted}</strong><small>DELETED</small></div>
              </div>
              <div className="diff-table">
                {comparison?.differences.length ? comparison.differences.slice(0, 8).map((difference) => (
                  <div className="diff-row" key={difference.key}>
                    <span className={`change-tag ${difference.change_type}`}>{difference.change_type.slice(0, 1).toUpperCase()}</span>
                    <code title={difference.key}>{difference.key}</code>
                    <span className="before" title={displayValue(difference.old_value)}>{displayValue(difference.old_value)}</span>
                    <span aria-hidden="true">→</span>
                    <span className="after" title={displayValue(difference.new_value)}>{displayValue(difference.new_value)}</span>
                  </div>
                )) : <div className="panel-empty compact"><span>{versions.length < 2 ? "Create two versions to compare." : "These versions have identical state."}</span></div>}
              </div>
            </section>

            <section className="panel metrics-panel" id="metrics">
              <div className="panel-heading"><div><p className="eyebrow">INSTRUMENTATION</p><h2>Storage &amp; work</h2></div></div>
              <div className="metric-cards">
                <div><small>NEW NODES</small><strong>{latestMetric?.new_nodes ?? 0}</strong><span>latest commit</span></div>
                <div><small>REUSED REFS</small><strong>{latestMetric?.reused_nodes ?? 0}</strong><span>latest commit</span></div>
                <div><small>DIFF WORK</small><strong>{comparison?.diff_metrics.work_examined ?? 0}</strong><span>{comparison?.diff_metrics.work_unit ?? "not measured"}</span></div>
                <div><small>DIFF TIME</small><strong>{comparison ? `${comparison.diff_ms.toFixed(3)} ms` : "-"}</strong><span>complete result</span></div>
              </div>
            </section>

            <section className="panel integrity-panel">
              <div className="panel-heading"><div><p className="eyebrow">CONTENT ADDRESSING</p><h2>Integrity</h2></div><span className="verified-badge">VERIFIED</span></div>
              <dl className="integrity-list">
                <div><dt>HEAD commit</dt><dd><code>{compactHash(opened?.head_hash)}</code></dd></div>
                <div><dt>Root hash</dt><dd><code>{compactHash(opened?.root_hash)}</code></dd></div>
                <div><dt>Merkle nodes</dt><dd>{opened?.integrity.nodes ?? 0}</dd></div>
                <div><dt>Changesets</dt><dd>{opened?.integrity.changesets ?? 0}</dd></div>
              </dl>
            </section>
          </div>
        )}

        {checkout && (
          <section className="panel checkout-panel" id="checkout">
            <div className="panel-heading">
              <div><p className="eyebrow">HISTORICAL STATE</p><h2>Checkout v{checkout.version}</h2><small>{checkout.returned_rows} of {checkout.total_rows} rows</small></div>
              <button className="icon-button" type="button" aria-label="Close checkout" onClick={() => setCheckout(null)}>×</button>
            </div>
            <div className="data-table" role="table" aria-label={`Version ${checkout.version} data`}>
              {Object.entries(checkout.state).map(([key, value]) => (
                <div className="data-row" role="row" key={key}><code>{key}</code><pre>{JSON.stringify(value, null, 2)}</pre></div>
              ))}
            </div>
            {checkout.truncated && <p className="table-note">Showing the first 250 rows. Use the API pagination parameters for the complete state.</p>}
          </section>
        )}
      </section>

      {modal && (
        <div
          className="modal-backdrop"
          role="button"
          tabIndex={0}
          aria-label="Close dialog"
          onClick={(event) => {
            if (event.currentTarget === event.target && !busy) setModal(null);
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape" || event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              if (!busy) setModal(null);
            }
          }}
        >
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <button className="modal-close" type="button" aria-label="Close" onClick={() => setModal(null)}>×</button>
            {modal === "create" && (
              <form onSubmit={submitCreate}><p className="eyebrow">NEW TIMELINE</p><h2 id="modal-title">Create repository</h2><p>Use a stable lowercase name. Revon creates an isolated SQLite object store.</p><label>Repository name<input required pattern="[a-z0-9][a-z0-9_-]{0,63}" value={newRepository} onChange={(event) => setNewRepository(event.target.value)} placeholder="customer-ledger" /></label><button className="button primary" disabled={busy}>Create repository</button></form>
            )}
            {modal === "import" && (
              <form onSubmit={submitImport}><p className="eyebrow">COMPLETE STATE</p><h2 id="modal-title">Import dataset</h2><p>Choose a UTF-8 CSV or JSON file. JSON arrays use the primary-key field; JSON objects are treated as keyed state.</p><label>Dataset<input required type="file" accept=".csv,.json,text/csv,application/json" onChange={(event) => setImportFile(event.target.files?.[0] ?? null)} /></label><label>Primary key<input required value={primaryKey} onChange={(event) => setPrimaryKey(event.target.value)} /></label><label>Commit message<input required value={importMessage} onChange={(event) => setImportMessage(event.target.value)} /></label><button className="button primary" disabled={busy || !importFile}>Import and commit</button></form>
            )}
            {modal === "commit" && (
              <form onSubmit={submitCommit}><p className="eyebrow">ATOMIC MUTATION</p><h2 id="modal-title">Commit batch to v{opened?.head}</h2><p>Provide a JSON object of key/value puts and optional keys to delete.</p><label>Puts (JSON)<textarea required rows={7} value={putsText} onChange={(event) => setPutsText(event.target.value)} spellCheck={false} /></label><label>Deletes (comma or newline separated)<textarea rows={3} value={deletesText} onChange={(event) => setDeletesText(event.target.value)} /></label><label>Commit message<input required value={commitMessage} onChange={(event) => setCommitMessage(event.target.value)} /></label><button className="button primary" disabled={busy}>Commit atomically</button></form>
            )}
            {modal === "settings" && (
              <form onSubmit={applySettings}><p className="eyebrow">CONNECTION</p><h2 id="modal-title">Backend API</h2><p>Change this only when Revon is running on another local port or host.</p><label>API base URL<input required type="url" value={settingsUrl} onChange={(event) => setSettingsUrl(event.target.value)} /></label><button className="button primary">Save and reconnect</button></form>
            )}
            {error && <div className="form-error" role="alert">{error}</div>}
          </section>
        </div>
      )}
      {busy && <div className="busy-bar" aria-label="Working" />}
    </main>
  );
}

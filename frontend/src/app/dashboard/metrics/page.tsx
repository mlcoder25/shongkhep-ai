"use client";
import { useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { Activity, Cpu, Database, Server, RefreshCw, Loader2, ExternalLink } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

interface AdminStats {
  total_users: number;
  active_users: number;
  users_by_plan: Record<string, number>;
  total_requests_all_time: number;
  model_info: { device?: string; dtype?: string; params?: string };
  redis_health: { status: string; version?: string; used_memory_human?: string };
}

function InfoRow({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-ink-800 last:border-0">
      <span className="text-sm text-ink-500">{label}</span>
      <span className={clsx("text-sm font-mono", accent ? "text-brand-400" : "text-ink-300")}>{value}</span>
    </div>
  );
}

export default function MetricsPage() {
  const user = useAuthStore(s => s.user);
  const [stats,      setStats]      = useState<AdminStats | null>(null);
  const [loading,    setLoading]    = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const data = await adminApi.stats();
      setStats(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed";
      if (isRefresh) toast.error(msg);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (!user) return null;

  if (!user || (user as { is_admin?: boolean }).is_admin === false) {
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <div className="card p-10 text-center">
          <Activity size={36} className="text-ink-700 mx-auto mb-3" />
          <p className="text-ink-500 text-sm">Metrics are available to admin accounts only.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8 flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink-50 mb-1">Platform Metrics</h1>
          <p className="text-ink-500 text-sm">Live stats from the Shongkhep AI backend</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => load(true)} disabled={refreshing}
                  className="btn-ghost border border-ink-700 text-sm flex items-center gap-2">
            {refreshing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Refresh
          </button>
          <a href="http://localhost:3001" target="_blank" rel="noopener noreferrer"
             className="btn-primary text-sm flex items-center gap-2">
            <Activity size={14} /> Grafana
            <ExternalLink size={12} />
          </a>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={28} className="text-brand-500 animate-spin" />
        </div>
      ) : !stats ? (
        <div className="card p-10 text-center text-ink-600 text-sm">
          Could not load admin stats. Ensure your account has admin access.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Summary stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "Total users",     value: stats.total_users.toLocaleString(),           icon: Server },
              { label: "Active users",    value: stats.active_users.toLocaleString(),           icon: Activity },
              { label: "Total requests",  value: stats.total_requests_all_time.toLocaleString(), icon: Cpu },
              { label: "Free / Basic / Pro",
                value: `${stats.users_by_plan.free || 0} / ${stats.users_by_plan.basic || 0} / ${stats.users_by_plan.pro || 0}`,
                icon: Database },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="card p-5">
                <div className="flex items-start justify-between mb-2">
                  <span className="text-xs text-ink-500">{label}</span>
                  <div className="w-7 h-7 rounded-lg bg-ink-800 flex items-center justify-center text-ink-500">
                    <Icon size={14} />
                  </div>
                </div>
                <p className="font-display text-2xl font-bold text-ink-50">{value}</p>
              </div>
            ))}
          </div>

          {/* Plan distribution */}
          <div className="card p-6">
            <h2 className="font-semibold text-ink-300 text-sm uppercase tracking-wider mb-4">Plan distribution</h2>
            {["free", "basic", "pro"].map(plan => {
              const count = stats.users_by_plan[plan] || 0;
              const pct = stats.total_users > 0 ? (count / stats.total_users) * 100 : 0;
              return (
                <div key={plan} className="mb-3 last:mb-0">
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className={`badge-${plan} capitalize`}>{plan}</span>
                    <span className="text-ink-500">{count} users ({pct.toFixed(1)}%)</span>
                  </div>
                  <div className="w-full h-2 bg-ink-800 rounded-full">
                    <div
                      className={clsx("h-full rounded-full transition-all duration-700",
                        plan === "pro" ? "bg-brand-500" : plan === "basic" ? "bg-saffron-400" : "bg-ink-600")}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Model info */}
            <div className="card p-6">
              <div className="flex items-center gap-2 mb-4">
                <Cpu size={16} className="text-brand-400" />
                <h2 className="font-semibold text-ink-300 text-sm uppercase tracking-wider">Model</h2>
              </div>
              {Object.keys(stats.model_info).length === 0 ? (
                <p className="text-ink-600 text-sm">Model not yet loaded</p>
              ) : (
                <>
                  <InfoRow label="Device"     value={stats.model_info.device || "—"} accent />
                  <InfoRow label="Dtype"      value={stats.model_info.dtype  || "—"} />
                  <InfoRow label="Parameters" value={stats.model_info.params || "—"} />
                  <InfoRow label="Model ID"   value="google/mt5-small" />
                </>
              )}
            </div>

            {/* Redis info */}
            <div className="card p-6">
              <div className="flex items-center gap-2 mb-4">
                <Database size={16} className={stats.redis_health.status === "ok" ? "text-brand-400" : "text-red-400"} />
                <h2 className="font-semibold text-ink-300 text-sm uppercase tracking-wider">Redis Cache</h2>
                <span className={clsx(
                  "ml-auto badge",
                  stats.redis_health.status === "ok" ? "bg-brand-950 text-brand-400 border-brand-800" : "bg-red-950 text-red-400 border-red-800"
                )}>
                  {stats.redis_health.status}
                </span>
              </div>
              {stats.redis_health.version && (
                <>
                  <InfoRow label="Version"     value={stats.redis_health.version} accent />
                  <InfoRow label="Memory used" value={stats.redis_health.used_memory_human || "—"} />
                </>
              )}
              <InfoRow label="Cache TTL"  value="3600s (1 hour)" />
              <InfoRow label="Max memory" value="256 MB (allkeys-lru)" />
            </div>
          </div>

          {/* Links */}
          <div className="card p-5 flex flex-wrap gap-3">
            <p className="text-sm text-ink-500 w-full">External observability links</p>
            {[
              { label: "Grafana dashboards", url: "http://localhost:3001", desc: "admin / grafanapass" },
              { label: "Prometheus",         url: "http://localhost:9090", desc: "" },
              { label: "Flower (Celery)",    url: "http://localhost:5555", desc: "admin / flowerpass" },
              { label: "API Metrics",        url: "http://localhost:8000/metrics", desc: "" },
            ].map(({ label, url, desc }) => (
              <a key={url} href={url} target="_blank" rel="noopener noreferrer"
                 className="flex items-center gap-2 px-3 py-2 rounded-xl bg-ink-800 border border-ink-700 text-sm text-ink-400 hover:text-ink-200 hover:border-ink-600 transition-all">
                <ExternalLink size={13} />
                {label}
                {desc && <span className="text-ink-600 text-xs font-mono ml-1">{desc}</span>}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

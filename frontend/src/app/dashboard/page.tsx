"use client";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/authStore";
import { usageApi } from "@/lib/api";
import { BarChart3, Zap, Key, TrendingUp, Calendar } from "lucide-react";
import Link from "next/link";
import clsx from "clsx";

interface UsageStats {
  total_requests: number;
  total_characters_processed: number;
  plan: string;
  monthly_limit: number;
  usage_count: number;
  remaining_requests: number;
  usage_percentage: number;
  recent_logs: Array<{
    id: string;
    article_language: string;
    characters_used: number;
    summary_tokens: number;
    created_at: string;
  }>;
}

function StatCard({ icon: Icon, label, value, sub, accent = false }: {
  icon: React.ElementType; label: string; value: string; sub?: string; accent?: boolean;
}) {
  return (
    <div className={clsx("card p-5", accent && "border-brand-700/50 bg-brand-950/30")}>
      <div className="flex items-start justify-between mb-3">
        <span className="text-sm text-ink-500">{label}</span>
        <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center",
          accent ? "bg-brand-600/20 text-brand-400" : "bg-ink-800 text-ink-400")}>
          <Icon size={16} />
        </div>
      </div>
      <p className="font-display text-3xl font-bold text-ink-50">{value}</p>
      {sub && <p className="text-xs text-ink-500 mt-1">{sub}</p>}
    </div>
  );
}

function UsageBar({ pct }: { pct: number }) {
  const color = pct > 90 ? "bg-red-500" : pct > 70 ? "bg-saffron-400" : "bg-brand-500";
  return (
    <div className="w-full h-2 bg-ink-800 rounded-full overflow-hidden">
      <div className={clsx("h-full rounded-full transition-all duration-700", color)} style={{ width: `${Math.min(pct, 100)}%` }} />
    </div>
  );
}

export default function DashboardOverview() {
  const user = useAuthStore((s) => s.user);
  const [stats, setStats] = useState<UsageStats | null>(null);

  useEffect(() => {
    usageApi.stats(5).then(setStats).catch(() => {});
  }, []);

  if (!user) return null;

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-ink-50 mb-1">
          Good day, <span className="text-brand-400">{user.email.split("@")[0]}</span>
        </h1>
        <p className="text-ink-500 text-sm">Here's your Shongkhep AI overview</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard icon={Zap}      label="Requests used"     value={String(user.usage_count)}              sub="this month"   accent />
        <StatCard icon={BarChart3} label="Remaining"         value={String(user.remaining_requests)}       sub={`of ${user.monthly_limit}`} />
        <StatCard icon={TrendingUp} label="Characters"       value={stats ? (stats.total_characters_processed / 1000).toFixed(1) + "k" : "—"} sub="total processed" />
        <StatCard icon={Calendar}  label="Plan"              value={user.plan.charAt(0).toUpperCase() + user.plan.slice(1)} sub="active" />
      </div>

      {/* Usage bar */}
      <div className="card p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-ink-300">Monthly usage</span>
          <span className="text-sm text-ink-500">{user.usage_count} / {user.monthly_limit} requests</span>
        </div>
        <UsageBar pct={user.usage_percentage} />
        <p className="text-xs text-ink-600 mt-2">{user.usage_percentage.toFixed(1)}% used · Resets on the 1st of next month</p>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        <Link href="/dashboard/summarize" className="card-hover p-5 flex items-center gap-4 cursor-pointer">
          <div className="w-10 h-10 rounded-xl bg-brand-600/20 border border-brand-600/30 flex items-center justify-center text-brand-400">
            <Zap size={20} />
          </div>
          <div>
            <p className="font-medium text-ink-100 text-sm">Summarize an article</p>
            <p className="text-xs text-ink-500">Try the web interface</p>
          </div>
        </Link>
        <Link href="/dashboard/api-key" className="card-hover p-5 flex items-center gap-4 cursor-pointer">
          <div className="w-10 h-10 rounded-xl bg-ink-800 border border-ink-700 flex items-center justify-center text-ink-400">
            <Key size={20} />
          </div>
          <div>
            <p className="font-medium text-ink-100 text-sm">View your API key</p>
            <p className="text-xs text-ink-500">Integrate in your app</p>
          </div>
        </Link>
      </div>

      {/* Recent activity */}
      {stats && stats.recent_logs.length > 0 && (
        <div className="card p-6">
          <h2 className="font-semibold text-ink-200 mb-4 text-sm uppercase tracking-wider">Recent requests</h2>
          <div className="space-y-3">
            {stats.recent_logs.map((log) => (
              <div key={log.id} className="flex items-center justify-between py-2.5 border-b border-ink-800 last:border-0">
                <div className="flex items-center gap-3">
                  <span className={clsx("badge", log.article_language === "bn" ? "badge-basic" : "badge-free")}>
                    {log.article_language === "bn" ? "বাংলা" : "EN"}
                  </span>
                  <span className="text-sm text-ink-400">{log.characters_used.toLocaleString()} chars</span>
                </div>
                <span className="text-xs text-ink-600">
                  {new Date(log.created_at).toLocaleString("en-BD", { dateStyle: "short", timeStyle: "short" })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

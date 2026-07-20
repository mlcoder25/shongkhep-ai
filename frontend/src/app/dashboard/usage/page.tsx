"use client";
import { useEffect, useState } from "react";
import { usageApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { BarChart3, FileText, Hash, Loader2 } from "lucide-react";
import clsx from "clsx";

interface UsageLog {
  id: string;
  article_language: string;
  characters_used: number;
  summary_tokens: number;
  created_at: string;
}

interface Stats {
  total_requests: number;
  total_characters_processed: number;
  plan: string;
  monthly_limit: number;
  usage_count: number;
  remaining_requests: number;
  usage_percentage: number;
  recent_logs: UsageLog[];
}

export default function UsagePage() {
  const user = useAuthStore((s) => s.user);
  const [stats,   setStats]   = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    usageApi.stats(50).then((d) => { setStats(d); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <Loader2 size={28} className="text-brand-500 animate-spin" />
      </div>
    );
  }

  if (!user || !stats) return null;

  const engCount = stats.recent_logs.filter((l) => l.article_language === "en").length;
  const bnCount  = stats.recent_logs.filter((l) => l.article_language === "bn").length;

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-ink-50 mb-1">Usage Analytics</h1>
        <p className="text-ink-500 text-sm">Your summarization usage this billing period</p>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {[
          { icon: BarChart3, label: "Total requests",      value: stats.usage_count.toLocaleString()                       },
          { icon: FileText,  label: "Characters processed", value: (stats.total_characters_processed / 1000).toFixed(1) + "k" },
          { icon: Hash,      label: "Remaining",            value: stats.remaining_requests.toLocaleString()                },
        ].map(({ icon: Icon, label, value }) => (
          <div key={label} className="card p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-brand-950 border border-brand-900 flex items-center justify-center text-brand-400 shrink-0">
              <Icon size={18} />
            </div>
            <div>
              <p className="text-xs text-ink-500 mb-0.5">{label}</p>
              <p className="font-display text-2xl font-bold text-ink-50">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Usage bar */}
      <div className="card p-6 mb-6">
        <div className="flex justify-between text-sm mb-3">
          <span className="font-medium text-ink-300">Monthly quota</span>
          <span className="text-ink-500">{stats.usage_count} / {stats.monthly_limit}</span>
        </div>
        <div className="w-full h-3 bg-ink-800 rounded-full overflow-hidden mb-2">
          <div
            className={clsx(
              "h-full rounded-full transition-all duration-700",
              stats.usage_percentage > 90 ? "bg-red-500" : stats.usage_percentage > 70 ? "bg-saffron-400" : "bg-brand-500"
            )}
            style={{ width: `${Math.min(stats.usage_percentage, 100)}%` }}
          />
        </div>
        <p className="text-xs text-ink-600">{stats.usage_percentage.toFixed(1)}% used</p>

        {/* Language breakdown */}
        {stats.recent_logs.length > 0 && (
          <div className="flex gap-4 mt-4 pt-4 border-t border-ink-800">
            <div className="flex items-center gap-2 text-sm">
              <span className="badge badge-basic">বাংলা</span>
              <span className="text-ink-400">{bnCount} requests</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="badge badge-free">English</span>
              <span className="text-ink-400">{engCount} requests</span>
            </div>
          </div>
        )}
      </div>

      {/* Log table */}
      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-ink-800">
          <h2 className="font-semibold text-ink-200 text-sm uppercase tracking-wider">Request log</h2>
        </div>

        {stats.recent_logs.length === 0 ? (
          <div className="py-16 text-center text-ink-600 text-sm">No requests yet. Start summarizing!</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-800 text-left">
                  {["Language", "Characters", "Tokens", "Date"].map((h) => (
                    <th key={h} className="px-5 py-3 text-xs font-semibold text-ink-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {stats.recent_logs.map((log, i) => (
                  <tr key={log.id} className={clsx("border-b border-ink-800/50 last:border-0", i % 2 === 0 ? "" : "bg-ink-900/30")}>
                    <td className="px-5 py-3.5">
                      <span className={log.article_language === "bn" ? "badge-basic" : "badge-free"}>
                        {log.article_language === "bn" ? "বাংলা" : "English"}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-ink-400 font-mono">{log.characters_used.toLocaleString()}</td>
                    <td className="px-5 py-3.5 text-ink-400 font-mono">{log.summary_tokens}</td>
                    <td className="px-5 py-3.5 text-ink-500">
                      {new Date(log.created_at).toLocaleString("en-BD", { dateStyle: "medium", timeStyle: "short" })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/store/authStore";
import {
  LayoutDashboard, Zap, BarChart3, Key, CreditCard,
  LogOut, Loader2, Webhook, Activity
} from "lucide-react";
import clsx from "clsx";

const NAV_ITEMS = [
  { href: "/dashboard",            icon: LayoutDashboard, label: "Overview"    },
  { href: "/dashboard/summarize",  icon: Zap,             label: "Summarize"   },
  { href: "/dashboard/usage",      icon: BarChart3,       label: "Usage"       },
  { href: "/dashboard/api-key",    icon: Key,             label: "API Key"     },
  { href: "/dashboard/webhooks",   icon: Webhook,         label: "Webhooks"    },
  { href: "/dashboard/billing",    icon: CreditCard,      label: "Billing"     },
  { href: "/dashboard/metrics",    icon: Activity,        label: "Metrics"     },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router   = useRouter();
  const pathname = usePathname();
  const { user, hydrated, fetchMe, logout } = useAuthStore();

  useEffect(() => {
    fetchMe().then(() => {
      if (!useAuthStore.getState().user) router.push("/login");
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!hydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 size={32} className="text-brand-500 animate-spin" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 bg-ink-900 border-r border-ink-800 flex flex-col">
        <div className="px-5 py-5 border-b border-ink-800">
          <Link href="/dashboard" className="flex items-center gap-2.5">
            <span className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white font-display font-bold text-lg">স</span>
            <span className="font-display text-lg font-bold text-ink-50 leading-none">
              Shongkhep<br />
              <span className="text-brand-400 text-xs font-body font-normal tracking-widest uppercase">AI v2</span>
            </span>
          </Link>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
            const active = pathname === href;
            return (
              <Link key={href} href={href}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150",
                  active
                    ? "bg-brand-600/20 text-brand-300 border border-brand-600/30"
                    : "text-ink-400 hover:text-ink-200 hover:bg-ink-800"
                )}
              >
                <Icon size={17} />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-ink-800">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-brand-800 flex items-center justify-center text-brand-300 font-semibold text-sm uppercase">
              {user.email[0]}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-ink-200 truncate">{user.email}</p>
              <span className={`badge-${user.plan}`}>{user.plan.charAt(0).toUpperCase() + user.plan.slice(1)}</span>
            </div>
          </div>
          <button onClick={() => { logout(); router.push("/login"); }}
                  className="btn-ghost w-full text-sm flex items-center gap-2 justify-center text-ink-500">
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto bg-ink-950">
        {children}
      </main>
    </div>
  );
}

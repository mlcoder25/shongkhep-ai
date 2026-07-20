"use client";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/authStore";
import { plansApi, authApi } from "@/lib/api";
import { CheckCircle, Zap, Star, Rocket, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

interface Plan {
  name: string;
  monthly_requests: number;
  price_bdt: number;
  price_usd: number;
  features: string[];
}

const PLAN_ICONS: Record<string, React.ElementType> = {
  free:  Zap,
  basic: Star,
  pro:   Rocket,
};

export default function BillingPage() {
  const { user, setUser } = useAuthStore();
  const [plans,     setPlans]     = useState<Plan[]>([]);
  const [upgrading, setUpgrading] = useState<string | null>(null);

  useEffect(() => {
    plansApi.info().then((d) => setPlans(d.plans)).catch(() => {});
  }, []);

  const handleUpgrade = async (planName: string) => {
    if (planName === user?.plan) return;
    setUpgrading(planName);
    try {
      await plansApi.upgrade(planName);
      const updated = await authApi.me();
      setUser(updated);
      toast.success(`Upgraded to ${planName} plan! 🎉`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Upgrade failed");
    } finally {
      setUpgrading(null);
    }
  };

  if (!user) return null;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-ink-50 mb-1">Plans & Billing</h1>
        <p className="text-ink-500 text-sm">
          You are on the <span className={`badge-${user.plan}`}>{user.plan}</span> plan.
          {" "}Upgrade for more summaries per month.
        </p>
      </div>

      {/* Mock payment notice */}
      <div className="p-4 rounded-xl bg-brand-950 border border-brand-800 text-brand-300 text-sm mb-8 flex items-start gap-2">
        <span className="mt-0.5">ℹ</span>
        <p>
          <strong>Demo mode:</strong> Upgrades are mocked — no payment is processed.
          In production, this will integrate with SSLCommerz or bKash.
        </p>
      </div>

      {/* Plan cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map((plan) => {
          const isCurrentPlan = user.plan === plan.name;
          const Icon = PLAN_ICONS[plan.name] || Zap;
          const isLoading = upgrading === plan.name;

          return (
            <div
              key={plan.name}
              className={clsx(
                "card p-6 flex flex-col gap-5 transition-all duration-200",
                isCurrentPlan && "border-brand-600 shadow-lg shadow-brand-950/40 relative",
                !isCurrentPlan && "hover:border-ink-700"
              )}
            >
              {isCurrentPlan && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-brand-600 text-white text-xs font-semibold px-3 py-1 rounded-full whitespace-nowrap">
                  Current plan
                </div>
              )}

              {/* Plan header */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Icon size={16} className={isCurrentPlan ? "text-brand-400" : "text-ink-500"} />
                    <p className="text-sm font-semibold text-ink-200 capitalize">{plan.name}</p>
                  </div>
                  <p className="font-display text-4xl font-bold text-ink-50">
                    ৳{plan.price_bdt.toLocaleString()}
                    <span className="text-base font-body font-normal text-ink-500">/mo</span>
                  </p>
                  <p className="text-xs text-ink-600 mt-0.5">${plan.price_usd} USD</p>
                </div>
              </div>

              {/* Limit */}
              <div className="py-3 px-4 rounded-xl bg-ink-800 border border-ink-700 text-center">
                <p className="font-display text-xl font-bold text-ink-100">
                  {plan.monthly_requests.toLocaleString()}
                </p>
                <p className="text-xs text-ink-500">summaries per month</p>
              </div>

              {/* Features */}
              <ul className="space-y-2 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-ink-400">
                    <CheckCircle size={14} className="text-brand-500 shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <button
                onClick={() => handleUpgrade(plan.name)}
                disabled={isCurrentPlan || isLoading}
                className={clsx(
                  "w-full py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-2 transition-all",
                  isCurrentPlan
                    ? "bg-ink-800 text-ink-500 cursor-default border border-ink-700"
                    : "btn-primary"
                )}
              >
                {isLoading && <Loader2 size={15} className="animate-spin" />}
                {isCurrentPlan ? "Current plan" : `Switch to ${plan.name}`}
              </button>
            </div>
          );
        })}
      </div>

      {/* Payment methods note */}
      <div className="mt-8 p-5 card text-sm text-ink-500">
        <p className="font-medium text-ink-400 mb-2">Accepted payment methods (coming soon)</p>
        <div className="flex flex-wrap gap-2">
          {["bKash", "Nagad", "Rocket", "SSLCommerz", "Visa/Mastercard"].map((m) => (
            <span key={m} className="px-3 py-1 rounded-lg bg-ink-800 border border-ink-700 text-ink-400 text-xs">{m}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

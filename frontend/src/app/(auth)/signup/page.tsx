"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Eye, EyeOff, ArrowRight, Loader2, CheckCircle } from "lucide-react";
import toast from "react-hot-toast";

const PERKS = [
  "100 free summaries per month",
  "Bangla + English auto-detection",
  "REST API with your own key",
];

export default function SignupPage() {
  const router   = useRouter();
  const signup   = useAuthStore((s) => s.signup);
  const loading  = useAuthStore((s) => s.loading);

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [showPw,   setShowPw]   = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }
    try {
      await signup(email, password);
      toast.success("Account created! Welcome to Shongkhep AI 🎉");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Signup failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{
      background: "radial-gradient(ellipse 60% 55% at 70% 80%, hsla(145,55%,10%,0.6) 0%, transparent 55%), #131419",
    }}>
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 mb-6">
            <span className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center text-white font-display font-bold text-xl">স</span>
            <span className="font-display text-2xl font-bold text-ink-50">Shongkhep <span className="text-brand-400">AI</span></span>
          </Link>
          <h1 className="font-display text-3xl font-bold text-ink-50 mb-2">Create your account</h1>
          <p className="text-ink-500 text-sm">Free forever. No credit card needed.</p>
        </div>

        {/* Perks strip */}
        <div className="flex flex-col gap-2 mb-6">
          {PERKS.map((p) => (
            <div key={p} className="flex items-center gap-2.5 text-sm text-ink-400">
              <CheckCircle size={14} className="text-brand-500 shrink-0" />
              {p}
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="card p-8 space-y-5 shadow-2xl shadow-black/50">
          <div>
            <label className="label">Email address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="input"
            />
          </div>

          <div>
            <label className="label">Password</label>
            <div className="relative">
              <input
                type={showPw ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min. 8 characters"
                required
                minLength={8}
                className="input pr-11"
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-500 hover:text-ink-300 transition-colors"
              >
                {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {password.length > 0 && password.length < 8 && (
              <p className="text-red-400 text-xs mt-1.5">Must be at least 8 characters</p>
            )}
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 py-3">
            {loading ? <Loader2 size={18} className="animate-spin" /> : <ArrowRight size={18} />}
            {loading ? "Creating account…" : "Create free account"}
          </button>
        </form>

        <p className="text-center text-sm text-ink-500 mt-6">
          Already have an account?{" "}
          <Link href="/login" className="text-brand-400 hover:text-brand-300 transition-colors font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

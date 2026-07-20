"use client";
import { useState } from "react";
import { useAuthStore } from "@/store/authStore";
import { authApi } from "@/lib/api";
import { Key, Copy, Check, RefreshCw, Eye, EyeOff, Loader2, Terminal } from "lucide-react";
import toast from "react-hot-toast";

const CODE_EXAMPLES = {
  curl: (key: string) =>
`curl -X POST http://localhost:8000/api/v1/summarize \\
  -H "X-API-Key: ${key}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "Your article text here...",
    "language": "auto"
  }'`,
  python: (key: string) =>
`import requests

response = requests.post(
    "http://localhost:8000/api/v1/summarize",
    headers={"X-API-Key": "${key}"},
    json={"text": "Your article text here...", "language": "auto"}
)
print(response.json()["summary"])`,
  js: (key: string) =>
`const response = await fetch(
  "http://localhost:8000/api/v1/summarize",
  {
    method: "POST",
    headers: {
      "X-API-Key": "${key}",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ text: "Your article...", language: "auto" })
  }
);
const { summary } = await response.json();`,
};

type Lang = "curl" | "python" | "js";

export default function ApiKeyPage() {
  const { user, setUser } = useAuthStore();
  const [revealed,     setRevealed]     = useState(false);
  const [copied,       setCopied]       = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [codeLang,     setCodeLang]     = useState<Lang>("curl");

  if (!user) return null;

  const maskedKey = user.api_key.slice(0, 8) + "•".repeat(24) + user.api_key.slice(-8);
  const displayKey = revealed ? user.api_key : maskedKey;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(user.api_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success("API key copied!");
  };

  const handleRegenerate = async () => {
    if (!confirm("Regenerate your API key? Your current key will stop working immediately.")) return;
    setRegenerating(true);
    try {
      await authApi.regenerateKey();
      const updated = await authApi.me();
      setUser(updated);
      setRevealed(false);
      toast.success("New API key generated");
    } catch {
      toast.error("Failed to regenerate key");
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-ink-50 mb-1">API Key</h1>
        <p className="text-ink-500 text-sm">Use this key to authenticate API requests from your application</p>
      </div>

      {/* Key card */}
      <div className="card p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-xl bg-brand-950 border border-brand-800 flex items-center justify-center text-brand-400">
            <Key size={18} />
          </div>
          <div>
            <p className="text-sm font-semibold text-ink-200">Your API key</p>
            <p className="text-xs text-ink-500">Keep this secret — treat it like a password</p>
          </div>
        </div>

        {/* Key display */}
        <div className="bg-ink-800 border border-ink-700 rounded-xl px-4 py-3 font-mono text-sm text-ink-300 flex items-center justify-between gap-3 mb-4 overflow-hidden">
          <span className="truncate">{displayKey}</span>
          <div className="flex items-center gap-1 shrink-0">
            <button onClick={() => setRevealed(!revealed)} className="p-1.5 hover:text-ink-100 text-ink-500 transition-colors rounded-lg hover:bg-ink-700">
              {revealed ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
            <button onClick={handleCopy} className="p-1.5 hover:text-ink-100 text-ink-500 transition-colors rounded-lg hover:bg-ink-700">
              {copied ? <Check size={15} className="text-brand-400" /> : <Copy size={15} />}
            </button>
          </div>
        </div>

        <div className="flex gap-3">
          <button onClick={handleCopy} className="btn-primary flex-1 text-sm flex items-center justify-center gap-2">
            {copied ? <Check size={15} /> : <Copy size={15} />}
            {copied ? "Copied!" : "Copy key"}
          </button>
          <button onClick={handleRegenerate} disabled={regenerating} className="btn-ghost border border-ink-700 text-sm flex items-center gap-2">
            {regenerating ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
            Regenerate
          </button>
        </div>
      </div>

      {/* Code examples */}
      <div className="card overflow-hidden">
        <div className="flex items-center gap-3 px-5 py-4 border-b border-ink-800">
          <Terminal size={16} className="text-ink-500" />
          <span className="text-sm font-medium text-ink-300">Code examples</span>
          <div className="ml-auto flex rounded-lg overflow-hidden border border-ink-700">
            {(["curl", "python", "js"] as Lang[]).map((l) => (
              <button
                key={l}
                onClick={() => setCodeLang(l)}
                className={`px-3 py-1.5 text-xs font-mono transition-colors ${codeLang === l ? "bg-brand-600 text-white" : "text-ink-500 hover:text-ink-300 hover:bg-ink-800"}`}
              >
                {l === "js" ? "JavaScript" : l}
              </button>
            ))}
          </div>
        </div>
        <pre className="p-5 text-xs font-mono text-ink-400 overflow-x-auto leading-relaxed">
          <code>{CODE_EXAMPLES[codeLang](revealed ? user.api_key : "sk-your-api-key")}</code>
        </pre>
      </div>

      {/* Warning */}
      <div className="mt-4 p-4 rounded-xl bg-saffron-400/10 border border-saffron-400/20 text-saffron-400 text-sm">
        ⚠ Never expose your API key in client-side code or public repositories. Use environment variables.
      </div>
    </div>
  );
}

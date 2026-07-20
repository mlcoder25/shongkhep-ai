"use client";
import { useEffect, useState } from "react";
import { webhooksApi } from "@/lib/api";
import { Webhook, Plus, Trash2, Send, Loader2, ExternalLink, ShieldCheck } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

interface WebhookEntry {
  id: string;
  url: string;
  events: string;
  is_active: boolean;
  created_at: string;
}

const ALL_EVENTS = ["summarize.complete", "limit.reached", "limit.warning"];

export default function WebhooksPage() {
  const [hooks,      setHooks]      = useState<WebhookEntry[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [creating,   setCreating]   = useState(false);
  const [showForm,   setShowForm]   = useState(false);
  const [url,        setUrl]        = useState("");
  const [secret,     setSecret]     = useState("");
  const [events,     setEvents]     = useState<string[]>(["summarize.complete"]);
  const [testing,    setTesting]    = useState<string | null>(null);
  const [deleting,   setDeleting]   = useState<string | null>(null);

  const load = () => webhooksApi.list().then(setHooks).catch(() => {}).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;
    setCreating(true);
    try {
      await webhooksApi.create({ url, secret: secret || undefined, events });
      toast.success("Webhook created!");
      setShowForm(false);
      setUrl(""); setSecret(""); setEvents(["summarize.complete"]);
      load();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to create webhook");
    } finally {
      setCreating(false);
    }
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      await webhooksApi.test(id);
      toast.success("Test ping queued!");
    } catch { toast.error("Test failed"); }
    finally { setTesting(null); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this webhook?")) return;
    setDeleting(id);
    try {
      await webhooksApi.delete(id);
      setHooks(h => h.filter(x => x.id !== id));
      toast.success("Webhook deleted");
    } catch { toast.error("Delete failed"); }
    finally { setDeleting(null); }
  };

  const toggleEvent = (ev: string) => {
    setEvents(prev => prev.includes(ev) ? prev.filter(e => e !== ev) : [...prev, ev]);
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8 flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink-50 mb-1">Webhooks</h1>
          <p className="text-ink-500 text-sm">Receive real-time POST notifications when events occur in your account.</p>
        </div>
        <button onClick={() => setShowForm(s => !s)} className="btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Add webhook
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <form onSubmit={handleCreate} className="card p-6 mb-6 space-y-4 animate-slide-up">
          <h2 className="font-semibold text-ink-200">New webhook</h2>

          <div>
            <label className="label">Endpoint URL</label>
            <input type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://yourapp.com/webhook" required className="input" />
          </div>

          <div>
            <label className="label">Secret (for HMAC signature, optional)</label>
            <input type="text" value={secret} onChange={e => setSecret(e.target.value)} placeholder="Leave blank to auto-generate" className="input" />
          </div>

          <div>
            <label className="label">Events to subscribe</label>
            <div className="flex flex-wrap gap-2 mt-1">
              {ALL_EVENTS.map(ev => (
                <button
                  key={ev}
                  type="button"
                  onClick={() => toggleEvent(ev)}
                  className={clsx(
                    "px-3 py-1.5 rounded-lg text-xs font-mono border transition-all",
                    events.includes(ev)
                      ? "bg-brand-950 border-brand-700 text-brand-300"
                      : "bg-ink-800 border-ink-700 text-ink-500 hover:text-ink-300"
                  )}
                >
                  {ev}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={creating || events.length === 0} className="btn-primary flex items-center gap-2 text-sm">
              {creating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              {creating ? "Creating…" : "Create webhook"}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-ghost text-sm">Cancel</button>
          </div>
        </form>
      )}

      {/* Security note */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-brand-950/50 border border-brand-900 text-sm text-brand-300 mb-6">
        <ShieldCheck size={16} className="shrink-0 mt-0.5" />
        <p>
          Payloads are signed with <code className="font-mono text-brand-400">HMAC-SHA256</code>.
          Verify the <code className="font-mono text-brand-400">X-Shongkhep-Signature</code> header on your server.
        </p>
      </div>

      {/* Webhook list */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={24} className="text-brand-500 animate-spin" />
        </div>
      ) : hooks.length === 0 ? (
        <div className="card py-16 text-center">
          <Webhook size={32} className="text-ink-700 mx-auto mb-3" />
          <p className="text-ink-600 text-sm">No webhooks yet. Add one to receive event notifications.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {hooks.map(hook => (
            <div key={hook.id} className="card p-5">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={clsx("w-2 h-2 rounded-full shrink-0", hook.is_active ? "bg-brand-400" : "bg-ink-600")} />
                    <a href={hook.url} target="_blank" rel="noopener noreferrer"
                       className="text-sm font-mono text-ink-300 hover:text-brand-300 transition-colors flex items-center gap-1 truncate">
                      {hook.url}
                      <ExternalLink size={11} className="shrink-0" />
                    </a>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {hook.events.split(",").map(ev => (
                      <span key={ev} className="px-2 py-0.5 rounded bg-ink-800 border border-ink-700 text-xs font-mono text-ink-500">{ev.trim()}</span>
                    ))}
                  </div>
                  <p className="text-xs text-ink-700 mt-2">
                    Created {new Date(hook.created_at).toLocaleDateString("en-BD")}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button onClick={() => handleTest(hook.id)} disabled={testing === hook.id}
                          className="btn-ghost text-xs flex items-center gap-1.5 border border-ink-700">
                    {testing === hook.id ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                    Test
                  </button>
                  <button onClick={() => handleDelete(hook.id)} disabled={deleting === hook.id}
                          className="btn-danger text-xs flex items-center gap-1.5">
                    {deleting === hook.id ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

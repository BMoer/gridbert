import { type FormEvent, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { register } from "../../api/client";
import { useAuthStore } from "../../stores/authStore";

export function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await register(email, password, name);
      setAuth(res.access_token, { user_id: res.user_id, name: res.name, email });
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registrierung fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4" style={{ background: "var(--bone)" }}>
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 style={{ fontFamily: "var(--font-display)", fontSize: "2rem", fontWeight: 700, color: "var(--ink)" }}>
            Grid<span style={{ color: "var(--terracotta)" }}>bert</span>
          </h1>
          <p className="mt-2" style={{ color: "var(--warm-grau)", fontFamily: "var(--font-body)" }}>
            Erstelle deinen Account
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-xl p-6"
          style={{ background: "var(--kreide)", boxShadow: "var(--shadow-card)" }}
        >
          <h2 className="text-lg font-semibold" style={{ color: "var(--ink)" }}>Registrieren</h2>

          {error && (
            <p className="rounded px-3 py-2 text-sm" style={{ background: "rgba(184,58,58,0.1)", color: "var(--fehler)" }}>{error}</p>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium" style={{ color: "var(--ink)" }}>Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border px-3 py-2 focus:outline-none"
              style={{ borderColor: "var(--warm-grau)", background: "var(--kreide)" }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "var(--terracotta)"; e.currentTarget.style.boxShadow = "0 0 0 1px var(--terracotta)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--warm-grau)"; e.currentTarget.style.boxShadow = "none"; }}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium" style={{ color: "var(--ink)" }}>E-Mail</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border px-3 py-2 focus:outline-none"
              style={{ borderColor: "var(--warm-grau)", background: "var(--kreide)" }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "var(--terracotta)"; e.currentTarget.style.boxShadow = "0 0 0 1px var(--terracotta)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--warm-grau)"; e.currentTarget.style.boxShadow = "none"; }}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium" style={{ color: "var(--ink)" }}>Passwort</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="w-full rounded-lg border px-3 py-2 focus:outline-none"
              style={{ borderColor: "var(--warm-grau)", background: "var(--kreide)" }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "var(--terracotta)"; e.currentTarget.style.boxShadow = "0 0 0 1px var(--terracotta)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--warm-grau)"; e.currentTarget.style.boxShadow = "none"; }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg px-4 py-2 font-medium text-white disabled:opacity-50"
            style={{ background: "var(--terracotta)" }}
          >
            {loading ? "Wird erstellt..." : "Account erstellen"}
          </button>

          <p className="text-center text-sm" style={{ color: "var(--warm-grau)" }}>
            Bereits registriert?{" "}
            <Link to="/login" style={{ color: "var(--terracotta)" }} className="hover:underline">
              Anmelden
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}

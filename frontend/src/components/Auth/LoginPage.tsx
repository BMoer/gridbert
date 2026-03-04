import { type FormEvent, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login } from "../../api/client";
import { useAuthStore } from "../../stores/authStore";

export function LoginPage() {
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
      const res = await login(email, password);
      setAuth(res.access_token, { user_id: res.user_id, name: res.name, email });
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gridbert-600">Gridbert</h1>
          <p className="mt-2 text-gray-500">Dein persönlicher Energie-Agent</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 rounded-xl bg-white p-6 shadow-md">
          <h2 className="text-lg font-semibold text-gray-800">Anmelden</h2>

          {error && (
            <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">E-Mail</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-gridbert-500 focus:outline-none focus:ring-1 focus:ring-gridbert-500"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Passwort</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-gridbert-500 focus:outline-none focus:ring-1 focus:ring-gridbert-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-gridbert-500 px-4 py-2 font-medium text-white hover:bg-gridbert-600 disabled:opacity-50"
          >
            {loading ? "Wird angemeldet..." : "Anmelden"}
          </button>

          <p className="text-center text-sm text-gray-500">
            Noch kein Konto?{" "}
            <Link to="/register" className="text-gridbert-600 hover:underline">
              Registrieren
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/axios";

export default function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("demo@alemx.com");
  const [pass,  setPass]  = useState("demo123");
  const [err,   setErr]   = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      const body = new URLSearchParams({
        grant_type: "password",
        username: email,
        password: pass,
      });
      const { data } = await api.post("/login", body);
      localStorage.setItem("token", data.access_token);
      nav("/");
    } catch {
      setErr("Invalid credentials");
    }
  };

  return (
    <div className="login-page">
      {/* “slide” reutiliza la misma clase del dashboard */}
      <div className="slide" style={{ maxWidth: 420 }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 32, textAlign:"center", color:"#4f46e5" }}>
          Ad Dashboard
        </h1>

        <form onSubmit={submit}>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
          />

          <input
            type="password"
            value={pass}
            onChange={(e) => setPass(e.target.value)}
            placeholder="Password"
            required
          />

          {err && (
            <p style={{ color: "#dc2626", marginBottom: 12 }}>{err}</p>
          )}

          <button className="btn" style={{ width: "100%" }}>
            Log In
          </button>
        </form>
      </div>
    </div>
  );
}

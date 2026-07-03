// Login.jsx — Babylon Web App UI Kit · Cold Collapse v8
// Spire-primary CTA, cooled substrate gradient, JetBrains Mono labels

const LoginPage = ({ onLogin }) => {
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState(null);
  const [submitting, setSubmitting] = React.useState(false);

  function handleSubmit(e) {
    e.preventDefault();
    if (!username || !password) { setError("Please enter username and password"); return; }
    setSubmitting(true); setError(null);
    setTimeout(() => {
      setSubmitting(false);
      if (password === "wrong") setError("Login failed — invalid credentials");
      else onLogin({ username, is_authenticated: true });
    }, 700);
  }

  const inputStyle = {
    background: "var(--void)", border: "1px solid var(--wet-steel)", borderRadius: 4,
    padding: "11px 14px", fontSize: 13, color: "var(--bone)", outline: "none",
    fontFamily: "var(--font-sans)", transition: "border-color .15s, box-shadow .15s"
  };

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "radial-gradient(ellipse at center, #0d1016 0%, #06070b 70%)",
      fontFamily: "var(--font-sans)", position: "relative", overflow: "hidden"
    }}>
      {/* Scanlines */}
      <div style={{ position: "absolute", inset: 0, background: "repeating-linear-gradient(0deg, rgba(0,0,0,.18) 0, rgba(0,0,0,.18) 1px, transparent 1px, transparent 4px)", pointerEvents: "none" }}/>

      <div style={{
        width: "100%", maxWidth: 400, borderRadius: 8,
        border: "1px solid var(--wet-steel)", background: "var(--concrete)",
        padding: "44px 44px 32px", textAlign: "center", position: "relative",
        boxShadow: "0 0 32px rgba(77,217,230,.06), 0 8px 32px rgba(0,0,0,.6)"
      }}>
        {/* Crosshair corners */}
        {["tl","tr","bl","br"].map(c => (
          <span key={c} style={{
            position: "absolute", width: 12, height: 12, borderColor: "var(--laser)", borderStyle: "solid", opacity: .5,
            top: c.startsWith("t") ? 8 : "auto", bottom: c.startsWith("b") ? 8 : "auto",
            left: c.endsWith("l") ? 8 : "auto", right: c.endsWith("r") ? 8 : "auto",
            borderWidth: c === "tl" ? "1px 0 0 1px" : c === "tr" ? "1px 1px 0 0" : c === "bl" ? "0 0 1px 1px" : "0 1px 1px 0"
          }}/>
        ))}

        <h1 style={{
          fontFamily: "var(--font-sans)", fontSize: 32, fontWeight: 700,
          color: "var(--bone)", letterSpacing: "0.32em", textTransform: "uppercase",
          marginBottom: 6
        }}>BAB<span style={{color:"var(--spire)",textShadow:"0 0 16px rgba(77,217,230,.5)"}}>Y</span>LON</h1>
        <p style={{
          fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.28em", textTransform: "uppercase",
          color: "var(--fog)", marginBottom: 28
        }}>The Fall of America</p>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <input
            type="text" placeholder="Username" value={username}
            onChange={e => setUsername(e.target.value)}
            style={inputStyle}
            onFocus={e => { e.target.style.borderColor="var(--spire)"; e.target.style.boxShadow="0 0 0 3px rgba(77,217,230,.1)"; }}
            onBlur={e => { e.target.style.borderColor="var(--wet-steel)"; e.target.style.boxShadow="none"; }}
          />
          <input
            type="password" placeholder="Password" value={password}
            onChange={e => setPassword(e.target.value)}
            style={inputStyle}
            onFocus={e => { e.target.style.borderColor="var(--spire)"; e.target.style.boxShadow="0 0 0 3px rgba(77,217,230,.1)"; }}
            onBlur={e => { e.target.style.borderColor="var(--wet-steel)"; e.target.style.boxShadow="none"; }}
          />
          {error && <p style={{ color: "var(--laser)", fontFamily: "var(--font-mono)", fontSize: 11, margin: 0, letterSpacing: ".05em" }}>✕ {error}</p>}
          <button type="submit" disabled={submitting} style={{
            marginTop: 8, background: submitting ? "rgba(77,217,230,.4)" : "var(--spire)",
            color: "var(--void)", border: "none", borderRadius: 4, padding: "12px",
            fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, letterSpacing: "0.18em", textTransform: "uppercase",
            cursor: submitting ? "not-allowed" : "pointer",
            boxShadow: submitting ? "none" : "0 0 16px rgba(77,217,230,.25)",
            transition: "filter .15s, box-shadow .15s"
          }}
            onMouseOver={e => !submitting && (e.target.style.filter="brightness(1.1)", e.target.style.boxShadow="0 0 24px rgba(77,217,230,.4)")}
            onMouseOut={e => (e.target.style.filter="", e.target.style.boxShadow=submitting?"none":"0 0 16px rgba(77,217,230,.25)")}
          >
            {submitting ? "Authenticating..." : "Log In"}
          </button>
        </form>
        <p style={{ marginTop: 18, fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--shroud)", letterSpacing: ".1em" }}>
          DEMO · ANY USER + ANY PASS (EXCEPT "WRONG")
        </p>
      </div>
    </div>
  );
};

Object.assign(window, { LoginPage });

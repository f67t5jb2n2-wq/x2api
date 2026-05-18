export default function HomePage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "2rem",
      }}
    >
      <section
        style={{
          width: "min(760px, 100%)",
          border: "1px solid var(--border)",
          borderRadius: "28px",
          padding: "2rem",
          background: "var(--card)",
          backdropFilter: "blur(14px)",
          boxShadow: "0 24px 80px rgba(31, 41, 55, 0.12)",
        }}
      >
        <p
          style={{
            margin: 0,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            fontSize: "0.8rem",
            color: "var(--accent)",
          }}
        >
          x2ding
        </p>
        <h1 style={{ marginBottom: "0.75rem", fontSize: "clamp(2rem, 6vw, 4rem)" }}>
          RSS subscriptions for X monitors.
        </h1>
        <p style={{ fontSize: "1.05rem", lineHeight: 1.6, maxWidth: "56ch" }}>
          Use an API key to manage targets, then consume a dedicated RSS feed token from your client.
        </p>
      </section>
    </main>
  );
}

import Link from "next/link";

export default function NotFound() {
  return (
    <main className="notFoundPage">
      <section className="notFoundPanel">
        <div className="notFoundEyebrow">ProductAI</div>
        <h1 className="notFoundTitle">Page not found</h1>
        <p className="notFoundCopy">
          The page you tried to open does not exist or may have been moved.
        </p>
        <div className="notFoundActions">
          <Link className="notFoundPrimaryAction" href="/">
            Back to chat
          </Link>
          <Link className="notFoundSecondaryAction" href="/dashboard">
            Open dashboard
          </Link>
        </div>
      </section>
    </main>
  );
}

import type { ReactNode } from "react";
import { Link } from "react-router-dom";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="app-shell">
      <header className="top-bar">
        <div>
          <Link to="/" className="brand">
            ETF Decision Support System
          </Link>
          <p className="subtitle">Vietnamese ETF Analysis & SMART Decision Support</p>
        </div>
      </header>

      <main className="main-content">{children}</main>

      <footer className="footer-note">
        This system provides decision-support analysis for educational purposes and does
        not constitute financial advice.
      </footer>
    </div>
  );
}

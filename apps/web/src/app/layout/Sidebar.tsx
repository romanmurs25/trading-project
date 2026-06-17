import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/instruments", label: "Instruments" },
  { to: "/data-quality", label: "Data Quality" },
  { to: "/sessions", label: "Sessions" },
  { to: "/futures-chain", label: "Futures Chain" },
  { to: "/continuous", label: "Continuous" },
  { to: "/research", label: "Research" },
  { to: "/settings", label: "Settings" },
];

export function Sidebar() {
  return (
    <aside className="sidebar" aria-label="Main navigation">
      <div className="sidebar-brand">Trading Research</div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end} className="nav-link">
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

import { NavLink } from "react-router-dom";

import { ru } from "../../i18n/ru";

const navItems = [
  { to: "/", label: ru.nav.dashboard, end: true },
  { to: "/instruments", label: ru.nav.instruments },
  { to: "/data-quality", label: ru.nav.dataQuality },
  { to: "/live-data", label: ru.nav.liveData },
  { to: "/sessions", label: ru.nav.sessions },
  { to: "/futures-chain", label: ru.nav.futuresChain },
  { to: "/continuous", label: ru.nav.continuous },
  { to: "/research", label: ru.nav.research },
  { to: "/settings", label: ru.nav.settings },
];

export function Sidebar() {
  return (
    <aside className="sidebar" aria-label="Основная навигация">
      <div className="sidebar-brand">{ru.brand}</div>
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

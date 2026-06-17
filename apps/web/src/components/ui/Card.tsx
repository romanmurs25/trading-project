import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  title?: string;
  action?: ReactNode;
}

export function Card({ children, title, action }: CardProps) {
  return (
    <section className="card">
      {(title || action) && (
        <div className="card-header">
          {title ? <h2>{title}</h2> : <span />}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

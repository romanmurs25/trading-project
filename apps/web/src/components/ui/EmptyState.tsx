import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  message: string;
  children?: ReactNode;
}

export function EmptyState({ title, message, children }: EmptyStateProps) {
  return (
    <div className="state-box">
      <h3>{title}</h3>
      <p>{message}</p>
      {children}
    </div>
  );
}

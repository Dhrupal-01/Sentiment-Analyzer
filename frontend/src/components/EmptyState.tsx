import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionText?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No data available',
  description = 'There are no records matching your current filter criteria.',
  actionText,
  onAction,
  icon,
}) => {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon || <Inbox size={48} />}</div>
      <h3>{title}</h3>
      <p>{description}</p>
      {actionText && onAction && (
        <button type="button" onClick={onAction} className="btn btn-secondary">
          {actionText}
        </button>
      )}
    </div>
  );
};

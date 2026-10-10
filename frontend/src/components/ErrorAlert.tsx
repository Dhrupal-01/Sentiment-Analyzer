import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorAlertProps {
  message: string;
  onRetry?: () => void;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({ message, onRetry }) => {
  return (
    <div className="alert-error" role="alert">
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <AlertCircle size={18} style={{ flexShrink: 0 }} />
        <span style={{ fontSize: '13px' }}>{message}</span>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="btn btn-secondary"
          style={{ padding: '4px 10px', fontSize: '12px' }}
        >
          <RefreshCw size={12} />
          Retry
        </button>
      )}
    </div>
  );
};

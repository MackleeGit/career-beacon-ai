// src/components/Toast.jsx
import { useEffect } from 'react';

/**
 * A slide-up confirmation toast.
 * Props:
 *   message    – string shown in the toast
 *   onConfirm  – called when user clicks the confirm button
 *   onCancel   – called when user clicks Cancel or the backdrop
 *   confirmLabel – text for the confirm button (default: "Yes, log out")
 *   confirmDanger – if true, confirm button is styled red (default: true)
 */
export default function Toast({
  message,
  onConfirm,
  onCancel,
  confirmLabel = 'Yes, log out',
  confirmDanger = true,
}) {
  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onCancel(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onCancel]);

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onCancel}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 999,
          background: 'rgba(0,0,0,0.45)',
          backdropFilter: 'blur(2px)',
          animation: 'fadeIn 0.15s ease',
        }}
      />

      {/* Toast card */}
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="toast-msg"
        style={{
          position: 'fixed',
          bottom: '32px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 1000,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-lg)',
          padding: '20px 24px',
          minWidth: '300px',
          maxWidth: '90vw',
          boxShadow: '0 8px 40px rgba(0,0,0,0.4)',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          animation: 'slideUp 0.2s cubic-bezier(0.34,1.56,0.64,1)',
        }}
      >
        <p id="toast-msg" style={{ margin: 0, fontSize: '0.95rem', color: 'var(--text-primary)', fontWeight: 500 }}>
          {message}
        </p>
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button
            id="toast-cancel-btn"
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            id="toast-confirm-btn"
            type="button"
            className="btn btn--sm"
            onClick={onConfirm}
            style={{
              background: confirmDanger ? 'hsl(0,72%,50%)' : 'var(--accent)',
              color: '#fff',
              border: 'none',
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translateX(-50%) translateY(20px); }
          to   { opacity: 1; transform: translateX(-50%) translateY(0);    }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
      `}</style>
    </>
  );
}

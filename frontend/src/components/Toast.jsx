// src/components/Toast.jsx
import { useEffect } from 'react';
import { X, CheckCircle2, AlertCircle, Info } from './Icons';

/**
 * Universal Toast & Confirmation Dialog component.
 *
 * Mode 1: Notification Toast (default when onCancel is omitted)
 *   Renders a lightweight, non-blocking floating pill/snackbar with auto-dismiss.
 *
 * Mode 2: Confirmation Dialog (when onCancel or isConfirmation is provided)
 *   Renders a focused modal confirmation box with Cancel + Confirm actions.
 */
export default function Toast({
  message,
  onConfirm,
  onCancel,
  onClose,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  confirmDanger = false,
  type = 'info', // 'success' | 'error' | 'info'
  autoCloseMs = 4000,
}) {
  const isConfirmDialog = Boolean(onCancel);
  const handleDismiss = onClose || onCancel || onConfirm;

  useEffect(() => {
    if (!isConfirmDialog && autoCloseMs && handleDismiss) {
      const timer = setTimeout(() => {
        handleDismiss();
      }, autoCloseMs);
      return () => clearTimeout(timer);
    }
  }, [isConfirmDialog, autoCloseMs, handleDismiss]);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape' && handleDismiss) handleDismiss();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [handleDismiss]);

  // Mode 2: Confirmation Modal Dialog
  if (isConfirmDialog) {
    return (
      <>
        <div
          onClick={handleDismiss}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 999,
            background: 'var(--backdrop)',
            backdropFilter: 'blur(2px)',
          }}
        />

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
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--r-lg)',
            padding: '20px 24px',
            minWidth: '320px',
            maxWidth: '460px',
            width: 'calc(100vw - 32px)',
            boxShadow: 'var(--shadow-xl)',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          <p
            id="toast-msg"
            style={{
              margin: 0,
              fontSize: '0.92rem',
              color: 'var(--text-primary)',
              fontWeight: 500,
              lineHeight: 1.5,
            }}
          >
            {message}
          </p>
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
            <button
              id="toast-cancel-btn"
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={onCancel}
            >
              {cancelLabel}
            </button>
            <button
              id="toast-confirm-btn"
              type="button"
              className={`btn btn--sm ${confirmDanger ? 'btn--danger' : 'btn--primary'}`}
              onClick={onConfirm}
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </>
    );
  }

  // Mode 1: Notification Toast / Snackbar (floating, non-blocking)
  return (
    <div
      role="status"
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 1000,
        background: 'var(--surface-elevated, var(--surface))',
        color: 'var(--text-primary)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--r-md)',
        padding: '12px 18px',
        boxShadow: 'var(--shadow-lg)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        maxWidth: 'min(420px, calc(100vw - 32px))',
        animation: 'slideUp 0.2s ease-out',
      }}
    >
      {type === 'success' ? (
        <CheckCircle2 size={18} style={{ color: 'var(--status-success)', flexShrink: 0 }} />
      ) : type === 'error' ? (
        <AlertCircle size={18} style={{ color: 'var(--status-danger)', flexShrink: 0 }} />
      ) : (
        <Info size={18} style={{ color: 'var(--accent)', flexShrink: 0 }} />
      )}
      <span style={{ fontSize: '0.86rem', lineHeight: 1.4, flex: 1 }}>{message}</span>
      <button
        type="button"
        className="btn btn--ghost btn--xs"
        onClick={handleDismiss}
        style={{ padding: '4px', color: 'var(--text-muted)' }}
        aria-label="Dismiss notification"
      >
        <X size={14} />
      </button>
    </div>
  );
}

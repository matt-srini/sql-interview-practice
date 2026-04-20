export default function ToastViewport({ toasts = [], onDismiss }) {
  if (!toasts.length) return null;

  return (
    <div className="toast-viewport" role="status" aria-live="polite" aria-label="Notifications">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast-item toast-item-${toast.tone}`}>
          <div className="toast-item-body">
            {toast.title ? <p className="toast-item-title">{toast.title}</p> : null}
            {toast.message ? <p className="toast-item-message">{toast.message}</p> : null}
          </div>
          <button
            className="toast-item-dismiss"
            onClick={() => onDismiss?.(toast.id)}
            aria-label="Dismiss notification"
            title="Dismiss"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

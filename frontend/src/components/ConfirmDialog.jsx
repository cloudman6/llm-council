import React, { useEffect } from 'react';
import './ConfirmDialog.css';

export default function ConfirmDialog({
  isOpen,
  title = "Confirm Delete",
  message = "Are you sure you want to delete this conversation? This action cannot be undone.",
  onConfirm,
  onCancel,
  confirmText = "Delete",
  cancelText = "Cancel"
}) {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCancel();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        onConfirm();
      }
    };

    // Add event listener when dialog opens
    document.addEventListener('keydown', handleKeyDown);

    // Clean up event listener when dialog closes or component unmounts
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onCancel();
    }
  };

  return (
    <div className="confirm-dialog-overlay" onClick={handleBackdropClick}>
      <div className="confirm-dialog">
        <div className="confirm-dialog-header">
          <h3>{title}</h3>
        </div>

        <div className="confirm-dialog-body">
          <p>{message}</p>
        </div>

        <div className="confirm-dialog-footer">
          <button
            className="confirm-dialog-btn confirm-dialog-btn-cancel"
            onClick={onCancel}
          >
            {cancelText}
          </button>
          <button
            className="confirm-dialog-btn confirm-dialog-btn-confirm"
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
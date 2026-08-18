import { useEffect } from "react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  loading?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  loading = false,
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !loading) onCancel();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [loading, onCancel, open]);

  if (!open) return null;
  return (
    <div
      aria-modal="true"
      className="fixed inset-0 z-50 grid place-items-center bg-slate-950/80 px-5 backdrop-blur-sm"
      role="dialog"
    >
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-6 shadow-2xl shadow-black/50">
        <h2 className="text-xl font-black text-white">{title}</h2>
        <p className="mt-3 text-sm leading-6 text-slate-400">{description}</p>
        <div className="mt-7 flex justify-end gap-3">
          <button className="text-button" type="button" onClick={onCancel} disabled={loading}>
            Cancel
          </button>
          <button className="danger-button" type="button" onClick={onConfirm} disabled={loading}>
            {loading ? "Removing…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

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
      <div className="panel w-full max-w-md p-6 shadow-2xl shadow-black/50">
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-xl border border-red-400/15 bg-red-400/8 text-red-300">
            <AlertTriangle aria-hidden="true" size={19} />
          </span>
          <h2 className="text-xl font-black text-white">{title}</h2>
        </div>
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

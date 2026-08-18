interface BrandProps {
  compact?: boolean;
}

export function Brand({ compact = false }: BrandProps) {
  return (
    <div className="flex items-center gap-3">
      <div className="grid size-10 place-items-center rounded-xl bg-orange-500 text-lg font-black text-slate-950 shadow-lg shadow-orange-500/20">
        L
      </div>
      <div>
        <p className="text-lg font-bold tracking-tight text-white">LeetRank</p>
        {!compact && (
          <p className="text-xs font-medium tracking-wide text-slate-500">
            Practice together. Climb together.
          </p>
        )}
      </div>
    </div>
  );
}

interface BrandProps {
  compact?: boolean;
}

export function Brand({ compact = false }: BrandProps) {
  return (
    <div className="flex items-center gap-3">
      <div className="relative grid size-10 place-items-center overflow-hidden rounded-xl bg-gradient-to-br from-orange-400 to-orange-600 text-lg font-black text-slate-950 shadow-lg shadow-orange-500/20">
        <span className="relative z-10">L</span>
        <span className="absolute -bottom-2 -right-2 size-6 rounded-full border-4 border-slate-950/20" />
      </div>
      <div>
        <p className="text-lg font-black tracking-[-0.035em] text-white">LeetRank</p>
        {!compact && (
          <p className="text-xs font-semibold tracking-wide text-slate-500">
            Practice together. Climb together.
          </p>
        )}
      </div>
    </div>
  );
}

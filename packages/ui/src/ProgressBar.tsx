interface ProgressBarProps {
  progressPct: number;
  label?: string;
}

export function ProgressBar({ progressPct, label }: ProgressBarProps) {
  return (
    <div className="w-full">
      {label ? <p className="mb-1 text-sm text-gray-600">{label}</p> : null}
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          className="h-full rounded-full bg-brand-500 transition-all"
          style={{ width: `${Math.min(100, Math.max(0, progressPct))}%` }}
        />
      </div>
    </div>
  );
}

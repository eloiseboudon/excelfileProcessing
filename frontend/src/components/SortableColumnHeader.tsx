import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';

export interface SortConfig {
  column: string | null;
  direction: 'asc' | 'desc' | null;
}

interface SortableColumnHeaderProps {
  label: string;
  columnKey: string;
  currentSort: SortConfig;
  onSort: (column: string) => void;
  className?: string;
}

function SortableColumnHeader({ label, columnKey, currentSort, onSort, className }: SortableColumnHeaderProps) {
  const isActive = currentSort.column === columnKey;

  return (
    <button
      type="button"
      onClick={() => onSort(columnKey)}
      className={`inline-flex items-center gap-1 hover:text-[#B8860B] transition-colors ${className ?? ''}`}
    >
      <span>{label}</span>
      {isActive && currentSort.direction === 'asc' ? (
        <ArrowUp className="w-3.5 h-3.5 text-[#B8860B]" />
      ) : isActive && currentSort.direction === 'desc' ? (
        <ArrowDown className="w-3.5 h-3.5 text-[#B8860B]" />
      ) : (
        <ArrowUpDown className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
      )}
    </button>
  );
}

export default SortableColumnHeader;

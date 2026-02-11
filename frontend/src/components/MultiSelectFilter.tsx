import { useState, useRef, useEffect } from 'react';

interface MultiSelectFilterProps {
  options: string[];
  selected: string[];
  onChange: (values: string[]) => void;
}

function MultiSelectFilter({ options, selected, onChange }: MultiSelectFilterProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleOption = (opt: string, checked: boolean) => {
    if (checked) {
      onChange([...selected, opt]);
    } else {
      onChange(selected.filter((v) => v !== opt));
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full px-2 py-1 bg-[var(--color-bg-surface)] border border-[var(--color-border-strong)] rounded text-left overflow-hidden whitespace-nowrap text-ellipsis"
      >
        {selected.length ? selected.join(', ') : 'Tous'}
      </button>
      {open && (
        <div className="absolute z-10 mt-1 max-h-60 overflow-auto bg-[var(--color-bg-surface)] border border-[var(--color-border-strong)] rounded shadow-lg">
          {options.map((opt) => (
            <label key={opt} className="flex items-center space-x-2 px-2 py-1 hover:bg-[var(--color-bg-elevated)]">
              <input
                type="checkbox"
                checked={selected.includes(opt)}
                onChange={(e) => toggleOption(opt, e.target.checked)}
                className="rounded"
              />
              <span>{opt}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

export default MultiSelectFilter;

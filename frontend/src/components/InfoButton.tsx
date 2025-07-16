import { Info } from 'lucide-react';
import { useState } from 'react';

interface InfoButtonProps {
  text: string;
}

function InfoButton({ text }: InfoButtonProps) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-block ml-1 align-middle">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-zinc-400 hover:text-white"
      >
        <Info className="w-4 h-4" />
      </button>
      {open && (
        <div className="absolute left-5 top-0 z-10 w-60 text-xs bg-zinc-800 border border-zinc-600 rounded p-2">
          {text}
        </div>
      )}
    </span>
  );
}

export default InfoButton;

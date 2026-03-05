import { Sun, Moon } from 'lucide-react';
import { useTheme } from './ThemeProvider';

declare const __APP_VERSION__: string;

export default function Footer() {
  const { theme, toggleTheme } = useTheme();

  return (
    <footer className="border-t border-[#B8860B]/15 bg-[var(--color-bg-nav)] backdrop-blur-lg">
      <div className="flex items-center justify-between px-4 sm:px-6 h-10 text-xs text-[var(--color-text-muted)]">
        <span>&copy; {new Date().getFullYear()} AJT Pro &middot; v{__APP_VERSION__}</span>
        <button
          onClick={toggleTheme}
          className="flex items-center justify-center h-7 w-7 rounded-md bg-gold text-black transition-transform hover:scale-110"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
        </button>
      </div>
    </footer>
  );
}

import { getCurrentWeekYear } from '../utils/date';

function WeekToolbar() {
  return (
    <div className="mb-4">
      <div className="flex flex-col sm:flex-row sm:justify-between items-center gap-4">
        <div className="flex items-center gap-4">
          <span className="text-[var(--color-text-muted)]">Semaine en cours : {getCurrentWeekYear()}</span>
        </div>
      </div>
    </div>
  );
}

export default WeekToolbar;

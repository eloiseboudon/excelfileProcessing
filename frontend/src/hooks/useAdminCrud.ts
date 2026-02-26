import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { useNotification } from '../components/NotificationProvider';

interface UseAdminCrudOptions<T extends { id: number }> {
  fetchFn: () => Promise<T[]>;
  createFn: (payload: Record<string, unknown>) => Promise<unknown>;
  updateFn: (id: number, payload: Record<string, unknown>) => Promise<unknown>;
  deleteFn: (id: number) => Promise<unknown>;
  initialItem?: Omit<T, 'id'>;
  onFieldChange?: (item: T, field: string, value: string) => T;
  confirmDelete?: boolean;
  confirmDeleteMessage?: string;
  enabled?: boolean;
}

interface UseAdminCrudReturn<T extends { id: number }> {
  data: T[];
  setData: Dispatch<SetStateAction<T[]>>;
  handleChange: (id: number, field: string, value: string) => void;
  handleSave: (id: number) => Promise<void>;
  handleDelete: (id: number) => Promise<void>;
  handleAdd: () => void;
  reload: () => Promise<void>;
}

export function useAdminCrud<T extends { id: number }>(
  options: UseAdminCrudOptions<T>
): UseAdminCrudReturn<T> {
  const {
    createFn,
    updateFn,
    deleteFn,
    initialItem,
    onFieldChange,
    confirmDelete = false,
    confirmDeleteMessage = 'Supprimer cet élément ?',
    enabled = true,
  } = options;

  const [data, setData] = useState<T[]>([]);
  const notify = useNotification();

  const fetchFnRef = useRef(options.fetchFn);
  useEffect(() => {
    fetchFnRef.current = options.fetchFn;
  });

  const load = useCallback(async () => {
    try {
      setData(await fetchFnRef.current());
    } catch {
      setData([]);
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      load();
    }
  }, [enabled, options.fetchFn, load]);

  const handleChange = useCallback(
    (id: number, field: string, value: string) => {
      setData((prev) =>
        prev.map((item) => {
          if (item.id !== id) return item;
          const updated = { ...item, [field]: value };
          return onFieldChange ? onFieldChange(updated, field, value) : updated;
        })
      );
    },
    [onFieldChange]
  );

  const handleSave = useCallback(
    async (id: number) => {
      const item = data.find((d) => d.id === id);
      if (!item) return;
      const payload: Record<string, unknown> = { ...item };
      delete payload.id;
      try {
        if (id < 0) {
          await createFn(payload);
          notify('Entrée créée', 'success');
        } else {
          await updateFn(id, payload);
          notify('Entrée mise à jour', 'success');
        }
        await load();
      } catch (err) {
        notify(err instanceof Error ? err.message : 'Erreur de sauvegarde', 'error');
      }
    },
    [data, createFn, updateFn, load, notify]
  );

  const handleDelete = useCallback(
    async (id: number) => {
      if (id < 0) {
        setData((prev) => prev.filter((i) => i.id !== id));
        return;
      }
      if (confirmDelete && !window.confirm(confirmDeleteMessage)) return;
      try {
        await deleteFn(id);
        notify('Entrée supprimée', 'success');
        await load();
      } catch (err) {
        notify(err instanceof Error ? err.message : 'Erreur de suppression', 'error');
      }
    },
    [confirmDelete, confirmDeleteMessage, deleteFn, load, notify]
  );

  const handleAdd = useCallback(() => {
    const newItem = {
      id: Date.now() * -1,
      ...(initialItem ??
        (data.length > 0
          ? Object.fromEntries(
              Object.keys(data[0])
                .filter((k) => k !== 'id')
                .map((k) => [k, ''])
            )
          : {})),
    } as T;
    setData((prev) => [...prev, newItem]);
  }, [data, initialItem]);

  return { data, setData, handleChange, handleSave, handleDelete, handleAdd, reload: load };
}

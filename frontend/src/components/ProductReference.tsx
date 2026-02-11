import { useEffect, useState } from 'react';
import {
  fetchProducts,
  fetchBrands,
  fetchColors,
  fetchMemoryOptions,
  fetchDeviceTypes,
  bulkUpdateProducts,
  createProduct,
  fetchRAMOptions,
  fetchNormeOptions,
  deleteProduct,
  bulkDeleteProducts,
} from '../api';
import { useNotification } from './NotificationProvider';
import ProductReferenceForm from './ProductReferenceForm';
import ProductReferenceTable from './ProductReferenceTable';

export interface ProductItem {
  id: number;
  ean: string | null;
  model: string;
  description: string;
  brand_id: number | null;
  brand: string | null;
  memory_id: number | null;
  memory: string | null;
  color_id: number | null;
  color: string | null;
  type_id: number | null;
  type: string | null;
  ram_id: number | null;
  ram: string | null;
  norme_id: number | null;
  norme: string | null;
}

export interface Column {
  key: string;
  label: string;
}

function ProductReference() {
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [edited, setEdited] = useState<Record<number, Partial<ProductItem>>>({});
  const [filters, setFilters] = useState<Record<string, string | string[]>>({});
  const [visibleColumns, setVisibleColumns] = useState<string[]>([]);
  const [showColumnMenu, setShowColumnMenu] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [brands, setBrands] = useState<any[]>([]);
  const [colors, setColors] = useState<any[]>([]);
  const [memories, setMemories] = useState<any[]>([]);
  const [types, setTypes] = useState<any[]>([]);
  const [rams, setRams] = useState<any[]>([]);
  const [normes, setNormes] = useState<any[]>([]);
  const [selectedProducts, setSelectedProducts] = useState<number[]>([]);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const notify = useNotification();
  const [brandOptions, setBrandOptions] = useState<string[]>([]);
  const [colorOptions, setColorOptions] = useState<string[]>([]);
  const [memoryOptions, setMemoryOptions] = useState<string[]>([]);
  const [typeOptions, setTypeOptions] = useState<string[]>([]);
  const [ramOptions, setRamOptions] = useState<string[]>([]);
  const [normeOptions, setNormeOptions] = useState<string[]>([]);
  const selectedCount = selectedProducts.length;

  const columns: Column[] = [
    { key: 'id', label: 'ID' },
    { key: 'model', label: 'Modèle' },
    { key: 'description', label: 'Description' },
    { key: 'brand', label: 'Marque' },
    { key: 'memory', label: 'Mémoire' },
    { key: 'color', label: 'Couleur' },
    { key: 'type', label: 'Type' },
    { key: 'ram', label: 'RAM' },
    { key: 'norme', label: 'Norme' },
    { key: 'ean', label: 'EAN' },
  ];

  useEffect(() => {
    fetchProducts()
      .then((res) => {
        setProducts(res as ProductItem[]);
        setVisibleColumns(columns.map((c) => c.key));
      })
      .catch(() => setProducts([]));

    Promise.all([
      fetchBrands(),
      fetchColors(),
      fetchMemoryOptions(),
      fetchDeviceTypes(),
      fetchRAMOptions(),
      fetchNormeOptions(),
    ])
      .then(([b, c, m, t, r, n]) => {
        setBrands(b as any[]);
        setColors(c as any[]);
        setMemories(m as any[]);
        setTypes(t as any[]);
        setRams(r as any[]);
        setNormes(n as any[]);
        setBrandOptions((b as any[]).map((br) => br.brand));
        setColorOptions((c as any[]).map((co) => co.color));
        setMemoryOptions((m as any[]).map((me) => me.memory));
        setTypeOptions((t as any[]).map((ty) => ty.type));
        setRamOptions((r as any[]).map((ra) => ra.ram));
        setNormeOptions((n as any[]).map((no) => no.norme));
      })
      .catch(() => {
        setBrands([]);
        setColors([]);
        setMemories([]);
        setTypes([]);
        setRams([]);
        setNormes([]);
        setBrandOptions([]);
        setColorOptions([]);
        setMemoryOptions([]);
        setTypeOptions([]);
        setRamOptions([]);
        setNormeOptions([]);
      });
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [filters, rowsPerPage]);

  useEffect(() => {
    setSelectedProducts((prev) =>
      prev.filter((id) => products.some((product) => product.id === id))
    );
  }, [products]);

  const filteredData = products.filter((row) =>
    columns.every((col) => {
      const filterValue = filters[col.key];
      if (!filterValue || (Array.isArray(filterValue) && filterValue.length === 0))
        return true;
      const value = (row as any)[col.key];
      if (['brand', 'memory', 'color', 'type', 'ram', 'norme'].includes(col.key)) {
        return (filterValue as string[]).includes(String(value ?? ''));
      }
      return String(value ?? '')
        .toLowerCase()
        .includes((filterValue as string).toLowerCase());
    })
  );

  const totalPages = Math.max(1, Math.ceil(filteredData.length / rowsPerPage));
  const paginatedData = filteredData.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [totalPages, currentPage]);

  const toggleColumn = (key: string) => {
    setVisibleColumns((prev) =>
      prev.includes(key) ? prev.filter((c) => c !== key) : [...prev, key]
    );
  };

  const handleChange = (
    id: number,
    field: keyof ProductItem,
    value: string | number | null
  ) => {
    setProducts((prev) =>
      prev.map((p) => (p.id === id ? { ...p, [field]: value } : p))
    );
    setEdited((prev) => ({
      ...prev,
      [id]: { ...(prev[id] || {}), [field]: value },
    }));
  };

  const handleAdd = () => {
    const id = Date.now() * -1;
    setProducts((prev) => [
      ...prev,
      {
        id,
        ean: '',
        model: '',
        description: '',
        brand_id: null,
        brand: null,
        memory_id: null,
        memory: null,
        color_id: null,
        color: null,
        type_id: null,
        type: null,
        ram_id: null,
        ram: null,
        norme_id: null,
        norme: null,
      },
    ]);
    setEdited((prev) => ({
      ...prev,
      [id]: {
        ean: '',
        model: '',
        description: '',
        brand_id: null,
        memory_id: null,
        color_id: null,
        type_id: null,
        ram_id: null,
        norme_id: null,
      },
    }));
  };

  const removeEditedEntries = (ids: number[]) => {
    if (!ids.length) return;
    setEdited((prev) => {
      const updated = { ...prev };
      ids.forEach((pid) => {
        delete updated[pid];
      });
      return updated;
    });
  };

  const toggleSelectProduct = (id: number) => {
    setSelectedProducts((prev) =>
      prev.includes(id) ? prev.filter((pid) => pid !== id) : [...prev, id]
    );
  };

  const handleDelete = async (id: number) => {
    if (id < 0) {
      setProducts((prev) => prev.filter((product) => product.id !== id));
      removeEditedEntries([id]);
      setSelectedProducts((prev) => prev.filter((pid) => pid !== id));
      notify('Produit supprimé', 'success');
      return;
    }
    if (!window.confirm('Supprimer ce produit ?')) return;
    try {
      await deleteProduct(id);
      setProducts((prev) => prev.filter((product) => product.id !== id));
      removeEditedEntries([id]);
      setSelectedProducts((prev) => prev.filter((pid) => pid !== id));
      notify('Produit supprimé', 'success');
    } catch {
      notify('Erreur lors de la suppression', 'error');
    }
  };

  const handleBulkDelete = async () => {
    if (!selectedCount || isBulkDeleting) return;
    if (
      !window.confirm(
        `Confirmez-vous la suppression de ${selectedCount} produit(s) ?`
      )
    )
      return;

    setIsBulkDeleting(true);
    const localIds = selectedProducts.filter((id) => id < 0);
    const remoteIds = selectedProducts.filter((id) => id > 0);
    let deletedRemoteIds: number[] = [];

    if (remoteIds.length) {
      try {
        const response = await bulkDeleteProducts(remoteIds);
        deletedRemoteIds = Array.isArray(response?.deleted)
          ? (response.deleted as number[])
          : remoteIds;
      } catch {
        notify('Erreur lors de la suppression', 'error');
      }
    }

    const idsToRemove = Array.from(
      new Set<number>([...localIds, ...deletedRemoteIds])
    );

    if (idsToRemove.length) {
      setProducts((prev) =>
        prev.filter((product) => !idsToRemove.includes(product.id))
      );
      removeEditedEntries(idsToRemove);
      setSelectedProducts((prev) =>
        prev.filter((pid) => !idsToRemove.includes(pid))
      );
      notify(`${idsToRemove.length} produit(s) supprimé(s)`, 'success');
    }

    setIsBulkDeleting(false);
  };

  const saveAll = async () => {
    const toCreate: any[] = [];
    const toUpdate: any[] = [];
    Object.entries(edited).forEach(([id, changes]) => {
      const numId = Number(id);
      if (numId < 0) {
        const { brand, memory, color, type, ram, norme, ...rest } = {
          ...(changes as any),
        };
        toCreate.push(rest);
      } else {
        toUpdate.push({ id: numId, ...(changes as any) });
      }
    });
    if (!toCreate.length && !toUpdate.length) return;
    try {
      await Promise.all(toCreate.map((p) => createProduct(p)));
      if (toCreate.length) {
        notify(`${toCreate.length} produit(s) créés`, 'success');
      }
      if (toUpdate.length) {
        await bulkUpdateProducts(toUpdate);
        notify(`${toUpdate.length} produit(s) mis à jour`, 'success');
      }
      setEdited({});
      const res = await fetchProducts();
      setProducts(res as ProductItem[]);
    } catch {
      notify("Erreur lors de l'enregistrement", 'error');
    }
  };

  return (
    <div>
      <ProductReferenceForm
        columns={columns}
        visibleColumns={visibleColumns}
        showColumnMenu={showColumnMenu}
        onToggleColumnMenu={() => setShowColumnMenu((s) => !s)}
        onToggleColumn={toggleColumn}
        onAdd={handleAdd}
        onSave={saveAll}
        onBulkDelete={handleBulkDelete}
        selectedCount={selectedCount}
        isBulkDeleting={isBulkDeleting}
        hasEdits={Object.keys(edited).length > 0}
      />
      <ProductReferenceTable
        columns={columns}
        visibleColumns={visibleColumns}
        paginatedData={paginatedData}
        filters={filters}
        onFilterChange={setFilters}
        filterOptions={{
          brandOptions,
          colorOptions,
          memoryOptions,
          typeOptions,
          ramOptions,
          normeOptions,
        }}
        referenceData={{
          brands,
          colors,
          memories,
          types,
          rams,
          normes,
        }}
        selectedProducts={selectedProducts}
        onToggleSelectProduct={toggleSelectProduct}
        onChange={handleChange}
        onDelete={handleDelete}
        currentPage={currentPage}
        totalPages={totalPages}
        rowsPerPage={rowsPerPage}
        onPageChange={setCurrentPage}
        onRowsPerPageChange={setRowsPerPage}
      />
    </div>
  );
}

export default ProductReference;

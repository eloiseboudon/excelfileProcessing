import { useCallback, useEffect, useMemo, useState } from 'react';
import type { SortConfig } from './SortableColumnHeader';
import { fetchProducts } from '../api';
import { useProductAttributeOptions } from '../hooks/useProductAttributeOptions';
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
  const [filters, setFilters] = useState<Record<string, string | string[]>>({});
  const [visibleColumns, setVisibleColumns] = useState<string[]>([]);
  const [showColumnMenu, setShowColumnMenu] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const {
    brandNames: brandOptions,
    colorNames: colorOptions,
    memoryNames: memoryOptions,
    typeNames: typeOptions,
    ramNames: ramOptions,
    normeNames: normeOptions,
  } = useProductAttributeOptions();

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
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [filters, rowsPerPage]);

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

  const [sortConfig, setSortConfig] = useState<SortConfig>({ column: null, direction: null });

  const handleSort = useCallback((column: string) => {
    setSortConfig((prev) => {
      if (prev.column !== column) return { column, direction: 'asc' };
      if (prev.direction === 'asc') return { column, direction: 'desc' };
      return { column: null, direction: null };
    });
  }, []);

  const sortedData = useMemo(() => {
    if (!sortConfig.column || !sortConfig.direction) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aVal: any = (a as any)[sortConfig.column!];
      const bVal: any = (b as any)[sortConfig.column!];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === 'number' && typeof bVal === 'number')
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
      return sortConfig.direction === 'asc'
        ? String(aVal).localeCompare(String(bVal), 'fr')
        : String(bVal).localeCompare(String(aVal), 'fr');
    });
  }, [filteredData, sortConfig]);

  const totalPages = Math.max(1, Math.ceil(sortedData.length / rowsPerPage));
  const paginatedData = sortedData.slice(
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

  return (
    <div>
      <ProductReferenceForm
        columns={columns}
        visibleColumns={visibleColumns}
        showColumnMenu={showColumnMenu}
        onToggleColumnMenu={() => setShowColumnMenu((s) => !s)}
        onToggleColumn={toggleColumn}
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
        filteredCount={filteredData.length}
        currentPage={currentPage}
        totalPages={totalPages}
        rowsPerPage={rowsPerPage}
        onPageChange={setCurrentPage}
        onRowsPerPageChange={setRowsPerPage}
        sortConfig={sortConfig}
        onSort={handleSort}
      />
    </div>
  );
}

export default ProductReference;

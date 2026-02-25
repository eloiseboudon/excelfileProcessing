import { useEffect, useState } from 'react';
import {
  fetchBrands,
  fetchColors,
  fetchDeviceTypes,
  fetchMemoryOptions,
  fetchNormeOptions,
  fetchRAMOptions,
} from '../api';

interface ProductAttributeOptions {
  brands: any[];
  colors: any[];
  memories: any[];
  types: any[];
  rams: any[];
  normes: any[];
  brandNames: string[];
  colorNames: string[];
  memoryNames: string[];
  typeNames: string[];
  ramNames: string[];
  normeNames: string[];
}

export function useProductAttributeOptions(): ProductAttributeOptions {
  const [brands, setBrands] = useState<any[]>([]);
  const [colors, setColors] = useState<any[]>([]);
  const [memories, setMemories] = useState<any[]>([]);
  const [types, setTypes] = useState<any[]>([]);
  const [rams, setRams] = useState<any[]>([]);
  const [normes, setNormes] = useState<any[]>([]);

  useEffect(() => {
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
      })
      .catch(() => {
        setBrands([]);
        setColors([]);
        setMemories([]);
        setTypes([]);
        setRams([]);
        setNormes([]);
      });
  }, []);

  return {
    brands,
    colors,
    memories,
    types,
    rams,
    normes,
    brandNames: brands.map((b) => b.brand),
    colorNames: colors.map((c) => c.color),
    memoryNames: memories.map((m) => m.memory),
    typeNames: types.map((t) => t.type),
    ramNames: rams.map((r) => r.ram),
    normeNames: normes.map((n) => n.norme),
  };
}

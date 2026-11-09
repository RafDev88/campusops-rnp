import type { LocationQuery } from "vue-router";
/** One definition for links, saved searches and visible publication criteria. */
export const publicationKeys = [
  "q",
  "institution_id",
  "topic",
  "author",
  "author_id",
  "year",
  "year_from",
  "year_to",
  "oa",
  "source",
  "favorites",
  "sort",
  "mode",
  "search_in",
  "approximate",
  "language",
  "work_type",
  "journal",
  "has_abstract",
  "has_doi",
  "retracted",
  "citations_min",
];
export const advancedFilterKeys = [
  "author",
  "author_id",
  "year_to",
  "source",
  "sort",
  "mode",
  "search_in",
  "approximate",
  "language",
  "work_type",
  "journal",
  "has_abstract",
  "has_doi",
  "retracted",
  "citations_min",
];
export const numberFilterKeys = [
  "year",
  "year_from",
  "year_to",
  "citations_min",
];
export const booleanFilterKeys = [
  "oa",
  "favorites",
  "approximate",
  "has_abstract",
  "has_doi",
  "retracted",
];
const meaningfulFalse = new Set(["oa", "has_abstract", "has_doi", "retracted"]);
const defaults: Record<string, unknown> = {
  sort: "relevance",
  mode: "all",
  search_in: "all",
};
export const filterLabels: Record<string, string> = {
  q: "Assunto",
  institution_id: "Instituição",
  topic: "Tema",
  author: "Autor",
  author_id: "Autor selecionado",
  year: "Ano",
  year_from: "A partir de",
  year_to: "Até",
  oa: "Leitura gratuita",
  source: "Informações da fonte",
  favorites: "Favoritos",
  mode: "Combinar palavras",
  search_in: "Onde pesquisar",
  approximate: "Títulos parecidos",
  language: "Idioma",
  work_type: "Tipo de trabalho",
  journal: "Revista ou veículo",
  has_abstract: "Resumo disponível",
  has_doi: "DOI disponível",
  retracted: "Retratação",
  citations_min: "Mínimo de citações",
};
export function filtersFromQuery(query: LocationQuery) {
  const result: Record<string, string | number | boolean> = {};
  for (const key of publicationKeys) {
    const raw = query[key];
    if (typeof raw !== "string" || !raw) continue;
    result[key] = numberFilterKeys.includes(key)
      ? Number(raw)
      : booleanFilterKeys.includes(key)
        ? raw === "true"
        : raw;
  }
  return result;
}
export function savedSearchDestination(
  filters: Record<string, string | number | boolean | null>,
) {
  const query: Record<string, string> = {};
  for (const key of publicationKeys) {
    const v = filters[key];
    if (
      v === undefined ||
      v === null ||
      v === "" ||
      (key in defaults && defaults[key] === v) ||
      (v === false && !meaningfulFalse.has(key))
    )
      continue;
    query[key] = String(v);
  }
  return { name: "publications", query };
}
export type PublicationFacets = {
  languages: { id: string; count: number }[];
  work_types: { id: string; count: number }[];
  topics: { id: string; name: string; count: number }[];
  institutions: { id: string; name: string; count: number }[];
};

import type { LocationQuery } from "vue-router";
export type SearchResult = {
  kind: string;
  id: string;
  title: string;
  subtitle: string;
  source: string;
  collected_at: string;
  favorite: boolean;
};
export const kinds: Record<string, string> = {
  institution: "Instituições",
  publication: "Publicações",
  researcher: "Pesquisadores",
  dataset: "Dados abertos",
};
export const value = (q: LocationQuery, key: string) =>
  typeof q[key] === "string" ? (q[key] as string) : "";
export function destination(item: SearchResult) {
  const name =
    {
      institution: "institutions",
      publication: "publications",
      researcher: "researchers",
      dataset: "search",
    }[item.kind] || "search";
  const query =
    item.kind === "publication"
      ? { publication: item.id }
      : item.kind === "dataset"
        ? { dataset: item.id }
        : { id: item.id };
  return { name, query };
}
export function params(query: LocationQuery, allowed: string[]) {
  const result = new URLSearchParams();
  for (const key of allowed)
    if (value(query, key)) result.set(key, value(query, key));
  return result.toString();
}
export { publicationKeys } from "./researchFilters";

export const languages: Record<string, string> = {
  pt: "Português",
  en: "Inglês",
  es: "Espanhol",
  fr: "Francês",
  de: "Alemão",
  it: "Italiano",
};
export const workTypes: Record<string, string> = {
  article: "Artigo",
  review: "Revisão",
  book: "Livro",
  "book-chapter": "Capítulo de livro",
  dissertation: "Dissertação ou tese",
  preprint: "Preprint",
  "proceedings-article": "Artigo em anais",
  dataset: "Conjunto de dados",
  report: "Relatório",
  other: "Outro",
};

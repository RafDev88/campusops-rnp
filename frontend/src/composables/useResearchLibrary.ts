import { onUnmounted, ref } from "vue";
import { api } from "../api";
import type { SearchResult } from "../discovery";
export type SavedResearch = {
  id: number;
  name: string;
  filters: Record<string, string | number | boolean | null>;
  alerts_enabled: boolean;
};
export type ResearchAlert = {
  id: number;
  title: string;
  publication_id: string;
  search_name: string;
  read: boolean;
};
export function useResearchLibrary() {
  const saved = ref<SavedResearch[]>([]),
    favorites = ref<SearchResult[]>([]),
    favoriteCount = ref(0),
    alerts = ref<ResearchAlert[]>([]),
    loading = ref(true),
    error = ref("");
  let controller: AbortController | undefined,
    generation = 0;
  async function load() {
    controller?.abort();
    controller = new AbortController();
    const current = ++generation;
    loading.value = true;
    error.value = "";
    try {
      const [s, f, a] = await Promise.all([
        api<SavedResearch[]>(
          "saved-searches",
          "GET",
          undefined,
          controller.signal,
        ),
        api<{ items: SearchResult[]; total: number }>(
          "search?favorites=true&limit=12",
          "GET",
          undefined,
          controller.signal,
        ),
        api<ResearchAlert[]>(
          "search-alerts",
          "GET",
          undefined,
          controller.signal,
        ),
      ]);
      if (current !== generation) return;
      saved.value = s;
      favorites.value = f.items;
      favoriteCount.value = f.total;
      alerts.value = a;
    } catch (e) {
      if ((e as Error).name !== "AbortError" && current === generation)
        error.value = (e as Error).message;
    } finally {
      if (current === generation) loading.value = false;
    }
  }
  async function removeSaved(id: number) {
    await api("saved-searches/" + id, "DELETE");
    await load();
  }
  async function readAlert(id: number) {
    await api(`search-alerts/${id}/read`, "POST");
    const item = alerts.value.find((a) => a.id === id);
    if (item) item.read = true;
  }
  onUnmounted(() => controller?.abort());
  return {
    saved,
    favorites,
    favoriteCount,
    alerts,
    loading,
    error,
    load,
    removeSaved,
    readAlert,
  };
}

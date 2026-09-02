import axios from "axios";

export const http = axios.create({
  baseURL: "/api/v1",
  timeout: 60000,
});

http.interceptors.response.use(
  (resp) => resp,
  (err) => {
    const message = err.response?.data?.error?.message || err.message || "请求失败";
    return Promise.reject(new Error(message));
  },
);

export const api = {
  health: () => http.get("/health"),
  meta: () => http.get("/meta"),
  dashboard: () => http.get("/dashboard"),
  policies: (params: Record<string, unknown>) => http.get("/policies", { params }),
  policy: (id: string) => http.get(`/policies/${id}`),
  related: (id: string) => http.get(`/policies/${id}/related`),
  analyze: (id: string) => http.post(`/policies/${id}/analyze`),
  compare: (policy_ids: string[]) => http.post("/policies/compare", { policy_ids }),
  favorites: () => http.get("/favorites"),
  addFavorite: (id: string) => http.post(`/favorites/${id}`),
  removeFavorite: (id: string) => http.delete(`/favorites/${id}`),
  subscriptions: () => http.get("/subscriptions"),
  addSubscription: (body: Record<string, unknown>) => http.post("/subscriptions", body),
  deleteSubscription: (id: string) => http.delete(`/subscriptions/${id}`),
  digests: () => http.get("/digests"),
  generateDigest: () => http.post("/digests/generate"),
  ingestUrl: (body: Record<string, unknown>) => http.post("/ingest/url", body),
  ingestSnapshot: () => http.post("/ingest/snapshot"),
  ingestCrawl: () => http.post("/ingest/crawl"),
  excelUrl: (ids: string[] = []) =>
    `/api/v1/export/excel${ids.length ? `?ids=${ids.join(",")}` : ""}`,
  pdfUrl: (id: string) => `/api/v1/export/pdf/${id}`,
};

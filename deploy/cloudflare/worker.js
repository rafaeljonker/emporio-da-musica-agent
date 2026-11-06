// emporio.fastmind.site -> the Modal app emporio-api. UPSTREAM comes from `make deploy-proxy`,
// PROXY_SECRET from `wrangler secret put PROXY_SECRET` (same value as Modal's emporio-proxy).
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const target = new URL(url.pathname + url.search, env.UPSTREAM);
    const headers = new Headers(request.headers);
    const ip = request.headers.get("CF-Connecting-IP") || "";
    headers.set("X-Forwarded-For", ip);
    headers.set("X-Forwarded-Host", url.host);
    // Overwrite whatever the client sent: the API trusts X-Client-IP only with this secret.
    headers.set("X-Client-IP", ip);
    headers.set("X-Proxy-Auth", env.PROXY_SECRET || "");
    return fetch(target, { method: request.method, headers,
      body: ["GET","HEAD"].includes(request.method) ? undefined : request.body, redirect: "manual" });
  },
};

// Stable loader. Keep this resource URL in Lovelace; the implementation is cache-busted on page load.
const url = "/api/anime_benchmark/static/anime-benchmark-card.impl.js?v=" + Date.now();
import(url).catch((error) => {
  console.error("Anime Benchmark card failed to load", error);
});

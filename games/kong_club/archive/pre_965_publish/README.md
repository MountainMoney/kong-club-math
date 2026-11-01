# Pre-96.50% publish snapshot

`library/` is gitignored, so the 250k 96.01% `publish_files` (books around 52–656 MB) were never in git.

On 2026-11-01 a 2,000-spin run overwrote `math-sdk/games/kong_club/library/publish_files`. A search of Desktop, Downloads, and the Slots tree found no second copy of those zst books.

What is kept here:

- `web_cache_luts/` — the lookup tables that were in the web-sdk math-books cache (small, not the 250k row set).
- `stake_uploads_250k_stub/` — the `stake_uploads/monkey_mayhem_math_v0_4_0_250k` folder. The book files there are stubs (under 1 KB), not the full 250k books.

Do not delete this folder. The live `library/publish_files` directory is the new 96.50% build.

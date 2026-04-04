## [1.4.1](https://github.com/victoremnm/cedh-research/compare/v1.4.0...v1.4.1) (2026-04-04)


### Bug Fixes

* **regional-elo:** polish player drilldown links ([e3ad4a8](https://github.com/victoremnm/cedh-research/commit/e3ad4a843363d73881415f00a71fef3c2cfda718))

# [1.4.0](https://github.com/victoremnm/cedh-research/compare/v1.3.0...v1.4.0) (2026-04-04)


### Bug Fixes

* **ci:** run semantic-release on node 24 ([#23](https://github.com/victoremnm/cedh-research/issues/23)) ([13ccc44](https://github.com/victoremnm/cedh-research/commit/13ccc446ddb41b3d021fb544b16b857ad3481859))


### Features

* add hand eval tooling and labels ([e780d6b](https://github.com/victoremnm/cedh-research/commit/e780d6b2d68fed58dd2d89e93cf70469fa3dd673))
* add sisay decklist and labels ([2f8f48e](https://github.com/victoremnm/cedh-research/commit/2f8f48e607b78df4da1abc06253061de0cbe0da8))
* add sisay keep heuristics ([15bcba3](https://github.com/victoremnm/cedh-research/commit/15bcba3bd856a3bf70ccff841cf8a07d7c138e8e))
* web/backend updates + dependency audit fix ([#16](https://github.com/victoremnm/cedh-research/issues/16)) ([c64ce19](https://github.com/victoremnm/cedh-research/commit/c64ce19f410b72a26e241407eec380ed5a987a05))

# [1.3.0](https://github.com/victoremnm/cedh-research/compare/v1.2.0...v1.3.0) (2026-02-05)


### Features

* **web:** add motif overlay assets and preview ([538ac15](https://github.com/victoremnm/cedh-research/commit/538ac15119b771b44aad57a9765f021b1b261675))

# [1.2.0](https://github.com/victoremnm/cedh-research/compare/v1.1.0...v1.2.0) (2026-02-04)


### Bug Fixes

* add regional loading state and active region indicator ([3e74b38](https://github.com/victoremnm/cedh-research/commit/3e74b38dbfb85b798fb7dddacbf5a6576996739b))
* default regional elo to california and simplify player column ([b3cd078](https://github.com/victoremnm/cedh-research/commit/b3cd078df5dda28976039c0fddbbfbe2d8a9d1d9))
* harden prep pages and align regional/midseason UX ([7420d97](https://github.com/victoremnm/cedh-research/commit/7420d97d2a2851766415e49e72e77f1b302c168e))
* require TopDeck API when key is configured ([3410ea3](https://github.com/victoremnm/cedh-research/commit/3410ea36bf8d44e7cc768522ef4d18d4d069ba2f))
* resolve regional query params in next server page ([7d842e0](https://github.com/victoremnm/cedh-research/commit/7d842e07e47b1dca5774b9747e30fcf894da2873))
* skip unknown latest commander and harden region selection ([f76220d](https://github.com/victoremnm/cedh-research/commit/f76220dbc91c6df22d7e7714aae57b95892da5ca))


### Features

* make midseason meta share player-weighted ([c6624f1](https://github.com/victoremnm/cedh-research/commit/c6624f1cb0ce2b6fafceb45415568e619e167760))
* weight midseason meta by player performance ([92e9fc7](https://github.com/victoremnm/cedh-research/commit/92e9fc7bc019a847f7f80e920fc63a7ec7206693))

# [1.1.0](https://github.com/victoremnm/cedh-research/compare/v1.0.0...v1.1.0) (2026-02-04)


### Bug Fixes

* **backend:** require service key for Supabase write-capable scripts ([59fc3f6](https://github.com/victoremnm/cedh-research/commit/59fc3f6fcec33949e50bd71dee690b2aa41384c3))
* **web:** normalize regional filtering and restore deck frequency profiles ([9865edf](https://github.com/victoremnm/cedh-research/commit/9865edf3a396ac761b0aed0d425d39703ef2dc72))
* **web:** support URLSearchParams-style searchParams on server pages ([cd8b40c](https://github.com/victoremnm/cedh-research/commit/cd8b40cb605c6673e50e8147abc74c829d13dc14))


### Features

* **methodology:** add Elo reference page and midseason consensus snapshot ([ac0e8f5](https://github.com/victoremnm/cedh-research/commit/ac0e8f575be0d83985cc4fe97c62b834031fd6d7))

# 1.0.0 (2026-02-04)


### Features

* Initial project setup with monorepo structure ([cd65ae6](https://github.com/victoremnm/cedh-research/commit/cd65ae6d269dd18e6e6a580330ea0eddd3746369))
* Support 16+ player tournaments and show 30-day top finishes ([#1](https://github.com/victoremnm/cedh-research/issues/1)) ([279fe9c](https://github.com/victoremnm/cedh-research/commit/279fe9c1f2f6014c438b9c13e8de84fe8e18df2f))

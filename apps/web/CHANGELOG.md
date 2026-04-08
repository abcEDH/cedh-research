# [1.6.0](https://github.com/abcEDH/cedh-research/compare/v1.5.1...v1.6.0) (2026-04-08)


### Bug Fixes

* harden regional elo consistency check ([#58](https://github.com/abcEDH/cedh-research/issues/58)) ([74a9938](https://github.com/abcEDH/cedh-research/commit/74a993821c96c6e05f7a4e213f4fab9fe98c1f5b))


### Features

* checkpoint TopDeck compliance and attribution ([#53](https://github.com/abcEDH/cedh-research/issues/53)) ([8a4df51](https://github.com/abcEDH/cedh-research/commit/8a4df51385e78414aec65f0f6c08265c2df05652))

## [1.5.1](https://github.com/abcEDH/cedh-research/compare/v1.5.0...v1.5.1) (2026-04-07)


### Bug Fixes

* **web:** exclude unknown commander rows in supabase queries ([#47](https://github.com/abcEDH/cedh-research/issues/47)) ([84d1499](https://github.com/abcEDH/cedh-research/commit/84d1499ef33a018f443e785c562d280e5b80f6e3))

# [1.5.0](https://github.com/abcEDH/cedh-research/compare/v1.4.2...v1.5.0) (2026-04-07)


### Bug Fixes

* **backfill:** add delta retry and scrub tooling ([f3aa35c](https://github.com/abcEDH/cedh-research/commit/f3aa35cb4c934b6a72e139d4a7745693390ff030))
* **backfill:** dedupe duplicate tournament entries ([2245451](https://github.com/abcEDH/cedh-research/commit/224545184a2be826da3ff29eb9a26d2b62da12ca))
* **backfill:** export manifest and allow larger pods ([5af89c2](https://github.com/abcEDH/cedh-research/commit/5af89c2b0d3ba15dbb0d92e830a949ede688c874))
* **backfill:** support supplemental manifest tids ([3d78686](https://github.com/abcEDH/cedh-research/commit/3d786861cf1dd4f86ccebe04d6da44fa8a1eed80))
* **ci:** make backfill progress observable ([a273664](https://github.com/abcEDH/cedh-research/commit/a273664e03cb4cbf10aeb161aeb9ec2a684d192c))
* **ci:** make integrity count checks resilient ([a3c80d8](https://github.com/abcEDH/cedh-research/commit/a3c80d860e2e7f47917ef4af7293e8f310f0ae1a))
* **ci:** recompute leaderboard data before backend validation ([0a7fcd3](https://github.com/abcEDH/cedh-research/commit/0a7fcd38cc060a4881da02891f0873f741c5b56c))
* **ci:** stabilize PR checks ([efbef3f](https://github.com/abcEDH/cedh-research/commit/efbef3fb523a8c1a47524276c6833c6b82e5e758))
* **db:** append new leaderboard metadata columns ([b5d73d6](https://github.com/abcEDH/cedh-research/commit/b5d73d668b4fb52a71d91a45b6c1b1bca7e95a3a))
* **db:** keep leaderboard rank column stable ([3555a9e](https://github.com/abcEDH/cedh-research/commit/3555a9ef17eb4281dbd9275968ee109bd7e6cf73))
* **db:** preserve leaderboard view column order ([94b94c7](https://github.com/abcEDH/cedh-research/commit/94b94c7747f6be30ba8def357d1689785686a67f))
* **web:** default regional player views to global ([d2de4ea](https://github.com/abcEDH/cedh-research/commit/d2de4ea1a609ba89a7c5537899b04be0efb47782))
* **web:** repair tournament prep region typing ([a4c8ca2](https://github.com/abcEDH/cedh-research/commit/a4c8ca274f678558bed49b1179a0be18b81819cb))
* **web:** use primary home region in tournament prep ([0911beb](https://github.com/abcEDH/cedh-research/commit/0911beb7a7ad9d0cf51fff8a8c5309cdebb16539))


### Features

* **backfill:** add supabase-backed all-time tid manifest ([51257c1](https://github.com/abcEDH/cedh-research/commit/51257c1c9b5833aac374020a6bdc66945d99173c))
* **leaderboard:** add global elo and historical backfill orchestration ([5315448](https://github.com/abcEDH/cedh-research/commit/5315448cd1e26f7e6af112c8bb321bfca7e94697))


### Performance Improvements

* **db:** index normalized tournament state ([6723675](https://github.com/abcEDH/cedh-research/commit/6723675be397e8090c5e0321c3e2f8b59cea1c55))

## [1.4.2](https://github.com/victoremnm/cedh-research/compare/v1.4.1...v1.4.2) (2026-04-05)


### Bug Fixes

* **regional-elo:** sync summary stats with canonical games ([ce1d6d8](https://github.com/victoremnm/cedh-research/commit/ce1d6d8b8edf8f000c460fc9a5b3b4e3c369a207))

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

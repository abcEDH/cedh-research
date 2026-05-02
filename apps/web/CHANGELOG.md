## [1.10.2](https://github.com/abcEDH/cedh-research/compare/v1.10.1...v1.10.2) (2026-05-02)


### Bug Fixes

* **web:** drop NaN% and zero-game dips on commanders page ([#152](https://github.com/abcEDH/cedh-research/issues/152)) ([88d6c40](https://github.com/abcEDH/cedh-research/commit/88d6c40e5c2558bf5d1b010dca970f6c3ecb72da))

## [1.10.1](https://github.com/abcEDH/cedh-research/compare/v1.10.0...v1.10.1) (2026-05-02)


### Performance Improvements

* **web:** consume regional Elo read models ([#145](https://github.com/abcEDH/cedh-research/issues/145)) ([b4601f8](https://github.com/abcEDH/cedh-research/commit/b4601f8cbf184a4a8885445620a7ee2d4ab4364d))

# [1.10.0](https://github.com/abcEDH/cedh-research/compare/v1.9.0...v1.10.0) (2026-05-02)


### Features

* overhaul home page, seed scouting events, and clean repo bloat ([#144](https://github.com/abcEDH/cedh-research/issues/144)) ([bd0b5ad](https://github.com/abcEDH/cedh-research/commit/bd0b5adde02d7ff2b5c835f9b9caaeb938bc7b32))

# [1.9.0](https://github.com/abcEDH/cedh-research/compare/v1.8.0...v1.9.0) (2026-05-02)


### Features

* **web:** refine home page, commander details, and expand trend history ([#143](https://github.com/abcEDH/cedh-research/issues/143)) ([8cb9e46](https://github.com/abcEDH/cedh-research/commit/8cb9e46d58a2c9e107084e72d5a162ec3b37294b))

# [1.8.0](https://github.com/abcEDH/cedh-research/compare/v1.7.7...v1.8.0) (2026-05-01)


### Features

* **backend:** persist latest tournament + commander metadata on player_commander_profiles (closes [#130](https://github.com/abcEDH/cedh-research/issues/130)) ([#133](https://github.com/abcEDH/cedh-research/issues/133)) ([c8fd33b](https://github.com/abcEDH/cedh-research/commit/c8fd33bd43528187c54044e8a8b5e5379698386e))
* **backend:** persist topdeck_elo + country slices on leaderboard (closes [#129](https://github.com/abcEDH/cedh-research/issues/129)) ([#134](https://github.com/abcEDH/cedh-research/issues/134)) ([10e4a04](https://github.com/abcEDH/cedh-research/commit/10e4a04656c4b5f8c512d8ab0689bf88baa28b90))

## [1.7.7](https://github.com/abcEDH/cedh-research/compare/v1.7.6...v1.7.7) (2026-04-29)


### Bug Fixes

* cache homepage and remove stale widgets ([#122](https://github.com/abcEDH/cedh-research/issues/122)) ([22722d9](https://github.com/abcEDH/cedh-research/commit/22722d999ccdca3fbfec9e2ec99523b30c704812))

## [1.7.6](https://github.com/abcEDH/cedh-research/compare/v1.7.5...v1.7.6) (2026-04-29)


### Bug Fixes

* load app fonts via next/font ([#123](https://github.com/abcEDH/cedh-research/issues/123)) ([1882cc2](https://github.com/abcEDH/cedh-research/commit/1882cc21b9eb5c0df05ddbfef8e42427c4fb4b06))

## [1.7.5](https://github.com/abcEDH/cedh-research/compare/v1.7.4...v1.7.5) (2026-04-17)


### Bug Fixes

* **cd:** add manual Vercel alias override ([#101](https://github.com/abcEDH/cedh-research/issues/101)) ([3e093ff](https://github.com/abcEDH/cedh-research/commit/3e093ffc6687b53d56ef76516dbb9cde4322168d))
* **cd:** drop project name from vercel ls to fix deployment lookup ([#97](https://github.com/abcEDH/cedh-research/issues/97)) ([25a6c11](https://github.com/abcEDH/cedh-research/commit/25a6c116fba6a9739bce147134091a74527e238e))
* **cd:** use Vercel REST API and fire on merge to main ([#98](https://github.com/abcEDH/cedh-research/issues/98)) ([4fa8856](https://github.com/abcEDH/cedh-research/commit/4fa88560ce4fec477ad86ccac9850892ae5159f3))
* **hygiene:** guard generated report paths ([#78](https://github.com/abcEDH/cedh-research/issues/78)) ([04dfaaa](https://github.com/abcEDH/cedh-research/commit/04dfaaa1216f21a100f675f35dfad729391382ce))

## [1.7.4](https://github.com/abcEDH/cedh-research/compare/v1.7.3...v1.7.4) (2026-04-11)


### Bug Fixes

* pin cedh-research.vercel.app alias to release tags only ([#96](https://github.com/abcEDH/cedh-research/issues/96)) ([4ecc67a](https://github.com/abcEDH/cedh-research/commit/4ecc67a7a15bbbb4af1e7c5b04403a2497f9fe4e))

## [1.7.3](https://github.com/abcEDH/cedh-research/compare/v1.7.2...v1.7.3) (2026-04-10)


### Bug Fixes

* restore release aliasing workflows ([#94](https://github.com/abcEDH/cedh-research/issues/94)) ([99d08b0](https://github.com/abcEDH/cedh-research/commit/99d08b032ce9b2b9f62fca2fd4f46677f64fef39))

## [1.7.2](https://github.com/abcEDH/cedh-research/compare/v1.7.1...v1.7.2) (2026-04-10)


### Bug Fixes

* simplify CD workflow to alias latest production deployment ([#93](https://github.com/abcEDH/cedh-research/issues/93)) ([5fe3c2f](https://github.com/abcEDH/cedh-research/commit/5fe3c2fc65f249bfccd0a0e5aaa615951eae3f22))

## [1.7.1](https://github.com/abcEDH/cedh-research/compare/v1.7.0...v1.7.1) (2026-04-10)


### Bug Fixes

* **cd:** trigger alias step on version tags to bypass [skip ci] ([#88](https://github.com/abcEDH/cedh-research/issues/88)) ([28e191b](https://github.com/abcEDH/cedh-research/commit/28e191b68d0787576dcee96d53882705671baeb1))

# [1.7.0](https://github.com/abcEDH/cedh-research/compare/v1.6.0...v1.7.0) (2026-04-08)


### Bug Fixes

* backfill moxfield commanders ([34658f3](https://github.com/abcEDH/cedh-research/commit/34658f325051c1291e606add8f62fbbd927937fc))
* backfill unknown-state elo games ([6af8ab4](https://github.com/abcEDH/cedh-research/commit/6af8ab48b1794fbf7e0c1fef2cbfe23894f2599d))
* **ci:** harden regional elo consistency check ([#59](https://github.com/abcEDH/cedh-research/issues/59)) ([12cc825](https://github.com/abcEDH/cedh-research/commit/12cc8251a935a1073ebb32ea28bb459b16217c9d))
* collapse double-faced commanders ([40b65cb](https://github.com/abcEDH/cedh-research/commit/40b65cbcee74ab80ede61df1d457ce0d712d0742))
* derive player home region from game history ([fa979bd](https://github.com/abcEDH/cedh-research/commit/fa979bd858bdffc47a83db03850a40200c29b578))
* fall back to legacy elo leaderboard ([4ebe586](https://github.com/abcEDH/cedh-research/commit/4ebe5868987957629a41035dad6926b31f7e5d47))
* fall back to legacy player event log ([fe59022](https://github.com/abcEDH/cedh-research/commit/fe5902242485554aa06aa012ba2950fc7a83ca02))
* include unknown games in regional totals ([421ac9c](https://github.com/abcEDH/cedh-research/commit/421ac9c97adef3c465da6cffce7272d0bba0fd5b))
* include unknown state games in global elo ([bf42ddd](https://github.com/abcEDH/cedh-research/commit/bf42dddaf64ffe66c6656b0955aa74a65a7efff3))
* normalize imported commander names ([3bf2acf](https://github.com/abcEDH/cedh-research/commit/3bf2acf3d33c3c1a9f0845e2eb45593e0f6f514f))
* preserve apostrophes in commander imports ([2589638](https://github.com/abcEDH/cedh-research/commit/2589638beec582be8d0e8e8124b5fbc3534837a4))
* recognize topdeck draw winners ([5b7299d](https://github.com/abcEDH/cedh-research/commit/5b7299d15ea2a0d5e8824368cbd937a5f8ca0dde))
* show all player games across regions ([7c2b95b](https://github.com/abcEDH/cedh-research/commit/7c2b95b0c2ae6cf9b57357736cd7bad2f7074c27))
* show country option for legacy elo regions ([3e617c9](https://github.com/abcEDH/cedh-research/commit/3e617c9aaa2e4bd5034e3828322d3cd18a6b945f))
* show global totals on regional leaderboard ([9bad367](https://github.com/abcEDH/cedh-research/commit/9bad367c6fa38ea7b92f3219206328e82554ac6f))
* show stored elo on player profiles ([f95bbd8](https://github.com/abcEDH/cedh-research/commit/f95bbd86d7c4443392534bac1069fc52c0b6547a))


### Features

* import moxfield commander mappings ([acad40c](https://github.com/abcEDH/cedh-research/commit/acad40c7cd4246077d1731b559f2d669a663b92d))
* infer elo countries from regions ([dfa8258](https://github.com/abcEDH/cedh-research/commit/dfa8258e3211ffcef76b47af8840bc1bc529ad29))
* resolve commanders from topdeck deck pages ([1c99bd7](https://github.com/abcEDH/cedh-research/commit/1c99bd7d78bbc5b4616fc8b6899de00e9b7a4cbf))
* scrape moxfield deck pages ([f270987](https://github.com/abcEDH/cedh-research/commit/f270987815d4abaa62c038515f967d442c6f9927))
* use topdeck stats on player profiles ([cd2a265](https://github.com/abcEDH/cedh-research/commit/cd2a265eb10ff4a6e149740ebe829192e96099a9))


### Performance Improvements

* avoid blocking regional leaderboard render ([db942fb](https://github.com/abcEDH/cedh-research/commit/db942fb8ad90327f81b4a37aedf4496009d143d9))
* precompute active elo profile data ([a547ff9](https://github.com/abcEDH/cedh-research/commit/a547ff98012cd7bd1f4b4b2684fd0dab239d097e))
* precompute commander profiles and country regions ([e7da338](https://github.com/abcEDH/cedh-research/commit/e7da338fd888519fd200ea4687fe1407895f6b48))
* speed global elo pages ([f7b2a2d](https://github.com/abcEDH/cedh-research/commit/f7b2a2d87d2975ff05beef76cfcb3d80b67ebdde))
* use precomputed regional elo views ([6e1f1cd](https://github.com/abcEDH/cedh-research/commit/6e1f1cd6914bd4ff8fbdf05945f5f02b6b0083a6))

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

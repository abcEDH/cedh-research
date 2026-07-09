## [1.20.1](https://github.com/abcEDH/cedh-research/compare/v1.20.0...v1.20.1) (2026-07-09)


### Bug Fixes

* **regional-elo:** strip internal rating before serializing to client ([32fb54e](https://github.com/abcEDH/cedh-research/commit/32fb54e8d7c40eee08efa366af8d73d8b646abca))
* **regional-elo:** strip legacy hidden_rating from client mapper defensively ([8e47c82](https://github.com/abcEDH/cedh-research/commit/8e47c826890619debc5841e99c68ab881077a984)), closes [#253](https://github.com/abcEDH/cedh-research/issues/253)
* **schema:** allow nullable values in CommanderStats schema ([209d751](https://github.com/abcEDH/cedh-research/commit/209d751b3831c1d756b7698e98ddeeac8759344b))

# [1.20.0](https://github.com/abcEDH/cedh-research/compare/v1.19.0...v1.20.0) (2026-06-21)


### Bug Fixes

* display database points natively and infer missing records ([b3d0479](https://github.com/abcEDH/cedh-research/commit/b3d047920d23730dc717f66d831e0fc7ff8ad538))
* do not derive losses from points alone to avoid overwriting data ([e165e11](https://github.com/abcEDH/cedh-research/commit/e165e1179d53607fdb95222280d42c441c109921))
* Enable all tournament detail links ([51068e4](https://github.com/abcEDH/cedh-research/commit/51068e49d5513b715ea2bcb722f31e0fd1631ab1))
* Load full tournament detail standings ([b611482](https://github.com/abcEDH/cedh-research/commit/b61148244382eb309a2770c4d97a20fe98a580dc))
* **migrations:** add placeholders for remote-only migration versions ([2782494](https://github.com/abcEDH/cedh-research/commit/2782494c60e0d6f6678b17b57a095a9a84e42df5))
* **migrations:** rename local migration files to match remote timestamps ([2f4870c](https://github.com/abcEDH/cedh-research/commit/2f4870c3b926201da67140d1c50754ae79ae3513))
* remove unused Any import ([78c85d9](https://github.com/abcEDH/cedh-research/commit/78c85d9c36780f301ce0894428750a9ce3d8a70b))
* Use exact tournament tier filters ([b2ce6f5](https://github.com/abcEDH/cedh-research/commit/b2ce6f56945696a617b0ec47a4b63a578c9cf8db))
* **web:** default tournament list filter to All Tiers ([454b28b](https://github.com/abcEDH/cedh-research/commit/454b28b4c77bec228bde649142b8639bb1d960f9))
* **web:** resolve merge conflict, keep module-level unstable_cache for recent tournaments ([093db42](https://github.com/abcEDH/cedh-research/commit/093db4230dfad23ccadcb19c0cde620d94205f41))
* **web:** use current date for period filters and stable React keys ([d829d33](https://github.com/abcEDH/cedh-research/commit/d829d3391b332af202b8ac2bf08fa7d019bd669e))
* **web:** use module-level unstable_cache for recent tournaments ([3220a7f](https://github.com/abcEDH/cedh-research/commit/3220a7f0dc39144483681e800b012bba390daabc))


### Features

* Add tournament browsing surfaces ([c346627](https://github.com/abcEDH/cedh-research/commit/c3466271ddfbee06cf9f1637d885a7d7bfad2243))
* **web:** add CEDH Tournament 7 to tournament summaries ([1fcd0d5](https://github.com/abcEDH/cedh-research/commit/1fcd0d5914dc80ff07f2665451fd882a1a6dc8e1))
* **web:** add stacked bar charts for top cut and overall meta representation ([a17b862](https://github.com/abcEDH/cedh-research/commit/a17b8624492185955b15270cadae8f784b1379a8))
* **web:** display top 4 commanders on tournament list cards ([dd7f551](https://github.com/abcEDH/cedh-research/commit/dd7f5511b3445dfed195205c7edd0636d65eff0f))
* **web:** show full commander names and include popular non-cut commanders ([c9843a1](https://github.com/abcEDH/cedh-research/commit/c9843a1c364d7233a24af13b92871ef7449dad85))
* **web:** top 10 support for top 40 cuts ([0ece844](https://github.com/abcEDH/cedh-research/commit/0ece84443bdce9513485aaa4f4f234d671f4f653))
* **web:** update commanders tab to single column ([118d6b3](https://github.com/abcEDH/cedh-research/commit/118d6b34ddce95acc5d6da7b119d9703fcf53be9))
* **web:** update tournament details layout and player links ([35df9f8](https://github.com/abcEDH/cedh-research/commit/35df9f8ec86670d4222aa897f548b5988e343d98))

# [1.19.0](https://github.com/abcEDH/cedh-research/compare/v1.18.4...v1.19.0) (2026-06-20)


### Bug Fixes

* **backend:** add statement_timeout to global Elo snapshot RPCs ([#229](https://github.com/abcEDH/cedh-research/issues/229)) ([d71882d](https://github.com/abcEDH/cedh-research/commit/d71882d66a611103c5a18ab1e2b4955d572ce025))
* **backend:** batch SupabaseClient.upsert to avoid statement timeout ([#226](https://github.com/abcEDH/cedh-research/issues/226)) ([7020ebe](https://github.com/abcEDH/cedh-research/commit/7020ebe7db94093c18c0761a05c75f3870af09c0))
* **backend:** push detect_active_players dedup into a Postgres RPC ([#227](https://github.com/abcEDH/cedh-research/issues/227)) ([f961247](https://github.com/abcEDH/cedh-research/commit/f961247e39be8d830ac9c4ffe446c4b58d8996e2))
* **backend:** refresh materialized views over the direct Postgres connection ([#230](https://github.com/abcEDH/cedh-research/issues/230)) ([9a52263](https://github.com/abcEDH/cedh-research/commit/9a522634cbae990a1f7ec3b6c80338511fd33565))
* **backend:** repair the three materialized-view refresh failures ([#228](https://github.com/abcEDH/cedh-research/issues/228)) ([78221f3](https://github.com/abcEDH/cedh-research/commit/78221f3f95a26383f6931f64c8202337cd12a692))


### Features

* Add tournament browsing surfaces ([#231](https://github.com/abcEDH/cedh-research/issues/231)) ([bba64f3](https://github.com/abcEDH/cedh-research/commit/bba64f3c353e44542cf4faa115f3e5ad70c4e961))

## [1.18.4](https://github.com/abcEDH/cedh-research/compare/v1.18.3...v1.18.4) (2026-06-17)


### Bug Fixes

* **benchmark:** materialize regional_elo_data_validity, drop retired survival_summary ([#224](https://github.com/abcEDH/cedh-research/issues/224)) ([e51ac93](https://github.com/abcEDH/cedh-research/commit/e51ac93fc79028c16b55e2117ed92e46db3f9e5d))

## [1.18.3](https://github.com/abcEDH/cedh-research/compare/v1.18.2...v1.18.3) (2026-06-16)


### Bug Fixes

* **ci:** use minimal safe workflow syntax to avoid startup errors ([7059969](https://github.com/abcEDH/cedh-research/commit/705996992033551b9d855730c31d45fd42141d78))
* **ci:** use safe Step-level secrets and actor check for preview deploy ([e02f22b](https://github.com/abcEDH/cedh-research/commit/e02f22ba7a2d3f38c1f67e3abbd535c33ecb7bf3))
* **ci:** use safer step-level environment overrides to unblock dependabot without startup errors ([cc2b053](https://github.com/abcEDH/cedh-research/commit/cc2b0533efe7b4e8fa77281fa0742cfdbe1f4fac))

## [1.18.2](https://github.com/abcEDH/cedh-research/compare/v1.18.1...v1.18.2) (2026-06-16)


### Bug Fixes

* **ci:** avoid pull_request object access on push events to prevent workflow startup errors ([aff9274](https://github.com/abcEDH/cedh-research/commit/aff927465d5ae523dfe86c26a499f4e09b479ada))
* **ci:** simplify workflows to resolve startup errors ([bfbca55](https://github.com/abcEDH/cedh-research/commit/bfbca55bcde8d586560129219494d34cdd0c26c0))
* **ci:** skip preview deploy and backend validation when secrets are missing ([186df66](https://github.com/abcEDH/cedh-research/commit/186df66b5ac84d3a2429c1774798b0c4ac673f5a))
* **deps:** force postcss deduplication to remediate GHSA-qx2v-qp2m-jg93 ([1931246](https://github.com/abcEDH/cedh-research/commit/1931246d63cc207f90a9a78d7f99bd50671244d0))

## [1.18.1](https://github.com/abcEDH/cedh-research/compare/v1.18.0...v1.18.1) (2026-06-16)


### Bug Fixes

* **ci:** unblock dependabot by providing fallback build secrets ([#221](https://github.com/abcEDH/cedh-research/issues/221)) ([4211ae6](https://github.com/abcEDH/cedh-research/commit/4211ae605da064c2989f8a1af053ec9959c5752d))

# [1.18.0](https://github.com/abcEDH/cedh-research/compare/v1.17.4...v1.18.0) (2026-06-16)


### Bug Fixes

* align june 10 supabase migration versions with remote ledger ([#210](https://github.com/abcEDH/cedh-research/issues/210)) ([ef6808f](https://github.com/abcEDH/cedh-research/commit/ef6808ff14b3329617de3c51f712822edb074c68))
* **ci:** bump elo recompute timeout to 60m, add PYTHONUNBUFFERED ([#195](https://github.com/abcEDH/cedh-research/issues/195)) ([18ee2ee](https://github.com/abcEDH/cedh-research/commit/18ee2ee35401816a7b49f569be3b621d6dc07a81))
* **client:** convert generator to list comprehension in execute_values call ([#207](https://github.com/abcEDH/cedh-research/issues/207)) ([14e74aa](https://github.com/abcEDH/cedh-research/commit/14e74aa9f769c8257cf9189e260332d7ac6cc758))
* **client:** restore headers attribute on SupabaseClient after supabase-py migration ([#206](https://github.com/abcEDH/cedh-research/issues/206)) ([09bd6ac](https://github.com/abcEDH/cedh-research/commit/09bd6ac5cc4fe8ee9ac691bb3595d3bf145ca043))
* **client:** restore url attribute on SupabaseClient ([#205](https://github.com/abcEDH/cedh-research/issues/205)) ([05ec272](https://github.com/abcEDH/cedh-research/commit/05ec272c515cd34dc287255c6c427537ac295dc9))
* **crons:** guard game_events upsert, add job timeout — unblocks daily Elo recompute ([#194](https://github.com/abcEDH/cedh-research/issues/194)) ([8c8a5d4](https://github.com/abcEDH/cedh-research/commit/8c8a5d40bdc07043156338a5c662e4b4d9dacd7c)), closes [#188](https://github.com/abcEDH/cedh-research/issues/188) [#193](https://github.com/abcEDH/cedh-research/issues/193) [#193](https://github.com/abcEDH/cedh-research/issues/193)
* **elo:** fix Elo recompute schema gaps, FK bug, and DirectPostgres reliability ([#201](https://github.com/abcEDH/cedh-research/issues/201)) ([6df69c7](https://github.com/abcEDH/cedh-research/commit/6df69c71af1f0e920dc014afaf39115c8cf8d0fe))
* **elo:** populate entry_id for top-rated player in game event rows ([#208](https://github.com/abcEDH/cedh-research/issues/208)) ([5c4a0d3](https://github.com/abcEDH/cedh-research/commit/5c4a0d341e22ee67e1f8933cbd3475026a02a9ea))
* **elo:** use canonical event counts for leaderboard W-L-D stats ([#204](https://github.com/abcEDH/cedh-research/issues/204)) ([3cdb4b6](https://github.com/abcEDH/cedh-research/commit/3cdb4b6e579197ea6cdf12327ec7dbd4c291a3a8))
* normalize commander profile start dates ([#211](https://github.com/abcEDH/cedh-research/issues/211)) ([6f0f6ee](https://github.com/abcEDH/cedh-research/commit/6f0f6ee288049e20a3fbba3a0cac96c544d7f1f3))


### Features

* **elo:** add primary commander per player to profile summaries ([#203](https://github.com/abcEDH/cedh-research/issues/203)) ([23d881c](https://github.com/abcEDH/cedh-research/commit/23d881c3e2f2de970a84bd9ad87dfe8f3b0a4ff6))
* **elo:** switch to incremental Elo from event-log watermark ([#202](https://github.com/abcEDH/cedh-research/issues/202)) ([6cad41c](https://github.com/abcEDH/cedh-research/commit/6cad41c04e5940e3342db82965a29ee846084fd3))


### Performance Improvements

* **elo:** fix O(n²) Elo recompute + merge PR [#196](https://github.com/abcEDH/cedh-research/issues/196) DirectPostgres path ([#199](https://github.com/abcEDH/cedh-research/issues/199)) ([d18bb8f](https://github.com/abcEDH/cedh-research/commit/d18bb8fe4a7648c29f6e2f2fefa17c175416d131))

## [1.17.4](https://github.com/abcEDH/cedh-research/compare/v1.17.3...v1.17.4) (2026-05-28)


### Bug Fixes

* **deps:** pin exclude-newer to absolute date to prevent CI re-resolution ([#191](https://github.com/abcEDH/cedh-research/issues/191)) ([2259881](https://github.com/abcEDH/cedh-research/commit/225988101e3066eb257b075dfc453f236105000e))
* **regional-elo:** fix PGRST108 by routing queries through global_elo_game_results ([#190](https://github.com/abcEDH/cedh-research/issues/190)) ([138a307](https://github.com/abcEDH/cedh-research/commit/138a3070178a6d43d77260287b90edc6532aea22))

## [1.17.3](https://github.com/abcEDH/cedh-research/compare/v1.17.2...v1.17.3) (2026-05-25)


### Bug Fixes

* remove duplicate Date column in Achievements table ([36bf347](https://github.com/abcEDH/cedh-research/commit/36bf347d92f72cd13cbb17d8e2d7a716faeb7858))

## [1.17.2](https://github.com/abcEDH/cedh-research/compare/v1.17.1...v1.17.2) (2026-05-13)


### Bug Fixes

* log status code and response body on Supabase select retry ([#181](https://github.com/abcEDH/cedh-research/issues/181)) ([90a7328](https://github.com/abcEDH/cedh-research/commit/90a73280c827288cbe21bd3a1572f9c597eeb8f2))

## [1.17.1](https://github.com/abcEDH/cedh-research/compare/v1.17.0...v1.17.1) (2026-05-12)


### Bug Fixes

* **migrations:** guard DROP POLICY for commander elo tables behind existence check ([2dd2e8a](https://github.com/abcEDH/cedh-research/commit/2dd2e8a0ef11847125b75751754e3cc33d4808a5))
* **migrations:** guard topdeck-elo cron schedule behind to_regclass check ([f0d9b4f](https://github.com/abcEDH/cedh-research/commit/f0d9b4fd4085b8e57575520aacb5499616304e7e))

# [1.17.0](https://github.com/abcEDH/cedh-research/compare/v1.16.0...v1.17.0) (2026-05-12)


### Bug Fixes

* **supabase:** guard cron migrations when extension is absent ([8b6dfb8](https://github.com/abcEDH/cedh-research/commit/8b6dfb8cd584c1b2d1883cd68716e35653c20a20))


### Features

* unify site header across all pages ([5df6870](https://github.com/abcEDH/cedh-research/commit/5df68702013255ec3c2c189c6031a97950e094c0))

# [1.16.0](https://github.com/abcEDH/cedh-research/compare/v1.15.0...v1.16.0) (2026-05-09)


### Features

* server-side query timing utilities ([#174](https://github.com/abcEDH/cedh-research/issues/174)) ([ffb38d5](https://github.com/abcEDH/cedh-research/commit/ffb38d50d6a6f5867dae2be19a51462e07c179bb))

# [1.15.0](https://github.com/abcEDH/cedh-research/compare/v1.14.0...v1.15.0) (2026-05-09)


### Features

* **web:** optimize tables for mobile responsiveness ([#167](https://github.com/abcEDH/cedh-research/issues/167)) ([e67200a](https://github.com/abcEDH/cedh-research/commit/e67200a2b0f2363d348c7ec60a29fadab46842a7))

# [1.14.0](https://github.com/abcEDH/cedh-research/compare/v1.13.3...v1.14.0) (2026-05-07)


### Bug Fixes

* pg_cron orchestration and event log access ([#171](https://github.com/abcEDH/cedh-research/issues/171)) ([509dddb](https://github.com/abcEDH/cedh-research/commit/509dddbb702b99d03cc23a3fcb2773057be73af6))


### Features

* replace hardcoded tournament suggestions with dynamic database query ([#173](https://github.com/abcEDH/cedh-research/issues/173)) ([2492e64](https://github.com/abcEDH/cedh-research/commit/2492e64c46b2b617a50ceed1c0e8313d4fb1bbc6))

## [1.13.3](https://github.com/abcEDH/cedh-research/compare/v1.13.2...v1.13.3) (2026-05-05)


### Performance Improvements

* optimize player page performance and caching ([#165](https://github.com/abcEDH/cedh-research/issues/165)) ([157c9c6](https://github.com/abcEDH/cedh-research/commit/157c9c66e1ff13804420cef4dc69ef77dbeda578)), closes [hi#level](https://github.com/hi/issues/level)

## [1.13.2](https://github.com/abcEDH/cedh-research/compare/v1.13.1...v1.13.2) (2026-05-04)


### Bug Fixes

* **analytics:** enable PostHog pageleave and autocapture ([#164](https://github.com/abcEDH/cedh-research/issues/164)) ([36b7b6b](https://github.com/abcEDH/cedh-research/commit/36b7b6b7cca18c94a0703c0635593d0f5cbe3d8d))

## [1.13.1](https://github.com/abcEDH/cedh-research/compare/v1.13.0...v1.13.1) (2026-05-03)


### Bug Fixes

* **regional-elo:** complete issue [#128](https://github.com/abcEDH/cedh-research/issues/128) gaps and documentation ([#162](https://github.com/abcEDH/cedh-research/issues/162)) ([0555f87](https://github.com/abcEDH/cedh-research/commit/0555f87f15b9548666c850553ac33741fb3a51e8))

# [1.13.0](https://github.com/abcEDH/cedh-research/compare/v1.12.1...v1.13.0) (2026-05-03)


### Features

* configure PostHog reverse proxy and secure project token ([#160](https://github.com/abcEDH/cedh-research/issues/160)) ([0e83a92](https://github.com/abcEDH/cedh-research/commit/0e83a922581868ad7488f8f36ea21278b8b4a20e))

## [1.12.1](https://github.com/abcEDH/cedh-research/compare/v1.12.0...v1.12.1) (2026-05-03)


### Performance Improvements

* **regional-elo:** bump cache TTLs, add loading state, achievements sort+filter ([#158](https://github.com/abcEDH/cedh-research/issues/158)) ([2941e7a](https://github.com/abcEDH/cedh-research/commit/2941e7a770eeb0a3d6671f162f24b19d80eea1cb))

# [1.12.0](https://github.com/abcEDH/cedh-research/compare/v1.11.0...v1.12.0) (2026-05-03)


### Features

* [Analytics] PostHog integration for user analytics ([#156](https://github.com/abcEDH/cedh-research/issues/156)) ([8956a79](https://github.com/abcEDH/cedh-research/commit/8956a7929e6718a2cf92a1dbda5f1c6e11e881d7)), closes [#74](https://github.com/abcEDH/cedh-research/issues/74) [#75](https://github.com/abcEDH/cedh-research/issues/75) [#76](https://github.com/abcEDH/cedh-research/issues/76) [#77](https://github.com/abcEDH/cedh-research/issues/77)

# [1.11.0](https://github.com/abcEDH/cedh-research/compare/v1.10.4...v1.11.0) (2026-05-03)


### Features

* **web:** move Region selector into header ([#157](https://github.com/abcEDH/cedh-research/issues/157)) ([d559b2a](https://github.com/abcEDH/cedh-research/commit/d559b2ab0170af64b3b5545d98a1920da50182db))

## [1.10.4](https://github.com/abcEDH/cedh-research/compare/v1.10.3...v1.10.4) (2026-05-03)


### Bug Fixes

* **backend:** harden ingestion against missing player lists and increase timeouts (closes [#153](https://github.com/abcEDH/cedh-research/issues/153)) ([#155](https://github.com/abcEDH/cedh-research/issues/155)) ([b46a87f](https://github.com/abcEDH/cedh-research/commit/b46a87f291d696ca576d80dd32c1986e560745ba))

## [1.10.3](https://github.com/abcEDH/cedh-research/compare/v1.10.2...v1.10.3) (2026-05-02)


### Bug Fixes

* resolve commander performance truncation and decklist parsing bugs ([#154](https://github.com/abcEDH/cedh-research/issues/154)) ([3448264](https://github.com/abcEDH/cedh-research/commit/3448264652687b6bf428c454f03602483b7222b1))

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

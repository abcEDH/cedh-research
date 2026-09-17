# Packages as deep modules

Each immediate child of this folder is a **module** with its **interface** at
its root files. Put implementation in `lib/` and co-located tests and fixtures
in `tests/`; subfolders are private. The copy-me layout is:

```text
packages/<name>/
  index.ts       # entry point: part of the module interface
  client.ts      # optional additional entry point
  lib/           # private implementation
  tests/         # tests and private fixtures
```

## Entry-point boundary

Import another package only through one of its root entry points. That seam
keeps its implementation private and gives callers leverage from a small,
stable interface.

## Intra-package freedom

Files in a package may freely use that package's implementation. This keeps
knowledge and changes local to the module.

## Tests through entry points

Tests exercise their package through the same interface as callers. They may
use fixtures in their own `tests/` folder, but must not deep-import any
package's implementation.

## No cycles

Packages must not form dependency cycles, so their interfaces remain clear
seams rather than coupled implementations.

Run `npm run lint:boundaries` to enforce these rules. Avoid giant barrel files:
expose several small root entry points when needed instead of re-exporting a
whole subtree through `index.ts`.

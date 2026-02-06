# Hand Eval Input Templates

Use these templates to pass deck context and hands with minimal noise.

**Minimal (Shorthand)**
```yaml
deck: Kinnan NBC
commanders: [Kinnan, Bonder Prodigy]
labels:
  engines: [...]
  tutors: [...]
  wins: [...]
hands:
  - pod: mixed
    seat: 2
    cards: [Forest, Llanowar Elves, Birds of Paradise, Flusterstorm, Hidden Strings, The Cabbage Merchant, Drift of Phantasms]
```

**Longhand (Recommended)**
```yaml
deck:
  name: Kinnan NBC
  commanders: [Kinnan, Bonder Prodigy]
  colors: [G, U]
  cost: GU
  special:
    - doubles nonland mana
    - 5UG spin

labels:
  engines: [Mystic Remora, Rhystic Study, Copy Enchantment, Mirrormade, Clever Impersonator]
  tutors: [Transmute Artifact, Tezzeret the Seeker, Nature's Rhythm, Green Sun's Zenith, Invasion of Ikoria, Chord of Calling, Trophy Mage]
  wins: [Basalt Monolith, Hullbreaker Horror, Finale of Devastation, Cephalid Coliseum, Thrasios, Triton Hero]
  fast_rocks: [Chrome Mox, Mox Diamond, Mox Opal, Mox Amber, Lotus Petal]
  ramp_rocks: [Sol Ring, Mana Vault, Grim Monolith, Arcane Signet, Talisman of Curiosity, Fellwar Stone]
  rituals: []

heuristics:
  - LED ignored
  - dorks +1 next turn
  - talismans -1 now +1 next turn
  - early_7_mana keep (Kinnan)

decklist:
  source: data/kinnan_list.txt
  changes:
    add: []
    cut: []

hands:
  - pod: mixed
    seat: 2
    cards:
      - Forest
      - Llanowar Elves
      - Birds of Paradise
      - Flusterstorm
      - Hidden Strings
      - The Cabbage Merchant
      - Drift of Phantasms
```

Notes:
- Paste only the **minimal** or **longhand** block.
- If a decklist is unchanged, just set `decklist.source` and leave `changes` empty.

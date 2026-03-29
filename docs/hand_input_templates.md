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

**Examples**

**Kinnan NBC (Minimal)**
```yaml
deck: Kinnan NBC
commanders: [Kinnan, Bonder Prodigy]
labels:
  engines: [Mystic Remora, Rhystic Study, Copy Enchantment, Mirrormade, Clever Impersonator]
  tutors: [Transmute Artifact, Tezzeret the Seeker, Nature's Rhythm, Green Sun's Zenith, Invasion of Ikoria, Chord of Calling, Trophy Mage]
  wins: [Basalt Monolith, Hullbreaker Horror, Finale of Devastation, Cephalid Coliseum, Thrasios, Triton Hero]
```

**Kinnan NBC (Longhand)**
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

decklist:
  source: data/kinnan_list.txt
  changes:
    add: []
    cut: []
```

**Blue Farm (Kraum/Tymna) Minimal**
```yaml
deck: Blue Farm
commanders: [Kraum, Ludevic's Opus, Tymna the Weaver]
labels:
  engines: [Mystic Remora, Rhystic Study, Esper Sentinel, Faerie Mastermind, Wheel of Fortune]
  tutors: [Demonic Tutor, Vampiric Tutor, Imperial Seal, Enlightened Tutor, Mystical Tutor, Gamble, Wishclaw Talisman]
  wins: [Underworld Breach, Thassa's Oracle, Tainted Pact, Demonic Consultation, Brain Freeze, Ad Nauseam]
```

**Blue Farm (Kraum/Tymna) Longhand**
```yaml
deck:
  name: Blue Farm
  commanders: [Kraum, Ludevic's Opus, Tymna the Weaver]
  colors: [U, B, R, W]
  cost: BW1
  special:
    - commander draw engines

labels:
  engines: [Mystic Remora, Rhystic Study, Esper Sentinel, Faerie Mastermind, Wheel of Fortune]
  tutors: [Demonic Tutor, Vampiric Tutor, Imperial Seal, Enlightened Tutor, Mystical Tutor, Gamble, Wishclaw Talisman, Intuition]
  wins: [Underworld Breach, Thassa's Oracle, Tainted Pact, Demonic Consultation, Brain Freeze, Ad Nauseam]
  fast_rocks: [Chrome Mox, Mox Diamond, Mox Opal, Mox Amber, Lotus Petal]
  ramp_rocks: [Sol Ring, Mana Vault, Arcane Signet, Fellwar Stone]
  rituals: [Dark Ritual, Cabal Ritual, Rite of Flame, Jeska's Will, Culling the Weak]

decklist:
  source: data/bluefarm_list.txt
  changes:
    add: []
    cut: []
```

**RogSi Minimal**
```yaml
deck: RogSi
commanders: [Rograkh, Son of Rohgahh, Silas Renn, Seeker Adept]
labels:
  engines: [Mystic Remora, Rhystic Study, Wheel of Fortune, Windfall, Timetwister]
  tutors: [Demonic Tutor, Vampiric Tutor, Imperial Seal, Mystical Tutor, Gamble, Wishclaw Talisman, Praetor's Grasp]
  wins: [Underworld Breach, Thassa's Oracle, Tainted Pact, Demonic Consultation, Brain Freeze, Ad Nauseam]
```

**RogSi Longhand**
```yaml
deck:
  name: RogSi
  commanders: [Rograkh, Son of Rohgahh, Silas Renn, Seeker Adept]
  colors: [U, B, R]
  cost: 0
  special:
    - commander enables free interaction
    - turbo wheels

labels:
  engines: [Mystic Remora, Rhystic Study, Wheel of Fortune, Wheel of Misfortune, Windfall, Timetwister]
  tutors: [Demonic Tutor, Vampiric Tutor, Imperial Seal, Mystical Tutor, Gamble, Wishclaw Talisman, Praetor's Grasp]
  wins: [Underworld Breach, Thassa's Oracle, Tainted Pact, Demonic Consultation, Brain Freeze, Ad Nauseam]
  fast_rocks: [Chrome Mox, Mox Diamond, Mox Opal, Mox Amber, Lotus Petal]
  ramp_rocks: [Sol Ring, Mana Vault, Grim Monolith, Arcane Signet, Talisman of Dominance, Talisman of Indulgence]
  rituals: [Dark Ritual, Cabal Ritual, Rite of Flame, Jeska's Will, Culling the Weak, Infernal Plunge]

decklist:
  source: data/rogsi_list.txt
  changes:
    add: []
    cut: []
```

**Kefka Minimal**
```yaml
deck: Kefka
commanders: [Kefka, Court Mage / Kefka, Ruler of Ruin]
labels:
  engines: [Mystic Remora, Rhystic Study, Wheel of Fortune]
  tutors: [Demonic Tutor, Vampiric Tutor, Imperial Seal, Mystical Tutor, Gamble, Wishclaw Talisman, Intuition]
  wins: [Underworld Breach, Thassa's Oracle, Tainted Pact, Demonic Consultation, Brain Freeze, Ad Nauseam]
```

**Kefka Longhand**
```yaml
deck:
  name: Kefka
  commanders: [Kefka, Court Mage / Kefka, Ruler of Ruin]
  colors: [U, B, R]
  cost: UBR2
  special:
    - midrange engine from command zone

labels:
  engines: [Mystic Remora, Rhystic Study, Wheel of Fortune]
  tutors: [Demonic Tutor, Vampiric Tutor, Imperial Seal, Mystical Tutor, Gamble, Wishclaw Talisman, Intuition]
  wins: [Underworld Breach, Thassa's Oracle, Tainted Pact, Demonic Consultation, Brain Freeze, Ad Nauseam]
  fast_rocks: [Chrome Mox, Mox Diamond, Mox Opal, Mox Amber, Lotus Petal]
  ramp_rocks: [Sol Ring, Mana Vault, Grim Monolith, Arcane Signet, Talisman of Creativity, Talisman of Dominance, Talisman of Indulgence]
  rituals: [Dark Ritual, Cabal Ritual, Rite of Flame, Jeska's Will, Culling the Weak, Rain of Filth]

decklist:
  source: data/kefka_list.txt
  changes:
    add: []
    cut: []
```

**RogThras Minimal**
```yaml
deck: RogThras
commanders: [Rograkh, Son of Rohgahh, Thrasios, Triton Hero]
labels:
  engines: [Mystic Remora, Rhystic Study]
  tutors: [Green Sun's Zenith, Finale of Devastation, Chord of Calling, Crop Rotation, Spellseeker]
  wins: [Thrasios, Triton Hero]
```

**RogThras Longhand**
```yaml
deck:
  name: RogThras
  commanders: [Rograkh, Son of Rohgahh, Thrasios, Triton Hero]
  colors: [U, G, R]
  cost: 0
  special:
    - big mana into Thrasios

labels:
  engines: [Mystic Remora, Rhystic Study]
  tutors: [Green Sun's Zenith, Finale of Devastation, Chord of Calling, Crop Rotation, Spellseeker, Nature's Rhythm]
  wins: [Thrasios, Triton Hero]
  fast_rocks: [Chrome Mox, Mox Diamond, Mox Amber, Lotus Petal]
  ramp_rocks: [Sol Ring, Springleaf Drum]
  rituals: [Malevolent Rumble]

decklist:
  source: data/rogthras_list.txt
  changes:
    add: []
    cut: []
```

**Sisay (Weatherlight Captain) Minimal**
```yaml
deck: Sisay (Oath of Nicol)
commanders: [Sisay, Weatherlight Captain]
labels:
  engines: [Mystic Remora, Rhystic Study, Esper Sentinel, Smothering Tithe]
  tutors: [Demonic Tutor, Vampiric Tutor, Enlightened Tutor, Chord of Calling, Crop Rotation, Neoform]
  wins: [Oath of Teferi, Nicol Bolas, Dragon-God, Aminatou, the Fateshifter, Emiel the Blessed, Derevi, Empyrial Tactician, Mount Doom, Orcish Bowmasters]
```

**Sisay (Weatherlight Captain) Longhand**
```yaml
deck:
  name: Sisay (Oath of Nicol)
  commanders: [Sisay, Weatherlight Captain]
  colors: [W, U, B, R, G]
  cost: W2
  special:
    - goal: WUBRG asap
    - Sisay activation scales with power

labels:
  engines: [Mystic Remora, Rhystic Study, Esper Sentinel, Smothering Tithe]
  tutors: [Demonic Tutor, Vampiric Tutor, Enlightened Tutor, Chord of Calling, Crop Rotation, Neoform]
  wins: [Oath of Teferi, Nicol Bolas, Dragon-God, Aminatou, the Fateshifter, Emiel the Blessed, Derevi, Empyrial Tactician, Mount Doom, Orcish Bowmasters]
  fast_rocks: [Chrome Mox, Mox Diamond, Mox Amber, Lotus Petal, Sol Ring, Mana Vault]
  ramp_rocks: [Arcane Signet, Relic of Legends]
  rituals: [Elvish Spirit Guide, Simian Spirit Guide, Tinder Wall]

decklist:
  source: pasted list
  changes:
    add: []
    cut: []
```

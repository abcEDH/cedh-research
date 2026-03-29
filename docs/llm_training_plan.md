# LLM Plan: Hand Evaluation + Keep/Mull Assistant

## Goal
Train a small public LLM (e.g., Ollama + Qwen) to evaluate 7-card hands for cEDH decks, with T1/T2 sequencing, seat-aware mulligan decisions, and pod-type heuristics.

## Scope & Non-Goals
- Scope: hand evaluation, sequencing heuristics, keep/mull guidance.
- Non-goals: full game simulation, perfect play lines, card price data.

## Data Sources
- Decklists (Kefka, Blue Farm, RogSi) from `data/*.txt`.
- Card metadata from Scryfall (cached in `.cache/scryfall_cards.json`).
- Label rules from `data/labels_*.json`.

## Dataset Design
### 1) Core Schema (JSONL)
Each training sample represents one hand evaluation.

```json
{
  "deck": "kefka",
  "pod": "fast|mixed|midrange",
  "seat": 1,
  "hand": ["Card A", "Card B", ...],
  "t1_sequence": "...",
  "t2_sequence": "...",
  "castable_t1": ["..."],
  "castable_t2": ["..."],
  "commander_turn": "T2|T3|T4+",
  "decision": "keep|mull",
  "reason": "short justification"
}
```

### 2) Prompt/Response Template
**Prompt**
```
Deck: {deck}
Pod: {pod}
Seat: {seat}
Hand: {hand}
Task: Evaluate T1/T2 sequencing and keep/mull.
```

**Response**
```
T1: ...
T2: ...
Castable T1: ...
Castable T2: ...
Commander castable by: T?
Decision: keep|mull
Reason: ...
```

### 3) Generation Strategy
- Use the local evaluator to auto-generate 5k–20k samples per deck.
- Randomize pod type and seat distribution.
- Include some “edge” hands: no lands, all mana, all value, etc.

## Tooling
### 1) Data Generation
- Extend `tools/hand_eval.py` to emit JSONL for many hands.
- Add a wrapper that loops seeds and writes output to `data/training/*.jsonl`.

### 2) Label Quality
- Keep a deterministic evaluator for consistency.
- Manually review 100–200 samples and adjust heuristics/labels.

## Training Approach
### Option A: LoRA Fine-Tune (Recommended)
- Base model: Qwen2.5 or Qwen2.5-Instruct.
- Use LoRA adapters for small, cheap updates.
- Tools: `unsloth`, `trl`, or `axolotl`.

### Option B: RAG Only (No Fine-Tune)
- Use your evaluator as the truth source.
- LLM acts as UI + reasoning layer, calls the evaluator.
- This is simpler and more reliable if exactness matters.

## Training Steps (LoRA)
1. Generate dataset: `data/training/*.jsonl`.
2. Convert to instruction format (prompt/response).
3. Train LoRA with small batch size.
4. Evaluate on held-out 10%.
5. Spot-check weird hands and adjust heuristics.

## Inference Setup (Ollama)
1. Export model or LoRA adapter.
2. Run with a system prompt that enforces the output format.
3. Optionally, run the evaluator first and give the LLM the structured data to explain.

## System Prompt (Draft)
```
You are a cEDH hand evaluator. Always:
- sequence T1 and T2
- list castable spells
- give a keep/mull decision with one-line reason
- use the pod and seat context
```

## Evaluation
- Accuracy vs evaluator baseline on 1k hands.
- Error categories: mana sequencing, pip misreads, seat heuristics.

## Deliverables
- `data/training/*.jsonl`
- LoRA adapter or Ollama model
- README for running inference

## Suggested Next Steps
1. Build JSONL generator for all decks.
2. Run 10k samples + quick review.
3. Choose LoRA toolchain and train.
4. Wrap in a small CLI or web UI.

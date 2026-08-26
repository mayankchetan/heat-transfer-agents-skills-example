---
name: heat-transfer-rag
description: 'Answer heat-transfer questions by grounding every claim in the local textbook RAG (A Heat Transfer Textbook, 6th ed.). Use when the user asks which equation or boundary conditions govern a heat-transfer setup, wants the governing PDE / correlation for a problem, needs page-and-equation citations from the book, or wants to scaffold the 2D heat solver from a cited setup. Retrieves from the heat_rag Chroma index and cites page + equation for every statement.'
argument-hint: 'a heat-transfer setup or the equation you want to identify'
---

# Heat-Transfer RAG (grounded answers)

Answer heat-transfer questions using the local retrieval RAG over *A Heat Transfer
Textbook*, 6th ed. (Lienhard & Lienhard). Every equation, boundary condition, or
correlation you report MUST come from a retrieved passage and carry its citation.
Never state a governing equation from memory without a supporting hit.

## When to Use
- "Which equation governs <setup>?" / "What are the boundary conditions for <setup>?"
- "Find the fin equation / the transient conduction PDE / the Nusselt correlation for ..."
- "Give me the governing equation with a page and equation citation."
- "Set up the 2D solver for this problem" — first ground the equation + BCs here.

## Prerequisites
- The index must exist (`data/chroma/`). If retrieval returns nothing, build it:
  `uv run python -m heat_rag ingest`
- Embeddings call the LiteLLM proxy, so `LITELLM_KEY` must be set in `.env`.

## Procedure
1. **Retrieve (default).** Turn the user's setup into 2–4 keyword-rich queries and
   run each:
   `uv run python -m heat_rag ask "<query>" -k 5`
   Vary the wording (physical phenomenon, geometry, equation name) to widen recall,
   e.g. "transient one-dimensional conduction", "lumped capacitance Biot number",
   "convective Robin boundary condition Newton's law of cooling".
   This returns the raw passages with citations — the default, most transparent mode.
2. **Select evidence.** Keep only hits whose passage actually contains the equation
   or boundary condition. Prefer higher `score`, but read the text — a high score
   with irrelevant content is not evidence. Discard the rest.
3. **Extract, don't invent.** Report the governing equation, assumptions, and
   boundary conditions using the wording of the retrieved passages. If the book’s
   symbols differ from the user's, map them explicitly.
4. **Cite every claim.** After each equation or BC, append the citation exactly as
   the RAG returns it: `book, p. <printed> (PDF p. <pdf>)[, eq. <label>]`. One
   citation per equation. If a claim has no supporting hit, say so — do not fill
   the gap from general knowledge.
5. **Handle gaps.**
   - No relevant hits after varied queries → tell the user, suggest closer terms,
     and offer to widen `-k`. Do not answer uncited.
   - Ambiguous setup (geometry, steady vs. transient, BC types unknown) → ask one
     clarifying question before committing to an equation.
6. **(Optional) Synthesize.** If the user wants a written explanation rather than
   raw passages, use the generative, cite-only layer:
   `uv run python -m heat_rag answer "<question>" -k 6`
   It feeds the retrieved passages to a chat model (via the LiteLLM proxy) under a
   strict "answer only from these excerpts, cite every claim with its [n] tag"
   instruction, then prints a Sources list. The model may summarise but cannot add
   equations or page numbers that are not in the excerpts. Still verify the [n]
   tags against the printed Sources before relying on the answer.
7. **(On request only) Scaffold.** If — and only if — the user explicitly asks for
   code, hand the cited governing equation + BC types to the finite-difference
   solver conventions in `.github/instructions/heat-equation-solver.instructions.md`,
   and note in a comment which page/equation each modeled term comes from.

## Output Format
- State the governing equation (LaTeX), then its citation on the next line.
- List each boundary condition with its own citation.
- End with a short "Sources" list of the distinct pages/equations used (the
  `answer` command already emits this).
- If any part is uncited, flag it plainly as not found in the textbook.

## Quality Check (before replying)
- [ ] Every equation and BC has a page/equation citation from an actual hit.
- [ ] No governing equation stated from memory without a supporting passage.
- [ ] Citations copied verbatim from `heat_rag ask` output (no invented page numbers).
- [ ] Gaps and ambiguities are called out, not papered over.

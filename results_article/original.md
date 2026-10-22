# Original SCRS manuscript — PDF-derived text transcription



> Source: `SCRS_Manuscript.pdf` (35 pages, supplied with the research materials). Running headers and page numbers are removed; line wrapping is normalized only for readability. The article's wording, reported values, equations, captions, and source inconsistencies are retained. Figures are represented by their captions, not embedded images.



---



# Symbolically-Compiled Reasoning Serving (SCRS): A Three-Tier Neuro-Symbolic Architecture for Deterministic and Cost-Efficient Inference of Large Language Models

**Mohammad Reza Bagheri K.**

Bagheri K. Mohammad Reza, affiliations, and funding acknowledgements are attached to this article.

October 2026.

## Abstract

Serving large language models (LLMs) in retrieval-augmented, reasoning-intensive applications faces three recurring structural inefficiencies: (i) the quadratic pre-fill cost of injecting long raw documents into the model context; (ii) the repeated regeneration of thousands of chain-of-thought tokens for requests that, although superficially different, share the same underlying decision topology; and (iii) the invocation of multi-billion-parameter models for the predominantly low-entropy, syntactic continuation of otherwise predictable text. This paper presents SCRS (Symbolically-Compiled Reasoning Serving), a three-tier serving architecture that converts inference from run-time textual interpretation into a compile–execute–render pipeline. At index time, Tier I compiles raw documents into typed symbolic propositional capsules and pre-computes position-decoupled key–value (KV) states by deferring rotary position embeddings (RoPE) to load time. At request time, Tier II maps each query onto a typed decision graph, retrieves structurally isomorphic candidate patterns, admits them through a hard transfer-compatibility gate, and executes them on a deterministic predicate runtime whose halting behaviour and output uniqueness are formally guaranteed. At generation time, Tier III renders the verified execution trace with a small local language model and escalates to the oracle LLM only at high-entropy branch points, where a short sequence of anchor tokens induces conditional entropy collapse. We state and prove formal guarantees for the Tier II runtime, analyse the entropy-collapse effect of anchor injection, and derive an honest expected-cost model that explicitly accounts for cache misses, bail-outs, and fallback traffic. An analytical projection, calibrated against published component measurements rather than new deployment data, suggests that for rule-governed workloads the architecture can

plausibly reduce projected serving cost by up to 78.4% and projected median end-to-end latency by 88.8%, while cross-domain pattern transfer is prevented by construction. A complete reproducibility protocol, a pinned reference stack, and a validation benchmark design are specified.

SCRS developed in Oxenn, as the infestructres for a Multi-tenant SEO/AEO/GEO SaaS.

Keywords: large language model serving; inference cost optimisation; speculative and cascade decoding; semantic caching; retrieval-augmented generation; prompt compression; neuro-symbolic systems; reproducibility.

## 1. Introduction and Problem Formulation

### 1.1 Motivation

The dominant engineering paradigm for systems built on large language models treats every incoming query q as a novel event. In a standard reasoning-oriented retrieval-augmented generation (RAG) pipeline [3], the raw text of the retrieved documents is concatenated with the query, the whole sequence is pre-filled by the model, an autoregressive chain-of-thought (CoT) trajectory is sampled [4], and only then is the user-visible answer produced. Modern reasoning models make this pattern considerably more expensive, since intermediate deliberation can consume thousands of tokens per request [5]. The end-to-end serving time and cost of such a pipeline can be approximated by the following latency model:

TE2E(q) = Tretr(q) + O(∣q∣ + ∣Draw∣) + (∣ZCoT∣ + ∣Yout∣) · τdec(ΘOr) 2 (1)

where Draw = {d1, …, dk} is the set of retrieved text documents, ZCoT is the intermediate reasoning token sequence, Yout is the final answer, and τdec(ΘOr) is the per-token decode time of the oracle model with parameters ΘOr, dominated by memory-bandwidth transfers of model weights [6]. Equation (1) exposes three structural inefficiencies, each of which has been studied in isolation but not yet unified within a single serving architecture.

Context bloat and prefix-cache invalidation. Natural language carries substantial syntactic redundancy, so raw retrieved documents contribute many tokens that carry little decision-relevant signal; moreover, long contexts are known to degrade retrieval fidelity inside the model itself [23]. Because the ordering of retrieved documents changes from query to query, standard prefix-caching mechanisms — which reuse KV states only for identical position-aligned prefixes — are invalidated after the first divergent document. This position dependence is a direct consequence of rotary position embeddings (RoPE) [2] and the causal attention mask, and it has motivated recent position-agnostic KV-reuse schemes that require selective re-computation of attention between cached segments [8, 9]. The cost of the quadratic pre-fill term in Equation (1) therefore recurs for almost every request in multi-document RAG traffic.

Isomorphic reasoning redundancy. In rule-governed domains — contract and SLA auditing, financial-regulation compliance, technical incident diagnosis — the space of surface problems is unbounded, but the space of decision topologies is small, finite, and highly repetitive. A payment-delay dispute and a delivery-penalty dispute may differ in every literal token while sharing an identical reasoning skeleton. Existing semantic caches for LLM workloads [11] retrieve by embedding similarity of raw text; they cannot recognise logical isomorphism, and worse, they may return a structurally similar but normatively incompatible pattern, producing confident yet invalid answers. Consequently, the pipeline regenerates thousands of near-identical CoT tokens [4, 5] for problems whose reasoning structure has already been solved before.

Token-level entropy asymmetry. Empirically, the conditional token distributions of language models are sharply peaked for most positions: entropy-rate studies [19] and analyses of neural text degeneration [20] show that a large fraction of generated tokens are near-deterministic continuations. This is precisely the observation exploited by speculative decoding, where a small draft model proposes tokens that the large model accepts in roughly 70–85% of positions [12, 13]. Routing every token — including trivially predictable syntactic glue — through the oracle model ΘOr is therefore a systematic waste of memory bandwidth and accelerator time; the oracle is genuinely needed only at the small number of high-entropy branch points where the decision direction is undetermined.

### 1.2 Approach and Contributions

SCRS addresses the three inefficiencies simultaneously and within one typed contract discipline, rather than as three independent optimisations. The architecture is organised as three orthogonal tiers connected by explicit data contracts: an index-time compiler that produces symbolic propositional capsules and reusable KV states; a hardened just-in-time (JIT) reasoning layer that retrieves, validates, and deterministically executes compiled decision graphs; and a token-level co-processor that renders the verified result with a small local model and escalates to the oracle only at measured uncertainty spikes. The contributions are as follows.

C1. Index-time propositional compilation. A representation that compiles raw documents into typed symbolic capsules (predicates, typed key–value facts, timestamps, and provenance), together with an information-preservation invariant that scopes exactly which question families the capsule set is required to answer (Section 4).

C2. Position-decoupled KV states. A capsule-level KV pre-computation scheme that stores pre-RoPE key vectors and applies position rotations at load time, reducing per-request capsule loading to a lightweight vector operation and composing with selective cross-attention re-computation for cache fusion (Section 4.3).

C3. Hardened isomorphic reasoning JIT. A compiled decision-graph format with canonical serialisation, a separation between topology hashing and template-identity hashing, a transfer-compatibility gate with domain, precondition, and exclusion checks, and a deterministic predicate runtime with statically validated acyclicity and typed symbol binding (Section 5).

C4. Entropy-interrupt co-processing. A token-level routing scheme in which a small local model performs high-speed rendering, a dual criterion (Top-K Shannon entropy and confidence margin) triggers hard interrupts, and the oracle injects a small number of anchor tokens that collapse the small model's conditional entropy (Section 6).

C5. Formal analysis. Halting and determinism guarantees for the Tier II runtime (Theorem 1), a conditional-entropy collapse property of anchor injection under explicit assumptions (Proposition 1), and an honest expected-cost model that

includes miss, bail-out, and fallback terms (Theorem 2) (Section 7).

C6. Reference implementation and reproducibility protocol. A pinned reference stack, fixed seeds and thresholds, a complete pipeline algorithm, and a benchmark design with adversarial cross-domain and stale-evidence traps; all performance figures in this paper are clearly labelled as analytical projections, not deployment measurements (Sections 8 and 9).

### 1.3 Scope and Positioning

To keep the claims of this paper verifiable, we state explicitly what SCRS is not. It is not a replacement for large reasoning models: whenever no verified pattern matches, or evidence is stale, the system falls back to the oracle and pays its full price, and the honest cost model of Section 7 quantifies exactly this regime. It is not a lossless decoding scheme: unlike speculative decoding with rejection sampling [12, 13], anchor tokens produced by the oracle are accepted unconditionally, so the rendered output distribution is not identical to the oracle's distribution; Section 6.3 discusses this trade-off and an optional verification mode. Finally, all quantitative end-to-end figures reported in Section 9 are projections of the analytical cost model under stated assumptions; they are intended to make the design-space structure falsifiable and testable, and the paper provides the protocol under which they should be confirmed or refuted. We regard this separation between architecture guarantees (provable), cost behaviour (projectable), and quality effects (hypotheses requiring measurement) as a methodological contribution in its own right.

### 1.4 Paper Organisation

Section 2 reviews related work. Section 3 states the design principles and gives an architectural overview. Sections 4–6 specify the three tiers. Section 7 presents the formal analysis, and Section 8 documents the reference implementation and reproducibility protocol. Section 9 develops the illustrative projection and the validation plan. Section 10 discusses limitations and threats to validity, and Section 11 concludes. Appendix A contains the full proofs, and Appendix B gives the capsule schema and the predicate grammar.

## 2. Background and Related Work

### 2.1 Autoregressive Decoding and Speculative Verification

Autoregressive decoding of transformer language models [1] is memory-bandwidth bound: generating one token requires streaming the full parameter set through the accelerator [6]. Speculative decoding [12] and its rejection-sampling formulation [13] amortise this cost by letting a small draft model propose multi-token spans that the large model verifies in parallel, accepting spans with probability one under the large model's distribution. Subsequent work broadens the mechanism: Big Little Decoder decouples draft and verify scopes [14]; Medusa augments the target model with multiple decoding heads [15]; EAGLE drafts at the feature level [16]; LayerSkip enables self-speculation with early-exit layers [17]; and SpecDec++ adaptively controls draft length with a trained stopping head [18]. Theoretical work on entropy rates of calibrated language models [19] and the peakedness of their next-token distributions [20] explains why draft acceptance rates are high for most positions. All of these methods accelerate a fixed two-model pair at token granularity. SCRS retains the small–large division of labour but moves the granularity of reuse upward: entire reasoning structures are cached and replayed deterministically, and token-level escalation is reserved for measured uncertainty spikes rather than uniformly applied.

### 2.2 KV-Cache Management and Prefix Reuse

PagedAttention [6] made KV memory a first-class, paged resource; SGLang's RadixAttention [7] organises prefix KV reuse in a radix tree and demonstrated large speed-ups for shared prefixes; Prompt Cache [8] generalises reuse to pre-computed, reusable attention modules with explicitly marked schema fields; CacheBlend [9] recombines multiple cached KV segments non-prefix-ly and corrects their mutual attention with selective re-computation; CacheGen [10] compresses and streams KV caches to remote decoders. All these systems remain within the token-representation level of reuse. SCRS is complementary: its capsules persist pre-RoPE key states so that position-dependent rotation can be deferred to load time — a design point adjacent to Prompt Cache [8] and CacheBlend [9] — while the higher-level decision logic is compiled separately into symbolic graphs that no KV-level mechanism can express.

### 2.3 Semantic Caching and Its Failure Modes

GPTCache [11] popularised embedding-similarity caching of prompt–response pairs for LLM applications, and cascade/routing systems such as FrugalGPT [24] and RouteLLM [25] choose between cheap and expensive models per query. The documented weakness of similarity-only caching is that embedding closeness is neither necessary nor sufficient for answer equivalence: two lexically close queries may fall under incompatible normative regimes, while two lexically distant queries may share one reasoning structure. SCRS adopts a strict defence-in-depth stance: vector retrieval (an HNSW index [26]) only nominates candidates; acceptance is decided by an explicit compatibility gate over domain identity, jurisdiction, adapter version, preconditions, and exclusions (Section 5.3), and execution itself is deterministic, so an accepted pattern cannot silently deviate from its compiled semantics.

### 2.4 Context Compression for Retrieval-Augmented Generation

RAG grounds generation in retrieved evidence [3], but injected raw text inflates pre-fill quadratically and dilutes attention [23]. Prompt-compression systems attack this at the token level: LLMLingua removes low-information tokens with a small scorer [21], and LongLLMLingua adds question-aware coarse-to-fine compression for long documents [22]. Self-RAG [30] trains the model to critique and retrieve adaptively. These approaches compress inside the language representation. SCRS instead compresses across representations: at index time, documents are compiled into typed propositional capsules whose semantics are validated once, and only capsules — not raw prose — are ever re-loaded at request time. The two families are composable, since a capsule store can also serve as a compressed evidence source for token-level compressors.

### 2.5 Structured and Constrained Execution of LLM Pipelines

Grammar-constrained decoding [27] guarantees syntactic well-formedness of generated artefacts by masking logits against a formal grammar; SGLang [7] executes structured programs that interleave prompts, parallelism, and control flow; agentic frameworks such as ReAct [29] interleave reasoning traces with tool calls. SCRS differs in what is compiled: not the output format but the decision procedure itself. The compiled pattern is an acyclic typed decision graph whose

predicate language is deliberately restricted (Section 5.4), which is exactly what enables the halting, determinism, and soundness guarantees of Section 7 — properties that free-form agent traces do not carry.

### 2.6 Research Gap

In summary, existing systems accelerate tokens (speculative decoding), reuse token representations (KV caching), cache raw exchanges (semantic caching), compress prompts (token pruning), or structure outputs (constrained decoding). No published serving architecture, to our knowledge, unifies index-time symbolic compilation of the evidence base, hardened reuse of complete reasoning structures under an explicit transfer-safety contract, and entropy-driven escalation between a local small model and an oracle — with formal execution guarantees and an honest cost accounting of the fallback regime. SCRS is designed to occupy precisely this gap.

## 3. System Overview and Design Principles

### 3.1 Design Principles

Four principles govern every component of SCRS, and each exists to eliminate a specific class of failure observed in ad-hoc LLM serving stacks. They are stated here because the formal guarantees of Section 7 refer back to them.

P1 — Typed data contracts. Every interface between tiers carries explicitly typed payloads: capsules with typed key–value fields, decision graphs with a typed symbol table, traces with typed node verdicts. Untyped string plumbing is excluded by construction. Typed contracts are what make static validation, provenance tracking, and deterministic re-execution possible; they play the role that intermediate representations play in compilers.

P2 — Retrieval is not acceptance. Vector similarity (an HNSW index [26]) may only nominate candidates. Admission to automatic execution requires an independent, hard compatibility gate over domain identity, preconditions, and exclusions (Section 5.3). This separation prevents the well-documented false-positive transfers of embedding-only semantic caches [11] from reaching the execution stage, let alone the user.

P3 — Fail-safe fallback. Any anomaly — a missing symbol, an expired piece of

evidence, a violated precondition, a graph that fails static validation — halts the fast path and routes the request to the oracle with explicitly marked fallback payloads. The system never silently degrades: a bail-out is a visible, logged, and metered event, and its expected cost is a first-class term in the cost model of Section 7.

P4 — Honest telemetry. Every oracle token consumed — reasoning, fallback, and anchor tokens alike — is attributed to the request that caused it. Performance reporting may not exclude guard overheads or bail-out costs. This principle is the reason Section 9 can be explicit about which numbers are projections and which assumptions they rest on.

### 3.2 Architectural Overview

Figure 1 depicts the three tiers and their contracts. The index-time tier runs once per document: raw text is compiled into typed propositional capsules, which are stored both as symbolic records and as position-decoupled KV states, and indexed for retrieval. The request-time tier runs once per query: the query is mapped to a typed problem structure, structurally isomorphic reasoning patterns are retrieved, and admitted patterns are executed to completion on a deterministic predicate runtime, yielding a verified execution trace. The token-time tier runs once per output token: a local small model renders the trace into prose, monitors its own uncertainty, and escalates to the oracle only at high-entropy branch points.

*Figure 1. The SCRS three-tier architecture. Solid boxes are deterministic components; dashed red boxes are oracle (large-model) invocations, which are the only unbounded-cost paths in the system.*

A complete request proceeds as follows. (a) The structural extractor (a small model at temperature 0) converts the user query into a typed problem structure containing a canonical signature, a symbol table, and evidence intents. (b) The signature is embedded and issued against the pattern index; the top-k candidates are ranked by cosine similarity. (c) Each candidate in turn must pass the transfer-compatibility gate; the first admissible candidate is selected, otherwise the system falls back. (d) The selected graph's evidence specification is resolved against the capsule store, with freshness and confidence checks. (e) The predicate runtime executes the graph deterministically, producing either a completed verified trace or a typed HALTED_* verdict (which triggers fallback). (f) The trace and capsules are rendered by the local model under entropy-interrupt control. (g) Telemetry records the path taken, the tokens consumed per component, and every guard decision. The remainder of the paper specifies each of these steps.

## 4. Tier I: Index-Time Symbolic Propositional Capsules

### 4.1 Capsule Formalisation

Let d be a raw document of length |d| tokens. The index-time compiler K maps d to a typed capsule c, a structured record rather than a token sequence:

c = ( docid , sourcetype , tpub , P , R ) (2)

where tpub is the publication timestamp; P = {p1, …, pm} is a set of predicates in a normalised (subject, predicate, object, condition, exception) form over the domain vocabulary; and R = {(kj, vj, τj)} is a set of typed key–value facts (numeric quantities, thresholds, enumerations, and units) with declared data types. Extraction is performed by a small model at temperature 0 with a fixed seed and a grammar-constrained output format [27], so that compilation is a repeatable function rather than a sampling process. A full JSON schema example is given in Appendix B.

### 4.2 Information-Preservation Invariant

Compilation is intentionally lossy with respect to surface form — ornamental phrases, rhetorical preambles, and duplicated clauses are discarded — but it must not be lossy with respect to the decision-relevant content of the domain. We therefore scope preservation to a declared question family Q of the domain, rather than to arbitrary ad-hoc queries: for every question Q in the family, answering from the capsule set must be information-equivalent to answering from the raw document. Formally, the compiler is required to satisfy

I(A(Q); Draw) − I(A(Q); K(Draw)) ≤ εloss (3)

for a tolerance εloss accepted by the domain owner, where A(Q) denotes the domain-relevant answer and I(·;·) mutual information. We state this invariant honestly: it is a specification and a validation obligation, not an automatic property. In practice it is operationalised as a checklist of representative question families per domain (obligations, deadlines, thresholds, exemptions, exceptions), each with golden answers, and the extractor output is regression-tested against them at index time; Appendix B shows the schema fields that carry this provenance. Under the invariant, the token compression ratio

∣K(d)∣ ρ = 1− (4) ∣d∣

is bounded by the density of predicate-bearing content in the domain. For contract-style and regulatory prose, where hedging and boilerplate dominate, the design target is ρ ≥ 0.75; the upper end (ρ ≈ 0.88) is reached on dense, well-structured corpora with little redundancy. Compression below the target indicates extractor under-coverage and blocks promotion of the affected capsules, rather than being silently accepted.

### 4.3 Position-Decoupled KV States

To eliminate capsule pre-fill at request time, the KV states of every capsule are computed once at index time, before any positional rotation is applied. For transformer layer l, the compiler stores

(l) (l−1) (l) (l) (l−1) (l) Kunrot(c) = H (c) WK , V (c) = H (c) WV (5)

i.e., the raw projections of the capsule's hidden states under the key and value matrices [1]. At request time, when capsule c is placed at token offset m within the assembled context, no attention arithmetic is re-run; instead the stored keys receive the RoPE rotation [2] for offset m:

Kactive(c, m) = RΘ,m ⊙ Kunrot(c) (l) (l) (6)

which is an O(|c| · dmodel) vector operation instead of the O(|c| · dmodel²) multi-layer attention computation, and it removes the capsule from the quadratic pre-fill term of Equation (1) entirely. Two caveats are documented rather than hidden. First, stored states are model- and checkpoint-specific: the KV store is versioned with the model identity and invalidated on any model upgrade. Second, cached segments do not attend to each other; as CacheBlend [9] analyses, cross-segment attention between cached blocks requires selective re-computation of a small subset of attention rows. SCRS adopts the same remedy: interactions among capsules and between capsules and the query are recomputed selectively at load time, at a cost that scales with the number of co-loaded capsules rather than with their length; Prompt Cache [8] provides an alternative modular-reuse formulation. The freshness gate attached to every capsule (a timestamp check against Δtmax and a minimum confidence cmin declared in the evidence specification) prevents stale evidence from entering the context silently.

## 5. Tier II: Hardened Isomorphic Reasoning JIT

### 5.1 Compiled Reasoning Graphs

A compiled reasoning pattern is an eight-tuple:

G = ( V , E , vroot , Σvars , Φev , Λax , Escope , νmeta ) (7)

Here V is a finite set of decision nodes (1 ≤ |V| ≤ Nmax); each node vi carries a typed predicate ψi in the guarded predicate language Lpred (Appendix B) and a verdict code ωi rendered at the end. E ⊆ V × V × {TRUE, FALSE} is a labelled edge set such that (V, E) is strictly acyclic — enforced statically before registration, not trusted from the authoring tool. Σvars is the typed symbol table: every symbol (e.g., a downtime-hours figure) has a declared type in {ENTITY, NUMBER, BOOLEAN, STRING_ENUM, TIMESTAMP} and a provenance requirement. Φev is the evidence specification: for each context-dependent symbol it declares the admissible source types, the maximum evidence age Δtmax, and the minimum confidence cmin. The scope envelope Escope bundles domain identity, jurisdiction, adapter version, a transfer-permission flag, a compatibility set, mandatory preconditions Ppre, and invalidating exclusions Xexcl; νmeta carries lifecycle metadata (status, shadow-validation counters, axiom version).

### 5.2 Canonical Serialisation: Topology Hash versus Identity Hash

A recurring error in pattern reuse is to treat two graphs as interchangeable because they use the same operators. SCRS separates two distinct hash identities. The topology hash captures decision structure: a canonical serialiser performs a pre-order depth-first traversal from the root, renders every predicate in an alphabetically sorted normal form, and replaces every symbol by its declared type, so that syntactically different but structurally identical graphs collide:

Htopo(G) = SHA - 256 ( IRVer ∥ sort(Σvars) ∥ DFS(vroot , E , Lpred ) ) (8)

The topology hash is used only for retrieval and analytics — never as a database key. The template-identity hash binds the pattern to its normative context and is the primary key:

Hid(G) = SHA - 256 ( Htopo(G) ∥ domain ∥ jurisdiction ∥ adapterver ∥ sort(Λax ) )(9)

This separation has a precise consequence: two structurally isomorphic

graphs from different domains (or different jurisdictions, or different adapter versions) share neither identity nor storage slot, so a cross-domain hit is impossible at the key level. Retrieval may still nominate them as candidates — which is exactly what the compatibility gate of Section 5.3 is designed to reject explicitly, and what the trap design of Section 9 measures.

### 5.3 The Transfer Compatibility Gate

Retrieval returns candidates with cosine similarity sim(e_q, e_G) ≥ θ_cand against the query signature embedding. A candidate reaches the deterministic executor only if the boolean gate

Vtr(Sq,G) = 1(verified(G)) ∧ 1(dom(Sq) = dom(Escope))

∧ 1(Ppre ⊆ Sq.pre) ∧ 1(Sq.excl ∩ Xexcl = ∅) (10)

evaluates to true, where verified(G) abbreviates the lifecycle condition status(G) = VERIFIED of Section 5.5, dom(·) is the domain identifier of the query structure and of the scope envelope, Ppre ⊆ Sq.pre requires every mandatory precondition to hold in the extracted problem structure, and the exclusion test rejects any pattern whose invalidating conditions Xexcl intersect the query's exclusion set. All four conjuncts are evaluated on typed fields — none involves a similarity score. The gate is deliberately conservative: a reject is cheap and safe (the request proceeds to the oracle), whereas a wrong accept is the single most dangerous event in the system, as the cross-domain trap analysis of Section 9 makes explicit. As a worked example, a server-downtime SLA credit pattern and a pre-sale handover-delay pattern may be near-identical in embedding space (both concern contractual delay compensation); the gate rejects the transfer because their domain identifiers, precondition vocabularies, and statutory references differ, and the query falls back to the oracle for correct treatment.

### 5.4 Executor Semantics and Static Validation

The predicate language L_pred is deliberately tiny: boolean connectives, comparisons, bounded arithmetic on typed values, and set membership over enumerated types; its grammar (Appendix B) is non-recursive and grammar-constrained generation [27] is used at authoring time. Before a pattern may be registered, a static validator runs a three-colour depth-first search from the root: it

rejects any graph containing a back-edge (which would create a cycle), verifies that every non-terminal node has well-typed outgoing edges for both TRUE and FALSE verdicts, checks depth against D_max = 16, and checks every predicate against the symbol table for type correctness and binding completeness. Only graphs that pass are persisted, and always with lifecycle status EXPERIMENTAL.

At run time the executor walks the graph from the root. At each node it evaluates ψ_i under the bound symbol values and the freshness-checked evidence; if any required symbol is missing, mistyped, or served by stale evidence, execution stops immediately with a typed verdict HALTED_MISSING_SYMBOL, HALTED_TYPE_MISMATCH, or HALTED_STALE_EVIDENCE, and the request is routed to the oracle with the partial trace attached as context. Because the graph is acyclic and each step strictly increases node depth, evaluation terminates in at most |V| steps; Section 7 makes this precise. The output of a completed run is a verified execution trace T_exec: the sequence of visited nodes, their predicate evaluations, the bound values used, and the terminal verdict — an audit artefact that downstream rendering (Tier III) must not contradict.

### 5.5 Pattern Lifecycle: Promotion and Invalidation

Newly compiled patterns enter the store as EXPERIMENTAL and are never auto -executed. Promotion to VERIFIED requires one of two evidence paths: agreement of the pattern's outcome with the oracle's outcome on M consecutive shadow executions (with M a per-domain constant), or explicit expert confirmation. Demotion to DEPRECATED is automatic whenever the axiom version bound in the pattern (a hash of the governing rule set Λ_ax, joined to the Tier I document-versioning system) advances, when the adapter version changes, or when shadow-validation disagreement exceeds a threshold. The lifecycle exists to make the cold -start regime explicit: a freshly deployed domain mostly serves traffic through the fallback path, and the fraction served by the fast path grows only as patterns are promoted — behaviour that the cost model of Section 7 captures through p_hit and p_halt.

## 6. Tier III: Entropy-Interrupt Co-Processing

### 6.1 Dual-Criterion Interrupt

After a verified trace is produced (or fallback capsules assembled), the answer must be rendered in prose. SCRS renders with a local small language model Θ_SLM (a 7B-parameter instruct model served by a high-throughput runtime [6, 28]) and treats Θ_Or strictly as a co-processor. At each generation step t the small model emits logits over the vocabulary; taking the K = 10 highest-probability tokens and renormalising yields a local distribution, from which two cheap statistics are computed inside the sampling loop (well under 0.1 ms per step on the reference hardware):

p t,i Ht = − ∑Ki=1πt,i log2 πt,i , πt,i = K (11) ∑ p j=1 t,j

ΔPt = p(1) − p(2) (12)

where pt,i are the Top-K probabilities sorted in decreasing order. The first statistic measures overall distributional uncertainty at the step; the second measures how decisive the top choice is even when entropy is moderate. A hard interrupt is issued exactly when

Trigt = 1(Ht > τH ∨ ΔPt < τΔ) ∧ 1(t − tlast > wcool) (13)

with thresholds τH (entropy, in bits), τΔ (margin), and a cooldown window wcool that prevents oscillation around a branch point. The criterion is dual on purpose: entropy alone misses the case where two plausible phrasings imply materially different commitments, and margin alone misses multi-way uncertainty. Both statistics are computed from the Top-K slice only, which is exact for the margin and a standard lower-bound surrogate for the entropy.

### 6.2 Anchor-Token Injection and Entropy Collapse

When an interrupt fires, local generation pauses; the generated prefix, the capsules, and the verified trace are sent to the oracle, which produces only k anchor tokens (k ∈ [3, 6]; k = 5 in the reference configuration):

At:t+k−1 ∼ POr ( · ∣ y<t , Csym , Texec ) (14)

The anchors are appended to the context and the small model resumes

decoding. Figure 2 illustrates the mechanism. The intent is not to outsource the whole sentence but to pin the branch: the anchors select one of the competing continuations, after which the small model's conditional distribution collapses onto the corresponding syntactic mode and the interrupt budget is not re-spent until the next genuine branch point (enforced by the cooldown). Section 6.3 analyses why this collapse is expected, and Proposition 1 states it formally.

*Figure 2. Illustrative mechanism trace of Tier III (schematic, synthesised for exposition, not measured): Top-K entropy H_t along generated positions. The local model decodes at high speed while H_t stays below the threshold τ_H; at branch points the interrupt fires and the oracle injects k = 5 anchor tokens (shaded windows), after which the conditional entropy collapses and local decoding resumes.*

### 6.3 Relation to Speculative Decoding and the Lossless Mode

It is important to position this mechanism honestly relative to speculative decoding [12, 13]. In speculative decoding, draft tokens are accepted with probability one under the target distribution via rejection sampling, so the output distribution is exactly the oracle's; the price is a verification pass over every drafted span. In SCRS, anchor tokens are accepted unconditionally: the rendered output is the small model's distribution conditioned on oracle-chosen branch points, which is not identical to the oracle's distribution. The design accepts this divergence deliberately — rendering quality is delegated to the small model except at measured uncertainty spikes — because rule-governed rendering after a

deterministic trace is exactly the regime where small models are reliable, and because the verification cost of full losslessness would erode the cost structure the architecture is built to obtain. For deployments that require distribution fidelity, an optional verification mode applies oracle rejection sampling to each anchor window, recovering the lossless guarantee of [12, 13] at a measured, switchable cost. Uncertainty-aware control of speculation effort has precedent in adaptive draft-length control [18]; SCRS differs in that the escalation signal is consumed at render time over a pre-verified content plan, so oracle involvement is structurally capped at branch points rather than spread across all positions.

## 7. Formal Analysis

This section states the three formal results. Full proofs are given in Appendix A. Throughout, fix a verified graph G, a typed problem structure S_q, and an evidence set E_rag that satisfies the freshness and confidence requirements declared in Φ_ev whenever the run completes.

### 7.1 Theorem 1: Halting and Deterministic Execution

Theorem 1. Let G have passed the static validator of Section 5.4 (acyclicity, depth bound D_max = 16, well-typed predicates over a complete symbol table). Then the Tier II runtime (i) halts in at most |V| predicate evaluations, and (ii) produces a unique execution trace for identical inputs: for the same S_q and E_rag, the probability distribution over traces is a point mass,

Var(Texec ∣ Sq , Erag) = 0 (16)

Proof sketch. Acyclicity and the depth bound make the walk strictly depth-increasing, so it terminates; the predicate language is non-recursive, total, and side -effect-free on typed values, so each node contributes exactly one boolean. Two cases exist at every node: either the required symbols are bound and the evidence is fresh, in which case the verdict — and therefore the outgoing edge — is a deterministic function of the input; or a binding/freshness condition fails, in which case the runtime emits a typed HALTED_* verdict at that node and stops. Randomness never enters the loop. The full argument, including the totality of the predicate semantics, is Appendix A.1.

Two remarks are in order. First, Theorem 1 covers the execution of an admitted

pattern; it makes no claim about the quality of the pattern, which is the lifecycle's business (Section 5.5). Second, determinism is what turns the trace T_exec into an audit artefact: re-running the same request reconstructs the same trace byte-for-byte, which is essential for the shadow-validation protocol used in pattern promotion.

### 7.2 Proposition 1: Conditional Entropy Collapse after Anchor Injection

Proposition 1. Let the rendering reach step t with Top-K entropy above the threshold, and suppose the latent decision underlying the continuation is a variable Z with competing values z_1, …, z_m (e.g., whether a force-majeure claim is accepted). Let A_k be the anchor sequence injected by the oracle, and assume that A_k determines Z, i.e., it carries (approximately) all the conditional uncertainty of Z given the prefix: I(Z; A_k | y_<t) ≈ H(Z | y_<t). Then the small model's uncertainty about subsequent tokens is reduced by the information the anchors carry about the continuation:

HSLM(Yt+k ∣ y<t , Ak) = HSLM(Yt+k ∣ y<t) − I(Yt+k ; Ak ∣ y<t) (15)

and, to the extent that the post-anchor uncertainty of Yt+k is driven by Z rather than by residual local ambiguity, HSLM(Yt+k | y<t, Ak) ≪ τH, so the next interrupt does not fire until a genuinely new branch point. The identity is the chain rule for conditional mutual information and is exact; the useful reading — that anchors which resolve the latent decision collapse the distribution — is an assumption-driven consequence, and its quantitative strength is precisely the information content I(Yt+k; Ak | y<t), which Section 9's validation protocol measures rather than assumes. Appendix A.2 gives the derivation and discusses when the assumption fails (anchors that are lexically decisive but normatively ambiguous).

### 7.3 Theorem 2: Honest Expected Cost and Latency

Analyses of caching architectures routinely assume a hit rate and ignore what happens on a miss. SCRS's cost model refuses this convenience. Let phit be the probability that retrieval nominates a candidate that passes the transfer gate; let phalt be the conditional probability that an admitted run nevertheless halts (missing or stale evidence discovered at run time); and let λanchor ∈ [0, 1] be the fraction of rendered tokens produced by the oracle inside anchor windows. The effective fast-

path probability is αeff = phit · (1 − phalt). The expected number of oracle reasoning tokens per request is then

E[NOr] = (1 − αeff) · NCoT (17)

where the bar denotes the mean full-reasoning length of the oracle on this workload; and the expected end-to-end latency is

E[TE2E] = Text + Tret + αeff (TDAG + TSLM(λanchor)) + (1 − αeff) (phit phalt Tbo + TOr)

(18)

with Text, Tret the extraction and retrieval costs, TDAG the deterministic execution time, TSLM(λanchor) the rendering time as a function of the interrupt load, Tbo the guard-and-abort overhead on halted admissions (retrieval, gate evaluation, and partial execution), and TOr the full oracle path. The derivation is Appendix A.3; its only assumption is independence between admission and halt events given the workload, which the telemetry of Section 8 can check. The salient property of Equation (18) is that the miss regime is priced explicitly: as αeff → 0 the architecture degrades gracefully to baseline-plus-guard-overhead, never below it. This is the formal counterpart of design principle P3.

## 8. Reference Implementation and Reproducibility Protocol

### 8.1 Pinned Reference Stack

To make every number in this paper reproducible by an independent group, the reference implementation pins the full stack. The orchestrator runs on Node.js 22 LTS with TypeScript 5.6 and Drizzle ORM over PostgreSQL 16.4 with the pgvector 0.7.4 extension. The vector index is HNSW [26] with cosine distance, build parameters m = 16 and ef_construction = 64, and query-time hnsw.ef_search = 40; the embedding model is text-embedding-3-small at a fixed 1536 dimensions with L2 normalisation. The small model of Tiers I and III is Qwen2.5-7B-Instruct [28] quantised to FP8 and served by vLLM 0.6.x [6] on a single NVIDIA L40S (48 GB). Oracle calls in the projection of Section 9 are costed as a frontier-class API model; the stack is deliberately agnostic to the specific provider.

### 8.2 Pinned Parameters and Determinism

All structural extraction and graph compilation calls run with temperature 0.0,

top_p = 1.0, and seed = 42. The Tier III monitors are pinned to τ_H = 1.85 bits, τ_Δ = 0.22, k = 5 anchor tokens, and w_cool = 12 tokens; the retrieval gate to θ_cand = 0.90; shadow validation to M = 20 agreeing runs. Table 1 consolidates the configuration. Seed-level pinning does not by itself guarantee bit-identical oracle outputs across providers or hardware; determinism claims in this paper are therefore confined to Tier II execution (Theorem 1), where no stochastic component exists — a distinction we consider essential to honest reporting.

*Table 1. Pinned configuration of the reference implementation.*

```text
Parameter                                                               Value                  Parameter            Value
Orchestrator                                                Node.js 22 / TS 5.6          Entropy threshold τ_H     1.85 bits
Database                                                      PostgreSQL 16.4            Confidence margin τ_Δ       0.22
Vector extension                                        pgvector 0.7.4 (HNSW)               Anchor length k        5 tokens
HNSW build / query                                      m = 16, ef_c = 64 / ef_s        Cooldown window w_cool     12 tokens
= 40
Embedding model                                             text-embedding-3-       Candidate threshold θ_cand       0.90
small (1536-d, L2)
Local SLM                                                 Qwen2.5-7B-Instruct,          Shadow-validation runs M      20
FP8, vLLM 0.6.x
Accelerator                                               1 × NVIDIA L40S (48            Extraction seed / temp    42 / 0.0
GB)
Graph depth bound D_max                                                       16            Top-K window K            10
```

All thresholds are deployment-tunable; the pinned values above define the configuration under which the projections of Section 9 are computed, and changing them requires re-running the protocol of Section 9.5.

### 8.3 The Unified Pipeline Algorithm

Algorithm 1 gives the complete request pipeline in the form implemented by the reference stack, including the telemetry contract (P4). The code-level distinction between FAST_PATH and FALLBACK_PATH bookkeeping is deliberate: it is what makes Equation (18) directly measurable at run time.

```text
ALGORITHM 1: Unified SCRS execution pipeline
--------------------------------------------------------------------------
Input : query q; domain context d_ctx
Config: theta_cand = 0.90; tau_H = 1.85; tau_D = 0.22; k = 5; w = 12
Output: answer Y; verified trace T_exec; telemetry M
--------------------------------------------------------------------------
1 t0 <- HighResTimer.now()
2 // STEP 1: typed structural extraction (SLM, pinned seed)
3 (S_q, n_ext) <- SLM.extractTypedStructure(q, d_ctx, seed=42, temp=0)
4 v_q <- Embedder.embedPinned1536(S_q.canonicalSignature)
5 // STEP 2: candidate retrieval (nomination only)
6 cands <- Index.queryHNSW(v_q, limit=3)
7 sel <- NULL
8 for cand in cands do
9      if cand.sim >= theta_cand AND StaticValidator(cand.graph).valid then
```

10 if TransferGate(S_q, cand.graph) == TRUE then sel <- cand; break 11 // STEP 3: evidence resolution and deterministic execution 12 if sel != NULL then 13 caps <- CapsuleStore.resolve(sel.graph.evidenceSpecs) // freshness gate 14 outcome <- DeterministicExecutor(sel.graph, S_q.bindings, caps) 15 if outcome.status == COMPLETED then 16 // STEP 4: entropy-interrupt rendering 17 Y <- ""; n_slm <- 0; n_anchor <- 0; n_int <- 0; t_last <- -inf 18 prompt <- BuildSafeStructuredPrompt(q, outcome.context, caps) 19 while not IsEOS(Y) do 20 (tok, topK) <- SLM.stepWithLogprobs(prompt + Y, K=10) 21 H_t <- TopKEntropy(topK); dP <- topK[0] - topK[1] 22 if (H_t > tau_H OR dP < tau_D) AND (step - t_last > w) then 23 anchors <- Oracle.generateAnchors(prompt + Y, max_tokens=k) 24 Y <- Y + anchors; n_anchor += len(anchors); t_last <- step 25 else Y <- Y + tok; n_slm += 1 26 M <- Telemetry('FAST_PATH', alpha_eff, n_ext, n_slm, n_anchor, oracleCallsAvoided = (n_int == 0), elapsed = now()-t0) 27 return (Y, outcome.trace, M) 28 // fall through on HALTED_* with partial trace 29 // STEP 5: safe fallback and experimental compilation 30 fCaps <- CapsuleStore.resolveFallback(S_q.missingEvidenceIntents) 31 (Y, newGraph, n_reason, n_out) <- Oracle.solveAndCompile(q, S_q, fCaps) 32 if StaticValidator(newGraph).valid then 33 PersistExperimental(newGraph, S_q.canonicalSignature, status=EXPERIMENTAL) 34 M <- Telemetry('FALLBACK_PATH', oracleCallsAvoided = 0, n_reason, n_out) 35 return (Y, [], M) --------------------------------------------------------------------------

### 8.4 Telemetry Schema

Every request emits a telemetry record with: the path taken (fast, halted, fallback); token counts attributed to extraction, retrieval, gate evaluation, deterministic execution, local rendering, anchor injection, and fallback reasoning; the identities and versions of every pattern and capsule touched; and the guard decisions (gate rejections with reasons, halted verdicts with codes). Aggregate reporting may only consume this schema, which makes the assumptions of Theorem 2 — in particular the independence of admission and halt — empirically checkable rather than declarative. The benchmark harness of Section 9.5 reads exactly this schema, so that projected and eventually measured quantities are comparable by construction.

## 9. Illustrative Performance Projection

No claim in this section is a deployment measurement. This section develops an illustrative projection: it feeds representative workload parameters into the analytical cost model of Section 7.3 to display the structure of the design space

across eight configurations. The purpose is falsifiability — the projection makes the architecture's expected behaviour precise enough to be confirmed or refuted by the validation protocol of Section 9.5 — and not empirical validation, which remains future work by construction.

### 9.1 Workload Model and Assumptions

The workload represents rule-governed question answering at 10,000 requests per month across three domains (commercial contract and SLA auditing; financial-regulation compliance; technical diagnosis of web architectures), with 15% adversarial cross-domain traps and 10% stale-evidence traps mixed in. Component assumptions, chosen to be conservative and traceable to the pinned stack: raw RAG context of 6,420 input tokens at the oracle; capsule compression ratio ρ = 0.85 within the target range of Section 4.2; effective fast-path probability αeff = 0.62 for tier configurations that include Tier II (a deliberate discount of the nominal hit rate to account for promotion lag and halts); anchor fraction λanchor ≈ 0.05–0.12 of rendered tokens depending on configuration; oracle pricing and decode speeds taken from published provider tariffs and the vLLM throughput literature [6, 28]. Cost includes amortised dedicated hosting of the local model plus all oracle token spend. Every row of Table 2 is derived from Equations (17)–(18) under these assumptions; changing an assumption changes the row mechanically, which is the intended behaviour of a projection.

### 9.2 Eight-Configuration Projection

Table 2. Illustrative projection of the analytical cost model across eight configurations (projection, not measurement; see Section 9.1 for assumptions).

```text
Configuration                    In-tok   Out-tok   α_eff (%)   TTFT (ms)    P50 (s)   P95 (s)   Acc. (%)   FT (%)   Cost ($)
```

## 1. Baseline (raw RAG + full      6,420    2,380        0             1,420    43.8      61.2      94.1        —      549.60

oracle)

## 2. Tier I only (capsules)        1,180    2,310        0             290      34.2      48.5      96.6*       —      381.90

## 3. Tier II only (hardened JIT)   2,440     905         62            510      16.4      45.1      95.8*       0      234.15

## 4. Tier III only (entropy        6,420     480         0              95      12.8      21.4      92.9*       —      341.20

interrupt)

## 5. Tier I + III (no JIT)         1,180     360         0              52       6.4      11.2      95.4*       —       98.40

## 6. Tier I + II (no entropy        448      878         62            140      13.1      36.0      97.1*       0      168.10

interrupt)

## 7. Naive unhardened JIT (no       380      690         78            110      10.2      31.5      81.4*     14.2†    139.50

gate)

## 8. Unified SCRS (I + II + III)    512      894         62             48       4.9      34.8      97.2*       0      118.70

In-tok / Out-tok: projected mean oracle input tokens and mean reasoning-plus-output tokens per request. α_eff: projected share of requests served entirely on the fast path. TTFT: projected time to first token. Acc.: * quality

figures are target hypotheses to be confirmed by the Section 9.5 protocol; they are model expectations, not measurements. FT (false transfer): † for configuration 7 the value models the exposure of gate-free admission to the 15% cross-domain trap subset, consistent with documented failure modes of embedding-only semantic caches [11]; for gated configurations the rate is 0 by construction of the identity hash and the gate (Section 5.2–5.3). Cost: projected USD per 10,000 requests, including amortised local-model hosting and all oracle spend; baseline-relative reductions shown in Figure 3.

*Figure 3. Projection of (a) serving cost per 10,000 requests and (b) median and 95th-percentile end-to-end latency across the eight configurations of Table 2. All values are outputs of the analytical model under the assumptions of Section 9.1, not measured results.*

### 9.3 Reading the Projection: What Each Tier Contributes

Tier I alone (row 2) attacks the input term: capsule compression reduces oracle input tokens by roughly 82%, which shortens pre-fill and raises answer quality in the projection because long, noise-bearing contexts are known to dilute attention [23]; the reasoning budget is untouched. Tier III alone (row 4) attacks the output term at token granularity: median latency drops sharply and reasoning-plus-output tokens fall by about 80%, because most rendered positions are low-entropy and never require the oracle [19, 20]. The two are complementary and compose almost multiplicatively (row 5): with compact capsules feeding a cheap renderer, the projection yields a 82.1% cost reduction even without any pattern reuse — but the reasoning itself is still regenerated per request, which the projection reflects as lower accuracy on multi-step queries than the JIT configurations (95.4% versus 97.2% targets) and as a higher interrupt load (an expected 9.6 interrupts per answer, versus 1.4 with Tier II, because the compiled trace removes most free-form decision points).

Tier II is what converts reuse into safety (rows 3, 6, 8). The hardened configuration recovers compiled reasoning rather than re-deriving it, cutting reasoning tokens by ~62% of requests entirely; the naive variant (row 7) is instructive as a counterfactual: without the transfer gate, its projected hit rate rises to 78%, but admission becomes vulnerable to cross-domain contamination on the trap subset — modelled here as a 14.2% false-transfer exposure, in line with the failure modes reported for embedding-similarity caching [11] — which drives projected accuracy below baseline (81.4%). The unified configuration (row 8) trades that unsound 16-point hit-rate gain for a 0% false-transfer rate by construction (Theorem 1, gate soundness, identity hashing), at a projected 78.4% cost reduction and an 88.8% median-latency reduction. The P95 column records the honest price of safety: the unified system falls back on 38% of requests, so its P95 latency (34.8 s) is dominated by fallback traffic and is higher than row 5's, which never falls back because it never reuses patterns. Whether that trade is correct is a policy question that the trap benchmark of Section 9.5 is designed to answer empirically.

### 9.4 Sensitivity of the Projection

Because the projection is a closed-form model, its sensitivity can be stated exactly. Cost scales linearly in (1 − αeff) through Equation (17): halving the fast-path share roughly doubles oracle reasoning spend per request, which is why promotion-lag periods (Section 5.5) dominate early-deployment economics. Latency is dominated by the fallback term for P95 and by rendering for P50; the crossover between rows 5 and 8 in the P95 column occurs exactly where (1 − αeff)·TOr exceeds the rendering savings. The compression ratio ρ enters through the pre-fill term; the projection's quality hypotheses, by contrast, are not derivable from the cost model at all, which is why Table 2 marks them as targets and Section 9.5 treats them as the primary objects of measurement.

### 9.5 Validation Protocol

The following protocol specifies how the projection is to be confirmed or refuted; it is part of the contribution, not an afterthought.

● Benchmark. 10,000 multi-step questions over the three pinned domains, of which 15% are cross-domain traps (superficially similar skeletons, incompatible governing rules) and 10% carry stale evidence injected

deliberately; golden answers and rule versions are released with version identifiers.

● Configurations. The eight rows of Table 2, each running the pinned stack of Table 1 with fixed seeds; at least three repetitions per configuration with independent document shuffles.

● Metrics. Domain-expert-graded accuracy on multi-step correctness; false-transfer rate on the trap subset; token counts per component from the telemetry schema; TTFT and P50/P95 latency; total cost from honest accounting including guard overheads.

● Statistical procedure. Paired comparisons against the baseline with bootstrap confidence intervals; pre-registered acceptance thresholds (e.g., the 0% false-transfer claim holds if zero cross-domain transfers are observed across all repetitions of gated configurations; cost reduction within 10% of the projection).

We deliberately publish falsifiable thresholds instead of narrative expectations: if the protocol refutes a projection row, the cost model — not the headline — is amended, and the amended model becomes the citation of record.

## 10. Limitations and Threats to Validity

### 10.1 Scope of Applicability

Open-ended and creative tasks. Tier II presumes that the reasoning of a domain can be compiled into typed decision graphs. For genuinely open-ended tasks — open brainstorming, literary writing, research exploration — the pattern space is not repetitive, the hit rate approaches zero, and the architecture reduces to Tier I plus Tier III over the fallback path. The projection of Section 9 is scoped to rule-governed workloads, and applying it elsewhere would be a misreading of the model.

Cold start and promotion lag. Because newly compiled patterns enter as EXPERIMENTAL and require M agreeing shadow runs (or expert sign-off) before promotion, a freshly deployed domain serves most traffic through the fallback path. Early-deployment economics are therefore governed by the (1 − α_eff) terms of Equations (17)–(18), and operators should budget accordingly rather than expect row-8 behaviour on day one.

Axiom drift. When governing rules change — a new tax circular, a revised rating algorithm — every pattern bound to the old axiom version must be demoted automatically. SCRS attaches the axiom hash to the pattern identity and joins it to the Tier I document-versioning system, but the correctness of invalidation is only as good as the upstream change detection: a missed regulatory amendment is outside the formal guarantees of Section 7 and constitutes a real operational risk.

### 10.2 Technical Caveats

KV-state coupling. Position-decoupled KV states are checkpoint-specific and must be invalidated on model upgrades; selective cross-attention re-computation (Section 4.3) adds a load-time cost that grows with the number of co-loaded capsules, which the latency model treats as part of T_ret but which deserves dedicated measurement in the validation protocol.

Threshold sensitivity. The interrupt thresholds τ_H, τ_Δ and the anchor length k were fixed for determinism, not because they are optimal. Entropy statistics depend on the tokenizer and the Top-K window; transferring the pinned values to another small model without re-calibration is unsafe. The calibration procedure (sweep over τ_H × τ_Δ on held-out branch points) is specified in the reproducibility protocol but its outcomes are workload-dependent.

Oracle dependence. Anchor quality is inherited from the oracle: a normatively ambiguous anchor could pass the entropy check while resolving the branch incorrectly. Proposition 1 makes this explicit — its assumption is about information, not correctness. The verification mode of Section 6.3 and the trap benchmark are the designed counterweights, but a residual risk remains on the fast path that lossless speculative decoding does not carry.

Security. Compiling documents into capsules moves the trust boundary: a poisoned source document becomes a poisoned capsule, and capsule poisoning is more persistent than prompt-level injection because capsules are reused across requests. Mitigations in the reference design (source-type whitelisting in Φ_ev, provenance fields, confidence minima, shadow validation) reduce but do not eliminate this exposure; a dedicated adversarial evaluation of capsule poisoning is required before deployment in adversarial environments, and we flag it as an open problem rather than a solved one.

Threats to validity of the projection. All Section 9 numbers derive from assumptions stated in Section 9.1; none is a measurement. The most consequential assumptions are the effective hit rate (α_eff = 0.62) and the trap-exposure model of configuration 7; both are exactly the quantities the validation protocol is designed to measure, and both are exposed as first-class parameters of the cost model rather than hidden in prose.

## 11. Conclusion

This paper argued that the apparent dichotomy between the reasoning quality of large models and the speed and cost of small ones is, for rule-governed workloads, largely an artefact of interpret-at-run-time serving. SCRS replaces that regime with a compile–execute–render pipeline: documents are compiled at index time into typed propositional capsules with position-decoupled KV states; recurring reasoning structures are compiled into hardened decision graphs that are retrieved, gated, and executed deterministically; and rendering is delegated to a local small model that escalates to the oracle only at measured entropy spikes, where a few anchor tokens collapse the residual uncertainty. Within this pipeline, halting and determinism are theorems rather than aspirations, the fallback regime is priced by an honest cost model instead of being assumed away, and cross-domain transfer of reasoning patterns is prevented by construction through identity hashing and a hard compatibility gate.

The paper is equally explicit about what remains open. The quantitative projections are model outputs awaiting the published validation protocol; quality effects of compression and anchor injection are hypotheses with falsifiable thresholds; and the security analysis of capsule poisoning is incomplete. The intended contribution is therefore twofold: a concrete, formally grounded serving architecture whose guarantees and costs can be stated separately and audited independently, and a methodological template for reporting serving research — projections labelled as projections, fallbacks priced, and validation protocols published alongside the claims they are meant to test. We believe this template is applicable beyond SCRS, wherever learned and symbolic components are composed under deployment constraints.

Declarations Author contributions. 【 To be completed upon de-anonymisation: conceptualisation, formal analysis, implementation, evaluation, and writing contributions per CRediT taxonomy. 】 Conflict of interest. 【 The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper. 】 Data availability. 【 The benchmark questions, golden answers, rule-version metadata, and telemetry schemas supporting the validation protocol of Section 9.5 will be deposited in a public repository upon acceptance; the URL is withheld for double-blind review. 】 Code availability. 【 The reference implementation of Algorithm 1 (TypeScript, pinned stack of Table 1) will be released under an open-source licence upon acceptance; the repository URL is withheld for double-blind review. 】 Funding. 【 Grant numbers and funding bodies to be inserted upon de-anonymisation.】

References [1] Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, L., and Polosukhin, I. Attention is all you need. Advances in Neural Information Processing Systems (NeurIPS) 30, 2017. arXiv:1706.03762. [2] Su, J., Ahmed, M., Lu, Y., Pan, S., Bo, W., and Liu, Y. RoFormer: Enhanced transformer with rotary position embedding. Neurocomputing 568:127063, 2024. arXiv:2104.09864. [3] Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., and Kiela, D. Retrieval-augmented generation for knowledge-intensive NLP tasks. Advances in Neural Information Processing Systems (NeurIPS) 33, 2020. arXiv:2005.11401. [4] Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q. V., and Zhou, D. Chain-of-thought prompting elicits reasoning in large language models. Advances in Neural Information Processing Systems (NeurIPS) 35, 2022. arXiv:2201.11903. [5] Guo, D., Yang, D., Zhang, H., Song, J., Zhang, R., Xu, R., Zhu, Q., Ma, S., Wang, P., Bi, X., et al. DeepSeek-R1: Incentivizing reasoning capability in LLMs via reinforcement learning. arXiv:2501.12948, 2025. [6] Kwon, W., Li, Z., Zhuang, S., Sheng, Y., Zheng, L., Yu, C. H., Gonzalez, J. E., Zhang, H., and Stoica, I. Efficient memory management for large language model serving with PagedAttention. In Proceedings of the 29th Symposium on Operating Systems Principles (SOSP), 2023. arXiv:2309.06180.

[7] Zheng, L., Yin, L., Xie, Z., Sun, C., Yu, J., Li, S., Liu, Y., Hao, Y., Chen, Y., Wang, J., Li, X., Lin, J., Zhong, Y., Hou, W., Wang, N., Wang, X., Cui, S., Li, S., Zhou, Y., Li, R., Chen, K., Li, Z., and Lin, Z. SGLang: Efficient execution of structured language model programs. Advances in Neural Information Processing Systems (NeurIPS) 37, 2024. arXiv:2312.07104. [8] Gim, I., Chen, L., Park, S., Yu, M., Hao, T., Jang, H., Ye, F., and Chowdhury, M. Prompt cache: Modular reuse of attention across generative models. In Proceedings of Machine Learning and Systems (MLSys) 7, 2024. arXiv:2311.05219. [9] Yao, H., Chen, Y., Xin, J., Lin, X., Arora, C., and Joshi, A. CacheBlend: Fast large language model serving for RAG with cached knowledge fusion. In Proceedings of the 20th European Conference on Computer Systems (EuroSys), 2025. arXiv:2405.16444. [10] Liu, Y., Li, H., Du, K., Yao, J., Cheng, Y., Huang, Y., Lu, S., Maire, M., Hoffmann, H., Holtzman, A., and Jiang, J. CacheGen: KV cache compression and streaming for fast large language model serving. In Proceedings of the ACM SIGCOMM Conference, 2024. arXiv:2310.07240. [11] Bang, F. GPTCache: An open-source semantic cache for LLM applications enabling faster answers and reduced costs. In Proceedings of the 3rd Workshop for Natural Language Processing Open Source Software (NLP-OSS) at EMNLP, 2023. arXiv:2311.04936. [12] Leviathan, Y., Kalman, M., and Matias, Y. Fast inference from transformers via speculative decoding. In Proceedings of the 40th International Conference on Machine Learning (ICML), 2023. arXiv:2211.17192. [13] Chen, C., Borgeaud, S., Irving, G., Lespiau, J., Sifre, L., and Jumper, J. Accelerating large language model decoding with speculative sampling. arXiv:2302.01318, 2023. [14] Kim, S., Mangalam, J., Moon, S., Malik, J., Mahoney, M. W., Gholami, A., and Keutzer, K. Big Little Decoder: Accelerating generative large language model inference. Advances in Neural Information Processing Systems (NeurIPS) 36, 2023. arXiv:2302.07863. [15] Cai, T., Li, Y., Geng, Z., Hong, H., Chen, J., Chang, E., Wu, P., Wang, J., Dao, T., and Ré, C. Medusa: Simple LLM inference acceleration framework with multiple decoding heads. In Proceedings of the 41st International Conference on Machine Learning (ICML), 2024. arXiv:2401.10774. [16] Li, Y., Wei, F., Zhang, C., and Zhang, H. EAGLE: Speculative sampling requires rethinking feature uncertainty. In Proceedings of the 41st International Conference on Machine Learning (ICML), 2024. arXiv:2401.15077. [17] Elhoushi, M., Shrivastava, A., Liskovich, D., Hosmer, B., Wurmstein, H., Lacoste, A., Lebret, X., Wojczuk, R., Ahrabian, R., and Kadra, A. LayerSkip: Enabling early-exit inference and self-speculative decoding. In Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (ACL), 2024. arXiv:2404.16710. [18] Huang, K., Guo, X., and Wang, M. SpecDec++: Boosting speculative decoding via adaptive candidate lengths. arXiv:2405.19715, 2024. [19] Braverman, M., Chen, X., Kakade, S., Narasimhan, K., Zhang, R., and Zhang, Y. Calibration, entropy rates, and memory in language models. In Proceedings of the 37th International Conference on Machine Learning (ICML), 2020. arXiv:1906.05664. [20] Holtzman, A., Buys, J., Du, L., Forbes, M., and Choi, Y. The curious case of neural text degeneration. In International Conference on Learning Representations (ICLR), 2020. arXiv:1904.09751.

[21] Jiang, H., Wu, Q., Lin, C.-Y., Yang, Y., and Qiu, L. LLMLingua: Compressing prompts for accelerated inference of large language models. In Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing (EMNLP), 2023. arXiv:2310.05736. [22] Jiang, H., Wu, Q., Luo, X., Li, D., Lin, C.-Y., Yang, Y., and Qiu, L. LongLLMLingua: Accelerating and enhancing LLMs in long context scenarios via prompt compression. In Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (ACL), 2024. arXiv:2310.06839. [23] Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., and Liang, P. Lost in the middle: How language models use long contexts. Transactions of the Association for Computational Linguistics 12:157–173, 2024. arXiv:2307.03172. [24] Chen, L., Zaharia, M., and Zou, J. FrugalGPT: How to use large language models while reducing cost and improving performance. arXiv:2305.05176, 2023. [25] Ong, I., Almahairi, A., Wu, V., Chiang, W.-L., Wu, T., Gonzalez, J. E., Kadous, M. W., and Stoica, I. RouteLLM: Learning to route LLMs with preference data. arXiv:2406.18665, 2024. [26] Malkov, Y. A., and Yashunin, D. A. Efficient and robust approximate nearest neighbor search using hierarchical navigable small world graphs. IEEE Transactions on Pattern Analysis and Machine Intelligence 42(4):824–836, 2018. arXiv:1603.09320. [27] Willard, B. T., and Louf, R. Efficient guided generation for large language models. arXiv:2308.08728, 2023. [28] Yang, A., Yang, B., Zhang, B., Hui, B., Zheng, B., Yu, B., Li, C., Liu, D., Huang, F., Wei, H., et al. Qwen2.5 technical report. arXiv:2412.15115, 2024. [29] Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., and Cao, Y. ReAct: Synergizing reasoning and acting in language models. In International Conference on Learning Representations (ICLR), 2023. arXiv:2210.03629. [30] Asai, A., Wu, Z., Wang, Y., Sil, A., and Hajishirzi, H. Self-RAG: Learning to retrieve, generate, and critique through self-reflection. In International Conference on Learning Representations (ICLR), 2024. arXiv:2310.11511.

## Appendix A. Proofs

### A.1 Proof of Theorem 1

Claim. If G has passed static validation, the runtime (i) halts in at most |V| predicate evaluations for any admissible input (S_q, E_rag), and (ii) Var(T_exec | S_q, E_rag) = 0, i.e., the trace is a deterministic function of the input.

Proof. Static validation establishes three preconditions. First, the three-colour DFS from the root found no back-edge, so (V, E) is a finite DAG; combined with the depth bound d(G) ≤ D_max = 16, every root-to-leaf path has length at most D_max. Second, every non-terminal node has well-typed outgoing edges for both truth values of its predicate, so the walk can never encounter a node it cannot leave. Third, every predicate ψ_i belongs to the guarded, non-recursive language L_pred,

whose semantics is total on well-typed, well-bound inputs: comparisons, bounded arithmetic, and set membership over declared enumerated types are defined for every value combination admissible under the symbol table, and none of them performs I/O, sampling, or global mutation.

(i) Halting. Consider the node-depth process d_0, d_1, … along the execution walk. Because the graph is acyclic, every taken edge strictly increases node depth; hence d_0 < d_1 < … and, since depths are bounded by D_max, the walk reaches a terminal node — or raises a typed halt — after at most D_max ≤ |V| steps. At each node the predicate evaluation itself terminates because L_pred is total and non-recursive. Thus the loop terminates in at most |V| predicate evaluations.

(ii) Uniqueness. Fix (S_q, E_rag). We show by induction over execution steps that the configuration (current node, remaining bindings, elapsed halts) is a deterministic function of the input. Base: the initial configuration is the root with the bindings extracted from S_q, deterministic by assumption. Step: at node v_i exactly one of two cases obtains. Case (a): all symbols referenced by ψ_i are bound and their evidence satisfies the freshness and confidence requirements of Φ_ev; by totality of the L_pred semantics, ψ_i evaluates to a unique boolean b ∈ {TRUE, FALSE}, and the labelled edge (v_i, ·, b) is unique by construction of the edge set. Case (b): some symbol is unbound or mistyped, or its evidence is stale or below the confidence floor; the runtime then emits the corresponding typed verdict HALTED_MISSING_SYMBOL, HALTED_TYPE_MISMATCH, or HALTED_STALE_EVIDENCE at v_i and stops. In both cases the next configuration is a function of the current one; no random source exists anywhere in the loop (sampling is confined to Tiers I and III, both outside this execution). Induction yields a unique trace T_exec, hence Var(T_exec | S_q, E_rag) = 0. □

### A.2 Derivation and Discussion of Proposition 1

Derivation. Let Z be the latent decision variable, A_k the injected anchor sequence, and y_<t the prefix. The chain rule for conditional mutual information gives, for any post-anchor position t + j:

HSLM(Yt+k ∣ y<t , Ak) = HSLM(Yt+k ∣ y<t) − I(Yt+k ; Ak ∣ y<t) (15)

i.e., the residual conditional entropy equals the prior conditional entropy minus the information the anchors carry about the continuation given the prefix. If the post-

anchor continuation is generated by the small model as Y | (Z, y_<t) with Z now pinned by A_k — I(Z; A_k | y_<t) ≈ H(Z | y_<t), so that P(Z = z* | y_<t, A_k) → 1 — then the multi-modal mixture over branches z_1, …, z_m is replaced by the single-branch conditional distribution, and the residual entropy is the within-branch (largely syntactic) entropy:

H_SLM(Y_(t+j) | y_<t, A_k) ≈ H_SLM(Y_(t+j) | y_<t, Z = z*),

which is low precisely because within a fixed branch the continuation is the kind of near-deterministic text that small models track reliably [19, 20]. This is the sense in which the anchors induce a collapse. Discussion of the assumption. The argument degrades exactly when A_k fails to pin Z: anchors that are lexically fluent but normatively ambiguous (e.g., 'the claim is partially acceptable') leave posterior mass on several branches, the collapse is partial, and the next interrupt fires soon after — a behaviour the cooldown window damps but does not remove. This is why the paper treats anchor quality as an oracle-inherited risk (Section 10.2) and why the validation protocol measures the empirical interrupt rate and its correlation with expert-graded correctness, rather than assuming the collapse. □

### A.3 Derivation of Theorem 2

Setup. Per request, three disjoint regimes are possible: (R1) fast path — a candidate is admitted and completes (probability α_eff = p_hit (1 − p_halt)); (R2) bail-out — a candidate is admitted but halts (probability p_hit · p_halt), paying guard-and-abort overhead T_bo and then the full oracle path; (R3) miss — no candidate passes the gate (probability 1 − p_hit), paying only extraction, retrieval, and the full oracle path. The oracle is additionally invoked in anchor windows on the fast path, contributing λ_anchor · |Y| tokens where |Y| is the rendered length.

Reasoning tokens. The oracle produces its full reasoning chain only in regimes R2 and R3, whose total probability is 1 − α_eff; hence E[N_Or] = (1 − α_eff) · N_CoT, which is Equation (17).

Latency. Every request pays T_ext + T_ret. Fast-path requests additionally pay T_DAG (deterministic execution) plus T_SLM(λ_anchor) (rendering with anchor load). Bail-out requests pay T_bo on top of the oracle path, and miss requests pay the oracle path directly; both R2 and R3 therefore contribute (T_bo-weighted or not) the same oracle latency T_Or, with total probability (1 − α_eff). Collecting terms

and using the independence of admission and halt events given the workload gives Equation (18):

E[TE2E] = Text + Tret + αeff (TDAG + TSLM(λanchor)) + (1 − αeff) (phit phalt Tbo + TOr)

(18)

The independence assumption is checkable from telemetry (Section 8.4): if staleness correlates with retrieval failure — as it will in domains with uneven freshness — the product p_hit(1 − p_halt) overstates α_eff, and the projection must use the empirically measured joint. The validation protocol of Section 9.5 therefore reports the joint distribution, not the marginals alone. □

## Appendix B. Capsule Schema and Predicate Grammar

### B.1 Capsule JSON Schema (Representative Excerpt)

The listing below shows the persisted form of one predicate and one typed fact of a capsule compiled from a service-level agreement clause; provenance and freshness fields are those consumed by Φ_ev at run time.

```text
{
"doc_id": "sla-msa-2024-071",
"source_type": "CONTRACT",                // whitelisted by Phi_ev
"t_pub": "2024-07-01T00:00:00Z",
"axiom_version": "sla-rules@2024-07",
"predicates": [{
"id": "p_014",
"subject": {"sym": "$Service",         "type": "ENTITY",
"prov": {"src": "p_001", "span": [210, 224]}},
"predicate": "QUALIFIES_FOR_CREDIT",
"object": {"sym": "$Downtime_Hours", "type": "NUMBER",
"unit": "hours", "prov": {"src": "R.k3"}},
"condition": "$Downtime_Hours > R.threshold_monthly",
"exception": "EXCL($Cause, [FORCE_MAJEURE, SCHEDULED_MAINT])"
}],
"facts": {
"R.k3": {"value": 4.5, "type": "NUMBER", "unit": "hours",
"valid_until": "2025-07-01", "confidence": 0.98},
"R.threshold_monthly": {"value": 2.0, "type": "NUMBER",
"unit": "hours", "valid_until": "2025-07-01"}
},
"kv_meta": {"model_id": "qwen2.5-7b@fp8-v3", "layers": 28,
"rope": "deferred", "status": "VERIFIED"}
}
```

*Table 3. Declared data types of the capsule symbol table and their run-time checks.*

```text
Type                                                      Value domain                  Run-time check at binding
ENTITY                                             Domain entity identifiers         Existence in entity index; source
whitelisted in Φ_ev
```

```text
Type                                               Value domain                       Run-time check at binding
NUMBER                                      Numeric quantities with units          Unit consistency; range bounds;
freshness Δt_max
BOOLEAN                                              True / false                Direct; may not shadow an unresolved
predicate
STRING_ENUM                                   Closed enumeration set             Membership in declared enumeration
TIMESTAMP                                        ISO-8601 instants                 Parse validity; freshness Δt_max
against t_now
```

A binding that fails its check raises HALTED_TYPE_MISMATCH or HALTED_STALE_EVIDENCE (Theorem 1, Case b); it is never silently coerced.

### B.2 Guarded Predicate Language (EBNF)

The run-time predicate language L_pred is intentionally minimal: no recursion, no unbounded iteration, no user-defined functions. The grammar below is the one enforced at authoring time by grammar-constrained generation [27] and re-checked statically by the three-colour validator of Section 5.4.

```text
pred    = expr ;
expr    = or_expr ;
or_expr = and_expr { "OR" and_expr } ;
and_expr = not_expr { "AND" not_expr } ;
not_expr = [ "NOT" ] comparison ;
comparison = operand ( "==" | "!=" | ">" | ">=" | "<" | "<=" | "IN" ) operand
| operand ;
operand = sym | literal | "(" expr ")" ;
sym      = "$" ident ;           (* must occur in Sigma_vars *)
literal = number | string | boolean | timestamp | enum_value ;
```

(* constraints enforced statically: 1. every sym occurs in Sigma_vars with a declared type; 2. operand types are comparable; NUMBER comparisons require equal units; 3. arithmetic is restricted to bounded binary +/- on NUMBER; 4. no recursion, no function abstraction, no I/O primitives. *)

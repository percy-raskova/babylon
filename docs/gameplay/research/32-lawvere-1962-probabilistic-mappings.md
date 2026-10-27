# 32 — Arrows that forget, objects that remember: Lawvere's category of probabilistic mappings (1962)

Read-only close reading, 2026-10-25. Question: **if a game's probabilities were morphisms in a category
rather than scalars with modifiers, what would change — and does composition really preserve history?**

Source: `lawvere-master/pdfs/1962-the-category-of-probabilistic-mappings.pdf`, 14 PDF pages: an
annotator's cover note, a 12-page typewritten seminar handout with handwritten margin notes, and an
appended 2011 email exchange. The scan has **no text layer**; every quotation below was read off the page
images (method in §6). Page numbers are the handout's own (`-n-` footer), which run one behind the PDF page:
**handout p.*n* = PDF p.*n*+1**. The cover note is PDF 1, the email is PDF 14.

Two authors occupy this document and they disagree in writing. Lawvere's typescript is the formal source.
The margin notes belong to a later reader who says, on the cover, that several of their own notes are
wrong: "in several places my initial thoughts are incorrect (e.g., P has products therefore… In fact P
does not have products or equalizers — only weak products and weak equalizers). Rather than 'correcting
them' by more markings I left them incorrect" (PDF 1). Throughout, **A** marks an annotator claim, **O** a
claim of the typescript, **D** my inference. The annotator is not a hostile witness — their errors are
instructive, because they are the errors a designer makes on first contact with this category.

---

## 0. What the document actually is

A research announcement, not a treatise. Twelve pages, three sections, no conclusion. It ends mid-program
with an open question ("is it possible to extend any process to a Markov process in a fashion which is
universal with respect to maps to (or from) Markov processes??", p.12). Almost every hard step is asserted
and deferred: associativity is stated without proof (2.7), the existence of optimal decision rules is
attributed to "topological arguments" with no hypotheses named (p.10), and the category-theoretic defects of
the construction are not discussed at all in the body — they appear only in the cover note and the 2011
email.

That shape matters for how much weight it can carry. It is the *origin* document for what later became the
standard category of Markov kernels; it is not a development of it. Everything usable is a definition, a
formula, or a construction; nothing is a theorem with a proof except by citation to the general theory.

**Two numbering systems.** The scan carries a stamped page number centred at the foot (the scan sequence,
1–14) and the handout's own `-n-` at the right. They differ by one. The title page is unnumbered and
undated; "1962" comes from the cover note, not from the document.

---

## 1. The formal machinery, as written

### 1.1 Objects: a set plus the questions that can be asked of it

> "The objects which we consider are measurable spaces. Thus, an object will be an ordered pair
> $\Omega=\langle S,\mathfrak{B}\rangle$ … where $\mathfrak{B}$ is a $\sigma$-algebra of subsets of $S$."
> (1.1.1, p.1)

A $\sigma$-algebra is closed under complement and countable union, contains $\varnothing$ and $S$ (axioms
(0)–(3), p.1). A map $f:S\to\Lambda$ into a partially ordered set is *measurable* if every sublevel set
$\{\omega \mid f(\omega)\prec\lambda\}$ is in $\mathfrak{B}$ (1.2, p.1) — the typewriter uses this
order-theoretic form rather than the usual "preimage of a Borel set" form, and it is the form that makes
"the set of worlds where utility is at most $\lambda$" the primitive measurable object.

**This is the single most game-relevant structural fact in the paper, and it is easy to read past: an
object is not a set of states, it is a set of states *together with the algebra of questions that have
well-defined answers about it*.** Two objects can have the same points and different $\mathfrak{B}$, and
they are different objects. §2.6 makes the difference operational (below).

A probability measure on $\Omega$ is $P:\mathfrak{B}\to[0,1]$ with $P(S)=1$ and countable additivity
(1.4, p.2); on a countable $S$ it is the function $p(x)=P(\{x\})$ with $\sum_x p(x)=1$ (1.5, p.2). The
Borel/Lebesgue case is mentioned in one sentence and never used.

### 1.2 What a morphism is: the whole conditional law, not a number

> **2.1** "We say $T$ is a **probabilistic mapping** from $\Omega$ to $\Omega'$ and write
> $\Omega \xrightarrow{T} \Omega'$ if and only if $T$ assigns, to each point in $\Omega$, a probability
> measure on $\Omega'$, and does so in a measurable way. More precisely, $T$ is a function of two variables
> $x\in S$, $B'\in\mathfrak{B}'$ having the properties" (p.5–6)

$$(0)\quad 0\le T(x,B')\le 1 \qquad \text{for all } x\in S,\ B'\in\mathfrak{B}'$$
$$(1)\quad T(x,S')=1 \qquad \text{for all } x\in S$$
$$(2)\quad T\Big(x,\bigcup_{i=1}^{\infty}B'_i\Big)=\sum_{i=1}^{\infty}T(x,B'_i) \qquad \text{disjoint } B'_i\in\mathfrak{B}'$$
$$(3)\quad \{x \mid T(x,B')\le a\}\in\mathfrak{B} \qquad \text{for each } 0\le a\le 1,\ B'\in\mathfrak{B}'$$

> "We will refer to $T(x,B')$ as the (conditional) $T$-probability of the event $B'$ in $\Omega'$, given the
> elementary event $x$ in $\Omega$, or as the $T$-probability that $x$ is mapped into $B'$." (p.6)

(0)–(2) say: for each $x$, $T(x,\cdot)$ is a probability measure on $\Omega'$. (3) says: for each event
$B'$, the function $x\mapsto T(x,B')$ is measurable. The annotator glosses (3) correctly as
$T(\cdot,B'):(S,\mathfrak{B})\to([0,1],\text{Borel})$ and then restates the equivalence the typescript
leaves implicit — that this is the same as $T$ being a measurable map from $\Omega$ into *the space of
probability measures on $\Omega'$* (margin, p.6). That equivalence is what §2.8 later turns into a functor.

**A morphism is therefore an entire transition table.** The scalar "probability of detection = 0.3" is not
a morphism and not a morphism's value at a point: it is one *entry* $T(x,B')$ of one kernel, at one world
$x$ and one event $B'$. Everything below follows from taking that seriously.

### 1.3 Composition: the integral, stated exactly

**2.3** For $\Omega \xrightarrow{T}\Omega' \xrightarrow{U}\Omega''$, composition is defined by

$$(T \circ U)(x,B'') \;=\; \int_{\Omega'} T(x,\mathrm{d}x')\cdot U(x',B'')$$

> "That is, $(T\circ U)(x,B'')$ is the $T(x,\cdot)$-expectation of $U(\cdot,B'')$." (p.6)

with the marginal note "$=\int_{\Omega'}U(\cdot,B'')\,\mathrm{d}(T(x,\cdot))$" and, in the annotator's
red ink, "**Note these are sampling distributions**" (p.6). In the countable case (2.4, p.6):

$$(T\circ U)(x,B'')=\sum_{x'\in S'} t(x,x')\,U(x',B''), \qquad\text{and if } S'' \text{ is countable,}\quad (T\circ U)(x,\{x''\})=\sum_{x'} t(x,x')\,u(x',x'')$$

i.e. **row-stochastic matrices multiplied in temporal order.** The typescript adds, flatly, that this is
"the correct law for composition of conditional probabilities in physical and other situations" (p.6).

**Notation warning, and it is not cosmetic.** In this paper `$\circ$` composes in *diagrammatic* order:
$T\circ U$ means "$T$ first, then $U$" — the opposite of the modern convention, where $U\circ T$ would be
"$T$ first." The convention is consistent across the paper: 2.6 reads "$P\circ T$ is the induced
distribution on $\Omega'$" for $1\xrightarrow{P}\Omega\xrightarrow{T}\Omega'$, and §3.1 writes
$(F\circ\delta)(x,\{f(x)\})$ for the observation $F$ followed by the decision rule $\delta$. Anyone
implementing from this document and anyone reading a modern restatement (Giry 1982 and everything after it)
will silently reverse every composite unless this is flagged. **D:** in a codebase, name the operation
`then` and never `compose`.

**Associativity and identities** are asserted (2.7, p.7): $T\circ(U\circ V)=(T\circ U)\circ V$; $i_\Omega$ is
the Dirac/identity kernel. The conclusion drawn is the point of the whole exercise:

> "Thus, the class $\mathcal{P}$ of all probabilistic mappings between measurable spaces, together with our
> notion of composition, is a category in the sense of Eilenberg–MacLane. Thus, the notions of functor,
> natural transformation, and adjoint functor have a well-defined meaning in connection with $\mathcal{P}$.
> The 'objects' of $\mathcal{P}$ are arbitrary measurable spaces." (2.7, p.7)

No proof of associativity is given; it is Fubini applied to the iterated integral. **O:** claimed.
**D:** true, and standard.

### 1.4 Deterministic maps are a subcategory, and the embedding is faithful

Every ordinary measurable $f:\Omega\to\Omega'$ is a probabilistic mapping via the Dirac kernel

$$T_f(x,B')=\begin{cases}1 & f(x)\in B'\\ 0 & f(x)\notin B'\end{cases}$$

("we call probabilistic mappings of this special sort **deterministic**", p.6), and the assignment is
functorial: $T_{f\circ g}=T_f\circ T_g$ (2.5, pp.6–7). The typescript calls this "a subcategory (2.7) of the
category of all probabilistic mappings" — the cross-reference is almost certainly a misprint (2.7 is the
associativity paragraph); the annotator glosses it in blue as "this subcategory $\mathcal{P}_{det}$ has
objects = measurable spaces, arrows = measurable functions" and writes **"Meas"** in the margin (p.6).

So: **the deterministic game is a subcategory of the stochastic game, and every deterministic plan is also a
stochastic one — but not conversely.** Nothing is lost by modelling deterministically, as long as you never
need to mix.

### 1.5 A measure-of-measures is still a measure (2.8–2.9)

For each object $\Omega$, let $\mathcal{S}(\Omega)$ be the set of all probability measures on $\Omega$,
equipped with the smallest $\sigma$-algebra making $P\mapsto P(A)$ measurable for every $A\in\mathfrak{B}$.
(2.8, p.7; the typescript's glyph is a script letter I transcribe as $\mathcal{S}$ — it could be
$\mathcal{D}$; nothing depends on the name.) Then for $\Omega\xrightarrow{T}\Omega'$,

$$\mathcal{S}(T)(P)(A')=\int_{\Omega}P(\mathrm{d}\omega)\,T(\omega,A')$$

so $\mathcal{S}(T)(P)=P\circ T$: the pushforward. And there is a map

$$\varphi_\Omega:\mathcal{S}(\Omega)\to\Omega,\qquad \varphi_\Omega(P,A)=P(A)$$

which is natural — the square with $\mathcal{S}(T)$, $T$, $\varphi_\Omega$, $\varphi_{\Omega'}$ commutes —
"so that $\varphi$ is a natural transformation of the functor $\mathcal{S}$ into the identity functor on
$\mathcal{P}$" (p.8). Finally:

> **2.9** "Actually $\mathcal{S}$ is co-adjoint to the inclusion of the deterministic subcategory into
> $\mathcal{P}$; i.e., … if $\Omega\xrightarrow{T}\Omega'$ is any probabilistic mapping then there is a
> unique deterministic mapping $f$ such that the diagram … is commutative." (p.8–9)
>
> "(In particular, there is a deterministic inclusion $\Omega\to\mathcal{S}(\Omega)$ and this is actually a
> retract with associated retraction $\varphi_\Omega$.)" (p.9)

Read plainly: $i\dashv\mathcal{S}$, with unit $\eta=\text{Dirac}:\Omega\to\mathcal{S}(\Omega)$ and counit
$\varphi:\mathcal{S}\to\mathrm{id}$; $\varphi_\Omega\circ\eta_\Omega=\mathrm{id}_\Omega$. The 2011 email
confirms the reading by naming the structure: "the whole Eilenberg–Moore category of the commutative pr
monad, not only the **Kleisli** category of free algebras" (PDF 14). So $\mathcal{P}$ is the Kleisli
category of what everyone now calls the Giry monad, and the paper's own §2.8–2.9 is the monad in embryo —
functor, unit, counit, and the Kleisli adjunction, with the multiplication left implicit (it is determined
by the adjunction; the paper never writes it).

Two consequences worth keeping:

1. **The type is closed under "uncertainty about uncertainty."** A distribution over distributions over
   $\Omega$ is again an object of the same kind; $\mathcal{S}\mathcal{S}$ needs no new machinery.
2. **A point is a special distribution and a distribution can always be used as a point.** The section
   $\Omega\to\mathcal{S}(\Omega)$ is not surjective, so this is an embedding with a retraction, not an
   isomorphism: you can always collapse a belief to a state, never recover the belief from the state.

Then the one place the paper reaches for a philosophical stake:

> "It is expected that this adjointness observation will aid in the analysis of various methodological
> problems such as Bohm's questions about quantum mechanics." (p.9)

One sentence, no development. Noted, not used.

### 1.6 The thing $\mathcal{P}$ has that Meas does not: convex combinations

$$P=\theta P_1+(1-\theta)P_2 \ \text{ is a probability measure, and }\ \int f\,\mathrm{d}P=\theta\!\int f\,\mathrm{d}P_1+(1-\theta)\!\int f\,\mathrm{d}P_2$$

for $0\le\theta\le1$ and bounded measurable $f$ (1.11, p.4). Because composition is integration and the
integral is linear in the measure, this extends from measures to **maps**: $(\theta T_1+(1-\theta)T_2)$ is
again a morphism, and

$$(\theta T_1+(1-\theta)T_2)\circ U=\theta\,(T_1\circ U)+(1-\theta)\,(T_2\circ U).$$

The typescript then states the design-relevant consequence at the exact point where it matters — the
decision problem of §3.1:

> "One of the 'virtues' of probability theory (and hence of the category $\mathcal{P}$) is that this general
> problem, when properly explicated, has a solution in many cases in which the corresponding deterministic
> problem does not; a basic reason for this is the **possibility in $\mathcal{P}$ of forming convex
> combinations of maps**, whereas there is no corresponding operation which produces deterministic maps."
> (p.9)

So: **mixing two plans is itself a plan; mixing two deterministic plans is not deterministic.** Randomised
strategy is native to the category and absent from the deterministic subcategory. This is the paper's
positive claim about $\mathcal{P}$, and it is the one it argues for rather than assumes.

### 1.7 What is missing: products and equalizers

**The typescript never discusses products or limits.** It uses products of measurable spaces without
comment in §3.2 (below). Everything about the categorical defects comes from the two paratexts:

> **A (cover):** "in several places my initial thoughts are incorrect (e.g., $\mathcal{P}$ has products
> therefore… In fact $\mathcal{P}$ does not have products or equalizers — only weak products and weak
> equalizers). … we have a rather detailed analysis of this category as we were trying to determine if it
> had equalizers (we proved it doesn't)." (PDF 1)

> **O (Lawvere, 2011):** "The most obvious property of this monad that most do not have is that the free on 1
> is 1, with the result that the **tensor product has projections ('marginals') which however do not have
> the universal property of the associated cartesian product**." (PDF 14)

> **O (Sturtz, 2011, quoted in the same email):** "It only has **weak equalizers**; given a parallel pair
> $f,g:X\to Y$, the weak equalizer is the extreme set of the set of all probability measures $P$ on $X$
> which satisfy $fP=gP$, along with the evaluation map. (Choquet Theory) In $\mathcal{P}$ arrows to $2$ with
> the powerset algebra correspond to measurable functions." (PDF 14)

Neither text defines "weak product" or "weak equalizer," and **no proof of the no-equalizer claim appears
anywhere in this artifact.** What can be established from the definitions alone is the *mechanism*, and the
mechanism is worth stating precisely because it is the whole design payload:

**Why the product fails.** Let $\Omega_1\times\Omega_2$ be the usual product of measurable spaces with
projections $\pi_i$. In $\mathcal{P}$ the projections are morphisms (deterministic), and the question is
whether this is a product: given $\Omega\xrightarrow{T_1}\Omega_1$ and $\Omega\xrightarrow{T_2}\Omega_2$,
is there a *unique* $\Omega\xrightarrow{W}\Omega_1\times\Omega_2$ with $\pi_i\circ W=T_i$?

- **Existence holds.** $W(x,A_1\times A_2):=T_1(x,A_1)\,T_2(x,A_2)$ is a kernel and has the right
  marginals. The mediating arrow always exists.
- **Uniqueness fails, and fails badly.** Any coupling of the two marginals works — the product coupling, the
  comonotone coupling, or any copula. There are as many mediating arrows as there are joints with those
  marginals.

So the object is right, the projections are right, and the universal property fails on *uniqueness*. That is
exactly what "weak product" means, and it is a stronger and more useful statement than "no product": **in a
probabilistic world you can always form the joint, and never canonically.** (D — this argument is mine; the
annotator asserts the conclusion, Lawvere states the tensor/marginal fact, neither gives the coupling
argument. It is elementary and I believe it is what they mean, but it is not in the document.)

The same shape recurs for equalizers. The equalizer of $f,g:X\to Y$ would be "the sub-object on which they
agree." Its probabilistic analogue is a set of *measures*: $\{\mu : f\circ\mu=g\circ\mu\}$. That set is
convex (closure under $\theta\mu_1+(1-\theta)\mu_2$ follows from linearity of composition), and every
element of it is a legitimate "world consistent with the constraint" — so the mediating arrow exists and is
never unique. Sturtz's "extreme set … along with the evaluation map" is the Choquet description of that
convex set by its extreme points; **O**, by quotation only — not proved here, and I could not verify the
Choquet details from this document alone (no proof, no reference beyond the parenthetical).

**D:** two corollaries the document does not draw but which matter downstream:

- No equalizers + no products ⇒ **no pullbacks**: "the sub-object where two conditions hold together" is not
  available as a categorical construction. In a simulation, the two things an engine does every tick — form
  a joint over simultaneous actors, and intersect conditions — are exactly the two operations that are not
  canonically available.
- The failure is a failure of *uniqueness*, not of *existence*. There is no cliff where the mathematics
  refuses to answer; it answers, ambiguously, every time. That is worse for a designer than a refusal,
  because the ambiguity looks like an answer.

Two further limits of the paratext, stated so they are not laundered later:

1. The annotator's own note on p.10 — "**Products exist in $\mathcal{P}$ and hence $\mathcal{P}^N$**" — is
   in the acknowledged-error zone of the cover note. It is wrong as stated ("exist" without "weakly"), and
   it is wrong in a specific and diagnostic way: the products used in §3.2 are products in **Meas**, and the
   annotator mistook their presence in the construction for their presence in $\mathcal{P}$.
2. The red note on p.9, "CARTESIAN CLOSED? No! but the map objects $[0,1]^{\Omega'}$ exist" (the superscript
   is not fully legible), is the annotator thinking aloud. Lawvere's 2011 reply says the opposite in
   substance: for an internal Hom "one needs to consider the category of all convex spaces and not just its
   full subcategory $\mathcal{P}$" — i.e. the closed structure lives in the Eilenberg–Moore category, not in
   the Kleisli category. **Treat the annotation as a question, not a finding.**

### 1.8 Stochastic processes: memory is a place, not a trace

This is the section that settles the working hypothesis. §3.2:

> "Let $N$ be the category with countably many objects and no non-identity maps, and let $\mathcal{P}^N$
> denote the category whose objects are sequences $\Omega_0,\Omega_1,\dots$ of objects in $\mathcal{P}$. We
> define a functor $\mathcal{P}^N\xrightarrow{\Phi}\mathcal{P}^N$ by
> $\Phi\{\Omega_k\}=\{\prod_{k<n}\Omega_k\}_n$" (p.10)

where the product is the measurable-space product with the smallest $\sigma$-algebra making the projections
measurable. "If $\Omega_n$ is thought of as the space of all possible states of a system at time $n$, then
$\Phi(\Omega)_n$ is the space of all possible **histories** of the system up to time $n$" (p.11). A process
is then

$$\Phi(\Omega)\xrightarrow{P}\Omega \qquad\text{i.e. a sequence}\qquad P_n:\prod_{k<n}\Omega_k\to\Omega_n$$

"in $\mathcal{P}^N$" (p.11). Maps of processes are sequences $f_n:\Omega_n\to\Omega'_n$ commuting with the
$P_n$; with the obvious composition this is "the category of temporally discrete stochastic processes"
$(\Phi,\mathcal{P}^N)$ (p.11). The annotator writes "**Show THIS IS EQUIVALENT TO THE KOLMOGOROV DEF.**"
(p.11) — the right instinct: this is the Kolmogorov extension picture, with the finite-history spaces and
their projections doing the work.

Then §3.3 specialises. If $\mathbb{N}$ is the additive monoid of non-negative integers as a one-object
category, the functor category $\mathcal{P}^{\mathbb{N}}$ is "the category of temporally discrete **Markov**
processes": an object is a measurable space $\Omega$ with a single $\Omega\xrightarrow{T}\Omega$, and a map
is a commuting square (p.12). Given an initial distribution $1\xrightarrow{P_0}\Omega$, one gets a general
process by putting $\Omega_n=\Omega$ for all $n$ and

$$P_n:\prod_{k<n}\Omega_k\to\Omega_{n-1}\xrightarrow{T}\Omega \qquad\text{"where the first is the projection"}$$

> "i.e., the dependence on the past is really only on the preceding moment and, furthermore, the law of
> transition from one time to the next does not change with time." (p.12)

This is the whole point, and it is easy to miss because it is delivered as a parenthetical. **The general
process has all of the past in the domain of every arrow. The Markov process is obtained from it by
composing with a projection — by explicitly throwing the past away.** Markovianity is not a default in this
framework and not a convenience; it is a *named arrow that discards information*, and it is exactly here
that the designer's choice lives. The paper then notes the functor $(1,\mathcal{P}^{\mathbb{N}})\to
(\Phi,\mathcal{P}^{\mathbb{N}})$ "raises the question of whether the above functor has an adjoint (or
co-adjoint)" (p.12) — and stops.

Note also §3.2's *object*: it is not a kernel that carries a history, it is a *space of histories*, and the
arrow at time $n$ is a kernel **out of** that space. Memory in this framework is a property of the domain.

### 1.9 Statistics and pattern recognition: what the text delivers

The title promises three applications. The body delivers one and sketches another.

**Pattern recognition / decisions (§3.1, p.9).** "A fairly general class of decision problems":

- a basic space $\Omega$ and a **measurable partition** $\Delta$ of $\Omega$, "elements of $\Delta$ being
  called 'patterns' or 'decisions'"; $f:\Omega\to\Delta$ is the quotient map;
- "Actually, for the formulation of the problem we could allow $f$ itself to be 'fuzzy'; i.e.,
  probabilistic" (p.9);
- a space $T$ of "observable states" and a probabilistic map $\Omega\xrightarrow{F}T$, "expressing the
  conditional probability $F(\omega,A)$ that the observed state lies in any $A\subseteq T$, given that the
  basic state is $\omega\in\Omega$";
- the problem is to find a "best" completion $\delta$ of the triangle $\Omega\xrightarrow{F}T$,
  $\Omega\xrightarrow{f}\Delta$, $\delta:T\to\Delta$.

"Best" is then made definite in two different ways (p.10):

$$\text{(Bayes)}\quad \max_\delta \int_\Omega (F\circ\delta)\big(x,\{f(x)\}\big)\,P(\mathrm{d}x)
\qquad\qquad
\text{(minimax)}\quad \max_\delta\ \inf_{x\in\Omega}\ (F\circ\delta)\big(x,\{f(x)\}\big)$$

The first is "the average (with respect to $P$) of the probability of making the correct decision by first
making the observation $F$ and then following the decision rule $\delta$"; the second is used "in the
absence of any such $P$." Existence: "The existence of solutions $\delta$ to these optimization problems can
be established in very great generality by topological arguments" (p.10) — asserted, no hypotheses.

Read the objective carefully, because it is not accuracy. $(F\circ\delta)(x,\{f(x)\})$ is **the probability
the rule assigns to the true cell**, and the Bayes criterion averages it over how often each world actually
occurs; the minimax criterion takes the worst world. Two rules with the same hit rate but different
confidence profiles get different scores. Confidence is not a separate stat here; it is the *shape of the
composite kernel*, scored by a functional the designer chooses.

**Stochastic processes (§3.2–3.3).** As above: history spaces, processes as arrows from history, Markov as
projection, and the (unanswered) adjoint question.

**Statistics.** Essentially absent. What is there is three things: the pushforward $P\circ T$ and the remark
that when $T$ is deterministic this is "the familiar … 'random variable'" (2.6, p.7); the functor
$\mathcal{S}$ on spaces of measures (2.8); and convexity of the space of measures (1.11). No estimation, no
sufficiency, no testing, no decision-theoretic statistics beyond the two functionals above. The 2011 email
adds one forward-looking sentence — "The commutativity of the monad means that all sorts of diagram
categories arising in statistics can be enriched" (PDF 14) — which is a promissory note, not a result.

One more construction deserves to be recorded because it is the text's only example of an arrow that is
neither deterministic nor a "random variable":

> **2.6** "Another interesting special case: $\Omega=\langle S,\mathfrak{B}\rangle$,
> $\Omega'=\langle S,\mathfrak{B}'\rangle$ where $\mathfrak{B}'$ is a sub-$\sigma$-algebra of
> $\mathfrak{B}$, and $T$ is the 'identity' mapping; then $P\circ T$ is just the restriction of $P$ from
> $\mathfrak{B}$ to $\mathfrak{B}'$." (p.7)

**Coarsening the algebra is an arrow.** Not a loss of precision, not a fog-of-war radius — a morphism, from
the finer object to the coarser one, and it has no inverse.

---

## 2. What it does not say

Stated plainly so nothing below leaks upward into the record as though the document said it.

1. **No definition of weak product or weak equalizer**, and no proof that $\mathcal{P}$ lacks equalizers. The
   claim is the annotator's, from an analysis not included ("we proved it doesn't"), plus one sentence from
   Lawvere in 2011 about tensor products and marginals. The coupling argument in §1.7 is mine.
2. **The body is silent on limits.** No mention of products, equalizers, pullbacks, or cartesian closure in
   the typescript at all. §3.2 uses products of measurable spaces as though they were unproblematic, which
   in Meas they are.
3. **The monad is never named and its multiplication is never written.** What is written is a functor
   $\mathcal{S}$, a natural transformation $\varphi:\mathcal{S}\Rightarrow\mathrm{id}$, and an adjunction.
   "Kleisli", "Eilenberg–Moore", "commutative monad" all come from the 2011 email.
4. **Associativity is asserted, not proved** (2.7). **Existence of optimal $\delta$ is asserted, not
   proved** (p.10). **The Kolmogorov equivalence is not asserted at all** — only the annotator's "Show THIS
   IS EQUIVALENT" (p.11).
5. **No statistics.** The title's middle term is unearned in the body (see §1.9).
6. **No algorithm, no example, no number.** Twelve pages without a single worked computation.
7. **Nothing about computation, finiteness, or implementation.** No remark on what happens when $S$ is
   finite (the case every game is in), though the countable case is treated in passing.
8. **No player, no stakes, no adversary.** There is no game-theoretic content: $\delta$ is chosen by a
   statistician facing nature, not by an opponent. Any adversarial reading is an import.
9. **The document ends mid-program** with the adjoint question and no conclusion, so it cannot be cited for
   *results* about process categories — only for the construction.
10. **Dating.** "1962" is the annotator's, not the document's. The email is 2011 and is retrospective
    testimony about a 1962 text; where the two differ (internal Hom, closed structure) the email is later and
    more authoritative, but it is not contemporaneous.

---

## 3. Design translation — mine, not the author's

Everything in this section is **D**. Lawvere wrote a category; I am reading it as an engine specification.
Where the text constrains the reading I say so; where it does not, the claim is a design proposal.

### 3.1 The claim in one paragraph

If a game's probabilities are morphisms, then a "chance" is not a number that gets modified — it is an
entire conditional law from a structured state to a structured state, and the operations available on it are
*compose*, *mix*, *push forward*, and *restrict the domain*. None of those operations can produce something
that is not a probability law, so the system cannot become incoherent. That is the whole trade: **you give
up the ability to say "−20% because it's night" and you get, in exchange, a system in which order,
correlation, memory, and ambiguity are representable rather than merely described.** Modifiers act on
entries and must be repaired afterwards (clamp, renormalise, define a stacking order); arrows act on arrows
and are closed. Every balance bug that comes from "which multiplier applies first" is a symptom of doing the
first thing while believing you are doing the second.

### 3.2 What actually changes

| | scalar + modifiers (default) | morphism in $\mathcal{P}$ |
|---|---|---|
| **what is stored** | a number and a list of factors | a whole conditional law (a table, in the finite case) |
| **what a "bonus" is** | surgery on one entry, which then needs renormalising | composition with another arrow, or a restriction of the domain |
| **closure** | modifiers push rows off $\sum=1$; needs clamping and ordering rules | composition, mixing, pushforward are closed by construction |
| **order of effects** | multiplication commutes, so sequence is *unrepresentable* | composition does not commute, so sequence is representable — and must be recorded |
| **correlation** | independence is assumed silently at every intersection | the joint is carried by the arrow; independence becomes a declared constraint |
| **memory** | a stateless multiplier; history must be re-injected by hand each turn | history is in the domain (a product object); Markov is an explicit projection |
| **ambiguity** | a number cannot be a set; ambiguity is flattened to a point | a set of measures is a first-class object; picking a point is an action |
| **failure mode** | incoherent stacking, order bugs, correlation blind spots | coherent but expensive: the matrices are unreadable, and the *authoring* is the hard part |
| **what the player sees** | one percentage | a distribution, or a sampled outcome — not a number |

### 3.3 Eight readings

**D1 — The unit of design is the kernel, not the chance.** Survival, detection, identification stop being
scalars and become arrows between named objects: the world-state object (who is where, who talks to whom,
what is written down), the observation object (what the state's file says), the decision object (what the
state does). "Detection chance 0.3" becomes one entry $\mathrm{Obs}(\omega,\{\text{flagged}\})$ of one
arrow. The number still exists — as a *reported value*, computed from the arrow at a state, never as the
stored thing. This is the same discipline as `13`'s "no number that carries a law's shape," taken one step
further: **a kernel is the most shape-free representation of a probability law there is** — it stipulates
nothing beyond the table. The cost is real and should be named: kernels do not remove the need for data,
they relocate the design decision from "what curve" to "which states and which questions," and *that* choice
is now the load-bearing act.

**D2 — Two kinds of modifier, and only one of them is legitimate.** A modifier on an entry ("−20% at
night") leaves the category and has to be repaired. The same intent expressed as an arrow ("the night
transition") or as a domain restriction ("the sub-object of night states," which is a pullback and therefore
*also* only weakly available — see D5) stays inside. The practical rule: **conditions go in the domain or in
the arrow; they never go on the output.** This is not stylistic. Multiplying one entry by 0.8 breaks
$\sum_{B'}T(x,B')=1$; the repair is a renormalisation, which is a nonlinear operation on the kernel that
behaves badly under composition, which is why stacking three modifiers requires a rule about stacking order,
which is where the bugs live.

**D3 — Non-commutativity is a feature you have to pay for.** Kernel composition is associative but not
commutative, so "infiltrate then raid" and "raid then infiltrate" are different arrows and the engine can
tell them apart. Scalar multiplication *is* commutative, so a modifier stack **cannot** distinguish them —
not "distinguishes them badly," cannot, at any level of tuning. Any mechanic whose outcome depends on
sequence is therefore not implementable in the scalar idiom, and the usual workaround (a separate
"order-sensitive" special case) is an admission that the representation is wrong. The price of getting
sequence is that **the engine must record which arrow happened when** — order becomes state, not
bookkeeping. For a turn-based game that is nearly free.

**D4 — No products: independence is a decision, not a default.** Three risks — survival, detection,
identification — that share a world state are three marginals of one joint. Three scalars fix only the
marginals, and there are infinitely many joints with those marginals. Multiplying them asserts the product
coupling: *exactly* independence. That assertion is a modelling claim with a consequence — it makes the
compound event "caught and killed" the product of two small numbers, and it makes the *correlated* disaster
(one betrayal causing both exposure and death) literally unreachable. The fix is not more precision; it is
carrying the joint (one arrow into the product object) or declaring the independence out loud and paying for
it. **Every multiplication of two chances in a design document is a hidden independence assumption.**

**D5 — No equalizers: ambiguity is a convex set, and choosing a point is a move.** The consistent-worlds
object for a constraint is $\{\mu: f\circ\mu=g\circ\mu\}$ — convex, with the pure readings as extreme
points and no canonical element. So an evidence update cannot honestly resolve to a point. What it can do is
present the set and make the player choose; the choice is then a real action with a real chance of being
wrong, rather than a diegetic flavour text over a number the engine already decided. This is the formal
version of the thing a game about infiltration wants and usually fakes: *the file is a set, the decision is
a point, and the gap between them is the game.* Two knock-on limits: no pullbacks means "the states where
condition A and condition B both hold" is not canonically constructible (you get a weak version with
non-unique mediating arrows), so conjunctions of intel must be authored, not computed.

**D6 — Identification is a coarsening, and §3.1 is already the mechanic.** §2.6's sub-σ-algebra arrow is the
only non-trivial non-deterministic example in the paper, and it is exactly the intelligence relation: the
state's picture of your organisation is a coarser algebra on the same points, reached by an arrow that has no
inverse. "Identification chance" is then not a roll but the value $(F\circ\delta)(x,\{f(x)\})$ — the
probability the attribution rule assigns to the true cell — scored either by its average over how often each
world occurs or by its worst case. Both criteria are in the text (p.10), and they are genuinely different
mechanics: the Bayes criterion rewards being right where it matters, the minimax criterion rewards never
being catastrophically wrong. A game can give different factions different functionals on the same kernel,
which is a cheaper way to make doctrines feel different than giving them different numbers. And because "we
could allow $f$ itself to be 'fuzzy'; i.e., probabilistic" (p.9), the ground truth does not have to be a
single answer — which is what a game about misrecognition (the informant who is genuinely both things) needs.

**D7 — Memory lives in the domain. This is the hypothesis, and it is false as stated.** See §3.4.

**D8 — Beliefs are objects of the same type as worlds, and nesting is free.** $\mathcal{S}$ with
$\Omega\rightleftarrows\mathcal{S}(\Omega)$ (Dirac in, evaluation out, composite the identity) says a
distribution over worlds can be used wherever a world can, without adding a type. So "the player's model of
the state's model of the player" is not a special subsystem; it is the same construction applied twice, and
$\mathcal{S}\mathcal{S}$ collapses. The asymmetry — an embedding with a retraction, not an isomorphism — is
the design constraint: **you can always collapse a belief into a state, and you can never get the belief
back.** Any mechanic that "commits" the player to a reading is therefore irreversible, and should be
presented as such.

### 3.4 The working hypothesis, tested

> *Hypothesis: composed arrows remember — the composite at turn 50 still contains turn 5's arrow, which is
> why early decisions resurface.*

**Verdict: refuted as stated, confirmed in a different place, and the corrected version is the useful one.**

*Refuted, first by the definition.* Composition is an integral, and an integral **sums over** the
intermediate state: $(T\circ U)(x,B'')=\int T(x,\mathrm{d}x')\,U(x',B'')$. The turn-5 arrow has been
averaged out. What survives at turn 50 is a number that *depends on* turn 5 — dependence is not containment,
and no inverse exists to recover the factor (kernels are not invertible in general, and 2.3 offers no
recovery map).

*Refuted harder by associativity.* If the composite carried its factorisation, then $(T\circ U)\circ V$ and
$T\circ(U\circ V)$ would have to differ, or the carried memory would have to be inaccessible. They are
equal (2.7). The composite is therefore exactly the equivalence class of all factorisations with that law —
which is to say, **the composite remembers its factors only up to "has the same law," i.e. not at all.**
This is the decisive argument, and it is one line: associativity is incompatible with compositional memory.

*Confirmed — in the object.* §3.2 builds memory the other way round. The arrow at time $n$ is
$P_n:\prod_{k<n}\Omega_k\to\Omega_n$: **turn 5 is literally in turn 50's domain**, by construction, not by
retention. The history is a space, and every arrow reads from it.

*Refined.* **Arrows forget; objects remember.** If early decisions must resurface, the state must be a
history object and the later arrow must have that history in its domain. Three consequences follow, and they
are the practical yield of this paper:

1. **Any compression of the past into a scalar is a Markov assumption.** `suspicion: 0..1` is a
   one-coordinate projection of history, and it asserts "nothing else about your past matters, given this
   number." That is a *claim*, testable in principle, and §3.3's projection is precisely the arrow that
   makes it. It is not a bookkeeping convenience — it is the modelling decision the whole game turns on.
2. **A modifier applied to a chance is not even a compression.** It is not a coordinate of any state space,
   so it is not a Markov assumption either; it is simply outside the representation. Nothing about it can
   resurface at turn 50, because at turn 50 it does not exist. This is the precise sense in which
   "early decisions resurface" is impossible in a modifier-stack game and possible in a kernel game: the
   former has no place to put the past.
3. **The interesting quantity is the gap.** If the projection is lossy in a way the player can feel — if the
   state's one-number file about you systematically discards what you actually did — then the game's drama
   is exactly the difference between the object and its projection. That is a *designable* quantity, and it
   is not a dial: it is a choice of which $\sigma$-algebra the state's file is built on.

The slogan form: **the past survives by being a place you can still be in, not by being a weight you carry.**

### 3.5 What this does not buy

Because a design proposal that only lists gains is not a proposal:

- **It does not buy balance.** The category guarantees coherence, not interestingness. A perfectly coherent
  game can be dull, and a well-tuned scalar game can be gripping. What changes is *which failures are
  possible*: incoherence becomes unauthorable rather than merely unnoticed.
- **It does not scale for free.** Finite state spaces give row-stochastic matrices: composition is matrix
  multiplication, mixing is convex combination, coarsening is a 0/1 aggregation matrix, restriction is
  masking. All of it is $+\ \times\ \div$ on a finite carrier and a fold — no new primitive, no fitted curve,
  consistent with the guardrail argued in `13`. But the cost is $|S|^2$ per arrow, and the object choice
  (which questions, how fine the algebra) becomes the expensive design act.
- **It is not legible.** No player can read a matrix. Everything the player sees must be a sample, a
  distribution summary, or a set — and "showing the set" (D5) is a UI problem this document does not help
  with.
- **It cannot be cited for game claims.** Nothing here is about players, stakes, or adversaries. §3.1's
  $\delta$ is chosen by a statistician facing nature; the moment an opponent chooses, you are outside the
  paper.
- **The paratext is not a proof.** The no-equalizer result is the load-bearing negative claim and it is
  attested, not demonstrated, in this artifact. If a design decision rests on it, that decision rests on an
  annotator's memory of an unpublished analysis.

---

## 4. Proposed rulings

For the porch, in the idiom of `13` §5.1. Each is **D**, offered for a yes/no.

- **R1.** No probability in the design is stored as a scalar with modifiers. A chance is either an entry of
  a named kernel (computed at a named state) or it does not exist. *Rationale:* D1–D2.
- **R2.** Every multiplication of two chances must be accompanied, in the same document, by the independence
  claim it encodes, or replaced by a joint. *Rationale:* D4; the product that "does not exist."
- **R3.** Memory is a coordinate of the state object or it is nothing. A scalar "heat/grudge/suspicion" is
  admissible only if declared as a Markov assumption — i.e. as the claim "given this number, the rest of the
  past is irrelevant." *Rationale:* D7, §3.4.
- **R4.** Sequence-sensitive mechanics may not be built from commutative modifiers. If A-then-B differs from
  B-then-A, the representation must be arrows, and the engine must record the order. *Rationale:* D3.
- **R5.** Attribution/identification scores are two functionals (average vs worst case) on one kernel, not a
  single accuracy number; factions may differ in which functional they are scored by. *Rationale:* D6, p.10.
- **R6.** Ambiguity resolves to a set, and the player's choice of a point from that set is an action with
  consequences. *Rationale:* D5.
- **R7.** Intelligence is a coarsening of the algebra, not a fidelity percentage. *Rationale:* §2.6, D6.

---

## 5. Open questions

1. **Is the weak-product argument in §1.7 the intended one?** The coupling argument is mine; the annotator
   asserts the conclusion and Lawvere states the tensor/marginal fact. If the actual proof is different
   (e.g. about the tensor σ-algebra rather than the product σ-algebra), the design consequence is unchanged
   but the citation would have to change.
2. **Does the no-equalizer result survive in the finite case?** Every game state space is finite. The claim
   is stated for $\mathcal{P}$ generally. If finiteness repairs equalizers (I do not think it does — the
   convex set of couplings is still non-trivial — but I have not checked), D5 weakens considerably.
3. **What is the right $\sigma$-algebra for a faction's file?** The paper says coarsening is an arrow; it
   says nothing about which coarsenings are natural. This is the design question, and it is not answerable
   from the text.
4. **Can the history object be kept finite?** $\prod_{k<n}\Omega_k$ grows multiplicatively. Either the
   algebra is coarsened (which is a Markov assumption in disguise) or the history is compressed by a
   designed quotient (which is the same problem one level up). This is the real engineering wall, and §3.2
   does not address it.
5. **Is the adjoint question at the end of §3.3 worth anything?** "Is it possible to extend any process to a
   Markov process universally?" If yes, it would license "always present the Markov shadow of a
   history-dependent model" — a possible UI device. The paper does not answer it and I have not pursued it.

---

## 6. Method and OCR notes

**The scan has no text layer.** `pdftotext` returns only the annotator's cover note — the sole page with a
text layer; pages 2–14 are images. No `tesseract`/`ocrmypdf` on this host, and the `marker` install is
broken (`ModuleNotFoundError: cgi` under Python 3.13), so no OCR engine was used.

**Method.** Every page was rendered with `pdftoppm` at 200 dpi and read as an image; every formula and every
quotation was then re-rendered at 300–400 dpi and read again as a crop before being written down. Rendering
and cropping only; the PDF, the source tree, and the corpus were not modified. Typewritten body text was
consistently legible at 300 dpi. Handwriting was legible in the red/orange ink and mostly legible in blue
pencil; three passages were doubtful, and none of them carries a claim:

| where | what | status |
|---|---|---|
| p.9, red, upper right | "CARTESIAN CLOSED? No! but the map objects $[0,1]^{\Omega'}$ exist" — superscript uncertain, and the claim is disputed by the 2011 email (§1.7) | read but **not relied on** |
| p.11, blue pencil over the $\Phi(\Omega)\to\Omega$ line | a long diagonal annotation mentioning "coordinate functions", "$\Omega$", "discrete"; I can make out fragments only | **illegible, unused** |
| p.1, left margin | σ-algebra closure remarks ("$B\cap B'\in\mathfrak{B}$", "choose the σ-alg. on $\Delta$ generated by $\{f(\omega)\}$") | partly legible, **not relied on** |

Other uncertain readings, flagged where they are used:

- The functor glyph of §2.8 is a script letter that could be $\mathcal{S}$ or $\mathcal{D}$; transcribed
  $\mathcal{S}$ throughout, immaterial to every claim.
- The deterministic subcategory cross-reference prints as "(2.7)", which is the associativity paragraph; read
  as a misprint (§1.4).
- "commutative **pr** monad" in the email: the two letters are lowercase and unexpanded; presumably
  "probability". Quoted as printed.
- Sturtz's "arrows to 2 with the powerset algebra correspond to measurable functions" is loose: a
  $\mathcal{P}$-arrow into $2=\{0,1\}$ is given by a measurable $X\to[0,1]$ (the probability of $1$), so
  "measurable functions" must mean $[0,1]$-valued; a $\{0,1\}$-valued arrow is deterministic. His next clause
  ("or as a $\mathcal{P}$ map $X\times X\to[0,1]$") suggests he means the $[0,1]$ reading. **Reported as
  written, not corrected in the quotation, and not used for any design claim.**
- Page numbers: handout $n$ = PDF $n+1$; verified against the `-n-` footers on pp.8–12 (PDF 9–13).
- Provenance: the scan is stamped "g-c. Rota" on pp.1–2. Recorded, not interpreted.

---

## 7. Evidence table

**Status:** **O** = observed in Lawvere's own text — the 1962 typescript, or his 2011 email, which is part
of this artifact and whose location is given as `PDF 14` (Sturtz's letter, quoted inside that email, is
marked per row); **A** = annotator's handwriting, cover note or margin (commentary — and the annotator warns
some of it is wrong); **D** = derived — my inference, argument, or design reading.
Page = handout page (`-n-`), which is PDF page − 1.

| # | Claim | Status | Where | Note |
|---|---|---|---|---|
| 1 | Objects are measurable spaces $\langle S,\mathfrak{B}\rangle$ | O | p.1 §1.1.1 | σ-algebra axioms (0)–(3) |
| 2 | Measurability defined by sublevel sets into a partially ordered set | O | p.1 §1.2 | order-theoretic form, not Borel-preimage |
| 3 | Probability measure: $P(S)=1$, countable additivity | O | p.2 §1.4 | |
| 4 | Countable case: $p(x)=P(\{x\})$, $\sum p=1$ | O | p.2 §1.5 | |
| 5 | Induced measure $(Pf)(B')=P(f^{-1}(B'))$ | O | p.2 §1.6 | |
| 6 | Probabilistic map = measurable family of measures, axioms (0)–(3) | O | p.5–6 §2.1 | (2) countable additivity in $B'$; (3) $x\mapsto T(x,B')$ measurable |
| 7 | $T(x,B')$ called the "(conditional) $T$-probability" | O | p.6 | the word *conditional* is the author's |
| 8 | Composition $(T\circ U)(x,B'')=\int T(x,\mathrm{d}x')U(x',B'')$ | O | p.6 §2.3 | the Chapman–Kolmogorov law, unlabelled |
| 9 | "the correct law for composition of conditional probabilities" | O | p.6 | author's justification, no proof |
| 10 | Countable composition: $\sum_{x'}t(x,x')u(x',x'')$ | O | p.6 §2.4 | row-stochastic matrix product |
| 11 | Deterministic maps as Dirac kernels; $T_{f\circ g}=T_f\circ T_g$ | O | p.6–7 §2.2, 2.5 | faithful subcategory |
| 12 | $\mathcal{P}$ is a category; functor/natural transformation/adjoint now meaningful | O | p.7 §2.7 | associativity asserted, not proved |
| 13 | $1\to\Omega$ is a probability measure; $P\circ T$ is the induced distribution | O | p.7 §2.6 | deterministic $T$ = "random variable" |
| 14 | Sub-σ-algebra + identity = restriction of $P$; an irreversible coarsening arrow | O | p.7 §2.6 | the only non-trivial non-deterministic example |
| 15 | $\mathcal{S}(\Omega)$ = probability measures with the evaluation σ-algebra | O | p.7 §2.8 | glyph ambiguous |
| 16 | $\mathcal{S}(T)(P)(A')=\int P(\mathrm{d}\omega)T(\omega,A')$ | O | p.8 | pushforward |
| 17 | $\varphi_\Omega(P,A)=P(A)$ is natural $\mathcal{S}\Rightarrow\mathrm{id}$ | O | p.8 | |
| 18 | $\mathcal{S}$ co-adjoint to the inclusion of the deterministic subcategory | O | p.8 §2.9 | $i\dashv\mathcal{S}$ |
| 19 | $\Omega\to\mathcal{S}(\Omega)$ is a retract with retraction $\varphi_\Omega$ | O | p.9 | Dirac then evaluate = identity |
| 20 | Adjointness "expected to aid … Bohm's questions about quantum mechanics" | O | p.9 | one sentence, no development |
| 21 | Convex combinations of measures are measures; integral is affine | O | p.4 §1.11 | |
| 22 | $\mathcal{P}$ admits convex combinations of *maps*; Meas does not | O | p.9 | the paper's one argued virtue |
| 23 | Decision problem: partition $\Delta$ = "patterns"/"decisions", $f:\Omega\to\Delta$ | O | p.9 §3.1 | $f$ may itself be probabilistic |
| 24 | Observation kernel $F:\Omega\to T$; rule $\delta:T\to\Delta$ | O | p.9 | |
| 25 | Bayes criterion $\max_\delta\int(F\circ\delta)(x,\{f(x)\})P(\mathrm{d}x)$ | O | p.10 | average probability of correct decision |
| 26 | Minimax criterion $\max_\delta\inf_x(F\circ\delta)(x,\{f(x)\})$ | O | p.10 | "in the absence of any such $P$" |
| 27 | Existence of optimal $\delta$ "by topological arguments" | O | p.10 | no hypotheses given |
| 28 | $\Phi\{\Omega_k\}_n=\prod_{k<n}\Omega_k$; history spaces | O | p.10 §3.2 | measurable-space product |
| 29 | A process is $\Phi(\Omega)\xrightarrow{P}\Omega$, i.e. $P_n:\prod_{k<n}\Omega_k\to\Omega_n$ | O | p.11 | memory is in the domain |
| 30 | Maps of processes = commuting squares; category $(\Phi,\mathcal{P}^N)$ | O | p.11 | |
| 31 | $\mathcal{P}^{\mathbb{N}}$ = temporally discrete Markov processes | O | p.12 §3.3 | object = $\Omega\xrightarrow{T}\Omega$ |
| 32 | Markov case = general process composed with the projection | O | p.12 | memory discarded by an arrow |
| 33 | "dependence on the past is really only on the preceding moment … law does not change with time" | O | p.12 | the definition of the Markov assumption |
| 34 | Functor $(1,\mathcal{P}^{\mathbb{N}})\to(\Phi,\mathcal{P}^{\mathbb{N}})$; adjoint question left open | O | p.12 | document ends here |
| 35 | $\mathcal{P}$ has no products, only weak products | A | PDF 1 cover | annotator; no proof in artifact |
| 36 | $\mathcal{P}$ has no equalizers; proved in an analysis not included | A | PDF 1 cover | "we proved it doesn't" |
| 37 | "the tensor product has projections ('marginals') which however do not have the universal property of the associated cartesian product" | O | PDF 14 | Lawvere 2011; the sharpest statement of #35 |
| 38 | Only weak equalizers; the weak equalizer is the extreme set of $\{P:fP=gP\}$ + evaluation map (Choquet) | O | PDF 14 | Sturtz, quoted; not proved here |
| 39 | "the free on 1 is 1" is what makes the tensor non-cartesian | O | PDF 14 | Lawvere 2011 |
| 40 | Internal Hom needs all convex spaces / Eilenberg–Moore, not just Kleisli | O | PDF 14 | so $\mathcal{P}$ is the Kleisli category |
| 41 | Commutativity of the monad enriches "diagram categories arising in statistics" | O | PDF 14 | promissory, no detail |
| 42 | Composition of probabilistic *relations* is "the challenge" | O | PDF 14 | Sturtz; unresolved |
| 43 | The product object in $\mathcal{P}$ has projections and non-unique mediating arrows (couplings) | D | §1.7 | my argument from #8, #12, #37 |
| 44 | No products + no equalizers ⇒ no pullbacks; conjunctions of conditions are not canonically constructible | D | §1.7 | |
| 45 | Composition does not remember its factors; associativity is incompatible with compositional memory | D | §3.4 | from #8, #12 |
| 46 | Memory is a property of the object, not the arrow; a scalar memory is a Markov assumption | D | §3.4 | from #28–#33 |
| 47 | Multiplying chances asserts independence (the product coupling) | D | §3.3 D4 | from #37, #43 |
| 48 | Entry surgery breaks $\sum=1$ and requires repairs that do not compose; arrow surgery is closed | D | §3.3 D2 | |
| 49 | Scalar modifier stacks cannot represent order at all (commutativity) | D | §3.3 D3 | |
| 50 | §3.1's two criteria are two scoreable doctrines on one kernel | D | §3.3 D6 | from #25–#26 |
| 51 | Nested belief needs no new type ($\mathcal{S}\mathcal{S}$ collapses) and commitment is irreversible | D | §3.3 D8 | from #18–#19 |
| 52 | A kernel is the least shape-carrying representation of a probability law | D | §3.3 D1 | consistent with `13` §0 |

---

## 8. Citation key

| Code | Artifact | Pages |
|---|---|---|
| — | `lawvere-master/pdfs/1962-the-category-of-probabilistic-mappings.pdf` | 14 PDF pages; handout pp.1–12 = PDF 2–13; cover = PDF 1; email = PDF 14 |

Offset: **handout page = PDF page − 1** (verified against `-n-` footers). Sections: I.1 measurable spaces
(pp.1–2), I.2 probabilistic mappings (pp.5–8), I.3 stochastic processes and decision maps (pp.9–12).
The artifact contains no section I.4 and no conclusion; **whether the original handout continued past p.12 is
not determinable from this scan** — page numbering is continuous and the last line is an open question, so I
treat pp.1–12 as the whole document and do not claim otherwise.

**Not read, load-bearing.** Giry, "A categorical approach to probability theory" (1982) — the standard
modern development of this construction, and the reason the monad bears her name; not in this file and not
consulted here, so every "modern restatement" remark above is from the 2011 email and general knowledge, not
from a checked source. The annotator's "rather detailed analysis" of equalizers, referenced on the cover, is
not in the artifact. No quotation above is attributed to a page I did not read.

**Read for context only.** `docs/gameplay/research/13-differential-equations-chaos-and-wealth-dynamics.md`
(guardrail framing, §0 and §5.1) and `26-rand-coin-doctrine-and-scorecards.md` (evidence-table and
ruling conventions). Neither is a source for any claim about Lawvere.

---

## 9. Closing

The paper's contribution to a game is not a formula for a probability. It is a separation of labour: **the
arrow carries the law and forgets; the object carries the past and remembers.** Everything a designer wants
from "early decisions resurface" is bought by making the state a history and paying the cost of carrying it —
and everything a designer fears from "modifier soup" is explained by the fact that a multiplier is not an
arrow at all, so there is nowhere for the past to be.

The two negative facts — no products, no equalizers — are the ones to keep nearest. They say that a
probabilistic world always permits a joint and never a canonical one, and always permits a consistent reading
and never a unique one. A simulation that respects that is not more precise than one that does not. It is
merely honest about where its assumptions are, which is the only thing that makes them findable.

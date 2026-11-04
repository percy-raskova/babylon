//! `L` — an organization's DOSSIER on others (Lane A brick 3; heat dossier
//! §5.1 A).
//!
//! **Symmetric form, asymmetric means** (Director ruling 2026-07-30,
//! ADR184 R3 consequence). Every actor holds a dossier, because
//! [`crate::capacity`]'s ruling makes repression and revolutionary action
//! the same allocation and an allocation runs on *belief* — so a movement
//! misreads the apparatus exactly as the apparatus misreads a movement.
//! What differs is **how each one resolves**: a state resolves by SPENDING
//! a surveillance instrument it must fund; a movement resolves by BEING
//! embedded in the social structures it moves through, which costs it
//! nothing and reaches only where it already stands. That asymmetry lives
//! in the resolution *paths* — which are content (BSL rules) and Phase 2
//! bindings — never in this type. This module supplies the operations; it
//! does not know who is looking or what it cost them.
//!
//! Scott's argument survives that symmetry rather than being flattened by
//! it: legibility is specifically what states do to populations, and the
//! reason is visible here as the *price* and *reach* of resolution, not as
//! a privileged type. The state buys a wide, shallow, standardized view;
//! the movement gets a narrow, deep, untransferable one.
//!
//! The heat reformulation splits one question-begging `[0,1]` scalar into
//! three quantities with different owners: what an actor **knows** (`L`,
//! here), what it **spends** (`K`, [`crate::capacity`]), and what its target
//! **is** (`X`, [`crate::exposure`], derived and never stored).
//! Conflating them is what forced the old mechanic to key repression to
//! *conduct* — the ideological falsehood the dossier indicts. Kept apart,
//! nothing needs to ask whether the player broke a law.
//!
//! **A dossier is a projection, not a fraction of the truth.** Scott's five
//! properties of state legibility — interested, documentary, static,
//! aggregate, standardized — mean `L` keeps only what the state's own
//! categories can hold. So this type stores what the state has *resolved*
//! and nothing else: it holds no pointer back to ground truth, and there is
//! deliberately no method that answers "what is really there". Code that
//! wants the truth must ask the substrate; code that wants the state's
//! belief asks a `Dossier`. Those are different questions, and the type
//! system is what keeps them different.
//!
//! **There is no threat score here, and none may be added.** Sparrow's
//! conscious-opponent argument forbids an accumulated priority: an opponent
//! who knows he is being ranked reorganizes, so the ranking must be
//! recomputed from live structure at decision time. `L` records *resolution*
//! — which nodes and ties the state has managed to see — never a verdict
//! about a target. The verdict is [`crate::exposure`] evaluated over
//! the `Dossier` and its [`Dossier::scope`], every time it is asked for.
//!
//! **Growth and decay are not symmetric, and neither is conduct-keyed.**
//! Resolution grows through named collection channels and — Sparrow's
//! feedback loop — fastest where it is already high, because a resolved node
//! exposes its neighbors. It decays through membership turnover,
//! compartmentalization, and restructuring. Both are rules expressed as
//! content (BSL), not arithmetic baked in here; this module supplies only
//! the operations those rules drive.

mod codec;
mod model;

pub use model::Dossier;

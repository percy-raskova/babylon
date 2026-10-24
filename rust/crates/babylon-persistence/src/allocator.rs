//! Process-wide allocator shared by the runtime, client, and persistence
//! qualification consumers.

use mimalloc::MiMalloc;

// National reconstruction retires large graphs, registers and receipt owners.
// Use the same allocator in the runtime, client and persistence qualification
// consumers so freed owners do not leave gigabytes of glibc arenas resident.
#[global_allocator]
static ALLOCATOR: MiMalloc = MiMalloc;

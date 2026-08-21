//! Task 1 (#652 bsl-ls, PR A) — the pre-refactor golden-AST oracle
//! (plan §2.4). `read_all`'s parsed-tree shape is pinned, per file, for
//! every real `.bsl`/`.bscn` in the tree BEFORE the span-table refactor
//! touches `reader.rs`'s parser, so a change to what the reader *produces*
//! (as opposed to a read-only tap) shows up here rather than only in the
//! §5.6/tick-golden spot checks.
//!
//! **Corpus scope, and why it is walked rather than `include_str!`ed.**
//! Four directories hold every real BSL source file in this tree: the
//! shipped rule pack (`babylon-tick/content/rules/*.bsl`), this crate's
//! own conformance fixtures (`tests/conformance/*.bsl`), and the shipped
//! scenario corpus (`babylon-tick/content/scenarios/*.bscn` plus the one
//! prelude, `babylon-tick/content/declarations/worldview.bscn`). The plan
//! quoted 25/37/1 = 63 files, counted at planning time; re-deriving the
//! same command against this tree finds 30/37/1 = 68 — five conformance
//! `.bsl` fixtures (`rng_edge_type_draw`, `rng_expr_draw`, `rng_fold_draw`,
//! `rng_keyed_draw`, `rng_keyed_draw_guarded`) landed via #576 the same
//! day, after the plan's snapshot but before this branch point. Walking
//! the directories (sorted, for determinism — `read_dir` order is not
//! guaranteed) rather than hand-listing files means that kind of drift is
//! caught here instead of silently under-covering the corpus again.
use babylon_bsl::reader::read_all;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

/// One content directory: its path (relative to this crate's manifest
/// directory) and the extension it contributes.
const CORPUS_DIRS: &[(&str, &str)] = &[
    ("../babylon-tick/content/rules", "bsl"),
    ("tests/conformance", "bsl"),
    ("../babylon-tick/content/scenarios", "bscn"),
    ("../babylon-tick/content/declarations", "bscn"),
];

fn sha256_hex(bytes: &[u8]) -> String {
    use std::fmt::Write as _;
    let digest = Sha256::digest(bytes);
    digest.iter().fold(String::new(), |mut acc, byte| {
        let _ = write!(acc, "{byte:02x}");
        acc
    })
}

/// Every corpus file, sorted by filename WITHIN each directory (in the
/// fixed `CORPUS_DIRS` order) — deterministic regardless of the
/// filesystem's own `read_dir` ordering, and stable if a file is added to
/// or removed from one directory without touching the others' pins.
fn corpus_files() -> Vec<PathBuf> {
    let manifest_dir = Path::new(env!("CARGO_MANIFEST_DIR"));
    let mut files = Vec::new();
    for (dir, ext) in CORPUS_DIRS {
        let dir_path = manifest_dir.join(dir);
        let mut group: Vec<PathBuf> = std::fs::read_dir(&dir_path)
            .unwrap_or_else(|e| panic!("reading {}: {e}", dir_path.display()))
            .map(|entry| entry.expect("readable dir entry").path())
            .filter(|path| path.extension().and_then(|e| e.to_str()) == Some(*ext))
            .collect();
        group.sort();
        files.extend(group);
    }
    files
}

/// `(directory-relative label, pinned read_all digest)`, in `corpus_files`'
/// order. Filled in from a real run against the CURRENT (pre-refactor)
/// reader — the independent before/after oracle plan §2.4 describes. A
/// name mismatch means the corpus's membership moved; a hex mismatch means
/// `read_all`'s parsed-tree shape moved. Either is a STOP.
const PINNED_DIGESTS: &[(&str, &str)] = &[
    (
        "consciousness.bsl",
        "20c55d1ecde62fd8a0e70d92558ec99882a91ebe0303b41d785afa44dbca78bf",
    ),
    (
        "control-ratio.bsl",
        "7f411663760a1e5bac192bf87a99f4dbdd4c0088a7e74053672fa65a566181b7",
    ),
    (
        "decomposition.bsl",
        "6f26218d7a3bad2fb9362d327893a8029527fb4ef11ecda5d2afea3f1ccac388",
    ),
    (
        "dispossession.bsl",
        "1ed31856615e10db6df382d2ef8cce5bd0708f89f9c40b076178a9b95ab0f4aa",
    ),
    (
        "fundamental-theorem.bsl",
        "254248a466a05af48690b3fc4b60b7a6379deeef24c7d2736c6b3e544d36e6b5",
    ),
    (
        "imperial-rent.bsl",
        "4695b937241f8becedbaee60bfb7b45b9d15d7353ce8d17bd46bd53462557296",
    ),
    (
        "lifecycle.bsl",
        "e388d4e4f54301e528004a4d3b5233bc4f039928054c4b6c6a4d1774a7614064",
    ),
    (
        "metabolism.bsl",
        "faef0790620d4c6ddf88f24f2969995688b441b9a0270dc105ae32a808b023c1",
    ),
    (
        "organization.bsl",
        "951841ff4892b87d186585f4e8cd219b6454d68b90be65a9b638508724584046",
    ),
    (
        "production.bsl",
        "35d61b03ae407977cc27d4feae025b6fd896ecbb9e2b8f2052abf6abe8677678",
    ),
    (
        "solidarity.bsl",
        "0a097f3c88ba6f03cbb79b03a160eeaf1179139164403f188575bc57755bcc8f",
    ),
    (
        "territory.bsl",
        "1874fb9421b35e489287f7fdf867ecb0da2a0c1c8bd519b649170b9a560aff66",
    ),
    (
        "vitality-attrition.bsl",
        "eca982cfffcde650e0900f47fef643b363bcc59ce1ac46abd19e148aca1c55a2",
    ),
    (
        "vitality.bsl",
        "072d2a4f3d5a790a199cce9f8db9b2a4bae97d311336cd856f4ef41aa6efe517",
    ),
    (
        "worldview.bsl",
        "17d58fea55ae0f4b9212b102761df827323c59085af6f9ae80eec075c1660c82",
    ),
    (
        "doctrine_adventurism.bsl",
        "285229ce4700877b551328858e4c74dcaae2b87c5ea4da276e0f3e3e4db44762",
    ),
    (
        "doctrine_liquidation_absorbing.bsl",
        "9d0e31d8a247f4d309c908e69179d06d7025c4fe5556fbe487eef3685ada1936",
    ),
    (
        "doctrine_liquidationism.bsl",
        "69f0a462c8bc1224fc83bd8841ee3a119117ee16478d2182446eeea38aac7053",
    ),
    (
        "empty_when.bsl",
        "0f26bdcf7f2528b21543cdc2c957f5767b9c23e791a8ea9c3de58fec5b678107",
    ),
    (
        "event_bifurcation.bsl",
        "1a7b5691a65334230a5f0586c945963a167c4c5ff2cfa3950b47f002d918b8ee",
    ),
    (
        "event_edge_count.bsl",
        "e87391e6e7189f8ed3778005a8e6a81298ab09fd2c2499d2dd9fe16d9c3590af",
    ),
    (
        "event_forall.bsl",
        "386baa2a57681d622beda6297fd9439dd060cc4b3131308b502adc63e2df8e04",
    ),
    (
        "event_metric_conditions.bsl",
        "0f06890bdc03dd521541bb2019a84ea03bd27a3d2565c997bc6c114178c6acfb",
    ),
    (
        "event_node_condition.bsl",
        "c06bd83c4403151a70af815d420f0c60ab6c0b2d91a30d9f13399e5a7eb01cae",
    ),
    (
        "event_wealth_aggregates.bsl",
        "79a94a5bc1131676818ed8b253fcf254f07a619f94a0255a3560e9fe1a9d9fcd",
    ),
    (
        "rng_edge_type_draw.bsl",
        "ba83fecff0f748ea14e742b0f8c815a230d7581316b1ddb9203f5a1b04386540",
    ),
    (
        "rng_expr_draw.bsl",
        "8344aed7fc0d5e4045af424fb4787fbc8bee850de7bd8e4f23b09cdb8e5e6ac2",
    ),
    (
        "rng_fold_draw.bsl",
        "48429f2d62c274430dc35531e696bc122290f83dc3e1fc29416910c0740ec7ca",
    ),
    (
        "rng_keyed_draw.bsl",
        "bb51a0a08e95e91c2c981b9bcac92bbc374f17c4aed745dea8046246dfa485a5",
    ),
    (
        "rng_keyed_draw_guarded.bsl",
        "5212c874e1b4f1decdc0f7d8d91d0008d4a9308d3aef215f943bb272978dc5c1",
    ),
    (
        "unconditional.bsl",
        "61bf2a5b6690b6bffe3a3b67fe556ebfeecdf84efa1d1688c94f57c9100bcbf8",
    ),
    (
        "unknown_metric.bsl",
        "299f11b09e064918f81186c96a631d2d599ee7a79a5102a038d7b3ea5bd053f4",
    ),
    (
        "carceral-arc-conformance.bscn",
        "d1b4577f98813cfd17b5e8bd394918a56c5e822c051790bc045254cf6b2a13ad",
    ),
    (
        "consciousness-ternary-conformance.bscn",
        "aaf93f0493b4baa02972f0f35bc045d1096495ba05669b06e9344ea059c6913b",
    ),
    (
        "control-ratio-conformance.bscn",
        "dad3f4a61f7e433a682340a8a7c3f5f62725552d0c98e1c76b191114642ab64a",
    ),
    (
        "control-ratio-revolution-conformance.bscn",
        "57c40b939b24018b67fd01c811b52c4c103a06e372b16df35d489e1a1f71fe01",
    ),
    (
        "control-ratio-within-capacity-conformance.bscn",
        "71767fa10014db7e38abee1b4ee8b884cb7873009a688f8555eb7a9f8406c68c",
    ),
    (
        "control-ratio-zero-enforcer-conformance.bscn",
        "32d3cc3e7bff6b42909fdd77ee5709aa98a5adb85436e17e7f41d84650c1b105",
    ),
    (
        "decomposition-conformance.bscn",
        "9604a3dd733dca5e19ac3c7054d0bcee365e12cba98f45b311b0e61ef1dfbb72",
    ),
    (
        "decomposition-delay-conformance.bscn",
        "38629b42c921b772c50392c262db0cd7c83a3a706ed0749fd0bf5e0783530172",
    ),
    (
        "dispossession-ceiling-matrix-conformance.bscn",
        "f54909f01f5063f6484bbd4f91cd918a8e1db162d85af18b876046867fc04ef5",
    ),
    (
        "dispossession-conformance.bscn",
        "f5bfe458cc19b288afabb131ae954eabb48f263f96d97a7672ca955030932b57",
    ),
    (
        "dispossession-negative-input-conformance.bscn",
        "d39cf58c3161ae6ffdce2d445fdc9e20794678f40192a862e48264cbbbb7bdc1",
    ),
    (
        "dispossession-negative-weight-conformance.bscn",
        "2a4e78aaa6ab5c3beee1c321239a0d9d463479be3e5336be4348b3fe77e10c4f",
    ),
    (
        "dispossession-saturation-conformance.bscn",
        "b99361f2442a5dea483bc50e64bd385f33e105a3ad751a8dd561b39346fd7676",
    ),
    (
        "dispossession-single-rate-conformance.bscn",
        "561fdea375b900df8b4c12a2d39ada31e4cd57753b673d095ee2f06fa18fbc33",
    ),
    (
        "dispossession-zero-rate-conformance.bscn",
        "f51f85e92ef9acc659c9f10743562f28706f5d62662ce1a7a191bb176a08dcbc",
    ),
    (
        "edge-lane-e2e.bscn",
        "2349d230c64ba90225946e9b85334752f9c2beb5a6cb759a8b85635e43a0f800",
    ),
    (
        "edge-write-lane-e2e.bscn",
        "81fd0c95579c372ff02a32b4c8bc15e46579b488ee8093b6248e14d974ff36d8",
    ),
    (
        "imperial-rent-conformance.bscn",
        "5480badcd818c2b629420ae33562f9c2b590b8eff8d197b279544dd152768355",
    ),
    (
        "imperial-rent-multi-tribute-conformance.bscn",
        "55af1c7bcb4c9332c2b5845c7d622da955321edaea8d962c37f28d20c0f2210b",
    ),
    (
        "lifecycle-conformance.bscn",
        "d194d575355b6f30e446c892dd74b470fbcc3d3aaf9610d078fee6f93636b7a7",
    ),
    (
        "lifecycle-crisis-conformance.bscn",
        "754295542d9aaa3df0ebb1c805e632ea2a892ecc156bd4e9b0a7d36dc5fb74a4",
    ),
    (
        "lifecycle-zero-pop-p-conformance.bscn",
        "58bb3e5aa1ba9147a53c54ed2bc0a81a649fdaaf9dfc4e92d7e7b3f3a7e861af",
    ),
    (
        "metabolism-ceiling-conformance.bscn",
        "a7dd2c1e19633a3ac1e9f76730f39d4362615b6e32c5089ce0ff832d08526468",
    ),
    (
        "metabolism-ceiling-suppression-conformance.bscn",
        "2d4f0cb353ed980f10741a1c69d93cff4ba39698de64f7c2d8f892f73445e0ab",
    ),
    (
        "metabolism-conformance.bscn",
        "6050080ce553ae5916fcdc8ef23f83acaac3b1ec341cecae93e8f2a6702b5972",
    ),
    (
        "metabolism-entropy-high-conformance.bscn",
        "5c7e0ed77f6c866036870d8e09f9777187c02bfee6404c199e6fe2033d7144ec",
    ),
    (
        "metabolism-entropy-low-conformance.bscn",
        "bd08cdd45d41e4b44f38c13297232ddef0b0bcc6d10ec45282b185c2cf690a04",
    ),
    (
        "metabolism-extreme-damage-conformance.bscn",
        "b6995b06d7009056970b5dbc25eb3d246371c7326bb181fe308f4fc6d6dbf5ca",
    ),
    (
        "metabolism-ratcheted-ceiling-conformance.bscn",
        "996ed84bc534e80c93de5b0d8a91deed7bdf61cce9a23bcb15cb79abc512a9ce",
    ),
    (
        "metabolism-rounding-divergence-conformance.bscn",
        "04ae00c60aabb359788a2f96fa294b78cd5432300fef99495ae51dd2a0063615",
    ),
    (
        "organization-foundation.bscn",
        "90534d4658b3d6adaa637abef12279dcc914a5c805ee1b47ffd4e4d4c69f05ee",
    ),
    (
        "production-conformance.bscn",
        "4179010e9abe89641c1713891ffd0867aa1d26588d9c4e96d51e7ef072423721",
    ),
    (
        "query-lane-e2e.bscn",
        "d6cd61b2fedb9d80ca24ba4366f0f96c7bb57969007170c7d740fe5a1069d407",
    ),
    (
        "solidarity-conformance.bscn",
        "251b7bf2843f2a6d3db25bb79c822be177903bc4258cfd48c8caa56cd46d6223",
    ),
    (
        "territory-conformance.bscn",
        "2c0bf3c8a7a6d67ac4dacc7d24b5c1e8801075b725198cd207f0486035e2fc40",
    ),
    (
        "two-classes.bscn",
        "278918747d41b041853c13a1c31dfb13e34ff8315a2db6441a3a35834624c76e",
    ),
    (
        "us-counties-lifecycle-demo.bscn",
        "75af712c5d5562adf78c1d169852159c521732c4939333de5719fea58d8d6d17",
    ),
    (
        "vitality-attrition-conformance.bscn",
        "1f812b86b713632efb6910043c3579137b80b431201ccb2953b073676a3c52b3",
    ),
    (
        "vitality-conformance.bscn",
        "b61ffb7e5d64a6d88eeee1808200b7c0d724c364dc61e34fabf49e4ee4a11620",
    ),
    (
        "vitality-lifecycle-combined-conformance.bscn",
        "bef48841b30fe8fd32a142fd316d6cf8a3e357ef7252ba0ce3e9d0867cf44a0f",
    ),
    (
        "worldview-foundation.bscn",
        "e1ad5e1a5a0fafa858d398cdca5202b8897041329f60a8a03f6370b4b2e8e40d",
    ),
    (
        "worldview.bscn",
        "23a650f0f3bdb33da8e8bc66f6aa8d27475ddc8422adbcb93637f66cf3d26ae0",
    ),
];

#[test]
fn read_all_digest_is_pinned_across_the_full_content_corpus() {
    let files = corpus_files();
    let mut actual: Vec<(String, String)> = Vec::with_capacity(files.len());
    for path in &files {
        let label = path
            .file_name()
            .and_then(|n| n.to_str())
            .expect("utf8 filename")
            .to_string();
        let bytes =
            std::fs::read(path).unwrap_or_else(|e| panic!("reading {}: {e}", path.display()));
        let forms = read_all(&bytes)
            .unwrap_or_else(|e| panic!("{} failed to read_all: {e:?}", path.display()));
        let digest = sha256_hex(format!("{forms:#?}").as_bytes());
        actual.push((label, digest));
    }

    if actual.len() != PINNED_DIGESTS.len() {
        use std::fmt::Write as _;
        let mut dump = String::new();
        for (label, digest) in &actual {
            let _ = writeln!(dump, "    (\"{label}\", \"{digest}\"),");
        }
        panic!(
            "PINNED_DIGESTS is empty/stale ({} pinned vs {} discovered) — \
             paste this into PINNED_DIGESTS:\n{dump}",
            PINNED_DIGESTS.len(),
            actual.len()
        );
    }

    for ((label, digest), (expected_label, expected_digest)) in actual.iter().zip(PINNED_DIGESTS) {
        assert_eq!(
            label, expected_label,
            "content corpus membership/order moved — re-derive PINNED_DIGESTS deliberately"
        );
        assert_eq!(
            digest, expected_digest,
            "read_all's parsed tree for {label} moved"
        );
    }
}

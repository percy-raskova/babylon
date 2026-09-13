//! Embedded soundtrack order. Titles describe compositions, not live campaign events.

pub(super) struct MusicTrack {
    pub title: &'static str,
    pub path: &'static str,
    pub bytes: &'static [u8],
}

// Start each viewer session with History Breathing, then visit every recording.
pub(super) const DEFAULT_TRACK_INDEX: usize = 0;

macro_rules! soundtrack {
    ($(($title:literal, $path:literal)),+ $(,)?) => {
        pub(super) const MUSIC_TRACKS: &[MusicTrack] = &[
            $(MusicTrack {
                title: $title,
                path: concat!($path, ".ogg"),
                bytes: include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"), "/../../../assets/", $path, ".ogg"
                )),
            },)+
        ];
    };
}

soundtrack![
    ("History Breathing", "music/ambient/01_history_breathing"),
    ("Phi", "music/babylon_theme_phi"),
    ("Panopticon", "music/babylon_theme_panopticon"),
    ("Wages Falling", "music/crisis/01_wages_falling"),
    ("The Squeeze", "music/crisis/02_the_squeeze"),
    ("Material Disruption", "music/crisis/03_material_disruption"),
    ("Red Dawn", "music/endgame/01_red_dawn"),
    ("The Long Winter", "music/endgame/02_the_long_winter"),
    ("Iron Consolidation", "music/endgame/03_iron_consolidation"),
    ("Dual Power", "music/endgame/04_dual_power"),
    ("Shattered Map", "music/endgame/05_shattered_map"),
    ("Beast Engine", "music/entity/01_beast_engine"),
    ("Tribute Bleed", "music/entity/02_tribute_bleed"),
    ("Dissection", "music/entity/03_dissection"),
    ("The Mask", "music/entity/04_the_mask"),
    ("The Void", "music/fascist/01_the_void"),
    ("The Scapegoat", "music/fascist/02_scapegoat"),
    ("The Rally", "music/fascist/03_the_rally"),
    ("Blood and Soil", "music/fascist/04_blood_and_soil"),
    ("The Purge", "music/fascist/05_the_purge"),
    ("False Order", "music/fascist/06_false_order"),
    ("The Apparatus", "music/fascist/07_the_apparatus"),
    ("Economic Crisis", "music/fascist/08_economic_crisis"),
    ("Juggling Act", "music/fascist/09_juggling_act"),
    ("Unequal Exchange", "music/periphery/01_unequal_exchange"),
    ("Superwage", "music/periphery/02_superwage"),
    ("The Spark", "music/revolutionary/01_the_spark"),
    (
        "Solidarity Rising",
        "music/revolutionary/02_solidarity_rising"
    ),
    ("Class Awakening", "music/revolutionary/03_class_awakening"),
    (
        "The Internationale",
        "music/revolutionary/04_the_internationale"
    ),
    ("Rupture", "music/revolutionary/05_rupture"),
    ("Overshoot", "music/rift/01_overshoot"),
    ("The Silent Spring", "music/rift/02_the_silent_spring"),
    ("The Ballot", "music/superstructure/01_the_ballot"),
    (
        "The Reform Ceiling",
        "music/superstructure/02_the_reform_ceiling"
    ),
    ("Officeholder", "music/superstructure/03_officeholder"),
];

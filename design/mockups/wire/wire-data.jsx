// wire-data.jsx — mock data for The Wire
// Each story is rendered THREE TIMES (corporate / liberated / intel),
// with a euphemism map linking lexical equivalents across channels.

const WIRE_DATA = {
  meta: {
    tick: 42,
    session: "wayne-county-001",
    operator: "RASKOVA-2",
    freq: "88.7 MHz",
    qth: "WAYNE CO / GRID EN82",
    classification: "TS//SI//NOFORN",
    cable_id: "1847-A",
    page_of: "001/047",
    timestamp_utc: "2026-05-12T08:47:22Z",
  },

  // ---------- THE INDEX ----------
  // Coverage marks: which channels have a take on this story.
  // c = continental, l = liberated, i = intel
  index: [
    {
      id: "WC-RAID-0042",
      tick: 42,
      slug: "FEDERAL RAID · WCLF HQ · DEARBORN",
      hed: { c: "Federal Authorities Conduct Security Operation in Dearborn",
             l: "PIGS RAIDED LABOR FED HQ // 14 COMRADES SNATCHED",
             i: "BREACH // WCLF-DEARBORN // 14× DETAINED" },
      coverage: ["c", "l", "i"],
      pinned: true,
      severity: "critical",
    },
    {
      id: "WC-STRIKE-0041",
      tick: 41,
      slug: "AUTO PLANT · DEARBORN · WALKOUT",
      hed: { c: "Stellantis Reports Production Disruption at Sterling Plant",
             l: "STERLING DROPPED THEIR TOOLS AT 0600 // ENTIRE A-SHIFT OUT",
             i: "LABOR ACTION // STERLING ASSY // T-72H STRIKE CALL" },
      coverage: ["c", "l", "i"],
      severity: "warning",
    },
    {
      id: "WC-RENT-0040",
      tick: 40,
      slug: "RENT SCHEDULE · WAYNE CO PORTFOLIO",
      hed: { c: "Market Correction Brings Wayne County Rents to Regional Average",
             l: "LANDLORD CLASS SQUEEZES HARDER // 18% HIKE IN ONE QUARTER",
             i: "RENT EXTRACTION +0.042 // WAYNE-CORE / DEARBORN-S" },
      coverage: ["c", "l", "i"],
      severity: "warning",
    },
    {
      id: "WC-CONSC-0039",
      tick: 39,
      slug: "READING CIRCLES · WCLF PERIPHERY",
      hed: { c: "Local Book Clubs Draw Renewed Interest from Younger Readers",
             l: "STUDY GROUPS HITTING 200+ A WEEK // THE MASS LINE HOLDS",
             i: "CONSCIOUSNESS Δ +0.022 // WCLF-PERIPHERY" },
      coverage: ["c", "l", "i"],
      severity: "info",
    },
    {
      id: "WC-INFORMANT-0038",
      tick: 38,
      slug: "INFORMANT · ORGANIZING NETWORK",
      hed: { c: "FBI Confirms Cooperating Witness in Ongoing Inquiry",
             l: "RAT IN THE KITCHEN // BURNED COMRADE NAMED FRIDAY",
             i: "CHS-7 ACTIVE // WCLF/SOLIDARITY-NET // HEAT +0.071" },
      coverage: ["c", "l", "i"],
      severity: "critical",
    },
    {
      id: "WC-AID-0037",
      tick: 37,
      slug: "MUTUAL AID · DEARBORN-S BIOCAP CRISIS",
      hed: { c: "Faith Groups Coordinate Food Drive in Affected Neighborhoods",
             l: "NEIGHBORS FED 1,400 LAST WEEK WHILE CITY HALL SLEPT",
             i: "RESOURCE TRANSFER 1.4K HH // ALLIED-ORG CLUSTER" },
      coverage: ["c", "l"],
      severity: "info",
    },
  ],

  // ---------- THE STORY: WC-RAID-0042, fully rendered ----------
  // The euphemism map: each `term` ID is referenced via <span data-euph="t1">...</span>
  // in the body strings, and resolved at render time into highlights linked across columns.
  euphemisms: {
    "raid":       { c: "security operation",       l: "RAID",                  filter: "OWNERSHIP / SOURCING", note: "State spokesperson is sole source. Verb erased: who breached whom?" },
    "arrest":     { c: "detain for questioning",   l: "SNATCH / ABDUCT",       filter: "SOURCING",             note: "‘Detain’ implies temporary; 14 are still held without charge at +18h." },
    "organizers": { c: "individuals",              l: "COMRADES / ORGANIZERS", filter: "FLAK / IDEOLOGY",      note: "Subjecthood removed. Names withheld until family confirms." },
    "hq":         { c: "community center",         l: "WCLF HALL / OUR HALL",  filter: "OWNERSHIP",            note: "Property classification scrubbed. 11-year-old federation HQ at 7100 Schaefer." },
    "files":      { c: "materials",                l: "PRINTERS · ROLODEX · MUTUAL AID LEDGERS · STRIKE FUND BOOKS", filter: "SOURCING", note: "What was actually taken matters. ‘Materials’ permits any contraband framing." },
    "violence":   { c: "measured and proportionate", l: "BATTERING RAMS · FLASHBANGS · KNEE-ON-NECK",         filter: "IDEOLOGY",             note: "Worth-doing-ness assumed. The state grades its own paper." },
    "civilian":   { c: "concerned community members", l: "NEIGHBORS / FAMILIES / KIDS WATCHING",              filter: "SOURCING",             note: "Witnesses present, unnamed. Their account doesn’t lead." },
    "rifles":     { c: "an undisclosed quantity of firearms", l: "4× LEGALLY-REGISTERED HUNTING RIFLES",      filter: "OWNERSHIP / FLAK",     note: "Number hidden; legality omitted. ‘Stockpile’ framing preloaded." },
  },

  // The story split into ordered blocks. Each channel renders them in its register.
  story: {
    id: "WC-RAID-0042",
    tick: 42,
    location: "Dearborn, Wayne County, MI",
    time_local: "Tue 03:47 EDT",

    // Continental — passive voice, generous whitespace, official-source-led
    continental: {
      brand: "CONTINENTAL",
      monogram: "C\u2022N",
      kicker: "NATIONAL · LAW ENFORCEMENT",
      hed: "Federal Authorities Conduct Security Operation in Dearborn, Detain 14 for Questioning",
      dek: "Department of Homeland Security says the pre-dawn action targeted a Wayne County address tied to an ongoing public-safety inquiry. No charges have been announced.",
      byline: "By J. Halvorsen and M. Pereira · Updated 5h ago",
      paragraphs: [
        // Each para is an array of [text, optional {euph, sup}]
        [
          "DEARBORN, Mich. — Federal authorities conducted a coordinated ",
          { euph: "raid", text: "security operation" },
          " early Tuesday morning at a Wayne County ",
          { euph: "hq", text: "community center" },
          ", ",
          { euph: "arrest", text: "detaining 14 individuals for questioning" },
          " in connection with what officials described as \u201Congoing public-safety concerns.\u201D",
          { sup: 1 },
        ],
        [
          "The operation, executed under a sealed warrant, recovered an ",
          { euph: "files", text: "undisclosed quantity of materials" },
          " from the premises, according to a Department of Homeland Security spokesperson. A small number of ",
          { euph: "rifles", text: "firearms" },
          " were also secured.",
          { sup: 2 },
        ],
        [
          "The spokesperson confirmed that the action was \u201C",
          { euph: "violence", text: "measured and proportionate" },
          "\u201D to the underlying threat assessment, and noted that no agents were injured during the entry. One ",
          { euph: "organizers", text: "individual" },
          " was transported to a local hospital for evaluation; their condition was not disclosed.",
          { sup: 3 },
        ],
        [
          { euph: "civilian", text: "Concerned community members" },
          " gathered outside the address as the operation concluded, expressing concern over the methods employed. The Department declined to confirm whether charges will be filed; persons questioned may be released without charge, according to standard procedure.",
          { sup: 4 },
        ],
        [
          "Wayne County has been the subject of heightened federal attention in recent months following a series of reported workplace disruptions and what one law-enforcement source characterized as \u201Cescalating coordination between previously unaffiliated activist groups.\u201D",
          { sup: 5 },
        ],
      ],
      bibliography: [
        { n: 1, src: "DHS Office of Public Affairs", kind: "press release", id: "DHS-OPA-2026-0512-01", chunk: "chunk_corpus_dhs_pr_0418", sim: 0.91 },
        { n: 2, src: "DHS Office of Public Affairs", kind: "press release", id: "DHS-OPA-2026-0512-01", chunk: "chunk_corpus_dhs_pr_0419", sim: 0.88 },
        { n: 3, src: "Senior DHS official", kind: "background, attributable on consent", id: "BG-0512-022", chunk: "chunk_corpus_bg_0512_022", sim: 0.74 },
        { n: 4, src: "Continental newsroom; standard-procedure boilerplate", kind: "house style", id: "CN-STYLE-7.4.2", chunk: "chunk_corpus_cn_style_742", sim: 0.99 },
        { n: 5, src: "Law-enforcement source familiar with the matter", kind: "anonymous, single source", id: "ANON-0511-007", chunk: "chunk_corpus_anon_0511_007", sim: 0.66 },
      ],
    },

    // Liberated — pirate-radio phosphor, samizdat density
    liberated: {
      brand: "FREE SIGNAL",
      callsign: "WCLF-PIRATE-887",
      operator: "RASKOVA-2",
      hed: "PIGS RAIDED THE WCLF HALL // 14 COMRADES SNATCHED AT 0347",
      pre: "[ BEGIN TRANSMISSION · 0512Z · CIPHER: NONE · BROADCAST IN THE CLEAR ]",
      post: "[ END TRANSMISSION · TUNE 88.7 AT NEXT HOUR · DEATH TO IMPERIALISM ]",
      paragraphs: [
        {
          body: [
            "AT 0347 TUESDAY, FEDS WITH ",
            { euph: "violence", text: "BATTERING RAMS AND FLASHBANGS" },
            " BROKE THE FRONT DOOR OF THE ",
            { euph: "hq", text: "WCLF HALL ON SCHAEFER" },
            ". A SHOCK TEAM WENT IN BEFORE THE FIRST CALL TO COUNSEL WAS COMPLETE."
          ],
          margin: { ref: "AFFIDAVIT-WCLF-0512", chunk: "chunk_corpus_aff_0512", note: "front-door cam timestamp 03:47:22" },
        },
        {
          body: [
            "THEY DRAGGED ",
            { euph: "arrest", text: "14 OF OUR COMRADES" },
            " INTO THE COLD IN ZIP TIES. ",
            { euph: "civilian", text: "NEIGHBORS WATCHED FROM PORCHES" },
            ". KIDS WATCHED. PHOTOS WERE TAKEN. WE HAVE THEM. WE WILL PUBLISH THEM."
          ],
          margin: { ref: "WITNESS-CHAVEZ / WITNESS-OKONKWO", chunk: "chunk_corpus_wit_0512_a", note: "two unrelated witnesses, distinct apts" },
        },
        {
          body: [
            "BRO. J. KAMINSKI, 71, A LIFETIME UAW LOCAL 600 MAN, WAS KNELT ON FOR ELEVEN MINUTES. HE IS AT BEAUMONT NOW WITH BRUISED RIBS AND A FRACTURED ORBITAL. ",
            "HE WAS BRINGING COFFEE FROM THE BACK ROOM. HE WAS NOT RESISTING. WE HAVE THE COFFEE STILL ON THE FLOOR.",
          ],
          margin: { ref: "ER-RECORD / BEAUMONT-0512-0521", chunk: "chunk_corpus_er_0512", note: "admit 04:21 // GCS 14 // chest CT pending" },
        },
        {
          body: [
            "THEY SEIZED OUR ",
            { euph: "files", text: "PRINTERS, OUR MEMBERSHIP ROLODEX, MUTUAL AID LEDGERS, STRIKE FUND BOOKS" },
            ", AND A CABINET CONTAINING ",
            { euph: "rifles", text: "FOUR LEGALLY-REGISTERED HUNTING RIFLES" },
            " THAT BELONG TO THE WCLF RIFLE CLUB. THE CABINET HAS A PADLOCK AND A SIGN-OUT SHEET. THE SHEET IS ALSO GONE."
          ],
          margin: { ref: "INVENTORY-WCLF-0511 (TIMESTAMPED PRIOR TO RAID)", chunk: "chunk_corpus_inv_0511", note: "complete asset list 18h prior" },
        },
        {
          body: [
            "THE STATE CALLS THIS ",
            { euph: "raid", text: "‘PUBLIC SAFETY’" },
            ". WE CALL IT WHAT IT IS: TERROR DESIGNED TO BREAK THE STRIKE WAVE BEFORE IT CRESTS. ",
            "THE SCHEDULED STERLING WALKOUT IS IN 71 HOURS. THIS IS NOT A COINCIDENCE."
          ],
          margin: { ref: "STERLING WALKOUT CALL · WCLF COUNCIL · 0509", chunk: "chunk_corpus_swc_0509", note: "raid timed -71h from strike T0" },
        },
        {
          body: [
            "BAIL FUND OPEN. LEGAL OBSERVERS WANTED AT FEDERAL DETENTION. WE ASK FOR NOTHING BUT YOUR PRESENCE. ",
            "WE HOLD THE LINE. WE FEED EACH OTHER. WE DO NOT FORGET NAMES."
          ],
          margin: { ref: "WCLF MUTUAL AID PROTOCOL §3", chunk: "chunk_corpus_mutaid_p3", note: "rapid response activation 0512 05:00" },
        },
      ],
    },

    // Intel — hybrid: terse prose + structured fields + selective redactions
    intel: {
      classification: "TS//SI//NOFORN",
      cable_id: "1847-A",
      origin: "FBI/HSI JOINT TASKFORCE \u2014 ▮▮▮▮▮▮ FIELD OFFICE",
      routing: ["▮▮▮▮▮▮/CT", "DHS/I&A", "DOJ/NSD", "WHIT-HOUSE/SITROOM"],
      caveat: "HANDLE VIA COMINT CHANNELS ONLY",
      subj: "BREACH OPERATION · WCLF-DEARBORN · POST-ACTION",
      fields: [
        ["EVENT", "BREACH / DETAIN / SEIZE"],
        ["LOCAL TIME", "03:47 EDT · 12 MAY 2026"],
        ["LOCATION", "7100 ▮▮▮▮▮▮▮▮▮ AVE · DEARBORN · MI"],
        ["WARRANT", "FISC SEALED · 18 USC §371 PRELIM"],
        ["BREACH ELEMENTS", "2× ENTRY · 1× CONTAINMENT · 1× MEDICAL STBY"],
        ["DETAINEES", "14× PROCESSED · 0× CHARGED AT +18H"],
        ["MEDICAL", "1× HOSPITAL (SUBJ-7 · AGE 71 · ▮▮▮▮▮▮▮▮▮▮)"],
        ["SEIZED", "PRINT-PROD (3) · DEVICES (11) · LONG-GUNS (4× HUNTING-CLASS · REGISTERED)"],
        ["RESISTANCE", "NONE OBSERVED"],
        ["AGENT INJURY", "NONE"],
        ["CONFIDENCE", "HIGH · 0.84"],
      ],
      assessment: [
        "Action precedes WCLF-CALLED REGIONAL STRIKE at T+71H. Timing assessed deliberate.",
        "CHS-7 (WCLF/SOLIDARITY-NET) provided breach packet 0509\u20130511. Reliability nominal.",
        "Liberated-channel transmission on 88.7 MHz began 05:12 local; OP-handle ‘RASKOVA-2’. Disposition: active.",
        "Continental-press uptake at T+5h via DHS/OPA release; framing nominal.",
        "Recommend continued ELINT coverage of WCLF call tree; HEAT delta +0.071 confirmed by ▮▮▮▮▮▮▮▮.",
      ],
      refs: [
        { tag: "CHUNK", id: "chunk_corpus_warrant_0511", sim: 0.92, src: "FISC docket 26-▮▮▮▮" },
        { tag: "CHUNK", id: "chunk_corpus_chs7_0510",   sim: 0.81, src: "CHS-7 contact report" },
        { tag: "CHUNK", id: "chunk_corpus_strike_0509", sim: 0.77, src: "WCLF council minutes" },
        { tag: "CHUNK", id: "chunk_corpus_sigint_0512", sim: 0.95, src: "SIGINT/88.7 capture" },
      ],
      distribution: "▮▮▮▮▮▮ / ▮▮▮▮▮▮ / ▮▮▮▮▮▮ · NOFORN · 30D RETAIN",
    },
  },

  // ---------- MANUFACTURING CONSENT — five filters detected on this story ----------
  filters: [
    { id: "ownership",   label: "Ownership",         desc: "Continental is owned by a holding group with auto/defense exposure.",     hits: 3, color: "var(--rent)" },
    { id: "advertising", label: "Advertising",       desc: "Stellantis is Continental\u2019s second-largest advertiser this quarter.", hits: 2, color: "var(--heat)" },
    { id: "sourcing",    label: "Sourcing",          desc: "5 of 5 named sources in the Corporate piece are state/state-adjacent.",   hits: 5, color: "var(--cadre)" },
    { id: "flak",        label: "Flak",              desc: "Two prior WCLF-favorable pieces were retracted under advertiser pressure.", hits: 2, color: "var(--thermal)" },
    { id: "ideology",    label: "Anti-radical ideology", desc: "‘Public safety’ frame presupposes the legitimacy of state violence.", hits: 4, color: "var(--laser)" },
  ],
};

window.WIRE_DATA = WIRE_DATA;

; Organization practice circuit. A seeded organization spends one bounded
; weekly action on rooted work. PRESENCE situates that work; material fields
; on ADJACENCY relations relay capacity; MEMBERSHIP supplies a finite social base;
; COMMAND carries the state response; organized care changes the pressure of
; social reproduction. No territory label grants a bonus, and no rule applies
; a sigmoid. The slow-fast-slow recruitment trajectory follows from these
; interacting limits and feedbacks.
;
; `organization/practice` and `organization/practice-embedding` are seeded
; scenario state in this slice. They prove the causal circuit but are not yet
; a player-input boundary; next-week intent can replace those seeds without
; changing the material rules.
;
; D-1: `EventType/ORGANIZATION_SEEDED` is a KNOWINGLY-UNMINTED, probe-only
; event name — not in ADR196's mint, not a member of the frozen Python
; EventType enum, no consumer anywhere. The scenario deliberately leaves
; EventType undeclared (per-kind opt-in, D119), so the name is inert by
; design and nothing can catch a typo in it. It exists solely so this
; probe has an effect to gate; retire or mint it when the Events-in-BSL
; workstream (WS1, #502) gives emit effects a real observable.
;
; The retained kind probe exercises the content-declared `OrgKind` enum. It
; compares identity only; §2.13 forbids arithmetic on enum members.
(rule organization/kind-probe
  :role mechanic
  :evidence derived
  :material-basis "the state's coercive organs are a distinct material kind; content can see the difference (spec Q1)"
  :fuel 32
  (bindings
    (binding kind :field organization/kind)
    (binding active :field organization/active))
  (when (and (= active 1) (= kind OrgKind/STATE_APPARATUS)))
  (effects
    (emit EventType/ORGANIZATION_SEEDED (probe 1))))

(rule organization/p0-action-budget-reset
  :role mechanic
  :evidence derived
  :material-basis "Every organization receives one bounded weekly practice action; activity and practice kind govern whether the later rule can spend it. The unconditional set is the declared per-tick reset for this multi-writer field."
  :fuel 32
  (bindings
    (binding budget :field organization/action-budget))
  (effects
    (update-node self organization/action-budget (set 1))))

(rule organization/p0-territory-inbox-reset
  :role mechanic
  :evidence derived
  :material-basis "Rooted work and territorial relay are this tick's contributions, so every territory clears both inboxes before organizations act."
  :fuel 32
  (bindings
    (binding rooted-work :field territory/rooted-work-inbox))
  (effects
    (update-node self territory/rooted-work-inbox (set 0.0c))
    (update-node self territory/rooted-relay-inbox (set 0.0c))))

(rule organization/p1-rooted-work
  :role mechanic
  :evidence derived
  :material-basis "Situated practice changes only territories reached through PRESENCE relations whose material embedding matches the organization's chosen practice. One weekly action is divided across those matching branches, so an organization cannot create free organizer labor by adding PRESENCE edges. Reproductive pressure conditions each branch's local gain, while circulation remains on the relations that carry it elsewhere."
  :fuel 512
  (bindings
    (binding active :field organization/active)
    (binding practice :field organization/practice)
    (binding practice-embedding :field organization/practice-embedding)
    (binding budget :field organization/action-budget)
    (binding practice-rate :const organization/practice-rate)
    (binding branch-count :expr
      (fold count (neighbors self EdgeType/PRESENCE :out NodeType/TERRITORY)
        :as branch
        (if (= (field-of
                 (edge-between EdgeType/PRESENCE self branch)
                 presence/embedding)
               practice-embedding)
            1
            0))))
  (when (and (= active 1)
             (= practice PracticeKind/ROOTED_WORK)
             (> budget 0)
             (> branch-count 0)))
  (effects
    (for-each (neighbors self EdgeType/PRESENCE :out NodeType/TERRITORY)
      (guard (= (field-of
                  (edge-between EdgeType/PRESENCE self it)
                  presence/embedding)
                practice-embedding)
        (update-node it territory/rooted-work-inbox
          (add (* (/ practice-rate branch-count)
                  (field-of it territory/reproduction-pressure))))))
    (update-node self organization/action-budget (sub 1))))

(rule organization/p2-territorial-relay
  :role mechanic
  :evidence derived
  :material-basis "Rooted work becomes consequential across a declared circulation relation in proportion to its throughput and reproductive dependence, and in inverse proportion to alternate-route capacity and inventory buffers. No territory category or visible blockage grants intrinsic leverage."
  :fuel 256
  (bindings
    (binding capacity :field territory/rooted-capacity)
    (binding rooted-work :field territory/rooted-work-inbox)
    (binding relay-rate :const organization/relay-rate))
  (when (and (> (+ capacity rooted-work) 0.0c)
             (exists (neighbors self EdgeType/ADJACENCY :out NodeType/TERRITORY))))
  (effects
    (for-each (neighbors self EdgeType/ADJACENCY :out NodeType/TERRITORY)
      (update-node it territory/rooted-relay-inbox
        (add
          (*
            (*
              (*
                (*
                  (* (+ capacity rooted-work) relay-rate)
                  (field-of
                    (edge-between EdgeType/ADJACENCY self it)
                    adjacency/throughput-share))
                (- 1.0c
                   (field-of
                     (edge-between EdgeType/ADJACENCY self it)
                     adjacency/alternate-capacity-share)))
              (- 1.0c
                 (field-of
                   (edge-between EdgeType/ADJACENCY self it)
                   adjacency/inventory-buffer-share)))
            (field-of
              (edge-between EdgeType/ADJACENCY self it)
              adjacency/reproduction-dependence)))))))

(rule organization/p3-rooted-capacity-apply
  :role mechanic
  :evidence derived
  :material-basis "A territory's durable rooted capacity is the bounded accumulation of prior capacity, situated work performed there, and capacity relayed through declared adjacency."
  :fuel 32
  (bindings
    (binding capacity :field territory/rooted-capacity)
    (binding rooted-work :field territory/rooted-work-inbox)
    (binding rooted-relay :field territory/rooted-relay-inbox))
  (when (> (+ rooted-work rooted-relay) 0.0c))
  (effects
    (update-node self territory/rooted-capacity
      (set
        (if (< (+ (+ capacity rooted-work) rooted-relay) 1.0c)
            (+ (+ capacity rooted-work) rooted-relay)
            1.0c)))))

(rule organization/p4-recruitment
  :role mechanic
  :evidence derived
  :material-basis "Recruitment depends on the organization's rooted territorial capacity, the pressure of social reproduction, the unorganized share of its declared membership base, and command pressure in the same places."
  :fuel 512
  (bindings
    (binding active :field organization/active)
    (binding practice :field organization/practice)
    (binding membership :field organization/membership-share)
    (binding recruitment-rate :const organization/recruitment-rate)
    (binding rooted-capacity :expr
      (fold mean (neighbors self EdgeType/PRESENCE :out NodeType/TERRITORY)
        (field-of it territory/rooted-capacity)
        :weight (field-of it territory/resident-population)))
    (binding reproduction-pressure :expr
      (fold mean (neighbors self EdgeType/PRESENCE :out NodeType/TERRITORY)
        (field-of it territory/reproduction-pressure)
        :weight (field-of it territory/resident-population)))
    (binding command-pressure :expr
      (fold mean (neighbors self EdgeType/PRESENCE :out NodeType/TERRITORY)
        (field-of it territory/command-pressure)
        :weight (field-of it territory/resident-population))))
  (when (and (= active 1)
             (= practice PracticeKind/ROOTED_WORK)
             (< membership 1.0c)
             (exists (neighbors self EdgeType/MEMBERSHIP :out NodeType/SOCIAL_CLASS))
             (exists (neighbors self EdgeType/PRESENCE :out NodeType/TERRITORY))))
  (effects
    (update-node self organization/membership-share
      (set
        (if (< (+ membership
                  (* (* (* (* recruitment-rate rooted-capacity)
                           reproduction-pressure)
                        (- 1.0c membership))
                     (- 1.0c command-pressure)))
               1.0c)
            (+ membership
               (* (* (* (* recruitment-rate rooted-capacity)
                        reproduction-pressure)
                     (- 1.0c membership))
                  (- 1.0c command-pressure)))
            1.0c)))))

(rule organization/p5-command-response
  :role mechanic
  :evidence derived
  :material-basis "A state apparatus can answer rooted capacity only in territories reached through its declared COMMAND relation; the response grows against its remaining uncommitted capacity."
  :fuel 128
  (bindings
    (binding active :field organization/active)
    (binding kind :field organization/kind)
    (binding response-rate :const organization/command-response-rate))
  (when (and (= active 1)
             (= kind OrgKind/STATE_APPARATUS)
             (exists (neighbors self EdgeType/COMMAND :out NodeType/TERRITORY))))
  (effects
    (for-each (neighbors self EdgeType/COMMAND :out NodeType/TERRITORY)
      (update-node it territory/command-pressure
        (set
          (if (< (+ (field-of it territory/command-pressure)
                    (* (* response-rate
                          (field-of it territory/rooted-capacity))
                       (- 1.0c (field-of it territory/command-pressure))))
                 1.0c)
              (+ (field-of it territory/command-pressure)
                 (* (* response-rate
                       (field-of it territory/rooted-capacity))
                    (- 1.0c (field-of it territory/command-pressure))))
              1.0c))))))

(rule organization/p6-care-relief
  :role mechanic
  :evidence derived
  :material-basis "An organization converts part of its recruited social base into reproductive relief only through PRESENCE relations whose material embedding matches its current practice, reducing the pressure that first made rooted work possible."
  :fuel 256
  (bindings
    (binding active :field organization/active)
    (binding practice :field organization/practice)
    (binding practice-embedding :field organization/practice-embedding)
    (binding membership :field organization/membership-share)
    (binding care-rate :const organization/care-rate))
  (when (and (= active 1)
             (= practice PracticeKind/ROOTED_WORK)
             (> membership 0.0c)
             (exists (neighbors self EdgeType/PRESENCE :out NodeType/TERRITORY))))
  (effects
    (for-each (neighbors self EdgeType/PRESENCE :out NodeType/TERRITORY)
      (guard (= (field-of
                  (edge-between EdgeType/PRESENCE self it)
                  presence/embedding)
                practice-embedding)
        (update-node it territory/reproduction-pressure
          (set
            (if (> (- (field-of it territory/reproduction-pressure)
                      (* care-rate membership))
                   0.0c)
                (- (field-of it territory/reproduction-pressure)
                   (* care-rate membership))
                0.0c)))))))

(rule mods/local-probability-step
  :role mechanic
  :evidence designed
  :material-basis "A bounded host fixture advances a declared probability field."
  :fuel 64
  (anchor :before survival)
  (bindings
    (binding probability :field social-class/probability))
  (when (<= probability 0.75p))
  (effects
    (update-node self social-class/probability (add 0.25i))))

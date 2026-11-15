; Designed investment alternatives use only the closing company's captured evidence.
(rule company/portfolio-investment
  :role mechanic
  :evidence designed
  :material-basis "Completed company orders, utilization, inventories, equipment wear and available funds bound the next opening's portfolio. Material settlement checks financing and capacity again before any investment."
  :fuel 512
  (anchor :after ooda)
  (bindings
    (binding current-period :tick)
    (binding evidence-period :field company/evidence-period)
    (binding defer-weight :field company/defer-weight)
    (binding replacement-weight :field company/replacement-weight)
    (binding modest-weight :field company/modest-weight)
    (binding larger-weight :field company/larger-weight)
    (binding defer-mass :expr (quantize-mass defer-weight))
    (binding replacement-mass :expr (quantize-mass replacement-weight))
    (binding modest-mass :expr (quantize-mass modest-weight))
    (binding larger-mass :expr (quantize-mass larger-weight)))
  (when (= evidence-period current-period))
  (effects
    (choose :sample company/investment-portfolio :slot 0
      (branch CompanyPortfolio/DEFER
        :mass defer-mass
        (effects
          (update-node self company/selected-portfolio (set 0))
          (update-node self company/selection-period (set current-period))))
      (branch CompanyPortfolio/REPLACEMENT_ONLY
        :mass replacement-mass
        (effects
          (update-node self company/selected-portfolio (set 1))
          (update-node self company/selection-period (set current-period))))
      (branch CompanyPortfolio/MODEST_EXPANSION
        :mass modest-mass
        (effects
          (update-node self company/selected-portfolio (set 2))
          (update-node self company/selection-period (set current-period))))
      (branch CompanyPortfolio/LARGER_EXPANSION
        :mass larger-mass
        (effects
          (update-node self company/selected-portfolio (set 3))
          (update-node self company/selection-period (set current-period)))))))

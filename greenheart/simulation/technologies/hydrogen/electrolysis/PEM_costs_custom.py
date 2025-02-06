def calc_custom_electrolysis_capex_fom(electrolyzer_capacity_kW, electrolyzer_config):
    """calculates electrolyzer total installed capex and fixed O&M based on user-input values.
    Only used if greenheart_config["electrolyzer"]["cost_model"] is set to "custom"
    Requires additional inputs in greenheart_config["electrolyzer"]:
        - fixed_om: electrolyzer fixed o&m in $/kW-year
        - electrolyzer_capex: electrolyzer capex in $/kW

    Args:
        electrolyzer_capacity_kW (float or int): electrolyzer capacity in kW
        electrolyzer_config (dict): ``greenheart_config["electrolyzer"]``

    Returns:
        list(float): ``[capex,fixed_om]``::

            ``capex``: electrolyzer overnight capex in $
            ``fixed_om``: electrolyzer fixed O&M in $/year
    """
    electrolyzer_capex = electrolyzer_config["electrolyzer_capex"] * electrolyzer_capacity_kW
    if "fixed_om" in electrolyzer_config.keys():
        electrolyzer_fopex = electrolyzer_config["fixed_om"] * electrolyzer_capacity_kW
    else:
        electrolyzer_fopex = 0.0
    return electrolyzer_capex, electrolyzer_fopex

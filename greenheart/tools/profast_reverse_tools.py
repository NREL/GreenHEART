
def make_pf_config_from_profast(pf):
    pf_config = {"params":pf.vals,
        "capital_items":pf.capital_items,
        "fixed_costs":pf.fixed_costs,
        "feedstocks":pf.feedstocks,
        "incentives":pf.incentives,
        "coproducts":pf.coproducts,
        "LCO":pf.LCO}
    return pf_config


def convert_pf_res_to_pf_config(pf_config):
    pf_config_new = {}
    config_keys = list(pf_config.keys())
    pf_config_new.update({"params":{}})
    
    new_params = {}
    params = pf_config['params']
    for i in params:
        if i!="fraction of year operated":
            new_params.update({i:params[i]})
    pf_config_new.update({"params":new_params})
    
    if 'feedstocks' in config_keys:
        feedstocks = {}
        feedstock_keys = ["name","usage","unit","cost","escalation"]
        variables = pf_config['feedstocks']
        for i in variables:
            vals = [i,variables[i].usage,variables[i].unit,variables[i].cost,variables[i].escalation]
            feedstocks.update({i:dict(zip(feedstock_keys,vals))})
        pf_config_new.update({"feedstocks":feedstocks})
    
    if 'capital_items' in config_keys:
        variables = pf_config['capital_items']
        capital_items = {}
        citem_keys = ["name","cost","depr_type","depr_period","refurb"]
        for i in variables:
            vals = [i,variables[i].cost,variables[i].depr_type,variables[i].depr_period,variables[i].refurb]
            capital_items.update({i:dict(zip(citem_keys,vals))})
        pf_config_new.update({"capital_items":capital_items})
    
    if 'fixed_costs' in config_keys:
        variables = pf_config['fixed_costs']
        fixed_costs = {}
        fitem_keys = ["name","usage","unit","cost","escalation"]
        for i in variables:
            vals = [i,variables[i].usage,variables[i].unit,variables[i].cost,variables[i].escalation]
            fixed_costs.update({i:dict(zip(fitem_keys,vals))})
        pf_config_new.update({"fixed_costs":fixed_costs})
    
    if 'incentives' in config_keys:
        variables = pf_config['incentives']
        incentive_keys = ["name","value","decay","sunset_years","tax_credit"]
        incentives = {}
        for i in variables:
            if isinstance(variables[i].value,dict):
                new_value = {int(y):v for y,v in variables[i].value.items()}
                vals = [i,new_value,variables[i].decay,variables[i].sunset_years,variables[i].tax_credit]
            else:
                vals = [i,variables[i].value,variables[i].decay,variables[i].sunset_years,variables[i].tax_credit]
            incentives.update({i:dict(zip(incentive_keys,vals))})
        pf_config_new.update({"incentives":incentives})
    
    if 'coproducts' in config_keys:
        variables = pf_config['coproducts']
        coproduct_keys = ["name","usage","unit","cost","escalation"]
        coproducts = {}
        for i in variables:
            if isinstance(variables[i].usage,dict):
                new_usage = {int(y):v for y,v in variables[i].usage.items()}
                vals = [i,new_usage,variables[i].unit,variables[i].cost,variables[i].escalation]
            else:
                vals = [i,variables[i].usage,variables[i].unit,variables[i].cost,variables[i].escalation]
            coproducts.update({i:dict(zip(coproduct_keys,vals))})
        pf_config_new.update({"coproducts":coproducts})
    return pf_config_new
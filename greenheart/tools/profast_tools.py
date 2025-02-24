import numpy as np
import ProFAST
import numpy_financial as npf

def adjust_dollar_year(init_cost,init_dollar_year,adj_cost_year,costing_general_inflation):
    periods = adj_cost_year - init_dollar_year
    adj_cost = -npf.fv(costing_general_inflation,periods,0.0,init_cost)
    return adj_cost

def update_defaults(orig_dict,new_key,new_val):
    for key, val in orig_dict.items():
        if isinstance(val,dict):
            #go deeper
            tmp = update_defaults(orig_dict.get(key, { }), new_key,new_val)
            orig_dict[key] = tmp
        else:
            if isinstance(key,list):
                for i,k in enumerate(key):
                    if k == new_key:
                        orig_dict[k] = new_val
                    else:
                        orig_dict[k] = (orig_dict.get(key, []) + val[i])
            elif isinstance(key,str):
                if key == new_key:
                    orig_dict[key] = new_val
    return orig_dict

def update_params_based_on_defaults(pf_config,update_config):
    #TODO: update this
    if update_config['escalation']['replace all']:
        escalation_val = update_config['escalation']['escalation']
        pf_config = update_defaults(pf_config,'escalation',escalation_val)
    if update_config['depreciation type']['replace all']:
        depr_type = update_config['depreciation type']['depr type']
        pf_config = update_defaults(pf_config,'depr_type',depr_type)
    if update_config['depreciation period']['replace all']:
        depr_prd = update_config['depreciation period']['period']
        pf_config = update_defaults(pf_config,"depr_period",depr_prd)
    if update_config['refurbishment period']['replace all']:
        refurb_prd = update_config['refurbishment period']['refurb']
        pf_config = update_defaults(pf_config,"refurb",refurb_prd)
    return pf_config


def create_and_populate_profast(pf_config):
    
    pf = ProFAST.ProFAST()
    config_keys = list(pf_config.keys())
    if 'params' in config_keys:
        params = pf_config['params']
        inflation = params['general inflation rate']
        for i in params:
            pf.set_params(i,params[i])

    if 'feedstocks' in config_keys:
        variables = pf_config['feedstocks']
        for i in variables:
            pf.add_feedstock(i,variables[i]["usage"],variables[i]["unit"],variables[i]["cost"],variables[i]["escalation"])
            
    if 'capital_items' in config_keys:
        variables = pf_config['capital_items']
        for i in variables:
            pf.add_capital_item(i,variables[i]["cost"],variables[i]["depr_type"],variables[i]["depr_period"],variables[i]["refurb"])
    
    if 'fixed_costs' in config_keys:
        variables = pf_config['fixed_costs']
        for i in variables:
            pf.add_fixed_cost(i,variables[i]["usage"],variables[i]["unit"],variables[i]["cost"],variables[i]["escalation"])
    
    if 'coproducts' in config_keys:
        variables = pf_config['coproducts']
        for i in variables:
            pf.add_coproduct(i,variables[i]["usage"],variables[i]["unit"],variables[i]["cost"],variables[i]["escalation"])
    
    if 'incentives' in config_keys:
        variables = pf_config['incentives']
        for i in variables:
            pf.add_incentive(i,variables[i]["value"],variables[i]["decay"],variables[i]["sunset_years"],variables[i]["tax_credit"])
    return pf

def run_profast(pf):
    sol = pf.solve_price()
    summary = pf.get_summary_vals()
    price_breakdown = pf.get_cost_breakdown()
    return sol,summary,price_breakdown

def make_price_breakdown(price_breakdown,pf_config):
    price_breakdown_feedstocks = {}
    price_breakdown_capex = {}
    price_breakdown_fixed_cost = {}
    full_price_breakdown = {}
    #TODO: update lco_string
    lco_str = 'LCO{}'.format(pf_config['params']['commodity']['name'][0])
    lco_units = '$/{}'.format(pf_config['params']['commodity']['unit'])
    config_keys = list(pf_config.keys())
    if 'capital_items' in config_keys:
        capital_items = pf_config['capital_items']
        total_price_capex = 0
        capex_fraction = {}
        for item in capital_items:
            total_price_capex+=price_breakdown.loc[price_breakdown['Name']==item,'NPV'].tolist()[0]
        for item in capital_items:
            capex_fraction[item] = price_breakdown.loc[price_breakdown['Name']==item,'NPV'].tolist()[0]/total_price_capex
    cap_expense = price_breakdown.loc[price_breakdown['Name']=='Repayment of debt','NPV'].tolist()[0]\
        + price_breakdown.loc[price_breakdown['Name']=='Interest expense','NPV'].tolist()[0]\
        + price_breakdown.loc[price_breakdown['Name']=='Dividends paid','NPV'].tolist()[0]\
        - price_breakdown.loc[price_breakdown['Name']=='Inflow of debt','NPV'].tolist()[0]\
        - price_breakdown.loc[price_breakdown['Name']=='Inflow of equity','NPV'].tolist()[0]\
        - price_breakdown.loc[price_breakdown['Name']=='One time capital incentive','NPV'].tolist()[0]
    remaining_financial = price_breakdown.loc[price_breakdown['Name']=='Non-depreciable assets','NPV'].tolist()[0]\
        + price_breakdown.loc[price_breakdown['Name']=='Cash on hand reserve','NPV'].tolist()[0]\
        + price_breakdown.loc[price_breakdown['Name']=='Property insurance','NPV'].tolist()[0]\
        - price_breakdown.loc[price_breakdown['Name']=='Sale of non-depreciable assets','NPV'].tolist()[0]\
        - price_breakdown.loc[price_breakdown['Name']=='Cash on hand recovery','NPV'].tolist()[0]

    if 'capital_items' in config_keys:
        capital_items = pf_config['capital_items']
        for item in capital_items:
            key_name = '{}: {} ({})'.format(lco_str,item,lco_units)
            price_breakdown_capex[key_name] = price_breakdown.loc[price_breakdown['Name']==item,'NPV'].tolist()[0] + cap_expense*capex_fraction[item]
        full_price_breakdown.update(price_breakdown_capex)

    if 'fixed_costs' in config_keys:
        fixed_items = pf_config['fixed_costs']
        for item in fixed_items:
            key_name = '{}: {} ({})'.format(lco_str,item,lco_units)
            price_breakdown_fixed_cost[key_name] = price_breakdown.loc[price_breakdown['Name']==item,'NPV'].tolist()[0]
        full_price_breakdown.update(price_breakdown_fixed_cost)

    if 'feedstocks' in config_keys:
        feedstock_items = pf_config['feedstocks']
        for item in feedstock_items:
            key_name = '{}: {} ({})'.format(lco_str,item,lco_units)
            price_breakdown_feedstocks[key_name] = price_breakdown.loc[price_breakdown['Name']==item,'NPV'].tolist()[0]
        full_price_breakdown.update(price_breakdown_feedstocks)

    price_breakdown_taxes = price_breakdown.loc[price_breakdown['Name']=='Income taxes payable','NPV'].tolist()[0]\
        - price_breakdown.loc[price_breakdown['Name'] == 'Monetized tax losses','NPV'].tolist()[0]
    
    if pf_config['params']['general inflation rate'] > 0:
        price_breakdown_taxes = price_breakdown_taxes + price_breakdown.loc[price_breakdown['Name']=='Capital gains taxes payable','NPV'].tolist()[0]
    
    full_price_breakdown['{}: Taxes ({})'.format(lco_str,lco_units)] = price_breakdown_taxes
    full_price_breakdown['{}: Finances ({})'.format(lco_str,lco_units)] = remaining_financial
    lco_check = sum(list(full_price_breakdown.values()))
    full_price_breakdown['{}: Total ({})'.format(lco_str,lco_units)]=lco_check

    return full_price_breakdown,lco_check
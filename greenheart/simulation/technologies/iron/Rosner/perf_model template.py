'''
Direct Reduced Iron (DRI) model developed by Rosner et al.
Energy Environ. Sci., 2023, 16, 4121
doi.org/10.1039/d3ee01077e
'''

import pandas as pd
from pathlib import Path
from hopp.utilities import load_yaml
CD = Path(__file__).parent

def load_model(config):
    
    # If re-fitting the model, load an inputs dataframe, 
    # otherwise, load up the coeffs
    if config.performance_model['refit_coeffs']:
        input_df = pd.read_csv(CD/
            config.performance_model['inputs_fp'],index_col=[0,1,2])
        raise NotImplementedError('Coefficient re-fit not coded fit')
    else:
        coeff_df = pd.read_csv(CD/
            config.performance_model['coeffs_fp'],index_col=[0,1,2,3])   
        tech_coeffs = coeff_df['h2_dri_eaf']
    
    return tech_coeffs

def iron_win(config):

    tech_coeffs = load_model(config)

    # Calculate the hydrogen or iron capacity
    if config.hydrogen_amount_kgpy:
        iron_plant_capacity_mtpy = (config.hydrogen_amount_kgpy 
            / 1000
            / tech_coeffs.loc['Hydrogen'].values[0]
            * config.input_capacity_factor_estimate
        )
        hydrogen_amount_kgpy = config.hydrogen_amount_kgpy

    if config.desired_iron_mtpy:
        hydrogen_amount_kgpy = (config.desired_iron_mtpy 
            * 1000
            * tech_coeffs.loc['Hydrogen'].values[0]
            / config.input_capacity_factor_estimate
        )
        iron_plant_capacity_mtpy = (config.desired_iron_mtpy 
            / config.input_capacity_factor_estimate
        )

    return iron_plant_capacity_mtpy, hydrogen_amount_kgpy
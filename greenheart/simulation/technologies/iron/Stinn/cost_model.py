'''
Calculates the total direct capital cost (C) in 2018 US dollars.

From:
Estimating the Capital Costs of Electrowinning Processes
Caspar Stinn and Antoine Allanore 2020 Electrochem. Soc. Interface 29 44
https://iopscience.iop.org/article/10.1149/2.F06202IF
'''

import numpy as np
import pandas as pd
from pathlib import Path

CD = Path(__file__).parent

def main(config):
    # Load coefficients
    coeffs_fp = CD / config.cost_model['coeffs_fp']
    coeffs_df = pd.read_csv(coeffs_fp)
    coeffs = coeffs_df.set_index('Name')['Coeff'].to_dict()

    # Extract coefficients
    alpha_1_numerator = coeffs['alpha_1_numerator']
    alpha_1_denominator = coeffs['alpha_1_denominator']
    alpha_1_temp_offset = coeffs['alpha_1_temp_offset']
    alpha_2_numerator = coeffs['alpha_2_numerator']
    alpha_2_denominator = coeffs['alpha_2_denominator']
    alpha_2_temp_offset = coeffs['alpha_2_temp_offset']
    alpha_3 = coeffs['alpha_3']

    # Assign inputs from config
    T = config.electrolysis_temp  # Electrolysis temperature (°C)
    P = config.pressure  # Pressure (assumed unit)
    p = config.production_rate  # Production rate (kg/s)
    z = config.electron_moles  # Moles of electrons per mole of product
    F = config.faraday_const  # Electric charge per mole of electrons (C/mol)
    j = config.current_density  # Current density (A/m²)
    A = config.electrode_area  # Electrode area (m²)
    e = config.current_efficiency  # Current efficiency (dimensionless)
    M = config.molar_mass  # Electrolysis product molar mass (kg/mol)
    Q = config.installed_capacity  # Installed power capacity (MW)
    V = config.cell_voltage  # Cell operating voltage (V)
    N = config.rectifier_lines  # Number of rectifier lines

    # Pre-costs calculation
    term1 = alpha_1_numerator / (1 + np.exp(alpha_1_denominator * (T - alpha_1_temp_offset)))
    term2 = alpha_2_numerator / (1 + np.exp(alpha_2_denominator * (T - alpha_2_temp_offset)))

    pre_costs = term1 * P**0.8

    # Electrolysis and product handling contribution to total cost
    electrolysis_product_handling = ((p * z * F) / (j * A * e * M))**0.9

    # Power rectifying contribution
    power_rectifying_contribution = alpha_3 * Q * V**0.15 * N**0.5

    # Electrowinning costs
    electrowinning_costs = term2 * electrolysis_product_handling + power_rectifying_contribution

    # Return individual costs for modularity
    return {
        'pre_costs': pre_costs,
        'electrowinning_costs': electrowinning_costs,
        'total_costs': pre_costs + electrowinning_costs
    }

if __name__ == '__main__':
    class Config:
        def __init__(self):
            self.cost_model = {
                'coeffs_fp': 'cost_coeffs.csv'
            }
            # Example values for each variable (replace with actual values)
            self.electrolysis_temp = 1000  # Temperature in °C, example value
            self.pressure = 1.5  # Pressure, example value
            self.production_rate = 1.0  # Total production rate, kg/s
            self.electron_moles = 3  # Moles of electrons per mole of product, example value
            self.faraday_const = 96485  # Electric charge per mole of electrons (Faraday constant), C/mol
            self.current_density = 5000  # Current density, A/m², example value
            self.electrode_area = 30.0  # Electrode area, m², example value
            self.current_efficiency = 0.95  # Current efficiency (dimensionless), example value
            self.molar_mass = 0.018  # Electrolysis product molar mass, kg/mol (e.g., water)
            self.installed_capacity = 500.  # Installed power capacity, MW, example value
            self.cell_voltage = 4.18  # Cell operating voltage, V, example value
            self.rectifier_lines = 3  # Number of rectifier lines, example value

    results = main(Config())
    print(results)

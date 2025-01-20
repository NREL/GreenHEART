import copy
from typing import Dict, Union, Optional, Tuple

import pandas as pd
from pandas import DataFrame
from attrs import define, Factory, field

from pathlib import Path
import importlib
from hopp.utilities import load_yaml

# Get model locations loaded up to refer to
CD = Path(__file__).parent
model_locs_fp = CD / 'model_locations.yaml'
model_locs = load_yaml(model_locs_fp)

@define
class IronPerformanceModelConfig:
    """
    Configuration inputs for the iron performance model.

    Attributes:
        technology (str): The particular iron reduction technology being used in this case.
        site (dict): Contains information on the site where iron is being reduced.
        model (dict): Contains name of performance model and, if necessary, filepaths to
                        secure location passed from input if not part of public GreenHEART.
                        Also contains 'refit_coeffs' boolean to re-do model coefficient curve fitting.
        params (dict): The rest of the parameters for the performance model. TODO: define as fields.
    """
    technology: str = ''
    site: dict = {}
    model: dict = {}
    params: dict = {}

    def __attrs_post_init__(self):
        if self.technology == '':
            raise ValueError("Iron performance technology must be set.")
        if self.site == {}:
            raise ValueError("Iron performance site must be set.")
        if self.model == {}:
            raise ValueError("Iron performance model must be set.")

@define
class IronPerformanceModelOutputs:
    """
    Outputs from the iron performance model.

    Attributes:
        performances_df (DataFrame): Contains locations and modeled iron plant performance outputs.
    """
    performances_df: DataFrame = pd.DataFrame()

    def __attrs_post_init__(self):
        if len(self.performances_df) == 0:
            raise ValueError("No iron performance data has been calculated.")

def run_size_iron_plant_performance(config: IronPerformanceModelConfig) -> IronPerformanceModelOutputs:
    """
    Calculates either the annual iron production in metric tons based on plant capacity and
    available hydrogen or the amount of required hydrogen based on a desired iron production.

    Args:
        config (IronPerformanceModelConfig):
            Configuration object containing all necessary parameters for the capacity sizing,
            including capacity factor estimate and feedstock costs.

    Returns:
        IronPerformanceModelOutputs: An object containing iron plant capacity in metric tons
        per year and amount of hydrogen required in kilograms per year.

    """

    perf_model = config.model['name']
    if config.model['model_fp'] == '':
        config.model['model_fp'] = model_locs['performance'][perf_model]['model']
    if config.model['inputs_fp'] == '':
        config.model['inputs_fp'] = model_locs['performance'][perf_model]['inputs']
    if config.model['coeffs_fp'] == '':
        config.model['coeffs_fp'] = model_locs['performance'][perf_model]['coeffs']
    model = importlib.import_module(config.model['model_fp'])
    model_outputs = model.main(config)
    performances_df = model_outputs

    return IronPerformanceModelOutputs(performances_df)

@define
class IronCostModelConfig:
    """
    Configuration inputs for the iron cost model.

    Attributes:
        technology (str): The particular iron reduction technology being used in this case.
        site (dict): Contains information on the site where iron is being reduced.
        model (dict): Contains name of cost model and, if necessary, filepaths to
                        secure location passed from input if not part of public GreenHEART.
                        Also contains 'refit_coeffs' boolean to re-do model coefficient curve fitting.
        params (dict): The rest of the parameters for the cost model. TODO: define as fields.
    """
    performance: IronPerformanceModelOutputs
    technology: str = ''
    site: dict = {}
    model: dict = {}
    params: dict = {}

    def __attrs_post_init__(self):
        if self.technology == '':
            raise ValueError("Iron cost technology must be set.")
        if self.site == {}:
            raise ValueError("Iron cost site must be set.")
        if self.model == {}:
            raise ValueError("Iron cost model must be set.")

@define
class IronCostModelOutputs:
    """
    Outputs from the iron cost model.

    Attributes:
        costs_df (DataFrame): Contains locations and modeled iron plant cost outputs.
    """
    costs_df: DataFrame = pd.DataFrame()

    def __attrs_post_init__(self):
        if len(self.costs_df) == 0:
            raise ValueError("No iron performance data has been calculated.")

def run_iron_cost_model(config: IronCostModelConfig) -> IronCostModelOutputs:
    """
    Calculates the capital expenditure (CapEx) and operating expenditure (OpEx) for
    a iron manufacturing plant based on the provided configuration.

    Args:
        config (IronCostModelConfig):
            Configuration object containing all necessary parameters for the cost
            model, including plant capacity, feedstock costs, and integration options
            for oxygen and heat.

    Returns:
        IronCostModelOutputs: An object containing detailed breakdowns of capital and
        operating costs, as well as total plant cost and other financial metrics.

    Note:
        The calculation includes various cost components such as electric arc furnace
        (EAF) casting, shaft furnace, oxygen supply, hydrogen preheating, cooling tower,
        and more, adjusted based on the Chemical Engineering Plant Cost Index (CEPCI).
    """
    # If cost model name is "placeholder", use the code that was copied over from Green Steel
    cost_model = config.model['name']
    if config.model['model_fp'] == '':
        config.model['model_fp'] = model_locs['cost'][cost_model]['model']
    if config.model['inputs_fp'] == '':
        config.model['inputs_fp'] = model_locs['cost'][cost_model]['inputs']
    if config.model['coeffs_fp'] == '':
        config.model['coeffs_fp'] = model_locs['cost'][cost_model]['coeffs']
    model = importlib.import_module(config.model['model_fp'])
    model_outputs = model.main(config)

    return IronCostModelOutputs(costs_df = model_outputs)
        

@define
class IronFinanceModelConfig:
    """
    Configuration inputs for the iron finance model.

    Attributes:
        technology (str): The particular iron reduction technology being used in this case.
        site (dict): Contains information on the site where iron is being reduced.
        model (dict): Contains name of finance model and, if necessary, filepaths to
                        secure location passed from input if not part of public GreenHEART.
                        Also contains 'refit_coeffs' boolean to re-do model coefficient curve fitting.
        params (dict): The rest of the parameters for the finance model. TODO: define as fields.
    """
    performance: IronPerformanceModelOutputs
    cost: IronCostModelOutputs
    technology: str = ''
    site: dict = {}
    model: dict = {}
    params: dict = {}

    def __attrs_post_init__(self):
        if self.technology == '':
            raise ValueError("Iron finance technology must be set.")
        if self.site == {}:
            raise ValueError("Iron finance site must be set.")
        if self.model == {}:
            raise ValueError("Iron finance model must be set.")

@define
class IronFinanceModelOutputs:
    """
    Represents the outputs of the iron finance model, encapsulating the results of financial analysis for iron production.

    Attributes:
        sol (dict):
            A dictionary containing the solution to the financial model, including key
            financial indicators such as NPV (Net Present Value), IRR (Internal Rate of
            Return), and breakeven price.
        summary (dict):
            A summary of key results from the financial analysis, providing a
            high-level overview of financial metrics and performance indicators.
        price_breakdown (pd.DataFrame):
            A Pandas DataFrame detailing the cost breakdown for producing iron,
            including both capital and operating expenses, as well as the impact of
            various cost factors on the overall price of iron.
    """

    sol: dict
    summary: dict
    price_breakdown: pd.DataFrame


def run_iron_finance_model(
    config: IronFinanceModelConfig,
) -> IronFinanceModelOutputs:
    """
    Executes the financial model for iron production, calculating the breakeven price
    of iron and other financial metrics based on the provided configuration and cost
    models.

    This function integrates various cost components, including capital expenditures
    (CapEx), operating expenses (OpEx), and owner's costs. It leverages the ProFAST
    financial analysis software framework.

    Args:
        config (IronFinanceModelConfig):
            Configuration object containing all necessary parameters and assumptions
            for the financial model, including plant characteristics, cost inputs,
            financial assumptions, and grid prices.

    Returns:
        IronFinanceModelOutputs:
            Object containing detailed financial analysis results, including solution
            metrics, summary values, price breakdown, and iron price breakdown per
            tonne. This output is instrumental in assessing the financial performance
            and breakeven price for the iron production facility.
    """

    
    finance_model = config.model['name']
    if config.model['model_fp'] == '':
        config.model['model_fp'] = model_locs['finance'][finance_model]['model']
    model = importlib.import_module(config.model['model_fp'])
    model_outputs = model.main(config)

    sol, summary, price_breakdown = model_outputs
    return IronFinanceModelOutputs(sol=sol,
                                   summary=summary,
                                   price_breakdown=price_breakdown)



def run_iron_full_model(greenheart_config: dict) -> \
    Tuple[IronPerformanceModelOutputs, IronCostModelOutputs, IronFinanceModelOutputs]:
    """
    Runs the full iron model, including capacity (performance), cost, and finance models.

    Args:
        greenheart_config (dict): The configuration for the greenheart model.

    Returns:
        Tuple[IronPerformanceModelOutputs, IronCostModelOutputs, IronFinanceModelOutputs]:
            A tuple containing the outputs of the iron capacity, cost, and finance models.
    """
    # this is likely to change as we refactor to use config dataclasses, but for now
    # we'll just copy the config and modify it as needed
    iron_config = copy.deepcopy(greenheart_config['iron'])

    if iron_config["costs"]["lcoh"] != iron_config["finances"]["lcoh"]:
        raise(ValueError(
            "iron cost LCOH and iron finance LCOH are not equal. You must specify both values or neither. \
                If neither is specified, LCOH will be calculated."
            )
        )

    iron_technology = iron_config['technology']
    iron_site = iron_config['site']
    
    iron_performance_inputs = iron_config["performance"]
    performance_model = iron_config["performance_model"]

    iron_cost_inputs = iron_config["costs"]
    cost_model = iron_config["cost_model"]

    iron_finance_inputs = iron_config["finances"]
    finance_model = iron_config["finance_model"]

    iron_finance_inputs['operational_year'] = iron_cost_inputs['operational_year']
    iron_finance_inputs['installation_years'] = iron_cost_inputs['installation_years']
    iron_finance_inputs['plant_life'] = iron_cost_inputs['plant_life']
    iron_finance_inputs['cost_year'] = greenheart_config['project_parameters']['cost_year']

    # run iron performance model to get iron plant size
    performance_config = IronPerformanceModelConfig(
        technology= iron_technology,
        site = iron_site,
        model = performance_model,
        params = iron_performance_inputs
    )
    iron_performance = run_size_iron_plant_performance(performance_config)

    # run iron cost model to get iron plant costs
    cost_config = IronCostModelConfig(
        technology= iron_technology,
        site = iron_site,
        model = cost_model,
        params = iron_cost_inputs,
        performance = iron_performance
    )
    iron_cost = run_iron_cost_model(cost_config)

    # run iron finance model to get iron plant finances
    finance_config = IronFinanceModelConfig(
        technology= iron_technology,
        site = iron_site,
        model = finance_model,
        params = iron_finance_inputs,
        performance = iron_performance,
        cost = iron_cost
    )
    iron_finance = run_iron_finance_model(finance_config)

    return (
        iron_performance,
        iron_cost,
        iron_finance
    )

import pytest
import os

from ORBIT import load_config
from hopp.offshore.fixed_platform_h2 import install_h2_platform, calc_h2_platform_opex 

@pytest.fixture
def config():
    offshore_path = os.path.abspath(os.path.join(os.getcwd(), os.pardir, os.pardir,'hopp','offshore'))

    return load_config(os.path.join(offshore_path,"example_fixed_project_h2.yaml"))

def test_install_h2_platform(config):
    '''
    Test the code that calculates the platform installation cost
    '''
    distance = 24
    mass = 2100
    area = 500

    cost = install_h2_platform(mass, area, distance, install_duration=14)

    assert pytest.approx(cost) == 7200014

def test_calc_substructure_mass_and_cost(config):
    '''
    Test the code that calculates the CapEx from fixed_platform.py
    '''
    pass

def test_calc_platform_opex():
    '''
    Test the code that calculates the OpEx from fixed_platform.py
    '''
    lifetime = 20
    capacity = 200
    opex_rate = 123
    cost = calc_h2_platform_opex(lifetime, capacity, opex_rate)

    assert cost == 492000

def test_install_h2_platform_orbit(config):
    '''
    Test the code that calculates the platform installation cost w/ ORBIT
    '''
    pass 

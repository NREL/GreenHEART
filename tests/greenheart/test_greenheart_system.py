import warnings
from pathlib import Path

from pytest import warns, approx
from hopp.utilities.keys import set_nrel_key_dot_env

from greenheart.simulation.greenheart_simulation import GreenHeartSimulationConfig, run_simulation


set_nrel_key_dot_env()

from ORBIT.core.library import initialize_library


dirname = Path(__file__).parent
orbit_library_path = dirname / "input_files/"
output_path = Path(__file__).parent / "output/"

initialize_library(orbit_library_path)

turbine_model = "osw_18MW"
filename_turbine_config = orbit_library_path / f"turbines/{turbine_model}.yaml"
filename_orbit_config = orbit_library_path / f"plant/orbit-config-{turbine_model}-stripped.yaml"
filename_floris_config = orbit_library_path / f"floris/floris_input_{turbine_model}.yaml"
filename_greenheart_config = orbit_library_path / "plant/greenheart_config.yaml"
filename_greenheart_config_onshore = orbit_library_path / "plant/greenheart_config_onshore.yaml"
filename_hopp_config = orbit_library_path / "plant/hopp_config.yaml"
filename_hopp_config_wind_wave = orbit_library_path / "plant/hopp_config_wind_wave.yaml"
filename_hopp_config_wind_wave_solar = orbit_library_path / "plant/hopp_config_wind_wave_solar.yaml"
filename_hopp_config_wind_wave_solar_battery = (
    orbit_library_path / "plant/hopp_config_wind_wave_solar_battery.yaml"
)

rtol = 1e-5


def test_simulation_wind(subtests):
    config = GreenHeartSimulationConfig(
        filename_hopp_config=filename_hopp_config,
        filename_greenheart_config=filename_greenheart_config,
        filename_turbine_config=filename_turbine_config,
        filename_orbit_config=filename_orbit_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=False,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=1,
        output_level=5,
    )
    lcoe, lcoh, _, hi = run_simulation(config)

    with subtests.test("lcoh"):
        assert lcoh == approx(7.081719974333117)  # TODO base this test value on something

    with subtests.test("lcoe"):
        assert lcoe == approx(0.11273307765405276)  # TODO base this test value on something

    with subtests.test("energy sources"):
        expected_annual_energy_hybrid = hi.system.annual_energies.wind
        assert hi.system.annual_energies.hybrid == approx(expected_annual_energy_hybrid)

    with subtests.test("num_turbines conflict raise warning"):
        config.orbit_config["plant"]["num_turbines"] = 400
        with warns(UserWarning, match="The 'num_turbines' value"):
            lcoe, lcoh, _, hi = run_simulation(config)

    with subtests.test("depth conflict raise warning"):
        config.orbit_config["site"]["depth"] = 4000
        with warns(UserWarning, match="The site depth value"):
            lcoe, lcoh, _, hi = run_simulation(config)

    with subtests.test("turbine_spacing conflict raise warning"):
        config.orbit_config["plant"]["turbine_spacing"] = 400
        with warns(UserWarning, match="The 'turbine_spacing' value"):
            lcoe, lcoh, _, hi = run_simulation(config)

    with subtests.test("row_spacing conflict raise warning"):
        config.orbit_config["plant"]["row_spacing"] = 400
        with warns(UserWarning, match="The 'row_spacing' value"):
            lcoe, lcoh, _, hi = run_simulation(config)


def test_simulation_wind_wave(subtests):
    config = GreenHeartSimulationConfig(
        filename_hopp_config=filename_hopp_config_wind_wave,
        filename_greenheart_config=filename_greenheart_config,
        filename_turbine_config=filename_turbine_config,
        filename_orbit_config=filename_orbit_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=False,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=1,
        output_level=5,
    )

    lcoe, lcoh, _, hi = run_simulation(config)

    # TODO base this test value on something
    with subtests.test("lcoh"):
        assert lcoh == approx(7.994477969806273, rel=rtol)

    # prior to 20240207 value was approx(0.11051228251811765) # TODO base value on something
    with subtests.test("lcoe"):
        assert lcoe == approx(0.1327684219541139, rel=rtol)


def test_simulation_wind_wave_solar(subtests):
    config = GreenHeartSimulationConfig(
        filename_hopp_config=filename_hopp_config_wind_wave_solar,
        filename_greenheart_config=filename_greenheart_config,
        filename_turbine_config=filename_turbine_config,
        filename_orbit_config=filename_orbit_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=False,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=11,
        output_level=5,
    )

    lcoe, lcoh, _, hi = run_simulation(config)

    # prior to 20240207 value was approx(10.823798551850347)
    # TODO base this test value on something. Currently just based on output at writing.
    with subtests.test("lcoh"):
        assert lcoh == approx(12.549197376937979, rel=rtol)

    # prior to 20240207 value was approx(0.11035426429749774)
    # TODO base this test value on something. Currently just based on output at writing.
    with subtests.test("lcoe"):
        assert lcoe == approx(0.13255644222185253, rel=rtol)


def test_simulation_wind_wave_solar_battery(subtests):
    config = GreenHeartSimulationConfig(
        filename_hopp_config=filename_hopp_config_wind_wave_solar_battery,
        filename_greenheart_config=filename_greenheart_config,
        filename_turbine_config=filename_turbine_config,
        filename_orbit_config=filename_orbit_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=False,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=10,
        output_level=8,
    )

    results = run_simulation(config)

    with subtests.test("lcoh"):
        # TODO base this test value on something. Currently just based on output at writing.
        assert results.lcoh == approx(16.781418173568596, rel=rtol)

    with subtests.test("lcoe"):
        # TODO base this test value on something. Currently just based on output at writing.
        assert results.lcoe == approx(0.13274652127663025, rel=rtol)
    with subtests.test("no conflict in om cost does not raise warning"):
        with warnings.catch_warnings():
            warnings.simplefilter("error")

    with subtests.test("wind_om_per_kw conflict raise warning"):
        config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"]["om_capacity"][
            0
        ] = 1.0
        with warns(UserWarning, match="The 'om_capacity' value in the wind 'fin_model'"):
            _ = run_simulation(config)

    with subtests.test("pv_om_per_kw conflict raise warning"):
        config.hopp_config["technologies"]["pv"]["fin_model"]["system_costs"]["om_capacity"][0] = (
            1.0
        )
        with warns(UserWarning, match="The 'om_capacity' value in the pv 'fin_model'"):
            _ = run_simulation(config)

    with subtests.test("battery_om_per_kw conflict raise warning"):
        config.hopp_config["technologies"]["battery"]["fin_model"]["system_costs"]["om_capacity"][
            0
        ] = 1.0
        with warns(UserWarning, match="The 'om_capacity' value in the battery 'fin_model'"):
            _ = run_simulation(config)


def test_simulation_wind_onshore(subtests):
    config = GreenHeartSimulationConfig(
        filename_hopp_config=filename_hopp_config,
        filename_greenheart_config=filename_greenheart_config_onshore,
        filename_turbine_config=filename_turbine_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=False,
        use_profast=True,
        post_processing=False,
        incentive_option=1,
        plant_design_scenario=9,
        output_level=5,
    )
    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_installed_cost_mw"] = 1434000.0
    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_om_per_kw"] = 29.567
    # set skip_financial to false for onshore wind
    config.hopp_config["config"]["simulation_options"]["wind"]["skip_financial"] = False

    lcoe, lcoh, _, _ = run_simulation(config)

    # TODO base this test value on something
    with subtests.test("lcoh"):
        assert lcoh == approx(2.9553584701161095, rel=rtol)

    # TODO base this test value on something
    with subtests.test("lcoe"):
        assert lcoe == approx(0.03486192934806013, rel=rtol)


def test_simulation_wind_onshore_steel_ammonia(subtests):
    config = GreenHeartSimulationConfig(
        filename_hopp_config=filename_hopp_config,
        filename_greenheart_config=filename_greenheart_config_onshore,
        filename_turbine_config=filename_turbine_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=True,
        output_dir=output_path,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=9,
        output_level=7,
    )

    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_installed_cost_mw"] = 1434000.0
    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_om_per_kw"] = 29.567
    config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"]["om_fixed"][0] = (
        config.hopp_config["config"]["cost_info"]["wind_om_per_kw"]
    )
    # set skip_financial to false for onshore wind
    config.hopp_config["config"]["simulation_options"]["wind"]["skip_financial"] = False
    lcoe, lcoh, steel_finance, ammonia_finance = run_simulation(config)

    # TODO base this test value on something
    with subtests.test("lcoh"):
        assert lcoh == approx(2.955360744222285, rel=rtol)

    # TODO base this test value on something
    with subtests.test("lcoe"):
        assert lcoe == approx(0.03486192934806013, rel=rtol)

    # TODO base this test value on something
    with subtests.test("steel_finance"):
        lcos_expected = 1428.9844052002427

        assert steel_finance.sol.get("price") == approx(lcos_expected, rel=rtol)

    # TODO base this test value on something
    with subtests.test("ammonia_finance"):
        lcoa_expected = 1.0679224700416565

        assert ammonia_finance.sol.get("price") == approx(lcoa_expected, rel=rtol)


def test_simulation_wind_battery_pv_onshore_steel_ammonia(subtests):
    plant_design_scenario = 12

    config = GreenHeartSimulationConfig(
        filename_hopp_config=filename_hopp_config_wind_wave_solar_battery,
        filename_greenheart_config=filename_greenheart_config_onshore,
        filename_turbine_config=filename_turbine_config,
        filename_orbit_config=filename_orbit_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=True,
        output_dir=output_path,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=plant_design_scenario,
        output_level=8,
    )

    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_installed_cost_mw"] = 1434000.0
    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_om_per_kw"] = 29.567
    config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"]["om_fixed"][0] = (
        config.hopp_config["config"]["cost_info"]["wind_om_per_kw"]
    )
    # set skip_financial to false for onshore wind
    config.hopp_config["config"]["simulation_options"]["wind"]["skip_financial"] = False
    # exclude wave
    config.hopp_config["technologies"].pop("wave")
    config.hopp_config["site"]["wave"] = False
    # colocated end-use
    config.greenheart_config["plant_design"][f"scenario{plant_design_scenario}"][
        "transportation"
    ] = "colocated"

    # run the simulation
    greenheart_output = run_simulation(config)

    # TODO base this test value on something
    with subtests.test("lcoh"):
        assert greenheart_output.lcoh == approx(2.9371002038947327, rel=rtol)

    # TODO base this test value on something
    with subtests.test("lcoe"):
        assert greenheart_output.lcoe == approx(0.03475765253339192, rel=rtol)

    # TODO base this test value on something
    with subtests.test("steel_finance"):
        lcos_expected = 1420.7295755817165

        assert greenheart_output.steel_finance.sol.get("price") == approx(lcos_expected, rel=rtol)

    # TODO base this test value on something
    with subtests.test("ammonia_finance"):
        lcoa_expected = 1.0663431597014212

        assert greenheart_output.ammonia_finance.sol.get("price") == approx(lcoa_expected, rel=rtol)

    with subtests.test("check time series lengths"):
        expected_length = 8760

        for key in greenheart_output.hourly_energy_breakdown.keys():
            assert len(greenheart_output.hourly_energy_breakdown[key]) == expected_length


def test_simulation_wind_onshore_steel_ammonia_ss_h2storage(subtests):
    config = GreenHeartSimulationConfig(
        filename_hopp_config=filename_hopp_config,
        filename_greenheart_config=filename_greenheart_config_onshore,
        filename_turbine_config=filename_turbine_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=True,
        output_dir=output_path,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=9,
        output_level=7,
    )

    config.greenheart_config["h2_storage"]["size_capacity_from_demand"]["flag"] = True
    config.greenheart_config["h2_storage"]["type"] = "pipe"

    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_installed_cost_mw"] = 1434000.0
    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_om_per_kw"] = 29.567
    config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"]["om_fixed"][0] = (
        config.hopp_config["config"]["cost_info"]["wind_om_per_kw"]
    )
    # set skip_financial to false for onshore wind
    config.hopp_config["config"]["simulation_options"]["wind"]["skip_financial"] = False
    lcoe, lcoh, steel_finance, ammonia_finance = run_simulation(config)

    # TODO base this test value on something
    with subtests.test("lcoh"):
        assert lcoh == approx(9.775875962016503, rel=rtol)

    # TODO base this test value on something
    with subtests.test("lcoe"):
        assert lcoe == approx(0.03486192934806013, rel=rtol)

    # TODO base this test value on something
    with subtests.test("steel_finance"):
        lcos_expected = 1883.8052511395165
        assert steel_finance.sol.get("price") == approx(lcos_expected, rel=rtol)

    # TODO base this test value on something
    with subtests.test("ammonia_finance"):
        lcoa_expected = 1.0679224700416565
        assert ammonia_finance.sol.get("price") == approx(lcoa_expected, rel=rtol)

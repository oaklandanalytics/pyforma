import os

import pandas as pd
import numpy as np
import pytest
import pprint

from .. import pyforma

pp = pprint.PrettyPrinter(indent=4)


@pytest.fixture
def pro_forma_config_basic():
    return {
        "use_types": {
            "0br": {
                "price_per_sqft": 600,
                "size": 600,
                "parking_ratio": .3
            },
            "1br": {
                "price_per_sqft": 650,
                "size": 750,
                "parking_ratio": 1.0
            },
            "2br": {
                "price_per_sqft": 700,
                "size": 850,
                "parking_ratio": 1.5
            },
            "3br+": {
                "price_per_sqft": 750,
                "size": 1000,
                "parking_ratio": 2
            },
            "retail": {
                "rent_per_sqft": 3,
                "parking_ratio": 2
            }
        },
        "parking_types": {
            "surface": {
                "space_size": 300,
                "space_cost_sqft": 30
            },
            "deck": {
                "space_size": 250,
                "space_cost_sqft": 90
            },
            "underground": {
                "space_size": 250,
                "space_cost_sqft": 110
            }
        },
        "building_types": {
            "garden_apartments": {
                "cost_per_sqft": 400,
                "allowable_densities": [5, 15]
            }, "fancy_condos": {
                "cost_per_sqft": 800,
                "allowable_densities": [10-20]
            }, "ground_floor_retail": {
                "cost_per_sqft": 600
            }
        },
        "parcel_size": 10000,
        "floor_area_ratio": 3,
        "cap_rate": .06,
        "max_far": 1.2,
        "max_height": 20,
        "height_per_story": 12,
        "parcel_efficiency": .8,
        "building_efficiency": .8,
        "cost_shifter": 1.2,
        "parcel_acquisition_cost": 1000000,
        "non_res_parking_denom": 1000,
        "use_mix": {
            "use_types": ["0br", "1br", "2br"],
            "mix": [.3, .3, .4],
            "ground_floor": {
                "use": "retail",
                "size": 3000
            }
        },
        "absorption_in_months": 20,  # XXX not used yet
        "parking_type": "deck",
        "building_type": "garden_apartments",
        "built_dua": 10
    }


def test_pyforma_basic_vectorized(pro_forma_config_basic):

    pro_forma_config_basic["parcel_size"] = \
        pd.Series([10000, 20000])
    pro_forma_config_basic["use_types"]["2br"]["price_per_sqft"] = \
        pd.Series([750, 800])

    import time
    t1 = time.time()
    ret = pyforma.residential_sales_proforma(pro_forma_config_basic)
    print time.time()-t1

    del ret["num_units_by_type"]
    print pd.DataFrame(ret).transpose()


def test_pyforma_basic(pro_forma_config_basic):

    ret = pyforma.residential_sales_proforma(pro_forma_config_basic)

    assert (ret["num_units_by_type"] == [3, 3, 4]).all()

    assert ret["stories"] == 3

    assert ret["usable_floor_area"] == 3 * 600 + 3 * 750 + 4 * 850 + 3000

    assert ret["floor_area_including_common_space"] == \
        ret["usable_floor_area"] / .8

    assert ret["parking_spaces"] == \
        3 * .3 + 3 * 1 + 4 * 1.5 + 3000 / 1000.0 * 2

    assert ret["revenue_from_ground_floor"] == 3000 * 3 / .06

    assert ret["revenue"] == 3 * 600 * 600 + 3 * 750 * 650 + 4 * 850 * 700 + \
        ret["revenue_from_ground_floor"]

    assert ret["ground_floor_type"] == "retail"

    assert ret["profit"] == ret["revenue"] - ret["cost"]

    assert ret["parking_type"] == "deck"

    assert ret["parking_area"] == ret["parking_spaces"] * 250

    assert ret["total_floor_area"] == \
        ret["floor_area_including_common_space"] + ret["parking_area"]

    assert ret["footprint_size"] == ret["total_floor_area"] / ret["stories"]

    assert ret["parking_cost"] == ret["parking_area"] * 90

    assert ret["cost"] == ret["parking_cost"] + \
        ret["floor_area_including_common_space"] * 400 * 1.2 + 1000000

    assert ret["building_type"] == "garden_apartments"

    assert ret["built_far"] == 1.70375

    assert ret["height"] == 36

    assert "failure_height" in ret

    assert "failure_far" in ret

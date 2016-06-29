import os
import time

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
                "allowable_densities": [10, 20]
            }, "ground_floor_retail": {
                "cost_per_sqft": 600
            }
        },
        "parcel_size": 10000,
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


def test_cartesian_product():

    df = pyforma.cartesian_product(
        pd.Series([5, 10, 30], name="dua"),
        pd.Series([1, 1.5, 2], name="far"),
        pd.Series([1000, 2000, 3000], name="parcel_sizes"),
        pd.Series([500, 600], name="price_per_sqft")
    )

    assert len(df) == 3 * 3 * 3 * 2

    assert df.price_per_sqft.value_counts().loc[500] == 3 * 3 * 3

    assert df.dua.value_counts().loc[5] == 3 * 3 * 2

    assert len(df.query("dua == 5 and far == 1.5 and parcel_sizes == 1000" +
                        " and price_per_sqft == 600")) == 1


def test_performance_of_vectorized(pro_forma_config_basic):

    cfg = pro_forma_config_basic

    series = [
        pd.Series(np.arange(1, 300, 5), name="dua"),
        pd.Series(np.arange(.25, 8, .5), name="far"),
        pd.Series(np.arange(1000, 100000, 50000), name="parcel_size"),
        pd.Series(np.arange(500, 2000, 500), name="price_per_sqft")
    ]
    df = pyforma.cartesian_product(*series)

    cfg["parcel_size"] = df.parcel_size
    cfg["max_dua"] = df.dua
    cfg["max_far"] = df.far
    cfg["use_types"]["2br"]["price_per_sqft"] = df.price_per_sqft

    t1 = time.time()
    ret = pyforma.spot_residential_sales_proforma(pro_forma_config_basic)
    elapsed1 = time.time() - t1

    t1 = time.time()
    for index, row in df.iterrows():
        cfg["parcel_size"] = row.parcel_size
        cfg["max_dua"] = row.dua
        cfg["max_far"] = row.far
        cfg["use_types"]["2br"]["price_per_sqft"] = row.price_per_sqft
        ret = pyforma.spot_residential_sales_proforma(pro_forma_config_basic)
    elapsed2 = time.time() - t1

    factor = elapsed2 / elapsed1

    # if you run enough pro formas in a batch, it's 900x faster to run
    # the pandas version than to run them one by one - when you run
    # fewer pro formas, like you kind of have to do in a unit test, it
    # will only be 300x faster as is asserted here
    assert factor > 250


def test_different_parking_types(pro_forma_config_basic):

    cfg = pro_forma_config_basic

    d = {}
    for parking in ["surface", "deck", "underground"]:

        cfg["parking_type"] = parking
        d[parking] = \
            pyforma.spot_residential_sales_proforma(pro_forma_config_basic)

    assert d["surface"]["parking_spaces"] == d["deck"]["parking_spaces"] == \
        d["underground"]["parking_spaces"]

    spaces = d["surface"]["parking_spaces"]
    assert d["surface"]["parking_area"] == \
        spaces * cfg["parking_types"]["surface"]["space_size"]

    # surface pushes building up, underground keeps is low
    assert d["surface"]["stories"] > d["deck"]["stories"] > \
        d["underground"]["stories"]

    parking_far = d["deck"]["parking_area"] / cfg["parcel_size"]
    # these don't perfectly equal so do this weird subtraction
    assert d["deck"]["built_far"] - \
        parking_far - d["underground"]["built_far"] < .01
    assert d["deck"]["built_far"] - \
        parking_far - d["surface"]["built_far"] < .01

    assert -1 * (d["deck"]["profit"] - d["surface"]["profit"]) == \
        d["deck"]["parking_area"] * \
        cfg["parking_types"]["deck"]["space_cost_sqft"] - \
        d["surface"]["parking_area"] * \
        cfg["parking_types"]["surface"]["space_cost_sqft"]


def test_pyforma_basic_vectorized(pro_forma_config_basic):

    cfg = pro_forma_config_basic

    series = [
        pd.Series(np.arange(1, 300, 5), name="dua"),
        pd.Series(np.arange(.25, 8, .5), name="far"),
        pd.Series(np.arange(1000, 100000, 10000), name="parcel_size"),
        pd.Series(np.arange(500, 2000, 250), name="price_per_sqft")
    ]
    df = pyforma.cartesian_product(*series)
    print pyforma.describe_cartesian_product(*series)

    pro_forma_config_basic["parcel_size"] = df.parcel_size
    pro_forma_config_basic["use_types"]["2br"]["price_per_sqft"] = \
        df.price_per_sqft

    t1 = time.time()
    ret = pyforma.spot_residential_sales_proforma(pro_forma_config_basic)
    t2 = time.time()
    assert t2 - t1 < 1.0

    print "Ran {} pro forma in {:.2f}s".format(len(df), t2-t1)

    num_2_brs = ret["num_units_by_type"][2]
    del ret["num_units_by_type"]
    ret = pd.DataFrame(ret)

    one, two, three = df.loc[0], df.loc[1], df.loc[2]
    # only thing in the assumptions that's different is the price
    assert one.dua == two.dua == three.dua
    assert one.far == two.far == three.far
    assert one.parcel_size == two.parcel_size == three.parcel_size
    assert one.price_per_sqft + 500 == two.price_per_sqft + 250 == \
        three.price_per_sqft

    # since the only thing that's different is the price, the revenue
    # and profit should be different by the number of 2brs, the size of
    # the 2 brs, and the difference in the price per size
    one, two, three = ret.loc[0], ret.loc[1], ret.loc[2]
    assert 17.0375 == one.built_far == two.built_far == three.built_far
    assert two.profit - one.profit == \
        num_2_brs * cfg["use_types"]["2br"]["size"] * 250
    assert three.revenue - two.revenue == \
        num_2_brs * cfg["use_types"]["2br"]["size"] * 250


def test_pyforma_basic(pro_forma_config_basic):

    ret = pyforma.spot_residential_sales_proforma(pro_forma_config_basic)

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

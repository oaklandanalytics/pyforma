import pandas as pd
import numpy as np


def describe_cartesian_product(*args):
    """
    Returns a string to describe
    """
    n = reduce(lambda x, y: x * y, [len(s) for s in args])
    s = reduce(lambda x, y: str(x) + " x " + str(y),
               [len(s) for s in args]) + " = " + str(n)
    return s


def cartesian_product(*args):
    """
    Return the cartesion product of multiple series as a dataframe -
    just pass in the series as arguments (see the test)
    """

    dfs = [pd.DataFrame({s.name: s, "key": 0}) for s in args]
    df = reduce(
        lambda df1, df2: df1.merge(df2, how='left', on='key'),
        dfs)
    df.drop('key', 1, inplace=True)   # drop temp key
    return df


def price_per_sqft_with_affordable_housing(
    price_per_sqft,
    sqft_per_unit,
    AMI,
    depth_of_affordability,
    price_multiplier,
    cap_rate,
    pct_affordable_units
):

    AMI *= depth_of_affordability

    monthly_payment = AMI * .33 / 12 * price_multiplier

    value_of_payment = monthly_payment * 12 / cap_rate

    affordable_price_per_sqft = value_of_payment / sqft_per_unit

    blended_price_per_sqft = \
        pct_affordable_units * affordable_price_per_sqft + \
        (1-pct_affordable_units) * price_per_sqft

    return blended_price_per_sqft


def average_unit_size(cfg):
    """
    Compute the overall average unit size, combining the unit mix
    and sizes per unit
    """

    sizes = 0
    for use_type, mix in \
            zip(cfg["use_mix"]["use_types"], cfg["use_mix"]["mix"]):

        sizes += cfg["use_types"][use_type]["size"] * mix

    return sizes


def spot_residential_sales_proforma(cfg):
    """
    This takes a hierarchical Python object of a certain form and
    passes back another Python object.  Documenting the structure
    is not well suited to pydocs - see the Readme instead.
    """

    parcel_acres = cfg["parcel_size"] / 43560.0

    num_units_by_type = {"residential_units": 0}

    # compute basic measures for floor area in units
    usable_floor_area = 0
    revenue = 0
    parking_spaces = 0
    for use_type, mix in \
            zip(cfg["use_mix"]["use_types"], cfg["use_mix"]["mix"]):

        # this allow non-int numbers of units
        num_units = mix * cfg["built_dua"] * parcel_acres

        num_units_by_type["residential_units"] += num_units

        num_units_by_type[use_type + "_num_units"] = num_units

        use_cfg = cfg["use_types"][use_type]

        usable_floor_area += use_cfg["size"] * num_units

        if "affordable_housing" in cfg:

            aff_cfg = cfg["affordable_housing"]
            price_per_sqft = price_per_sqft_with_affordable_housing(
                use_cfg["price_per_sqft"],
                use_cfg["size"],
                aff_cfg["AMI"],
                aff_cfg.get("depth_of_affordability", 1.0),
                aff_cfg["price_multiplier_by_type"][use_type],
                cfg["cap_rate"],
                aff_cfg["pct_affordable_units"]
            )

        else:

            price_per_sqft = use_cfg["price_per_sqft"]

        revenue += use_cfg["size"] * price_per_sqft * num_units
        parking_spaces += use_cfg["parking_ratio"] * num_units

    # add in ground floor measures
    if "ground_floor" in cfg["use_mix"]:

        # this assumes ground floor is non-res - is that ok?
        ground_floor = cfg["use_mix"]["ground_floor"]
        ground_floor_type = ground_floor["use"]
        ground_floor_size = ground_floor["size"]

        usable_floor_area += ground_floor_size
        use_cfg = cfg["use_types"][ground_floor_type]
        revenue_from_ground_floor = \
            use_cfg["rent_per_sqft"] / cfg["cap_rate"] * ground_floor_size
        revenue += revenue_from_ground_floor
        parking_spaces += ground_floor_size / cfg["non_res_parking_denom"] * \
            use_cfg["parking_ratio"]

    # now compute parking attributes for the building so far
    parking_type = cfg["parking_type"]
    parking_cfg = cfg["parking_types"][parking_type]
    parking_area = parking_spaces * parking_cfg["space_size"]
    parking_cost = parking_area * parking_cfg["space_cost_sqft"]

    floor_area_including_common_space = \
        usable_floor_area / cfg["building_efficiency"]

    # compute the building footprint

    max_footprint = cfg["parcel_size"] * cfg["parcel_efficiency"]

    if parking_type == "surface":
        if max_footprint - parking_area < .1 * cfg["parcel_size"]:
            # building has to be 10% of the parcel
            raise Error("Parking covers >90%% of the parcel")
        max_footprint -= parking_area
        total_floor_area = floor_area_including_common_space

    elif parking_type == "deck":
        total_floor_area = floor_area_including_common_space + parking_area

    elif parking_type == "underground":
        total_floor_area = floor_area_including_common_space

    stories = np.ceil(total_floor_area / max_footprint)
    footprint_size = total_floor_area / stories

    # now compute costs
    building_type = cfg["building_types"][cfg["building_type"]]
    cost = floor_area_including_common_space * \
        building_type["cost_per_sqft"] * cfg["cost_shifter"] + \
        parking_cost + cfg["parcel_acquisition_cost"]

    profit = revenue - cost

    # check against max_dua
    failure_dua = cfg["built_dua"] > cfg["max_dua"] \
        if "max_dua" in cfg else False

    # check against max_far
    built_far = total_floor_area / cfg["parcel_size"]
    if "max_far" in cfg:
        failure_far = built_far > cfg["max_far"]

    # check against max_height
    height = stories * cfg["height_per_story"]
    if "max_height" in cfg:
        failure_height = height > cfg["max_height"]

    # check against buiding type densities
    failure_btype = \
        (cfg["built_dua"] < building_type["allowable_densities"][0]) | \
        (cfg["built_dua"] > building_type["allowable_densities"][1])

    out = {
        "built_far": built_far,
        "height": height,
        "usable_floor_area": usable_floor_area,
        "floor_area_including_common_space": floor_area_including_common_space,
        "ground_floor_type": ground_floor_type,
        "ground_floor_size": ground_floor_size,
        "footprint_size": footprint_size,
        "revenue_from_ground_floor": revenue_from_ground_floor,
        "parking_type": parking_type,
        "parking_spaces": parking_spaces,
        "parking_area": parking_area,
        "parking_cost": parking_cost,
        "total_floor_area": total_floor_area,
        "revenue": revenue,
        "cost": cost,
        "profit": profit,
        "stories": stories,
        "failure_dua": failure_dua,
        "failure_far": failure_far,
        "failure_height": failure_height,
        "failure_btype": failure_btype,
        "building_type": cfg["building_type"]
    }

    for k, v in num_units_by_type.iteritems():
        out[k] = v

    if "affordable_housing" in cfg:
        out["affordable_units"] = out["residential_units"] * \
            cfg["affordable_housing"]["pct_affordable_units"]

    return out

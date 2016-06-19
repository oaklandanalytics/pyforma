import pandas as pd


def residential_sales_proforma(cfg):

    cfg["use_mix"]["mix"] = pd.Series(cfg["use_mix"]["mix"])

    # this allow non-int numbers of units
    num_units_by_type = cfg["use_mix"]["mix"] * cfg["built_dua"]

    # compute basic measures for floor area in units
    usable_floor_area = 0
    revenue = 0
    parking_spaces = 0
    for use_type, num_units in \
            zip(cfg["use_mix"]["use_types"], num_units_by_type):

        use_cfg = cfg["use_types"][use_type]

        usable_floor_area += use_cfg["size"] * num_units
        revenue += use_cfg["size"] * use_cfg["price_per_sqft"] * num_units
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
            raise Error("Parking covers >90% of the parcel")
        max_footprint -= parking_area
        total_floor_area = floor_area_including_common_space

    elif parking_type == "deck":
        total_floor_area = floor_area_including_common_space + parking_area

    elif parking_type == "underground":
        total_floor_area = floor_area_including_common_space

    # what is pandas for ceil???
    stories = (total_floor_area / max_footprint).round()
    footprint_size = total_floor_area / stories

    # now compute costs
    building_type = cfg["building_types"][cfg["building_type"]]
    cost = floor_area_including_common_space * \
        building_type["cost_per_sqft"] * cfg["cost_shifter"] + \
        parking_cost + cfg["parcel_acquisition_cost"]

    profit = revenue - cost

    # check against max_dua
    failure_dua = cfg["built_dua"] > cfg["max_dua"] if "max_dua" in cfg else False

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

    return {
        "built_far": built_far,
        "height": height,
        "num_units_by_type": num_units_by_type,
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

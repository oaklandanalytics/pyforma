# pyforma

Real estate pro formas in Python

[![Build Status](https://travis-ci.org/oaklandanalytics/pyforma.svg?branch=master)](https://travis-ci.org/oaklandanalytics/pyforma) [![Coverage Status](https://coveralls.io/repos/github/oaklandanalytics/pyforma/badge.svg?branch=master)](https://coveralls.io/github/oaklandanalytics/pyforma?branch=master)


The pro formas contained in this project are taught in real estate analysis classes and predict which kinds of building(s) can be built on a plot of land by summing inflows and outflows of cash that will be gained and lost while constructing and selling a building.

Pro formas range from exceptionally simple to extraordinarily complex.  Most of the pro formas contained in this project are relatively simple as the purpose of this project is to run pro formas over large parts of a city to learn, for instance, the impact of an affordable housing policy on the number of housing units generated across the entire city.

From a programming perspective, this project hopes to write a reasonable API to execute pro formas in code, rather than the de facto standard for pro formas, which is Excel.  The API we chose is a hierarchical object, which clearly takes some inspiration from Javascript (this is the de rigueur appoach in JS), but the first implementation is written in Python as we think Python is a simpler language to get started running basic data science applications.  A javascript version of many of these pro formas will eventually be written so as to perform analysis in an interactive fashion directly in the browser.

Additionally, after many years of working with Python Pandas, I've determined that running vectorized financial analysis is challenging to both read and write.  The typical real estate analyst comes from an Excel background, and the code he or she reads and writes should not be complicated vector and matrix operations (e.g. argmax or dot product or matrix multiply).  On the other hand, Pandas runs roughly 900 times faster than a simple Python "for" loop.

The decision we made was thus to make the API first operate on scalars (i.e. numbers) so that the simple logic and intent of the API can become clear, and to allow the substitution of a pd.Series (a vector) for each scalar in almost all places in order to gain performance improvements over large datasets.

This has two additional benefits.  First, sometimes a value is not known for *every* parcel, in this case a scalar best guess can be substituted for having a specific value associated with every parcel.  Second, we can take advantage of the readability of the standard Pandas operation that `pd.Series([1, 2, 3]) * 2 == pd.Series([2, 4, 6])` so that the code is the same in almost every place whether a parameter is scalar or vector.

## Spot Pro Forma

The simplest pro forma we call a `spot` pro forma because it does not consider cash flows over time.  In this case most inflows and outflows are in costs per square foot and sales prices per sqft.  This pro forma is mainly an accounting of policies like parking ratios, ground floor retail, unit mixes and the like.  Even though it's so simple it's extrodinarily powerful as the level of detail in data necessary to run most parcel-scale pro formas is simply not available across the scope of a city, and the effect of such specific analysis on a city-wide scale would be modest.

The steps for computing a spot pro formas are roughly:

* Take a `built_dua` (the dwelling units per acre that is the density at which a building will be constructed) and multiply times a unit mix to get the number of units of each type (1BR, 2BR and so forth - the unit types are specified by the user as well).

* Use price per sqft, average unit size, and parking ratios per unit to compute the total total revenue, built space, and parking spaces for the building.

* If ground floor uses are specfied (e.g. retail), add revenue, built area, and parking spaces for the non-residential portion of the building.

* Take the number of parking spaces and the parking type specified of the user to compute the total built area and cost of parking.

* Apply a net to gross factor for common spaces.

* Based on the parking type (surface, deck, or underground), configure the building on the parcel to compute the area of the building footprint and number of stories.

* Compute profit as revenues minus costs.

* Check for constraint failures if the user passes a building configuration that conflicts with the building that gets contructed (e.g. garden apartments can't be more than 3 stories tall).  Also check for zoning violations such as maximum FAR and maximum height limits.

### The API

The spot pro forma API looks like this (a good place to start to learn how to use the API is to explore the thorough unit tests in the `tests` directory - this example comes directly from the tests).

```json
{
    "use_types": {
        "0br": {
            "price_per_sqft": 600,
            "size": 600,
            "parking_ratio": 0.3
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
            "rent_per_sqft": 30,
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
    "cap_rate": 0.06,
    "max_far": 1.2,
    "max_height": 20,
    "height_per_story": 12,
    "parcel_efficiency": 0.8,
    "building_efficiency": 0.8,
    "cost_shifter": 1.2,
    "parcel_acquisition_cost": 1000000,
    "non_res_parking_denom": 1000,
    "use_mix": {
        "use_types": ["0br", "1br", "2br"],
        "mix": [0.3, 0.3, 0.4],
        "ground_floor": {
            "use": "retail",
            "size": 3000
        }
    },
    "absorption_in_months": 20,
    "parking_type": "deck",
    "building_type": "garden_apartments",
    "built_dua": 10
}
```

Hopefully if you've followed most of the discussion so far, this API will be fairly easy to pick up on.  We'll parallel the logic described above with a discussion of the parameters in the API.

For starters there is a `unit_types` object which has parameters for each of the unit types.  Each unit type has a price per sqft, size, and parking ratio as described in the previous section.  

Non-residential uses, which are the ground floor uses (e.g. retail), have rent per sqft as this is standard and gets converted to a price per sqft using the cap rate also specfied in the object, as well as a parking ratio which uses square feet rather than number of untis and the `non_res_parking_denom` which gives the deominator for non-residential parking ratios.

Next comes a `parking_types` object which contains keys of surface, deck, and underground and have parking space sizes and costs per sqft.

Next there is a `building_types` object which contains all *possible* building types even though only one building type will actually be used for each pro forma (this will come in handy when vectorizing the operation).  Think of this as the data that comes out of the RSMeans handbook.  Right now, a building type gets a description name, and values of cost per sqft and reasonable limits on the number of stories.

Finally comes a `use_mix` object which has two lists of `use_types` and their `mix` which should be of the same length and the floats in the mix list should add up to 1.0.  This is the ratio of different unit types in the building (e.g. 30% 1BR and 70% 2BR).  There can also be a `ground_floor` object which gives the type and size of any non-residential space in the building.

Various scalar parameters are as follows:

* parcel_size is the size of the parcel in square feet
* cap_rate converts yearly rent to price, so a cap_rate of .05 means a rent of $30/sqft/year is equivalent to a sales price of $600/sqft
* max_height and max_far give density limits that will be tested after the building is configured
* height_per_story converts number of stories to building height
* the parcel_efficiency gives the maximum building footprint size based on the size of the parcel, and building_efficiency gives the ratio of sellable area to total area (accounts for common space)
* cost_shifter is optional and can be used to specify the RSMeans area cost shifter
* parcel_acquistion_cost is the cost of buying the parcel and building - this number typically comes out of some sort of statistical model
* finally, parking_type, building_type, and built_dua are three of the most important parameters as they specify exactly what form the current computations will take.  Although there are many building types, a few parking types, and many different densities at which a building can be built, each pro forma only uses one.

## Settings for affordable / inclusionary housing

**pyforma** has support to calculate the impact of affordable / inclusionary housing.  To enable affordable housing, include a sub-dictionary with the key affordable_housing and keys like the following (include as part of the larger config object described above).  Keys include

* AMI - the area median income, which is usually specified by HUD for current affordable housing policy, but which could be forecast median incomes for future years.  As before, this can be a scalar value or a Series of values per parcel.

* depth_of_affordability is the percent of AMI at which the housing should be affordable.  A value of 1.0 would be equivalent to AMI, and values are usually less than 1.0 in current housing policy.

* pct_affordable_units is the percentage of affordable units which are required for a development to be build.  A value of .2 would mean 20% of the units built would be affordable at this percentage of AMI.  This value can, and probably should, be varied by jurisdiction and in fact can be varied by parcel for complete flexibility.

* price_multiplier_by_type is a dictionary where keys are unit types as are specified elsewhere in the config object.  These are also multipliers which are usually set by policy such that different size units should be affordable at different levels of AMI - obviously smaller units are usually set to be affordable at smaller multiples of AMI, while larger units should be set higher.  Note that setting 

```
...
"affordable_housing": {
    "AMI": 80000,
    "depth_of_affordability": .8,
    "pct_affordable_units": .2,
    "price_multiplier_by_type": {
        "0br": .7,
        "1br": .75,
        "2br": .9,
        "3br+": 1.04
    }
}
...
```

If "affordable_housing" is set as an input, "affordable_units" will be set as a key in the output, which will be a Series providing the number of affordable units per development.

Note that the purpose of these parameters is to adjust the profitability of developments, which necessarily reduces the probability of a development being built relative to developments which have no inclusionary housing.  Thus an increase in affordable housing in an urban county and strong market like San Francisco, will probably work, and create potentially large numbers of affordability, while at the same time providing a suburbanizing force to development region-wide.  This is in fact the whole purpose of running analyses like these.  Also note that at some level of inclusionary housing, depending on market conditions, a development can go from profitable to unprofitable, which is why inclusionary rates are often linked to market cycles.


## Running pyforma far and wide

The real power of this API is not to call the API once with scalar values, but to pass in a Pandas Series of values (a vector of values) and perform the computation more efficiently.  Python is notoriously slow at performing "for loop" operations, and in fact in this case **using a Pandas Series and letting pyforma do the computation for you is *900* times faster than calling this API with scalars in a for loop**.  The use of scalars in the API is not for large numbers of operations, say 100k calls or more.

It's also clear that there are two main use cases for using pyforma:

* The "far" in the heading, which would be to explore many (potentially millions) of pro formas run on a single parcel to optimize the return on that parcel

* The "wide" in the heading, which would be to explore a pro forma on a large number of parcels (potentially millions) at the max zoning allowed or similar

In fact, the API is general simple enough that you can make any calls you want and aggregate them however you want.  For instance, the user of the API could run 20 pro formas per parcel for 2 million parcels, or about 40 million parcels in only a few seconds.  The 20 pro formas per parcel could test various inflection points, or parking types, etc, and then maximize the return per parcel before doing an aggregation across all parcels like summing feasible units in an area.

## A vectorized example, incluing use of the cartesian_product helper

Here is an example of using pyforma in a vectorized manner (again drawn from the unit tests).  First imagine you have an object called `cfg` which is set to the configuration object from the previous example.  In this example we want to test a series of DUA values, a series of FAR values, a series of parcel sizes, and a series of price per square foot numbers, and we want to test *all* combinations of those Series.

pyforma has a helper method to assist with this use case, called `cartesian_product`, which will perform the cross product for you - just pass the Series as arguments to the method like shown below.  The method will create a DataFrame which has columns that are named the same as each series, and will create a row in the DataFrame with every combination of values of the passed Series (and do so efficiently).  So if you pass four Series, with lengths 2, 3, 4, and 3 respectively, the length of the output DataFrame will be 2 * 3 * 4 * 3 = 72.  This is obviously polynomial expansion so use judiciously.

Once you have the set of values you want to test, simply substitute the Pandas Series for the previous scalar values (in this case the output of `cartesian_product` but could also be the actual values taken from parcels throughout a city), and finally call the appropriate method to run the pro formas.

```python 
df = pyforma.cartesian_product([
    pd.Series(np.arange(1, 300, 5), name="dua"),
    pd.Series(np.arange(.25, 8, .5), name="far"),
    pd.Series(np.arange(1000, 100000, 50000), name="parcel_size"),
    pd.Series(np.arange(500, 2000, 500), name="price_per_sqft")
])

# cfg is initially set to the object from the previous example
cfg["parcel_size"] = df.parcel_size
cfg["max_dua"] = df.dua
cfg["max_far"] = df.far
cfg["use_types"]["2br"]["price_per_sqft"] = df.price_per_sqft

ret = pyforma.spot_residential_sales_proforma(cfg)
```

## A note on parking types and vectorization

At this point there are three parking types, and thus the scalar passed takes one of the values "surface", "deck", and "underground".  For now, these can't be vectorized in a Series which mixes these values.  This keeps the code simple internally, but will probably change at a future date.  For now, simply call the method 3 times if you want to test multiple parking types.

## Benchmarks

Current benchmarks for the style of pro forma that pyforma current supports will run 18 million pro formas per second.

## Outputs (what the API returns)

Similar to the object passed as input, the `spot_residential_sales_proforma` returns a Python dictionary with key-value pairs.  If the values passed are scalars, the values returned will be scalars.  If any of the values passed are Series, most of the values returned will be Series as well.  Below is a list and description of the keys returned and a sample return object.

* built_far - the actual floor are ratio for the building
* height - the height for this building
* num_units_by_type - a list of the number of each type of unit in the mix array passed in (in units rather than in proportions).  For now these values can be partial units (floats).
* usable_floor_area - The amount of floor area (can be spread among floors) that is inside a unit or non-residential area
* floor_area_including_commin_space - The usable floor area plus the shared space
* ground_floor_type - this is passed in by the user and returned to the user for convenience
* ground_floor_size - this is passed in by the user and returned to the user for convenience
* footprint_size - the area of the building footprint
* revenue_from_the_ground_floor - if there is ground floor non-residential space, this is the revenue that space generates (a full price, not a yearly rent)
* parking_type - this is passed in by the user and returned to the user for convenience
* parking_spaces - the total number of parking spaces this building will require
* parking_area - the area of said parking spaces
* parking_cost - the cost of said parking spaces
* total_floor_area - the floor area plus common spaces plus parking (if it's not surface parking)
* revenue - the total revenue the building generates - i.e. an estimate of the NPV
* cost - the total cost to construct the building, which includes usable space, common space, and parking
* profit - revenue minus cost, duh (includes acquistion cost for the parcel in addition to construction cost)
* stories - the number of stories of the building
* failure_dua - a True/False value as to whether the building has a zoning failure where is exceeds the max DUA value
* failure_far - a True/False value as to whether the building has a zoning failure where is exceeds the max FAR value
* failure_height - a True/False value as to whether the building has a zoning failure where is exceeds the max height value
* failure_btype - a True/False value as to whether the density of this building exceeds the range specified as allowable for a given building type - e.g. no townhome is 5 stories; the building will be analyzed as requested but this is considered a "building type failure"
* building_type - this is passed in by the user and returned to the user for convenience

```
{
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
    "building_type": building_type
}
```

## Zoning failures

There are four zoning failures that are described in detail above - they are DUA, FAR, height, and building type.  At first it is not obvious why the API should even allow zoning to be violated, but this API is written to be as flexible as possible, and the user is free to pass in many different kinds of buildings.  They might be taller than the max height, they might be 10 story townhomes or 1 story condos, but when the results don't make sense this will be flagged as a constraint failure.  Make sure to check the constraint failures if your use case requires it.

# pyforma

Real estate pro formas in Python

[![Build Status](https://travis-ci.org/fscottfoti/pyforma.svg?branch=master)](https://travis-ci.org/fscottfoti/pyforma) [![Coverage Status](https://coveralls.io/repos/github/fscottfoti/pyforma/badge.svg?branch=master)](https://coveralls.io/github/fscottfoti/pyforma?branch=master)

The pro formas contained in this project are taught in real estate analysis classes and analyze which kinds of building(s) can be built on a plot of land by analyzing inflows and outflows of cash that will be gained and lost while constructing and selling a building.

Pro formas range from exceptionally simple to extraordinarily complex.  Most of the pro formas contained in this project are more on the simple side as the purpose of this project is typically to run pro formas over large parts of a city to learn, for instance, the impact of an affordable housing policy on the number of housing units generated across the entire city.

From a programming perspective, this project hopes to write a reasonable API to execute pro formas in code, rather than the de facto standard for pro formas, which is Excel.  The API we chose is a hierarchical object, which clearly takes some inspiration from Javascript (this is the de rigueur appoach in JS), but the first implementation is written in Python as we think Python is a simpler language to get started running basic data science applications.  A javascript version of many of these pro formas will eventually be written so as to perform analysis in an interacrive fashion directly in the browser.

Additionally, after many years of working with Python Pandas, I've determined that running vectorized financial analysis is challenging to both read and write.  When we're discussing pro formas, the typical user will be coming from an Excel background, and the code they read and write should not be complicated vector and matrix operations (e.g. argmax or dot product or matrix multiply).  On the other hand, Pandas runs roughly 900 times faster than a simple Python "for" loop.

The decision we made was thus to make the API first operate on scalars (i.e. numbers) so that the simple logic and intent of the API can become clear, and to allow the substitution of a pd.Series (a vector) for each scalar in almost all places in order to gain performance improvements over large datasets.

This has two additional benefits.  First, sometimes a value is not known for *every* parcel, in this case a scalar best guess can be substituted for having a specific value associated with every parcel.  Second, we can take advantage of the readability of the standard Pandas operation that `pd.Series([1, 2, 3]) * 2 == pd.Series([2, 4, 6])` so that the code is the same in almost every place whether a parameter is scalar or vector.

## Spot Pro Forma

The simplest pro forma we call a `spot` pro forma because it does not consider cash flows over time.  In this case most inflows and outflows are in costs per square foot and sales prices per sqft.  This pro forma is mainy an accounting of policies like parking ratios, ground floor retail, unit mixes and the like.  Even though it's so simple it's extrodinarily powerful as the level of detail in data necessary to run most parcel-scale pro formas is simply not available across the scope of a city.

The steps for computing a spot pro formas are roughly:

* Take a `built_dua` (the dwelling units per acre that is the density at which a building will be constructed) and multiply times a unit mix to get the number of units of each type (1BR, 2BR and so forth - the unit types are specified by the user as well).

* Use price per sqft, average unit size, and parking ratios per unit to compute the total total revenue, built space, and parking spaces for the building.

* If ground floor uses are specfied (e.g. retail), add revenue, built area, and parking spaces for the non-residential portion of the building.

* Take the number of parking spaces and the parking type specified of the user to compute the total built area and cost of parking.

* Apply a net to grossing factor for common spaces.

* Based on the parking type (surface, deck, or underground), configure the building on the parcel so that you know the building footprint and number of stories.

* Compute profit as revenue minus cost.

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

Non-residential uses, which are used as ground floor uses (e.g. retail), have rent per sqft as this is standard and gets converted to a price per sqft using the cap rate also specfied in the obejct, as well as a parking ratio which uses sqft rather than number of untis and the `non_res_parking_denom` which gives the deominator for non-residential parking ratios.

Next comes a `parking_types` object which contains keys of surface, deck, and underground and have parking space sizes and costs per sqft.

Next comes a `building_types` object which contains all *possible* building types even though only one building type will actually be used for each pro forma (this will come in handy when vectorizing the operation).  Think of this as the data that comes out of the RSMeans handbook.  Right now, a building type gets a description name, and values of cost per sqft and reasonable limits on the number of stories.

Finally comes a `use_mix` object which has two lists of `use_types` and their `mix` which should be of the same length and the floats in the mix list should add up to 1.0.  This is the ratio of different unit types in the building (e.g. 30% 1BR and 70% 2BR).  There can also be a `ground_floor` object which gives the type and size of any non-residential space in the building.

Various scalar parameters are as follows:

* parcel_size is the size of the parcel in square feet.
* cap_rate converts yearly rent to price, so a cap_rate of .05 means a rent of $30/sqft/year is equivalent to a sales price of $600/sqft.
* max_height and max_far give density limits that will be tested after the building is configured.
* height_per_story converts number of stories to building height.
* the parcel_efficiency gives the maximum building footprint size based on the size of the parcel, and building_efficiency gives the ratio of sellable area to total area (accounts for common space).
* cost_shifter is optional and can be used to specify the RSMeans area cost shifter.
* parcel_acquistion_cost is the cost of buying the parcel and building - this number typically comes out of some sort of statistical model.
* finally, parking_type, building_type, and built_dua are three of the most important parameters as they specify exactly what form the current computations will take.  Although there are many building types, a few parking types, and many different densities at which a building can be built, each pro forma only uses one.

## Running pyforma far and wide

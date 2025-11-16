"""
Configuration for LA Geography point-lookup API.

Defines which layers to query and which fields to extract for the response.
"""

# Base URL for GeoJSON files on S3
BASE_URL = "https://stilesdata.com/la-geography"

# Layer configuration: map layer name to query config
# Each config specifies:
#   - geojson_file: filename on S3
#   - response_key: key in the API response JSON
#   - name_field: which field contains the display name
#   - id_field: optional unique identifier field
LAYERS = [
    {
        "name": "la_neighborhoods_comprehensive",
        "geojson_file": "la_neighborhoods_comprehensive.geojson",
        "response_key": "neighborhood",
        "name_field": "name",
        "id_field": "slug",
        "description": "LA County neighborhood (comprehensive)",
    },
    {
        "name": "la_county_cities",
        "geojson_file": "la_county_cities.geojson",
        "response_key": "city",
        "name_field": "city_name",
        "id_field": "city_name",
        "description": "City or unincorporated area",
    },
    {
        "name": "lapd_divisions",
        "geojson_file": "lapd_divisions.geojson",
        "response_key": "lapd_division",
        "name_field": "aprec",
        "id_field": "prec",
        "description": "LAPD division",
    },
    {
        "name": "lapd_bureaus",
        "geojson_file": "lapd_bureaus.geojson",
        "response_key": "lapd_bureau",
        "name_field": "name",
        "id_field": "bureau",
        "description": "LAPD bureau",
    },
    {
        "name": "lafd_station_boundaries",
        "geojson_file": "lafd_station_boundaries.geojson",
        "response_key": "lafd_station",
        "name_field": "name",
        "id_field": "precinctid",
        "description": "LA Fire Department station (city)",
    },
    {
        "name": "lacofd_station_boundaries",
        "geojson_file": "lacofd_station_boundaries.geojson",
        "response_key": "lacofd_station",
        "name_field": "stanum",
        "id_field": "stanum",
        "description": "LA County Fire Department station",
    },
    {
        "name": "la_city_council_districts",
        "geojson_file": "la_city_council_districts.geojson",
        "response_key": "council_district",
        "name_field": "district_name",
        "id_field": "district",
        "description": "LA City Council district",
    },
    {
        "name": "la_city_neighborhood_councils",
        "geojson_file": "la_city_neighborhood_councils.geojson",
        "response_key": "neighborhood_council",
        "name_field": "name",
        "id_field": "nc_id",
        "description": "LA City Neighborhood Council",
    },
    {
        "name": "la_county_school_districts",
        "geojson_file": "la_county_school_districts.geojson",
        "response_key": "school_district",
        "name_field": "label",
        "id_field": "abbr",
        "description": "School district",
    },
    {
        "name": "la_county_election_precincts",
        "geojson_file": "la_county_election_precincts.geojson",
        "response_key": "election_precinct",
        "name_field": "precinct",
        "id_field": "precinct",
        "description": "Election precinct",
    },
    {
        "name": "la_county_airport_noise_contours",
        "geojson_file": "la_county_airport_noise_contours.geojson",
        "response_key": "airport_noise",
        "name_field": "airport_name",
        "id_field": "objectid",
        "description": "Airport noise contour",
        "extra_fields": ["class"],
    },
]

# LA County bounding box for validation (rough bounds)
LA_COUNTY_BBOX = {
    "min_lon": -119.0,
    "max_lon": -117.6,
    "min_lat": 33.7,
    "max_lat": 34.8,
}


import requests

# Index 0 is some documentation thingy, all others should be OK
FEATURE_INDEX = 1
ASSET_INDEX = 0


def test_ice_elevation_data() -> None:
    collection_response = requests.get(
        "https://catalog.osc-staging.earthcode.eox.at/collections/metadata:main/items/sentinel3-ampli-ice-sheet-elevation?f=json",
        headers={"Content-Type": "application/geo+json"},
    )
    assert collection_response.ok
    collection_json: dict = collection_response.json()
    items_link_json = next(
        (link_object for link_object in collection_json["links"] if link_object["rel"] == "items"),
        None,
    )
    assert items_link_json is not None, f"Couldn't find 'items' link in links {collection_json["links"]}"

    feature_collection_response = requests.get(items_link_json["href"])
    assert feature_collection_response.ok
    features_json: dict = feature_collection_response.json()
    asset_json: dict = list(features_json["features"][FEATURE_INDEX]["assets"].values())[ASSET_INDEX]

    asset_data_response = requests.get("https://eoresults.esa.int" + asset_json["href"])
    assert asset_data_response.ok

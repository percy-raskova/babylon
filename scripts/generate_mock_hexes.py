import json
import random
from pathlib import Path
from typing import Any

import h3


def generate_county_hexes(
    center_lat: float,
    center_lng: float,
    county_fips: str,
    county_name: str,
    count: int,
    params: dict[str, tuple[float, float]],
) -> list[dict[str, Any]]:
    # Get a starting hexagon
    start_hex = h3.latlng_to_cell(center_lat, center_lng, 7)

    # Run k-ring to get a bunch of hexes around the center
    # k=4 should give 61 hexes
    hexes = list(h3.grid_disk(start_hex, 4))
    random.shuffle(hexes)

    selected_hexes = hexes[:count]

    features = []

    for h in selected_hexes:
        # Generate random properties
        profit_rate = random.uniform(*params["profit_rate"])
        heat = random.uniform(*params["heat"])
        exploitation_rate = random.uniform(*params["exploitation_rate"])

        # Other required properties
        occ = random.uniform(0.1, 0.9)
        imperial_rent = random.uniform(0.1, 0.9)
        org_presence = random.randint(0, 100)
        dominant_class = random.choice(
            [
                "LABOR_ARISTOCRACY",
                "PROLETARIAT",
                "PETIT_BOURGEOISIE",
                "BOURGEOISIE",
                "LUMPENPROLETARIAT",
            ]
        )
        population = random.randint(1000, 50000)

        # h3.h3_to_geo_boundary returns a tuple of (lat, lng) tuples
        # GeoJSON expects [lng, lat]
        boundary = h3.cell_to_boundary(h)
        # Close the polygon by appending the first point
        coordinates = [[lng, lat] for lat, lng in boundary]
        coordinates.append(coordinates[0])

        feature = {
            "type": "Feature",
            "id": h,
            "geometry": {"type": "Polygon", "coordinates": [coordinates]},
            "properties": {
                "h3_index": h,
                "county_fips": county_fips,
                "county_name": county_name,
                "profit_rate": profit_rate,
                "exploitation_rate": exploitation_rate,
                "occ": occ,
                "imperial_rent": imperial_rent,
                "heat": heat,
                "org_presence": org_presence,
                "dominant_class": dominant_class,
                "population": population,
            },
        }
        features.append(feature)

    return features


def main() -> None:
    # Wayne County approx center (Detroit)
    wayne_params = {
        "profit_rate": (0.02, 0.08),
        "heat": (0.3, 0.7),
        "exploitation_rate": (0.6, 0.9),
    }
    wayne_features = generate_county_hexes(42.3314, -83.0458, "26163", "Wayne", 18, wayne_params)

    # Oakland County approx center (Pontiac)
    oakland_params = {
        "profit_rate": (0.08, 0.15),
        "heat": (0.0, 0.2),
        "exploitation_rate": (0.1, 0.4),
    }
    oakland_features = generate_county_hexes(
        42.6389, -83.2910, "26125", "Oakland", 18, oakland_params
    )

    # Macomb County approx center (Warren)
    macomb_params = {
        "profit_rate": (0.05, 0.10),
        "heat": (0.2, 0.5),
        "exploitation_rate": (0.3, 0.6),
    }
    macomb_features = generate_county_hexes(42.4920, -83.0238, "26099", "Macomb", 14, macomb_params)

    all_features = wayne_features + oakland_features + macomb_features

    feature_collection = {
        "type": "FeatureCollection",
        "metadata": {
            "tick": 0,
            "scenario": "detroit_test",
            "h3_resolution": 7,
            "available_metrics": [
                "profit_rate",
                "exploitation_rate",
                "occ",
                "imperial_rent",
                "heat",
                "org_presence",
            ],
            "bounds": {"sw": [42.1, -83.5], "ne": [42.7, -82.9]},
        },
        "features": all_features,
    }

    output_dir = Path(__file__).parent.parent / "web" / "frontend" / "src" / "fixtures"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "mock_map_data.json"

    with open(output_file, "w") as f:
        json.dump(feature_collection, f, indent=2)

    print(f"Generated {len(all_features)} hexes and wrote to {output_file}")


if __name__ == "__main__":
    main()

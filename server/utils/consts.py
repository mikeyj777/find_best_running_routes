from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ELEVATION_DATA_PATH = PROJECT_ROOT / "cache" / "elev" / "elevation_data.csv"

ELEVATION_BBOX = (
    36.462897,   # min latitude (south)
    -82.567254,  # min longitude (west)
    36.536380,   # max latitude (north)
    -82.454899   # max longitude (east)
)
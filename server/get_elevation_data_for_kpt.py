import csv
import pandas as pd

from core.data_fetcher import ElevationConnector

finished_coords = pd.DataFrame()
try:
    finished_coords = pd.read_csv('elevation_data.csv')
except Exception as e:
    pass

ec = ElevationConnector()

ul = [ 36.536380, -82.567254 ]
lr = [ 36.462897, -82.454899 ]

lat_step = (ul[0] - lr[0]) / 300 # about 100 ft
lng_step = (ul[1] - lr[1]) / 300

lat_start = lr[0]
lng_start = lr[1]

lat_stop = ul[0]
lng_stop = ul[1]

lat = lat_start
lng = lng_start

res = []
iter = -1
while lat <= lat_stop:
    while lng >= lng_stop:
        if not finished_coords.empty and not finished_coords[(finished_coords['latitude'] == lat) & (finished_coords['longitude'] == lng)].empty:
            print(f"Skipping {lat}, {lng}")
            lng += lng_step
            continue
        coords = [ { 'latitude': lat, 'longitude': lng } ]
        result = ec.fetch_elevation_for_coords(coords)
        print(f"iter: {iter} | Result: {result}")
        if isinstance(result, list):
            res.extend(result)
        if iter % 10 == 0:
            try:
              with open('elevation_data.csv', 'a', newline='') as csvfile:
                  fieldnames = ['latitude', 'longitude', 'elevation']
                  writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                  writer.writerows(res)
                  csvfile.flush()
                  res = []
            except Exception as e:
              print(f"Error writing to CSV: {e}.  current data: {res}")
        iter += 1

        lng += lng_step
    lat += lat_step
    lng = lng_start


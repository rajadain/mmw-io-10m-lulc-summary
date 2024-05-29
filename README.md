# MMW IO 10m LULC Summary

This repository builds on [Python Notebooks](https://gist.github.com/rajadain/1d3591a7a00c750466e3793bf1a9bcd2) created to query the [Impact Observatory](https://www.impactobservatory.com/) [10m LULC dataset on AWS Open Registry](https://registry.opendata.aws/io-lulc/), and format the output like the [MMW-Geoprocessing service](https://github.com/WikiWatershed/mmw-geoprocessing) does.

## Setup

This project requires Python 3.10+ and [uv](https://github.com/astral-sh/uv) and [jq](https://jqlang.github.io/jq/). To set the project up, run:

```bash
./scripts/setup
```

## Running

To run the project, give it a FeatureCollection GeoJSON, such as the ones under [examples](./examples/):

```bash
./scripts/run_python examples/LowerSchuylkill.geojson

{
  "List(0)": 19620912,
  "List(1)": 113354,
  "List(11)": 400816,
  "List(2)": 831411,
  "List(4)": 369,
  "List(5)": 225703,
  "List(7)": 3708295,
  "List(8)": 4074
}
```

## Comparing with MMW

Ensure the MMW Geoprocessing service is running at http://localhost:8090/. If elsewhere, edit the `MMW_GEOPROCESSING_API` variable in [scripts/run_geotrellis](./scripts/run_geotrellis).

Then, call `run_geotrellis` with one of the examples:

```bash
./scripts/run_geotrellis examples/LowerSchuylkill.geojson

{
  "List(1)": 105463,
  "List(11)": 390845,
  "List(2)": 730907,
  "List(4)": 525,
  "List(5)": 169751,
  "List(7)": 3591677,
  "List(8)": 5066
}
```

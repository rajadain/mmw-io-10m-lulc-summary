import argparse
from pystac_client import Client
from rasterio.coords import BoundingBox
from rasterio.enums import Resampling
from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.warp import transform_geom, calculate_default_transform, reproject
from shapely.geometry import shape, box
import geopandas as gpd
import json
import numpy as np
import os
import rasterio as rio
import tempfile


URL = "https://api.impactobservatory.com/stac-aws"
COLLECTION = "io-10m-annual-lulc"
ASSET = "supercell"
SQKM_PER_SQM = 0.000001


def to_year(year):
    """
    Convert a year to a STAC query.
    """
    return {
        "op": "like",
        "args": [{"property": "id"}, f"%-{year}"],
    }


def get_crs_for_aoi(aoi):
    # Determine the appropriate Albers Equal Area CRS based on the AoI's location
    if aoi.within(box(-170, 15, -50, 75)):  # North America
        return "EPSG:5070"
    elif aoi.within(box(-10, 34, 40, 72)):  # Europe
        return "EPSG:3035"
    elif aoi.within(box(25, -10, 180, 60)):  # Asia
        return "EPSG:102025"
    elif aoi.within(box(-20, -35, 55, 38)):  # Africa
        return "EPSG:102022"
    elif aoi.within(box(-90, -60, -30, 15)):  # South America
        return "EPSG:102033"
    elif aoi.within(box(112, -45, 155, -10)):  # Australia
        return "EPSG:102034"
    else:  # Global
        return "EPSG:54017"  # Behrmann Equal Area Cylindrical


# Function to clip and reproject the AoI
def clip_and_reproject_tile(tile_path, aoi, dst_crs="EPSG:3857"):
    with rio.open(tile_path) as src:
        reprojected_aoi = transform_geom(aoi.crs, src.crs, aoi.geometry[0])
        reprojected_aoi_bbox = BoundingBox(*shape(reprojected_aoi).bounds)
        clip_data, clip_transform = mask(src, [reprojected_aoi], crop=True)

        # Define the output metadata for the reprojected clip
        dst_transform, width, height = calculate_default_transform(
            src.crs,
            dst_crs,
            clip_data.shape[2],
            clip_data.shape[1],
            *reprojected_aoi_bbox,
        )
        dst_meta = src.meta.copy()
        dst_meta.update(
            {
                "crs": dst_crs,
                "transform": dst_transform,
                "width": width,
                "height": height,
            }
        )

        # Reproject the clipped data to the destination CRS
        reprojected_clip_data = np.empty(
            (src.count, height, width), dtype=src.dtypes[0]
        )
        reproject(
            source=clip_data,
            destination=reprojected_clip_data,
            src_transform=clip_transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
        )

        return reprojected_clip_data, dst_transform, dst_meta


def main():
    # Add argument for reading the input file
    parser = argparse.ArgumentParser("mmw_io_10m_lulc_summary")
    parser.add_argument(
        "geojson", help="A GeoJSON geometry to query the IO 10m LULC dataset with"
    )

    args = parser.parse_args()

    # Read and prepare the GeoJSON
    # Expects a FeatureCollection
    aoi = gpd.read_file(args.geojson)
    aoi_json = aoi.to_json()
    aoi_geom = json.loads(aoi_json)["features"][0]["geometry"]

    # Query the STAC API for tiffs that intersect with AoI
    client = Client.open(URL)
    search = client.search(
        collections=COLLECTION,
        intersects=aoi_geom,
        filter=to_year(2019),
    )
    tiffs = [item.assets[ASSET].href for item in search.items()]

    # Find the Albers Equal Area CRS for this AoI
    dst_crs = get_crs_for_aoi(aoi.geometry[0])

    # Reproject the tiffs and clip to the AoI to make tiles
    clips = []
    for tiff in tiffs:
        clip_data, clip_transform, clip_meta = clip_and_reproject_tile(tiff, aoi, dst_crs)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tif')
        with rio.open(temp_file.name, 'w', **clip_meta) as dst:
            dst.write(clip_data)
        clips.append(temp_file.name)

    # Merge the clipped rasters
    datasets = [rio.open(clip_path) for clip_path in clips]
    merged_data, merged_transform = merge(datasets)

    # Close datasets
    for ds in datasets:
        ds.close()

    # Count how many of each class type there are
    values, counts = np.unique(merged_data, return_counts=True)
    io_data = list(zip(values, counts))

    # Format and print in the MMW Geoprocessing format
    expected_geotrellis_output = {
        f"List({v})": int(c)
        for v, c in io_data
    }
    print(json.dumps(expected_geotrellis_output, sort_keys=True, indent=4))

    # Clean up temporary files
    for temp_file in clips:
        os.remove(temp_file)


if __name__ == "__main__":
    main()

import rasterio
from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.enums import Resampling
import os
import shutil
import fiona
from shapely.geometry import shape, box
import numpy as np


def remove_outliers(data, threshold=3):
    """
    Remove outliers from a dataset using Z-score method.

    The function calculates the Z-scores for each data point in the dataset.
    Z-score is a measure of how many standard deviations a data point is from the mean.
    Data points with a high Z-score (positive or negative) are considered outliers.

    Z-score formula:
        Z = (X - mean) / standard_deviation

    Where:
        Z - Z-score
        X - Data point
        mean - Mean of the dataset
        standard_deviation - Standard deviation of the dataset

    Parameters:
    data (array-like): The input data from which to remove outliers.
    threshold (float): The Z-score threshold to identify outliers. Default is 3.

    Returns:
    array-like: The data with outliers removed.
    ”””
    :param data:
    :param threshold:
    :return:
    """
    z_scores = np.abs((data - np.mean(data)) / np.std(data))
    return data[z_scores < threshold]


def rescale(data):
    data_cleaned = remove_outliers(data)
    if len(data_cleaned) == 0:
        return np.zeros_like(data_cleaned)
    min_val = np.min(data_cleaned)
    max_val = np.max(data_cleaned)
    if max_val == min_val:
        return np.zeros_like(data)
    return (data - min_val) / (max_val - min_val) * 100


def split_countries(admin_data, mlea_data, output_dir):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    with fiona.open(admin_data, "r") as adm0:
        with rasterio.open(mlea_data) as raster:
            nodata_value = raster.nodata
            raster_bounds = box(*raster.bounds)

            for feature in adm0:
                country_iso3 = feature['properties']['GID_0']
                geometry = feature['geometry']
                shape_geometry = shape(geometry)
                # buffered_geometry = shape_geometry.buffer(10)
                if not shape_geometry.intersects(raster_bounds):
                    print(f'Skipping {country_iso3} as it does not overlap with raster')
                    continue

                print(f"start processing {country_iso3}")

                out_image, out_transform = mask(raster, [shape_geometry], crop=True)
                if np.all(out_image == nodata_value):
                    print(f'Skipping {country_iso3} as it is entirely No Data')
                    continue

                out_image = rescale(out_image)

                out_meta = raster.meta.copy()
                out_meta.update(
                    {"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform,
                     "nodata": nodata_value,
                     "dtype": 'int16',
                     "compress": "deflate"
                     })

                original_filename = mlea_data.split("/")[1].replace(".tif", "")
                output_path = os.path.join(output_dir, f'{original_filename}_{country_iso3}.tif')

                with rasterio.open(output_path, 'w', **out_meta) as dest:
                    dest.write(out_image)

                print(f'Saved {output_path}')


def merge_countries(input_dir, output_path, delete_country=False):
    tiff_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith('.tif')]

    src_files_to_mosaic = []
    for tiff_file in tiff_files:
        src = rasterio.open(tiff_file)
        src_files_to_mosaic.append(src)

    mosaic, out_trans = merge(src_files_to_mosaic, resampling=Resampling.nearest)

    out_meta = src.meta.copy()
    out_meta.update({"driver": "GTiff",
                     "height": mosaic.shape[1],
                     "width": mosaic.shape[2],
                     "transform": out_trans,
                     "nodata": src.nodata,
                     "dtype": 'int16',
                     "compress": "deflate",
                     "TILED": "YES",
                     "BIGTIFF": "IF_SAFER",
                     "BLOCKXSIZE": 512,
                     "BLOCKYSIZE": 512
                     })

    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(mosaic)
    print(f'Merged TIFF file saved at: {output_path}')

    if delete_country:
        for tiff in tiff_files:
            os.remove(tiff)
        shutil.rmtree(input_dir)


if __name__ == "__main__":

    input_dir = "data"
    input_admin = "data/adm0_3857.fgb"

    years = range(2012, 2020)
    # years = [2019]

    for year in years:
        output_dir = f"output/{year}"

        split_countries(
            admin_data=input_admin,
            mlea_data=f"{input_dir}/Electricity_access_{year}.tif",
            output_dir=output_dir
        )

        merge_countries(
            input_dir=output_dir,
            output_path=f"output/Electricity_access_{year}.tif",
            delete_country=True
        )

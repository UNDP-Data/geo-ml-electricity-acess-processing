import rasterio
from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.enums import Resampling
import os
import shutil
import fiona
from shapely.geometry import shape, box
import numpy as np


def rescale(data):
    min_val = np.min(data)
    max_val = np.max(data)
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
                     # "dtype": 'int16'
                     })

                original_filename = mlea_data.split("/")[1].replace(".tif", "")
                output_path = os.path.join(output_dir, f'{original_filename}_{country_iso3}.tif')

                with rasterio.open(output_path, 'w', **out_meta) as dest:
                    dest.write(out_image)

                print(f'Saved {output_path}')


def merge_countries(input_dir, output_path):
    tiff_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith('.tif')]

    # 入力ファイルを開いて、データとメタデータを読み込む
    src_files_to_mosaic = []
    for tiff_file in tiff_files:
        src = rasterio.open(tiff_file)
        src_files_to_mosaic.append(src)

    # マージ処理を実行
    mosaic, out_trans = merge(src_files_to_mosaic, resampling=Resampling.nearest)

    # メタデータを更新
    out_meta = src.meta.copy()
    out_meta.update({"driver": "GTiff",
                     "height": mosaic.shape[1],
                     "width": mosaic.shape[2],
                     "transform": out_trans,
                     "nodata": src.nodata,
                     "dtype": 'int16'
                     })

    # 出力ファイルにマージ結果を書き込む
    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(mosaic)
    print(f'Merged TIFF file saved at: {output_path}')


if __name__ == "__main__":

    output_dir = "output/2019"
    input_dir = "data"
    input_admin = "data/adm0_3857.fgb"
    year = "2019"

    split_countries(
        admin_data=input_admin,
        mlea_data=f"{input_dir}/Electricity_access_{year}.tif",
        output_dir=output_dir
    )

    merge_countries(
        input_dir=output_dir,
        output_path=f"{output_dir}/Electricity_access_{year}.tif"
    )

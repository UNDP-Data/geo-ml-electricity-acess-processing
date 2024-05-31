# geo-ml-electricity-acess-processing

This repository is trying to fix the problem of current Machine Learning Electricity Access dataset which has issues of normalization and rescale of data representation.

## Prepare

Current electrcity access datasets that are from 2012 to 2019 are under data folder. However, you need to download Admin 0 dataset from blob stroage account.

```commandline
az login
az storage blob download \
    --account-name undpngddlsgeohubdev01 \
    --container-name hrea \
    --name https://undpngddlsgeohubdev01.blob.core.windows.net/hrea/rawdata/Shapefiles/admin/adm0_3857.fgb \
    --file data/adm0_3857.fgb \
    --connection-string <connection string>
```

Now, `adm0_3857.fgb` should be in `data`folder.

## Installation

You can use pipenv to install dependencies from requirements.txt

```commandline
pipenv install
pipenv run pip install -r requirements.txt
```

## Usage

```commandline
pipenv run python main.py
```

It will create rescaled MLEA data under output folder. The new dataset is rescaled 0-100 instead of current 0-255.

But the problem of normalization is still there. Each country has different scaled values, this causes the weird looks of data. Also, the admin 0 boundaries are not exactly matching original MLEA data's country boundary. So, the data after merging will looks a bit different particularly for the near country boundaries.

## Methodology to create original MLEA data

see [Electricity Mapping.pdf](./Electricity%20Mapping.pdf) for the methodologies how original MLEA data was created.
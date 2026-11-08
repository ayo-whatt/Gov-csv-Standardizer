# Government CSV Standardizer

A pipeline that cleans messy government CSV files and flags structural changes instead of loading bad data silently.

## Problem

Open government datasets often have inconsistent column names, mixed date formats, misspelled state names, and encoding problems. When a publisher renames or adds a column, a naive load produces wrong results without any error.

## Dataset

District-wise MGNREGA Data at a Glance, 2018-19 , published on data.gov.in. The raw file is stored unedited in `data/raw/`. Source and license details are in `data/SOURCES.md`.

## Status

In progress. Current stage: profiling the raw dataset.

## Setup

Setup instructions will be added once the pipeline runs.
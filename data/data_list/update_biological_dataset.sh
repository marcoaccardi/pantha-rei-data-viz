#!/bin/bash
# Set the variables
MOTU_API="https://nrt.cmems-du.eu/motu-web/Motu"
SERVICE_ID=GLOBAL_ANALYSIS_FORECAST_BIO_001_028-TDS
PRODUCT_ID=global-analysis-forecast-bio-001-028-daily
DEPTH_MIN=0.49402499198913574
DEPTH_MAX=0.49402499198913574
OUT_DIR="../../ocean_datasets/biological"
USERNAME="maccardi"
PASSWORD="HrdHrd1989!"

# Set the start and end dates
start_date=$(date -j -f "%Y-%m-%d" "2021-06-26" "+%s")
#end_date=$(date -j -f "%Y-%m-%d" "2020-11-30" "+%s")
end_date=$(date "+%s")
# Loop through each date and download the file
while [ "$start_date" -le "$end_date" ]
do
    date_arg=$(date -j -f "%s" "$start_date" "+%Y-%m-%d")
    echo "Downloading file for date: $date_arg"
    OUT_NAME="$date_arg.nc"
    motuclient --motu "${MOTU_API}" \
      --service-id "${SERVICE_ID}" \
      --product-id "${PRODUCT_ID}" \
      --date-min "${date_arg} 00:00:00" \
      --date-max "${date_arg} 23:59:59" \
      --depth-min "${DEPTH_MIN}" \
      --depth-max "${DEPTH_MAX}" \
      --variable chl \
      --variable dissic \
      --variable fe \
      --variable no3 \
      --variable nppv \
      --variable o2 \
      --variable ph \
      --variable phyc \
      --variable po4 \
      --variable si \
      --variable spco2 \
      --variable talk \
      --out-dir "${OUT_DIR}" \
      --out-name "${OUT_NAME}" \
      --user "${USERNAME}" \
      --pwd "${PASSWORD}"
    start_date=$((start_date+86400))
done
// extract lat, lon, name from a station
const m = require("max-api");
// path to ocean_datasets
const stations = require("../../ocean_datasets/stations/stations_data_array");
const fs = require("fs");
const path = require("path");

const JSON_FOLDER_PATH =
  __dirname + "/data_extraction/dataset_station/json-data";

m.addHandler("getDataFromRandomLocation", (date, stationIndex) => {
  let filename = stations[stationIndex];

  const filePath = path.join(JSON_FOLDER_PATH, filename);

  const fileContents = fs.readFileSync(`${filePath}.json`, "utf-8");

  const jsonData = JSON.parse(fileContents);

  //   const stationName = jsonData.name;
  //   const lat = jsonData.lat;
  //   const lon = jsonData.lon;
  const selectedDate = jsonData[date];

  const sstMin = parseFloat(selectedDate.SST_MIN);
  const sstMax = parseFloat(selectedDate.SST_MAX);

  m.outlet("SST_MIN", sstMin);
  m.outlet("SST_MAX", sstMax);
  //   m.outlet("STATION_NAME", stationName);
  //   m.outlet("LAT", lat);
  //   m.outlet("LON", lon);
});

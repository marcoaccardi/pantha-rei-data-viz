const m = require("max-api");
const stations = require("./stationDataES5.js");
// extract lat, lon, name, sst_min, sst_may from a station
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
const https = require("https");
const zeroPad = (n) => String(n).padStart(2, "0");
const m = require("max-api");
const coral_bleaching_monitor__db = {
  state: {
    datasets: [
      "CRW_BAA",
      "CRW_BAA_7D_MAX",
      "CRW_DHW",
      "CRW_HOTSPOT",
      "CRW_SST",
      "CRW_SSTANOMALY",
    ],
    dates: [new Date().toJSON(), new Date().toJSON()],
    coordsNorth: [21.025, 21.025],
    coordsEast: [-156.475, -156.475],
  },
  data: null,
  makeUrl: ({ datasets, dates, coordsNorth, coordsEast }) => {
    const format = "json";
    const tokens = datasets
      .map(
        (dataset) =>
          `${dataset}%5B(${dates[0]}):1:(${dates[1]})%5D%5B(${coordsNorth[0]}):1:(${coordsNorth[1]})%5D%5B(${coordsEast[0]}):1:(${coordsEast[1]})%5D`
      )
      .join(",");
    return `https://pae-paha.pacioos.hawaii.edu/erddap/griddap/dhw_5km.${format}?${tokens}`;
  },
  setState(state) {
    this.state = state;
  },
  setDates(dates) {
    this.state["dates"] = [
      new Date(dates[0]).toJSON(),
      new Date(dates[1]).toJSON(),
    ];
  },
  setDateFrom(date) {
    this.state["dates"] = [new Date(date).toJSON(), this.state["dates"][1]];
  },
  setDateTo(date) {
    this.state["dates"] = [this.state["dates"][0], new Date(date).toJSON()];
  },
  setCoordsNorth(coordsNorth) {
    this.state["coordsNorth"] = coordsNorth;
  },
  setCoordsEast(coordsEast) {
    this.state["coordsEast"] = coordsEast;
  },
  setCoordsFrom(coords) {
    this.setCoordsNorth([coords[0], this.state.coordsNorth[1]]);
    this.setCoordsEast([coords[1], this.state.coordsEast[1]]);
  },
  setCoordsTo(coords) {
    this.setCoordsNorth([this.state.coordsNorth[1], coords[0]]);
    this.setCoordsEast([this.state.coordsEast[1], coords[1]]);
  },
  formatData(jsonString) {
    if (!jsonString) return {};
    try {
      const result = {};
      const { table } = JSON.parse(jsonString);
      const [a, b, c, ...sets] = table.columnNames;

      const rows = table.rows.map((rowData, i) => {
        const [date, e, f, ...row] = rowData;
        return [date, ...row];
      });

      sets.forEach((set, i) => {
        const offset = 1;
        const index = i + offset;
        result[set] = {};

        rows.forEach(([date, ...row], iRow) => {
          result[set][date] = rows[iRow][index];
        });
      });

      return result;
    } catch (error) {
      m.post(error);
    }
  },
  loadData() {
    const url = this.makeUrl(this.state);
    return new Promise((resolve, reject) => {
      https
        .get(url, (res) => {
          var body = "";

          res.on("data", (chunk) => {
            body += chunk;
          });

          res.on("end", () => {
            this.data = this.formatData(body);
            resolve();
          });
        })
        .on("error", function (err) {
          reject(err);
        });
    });
  },
};

// (async () => {
//   db.setDates(["02-21-2023", "02-22-2023"]);
//   await db.loadData();
//   const response = db.data;
//   console.log(response);
// })();

module.exports = coral_bleaching_monitor__db;

const path = require("path");
const Max = require("max-api");
const db = require("./get_coral_bleaching_monitor__db");

var debug = false;

// This will be printed directly to the Max console
Max.post(`Loaded the ${path.basename(__filename)} script`);

Max.setDict("datasets", { datasets: db.state.datasets });
Max.setDict("data", {});

Max.addHandler("set_debug", (shouldDebug) => {
  Max.post(`debug mode ${shouldDebug ? "on" : "off"}`);

  debug = shouldDebug;
});

Max.addHandler("set_date_from", (year, month, day, hh, mm) => {
  Max.setDict("data", {});
  const from = `${day}-${month}-${year} ${hh}:${mm}`;
  db.setDateFrom(from);
  debug && Max.post(`set_date_from ${new Date(from).toJSON()}`);
});

Max.addHandler("set_date_to", (year, month, day, hh, mm) => {
  Max.setDict("data", {});
  const to = `${day}-${month}-${year} ${hh}:${mm}`;
  db.setDateTo(to);
  debug && Max.post(`set_date_to ${new Date(to).toJSON()}`);
});

Max.addHandler("set_coords_from", (north, east) => {
  Max.setDict("data", {});
  const from = [north, east];
  db.setCoordsFrom(from);
  debug && Max.post(`set_coords_from ${from}`);
});

Max.addHandler("set_coords_to", (north, east) => {
  Max.setDict("data", {});
  const to = [north, east];
  db.setCoordsTo(to);
  debug && Max.post(`set_coords_to ${to}`);
});

Max.addHandler("get_data", () => {
  Max.setDict("data", {});
  db.loadData().then(() => {
    // if (!db.data) return {};
    // Max.post("CRW_BAA", db.data.CRW_BAA)
    if (db.data) {
      let {
        CRW_BAA,
        CRW_BAA_7D_MAX,
        CRW_DHW,
        CRW_HOTSPOT,
        CRW_SST,
        CRW_SSTANOMALY,
      } = db.data;
      Max.setDict("data", db.data);
      Max.post(`state loaded`);
      Max.outlet("CRW_BBA", Object.values(CRW_BAA)[0]);
      Max.outlet("CRW_BAA_7D_MAX", Object.values(CRW_BAA_7D_MAX)[0]);
      Max.outlet("CRW_DHW", Object.values(CRW_DHW)[0]);
      Max.outlet("CRW_HOTSPOT", Object.values(CRW_HOTSPOT)[0]);
      Max.outlet("CRW_SST", Object.values(CRW_SST)[0]);
      Max.outlet("CRW_SSTANOMALY", Object.values(CRW_SSTANOMALY)[0]);
    }

    Max.outletBang();
  });
});
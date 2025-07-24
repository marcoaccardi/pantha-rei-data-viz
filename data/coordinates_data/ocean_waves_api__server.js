const m = require("max-api");
const https = require("https");
// STARTING dateWithHour ---> 2010-11-07T21:00:00Z
const date = "2010-12-07T00:00:00Z"; // Replace with desired date
const lat = -17.0; // Replace with desired latitude
const lon = 120.0; // Replace with desired longitude

m.addHandler("get_waves_data", (date, lat, lon) => {
  let dateWithHour = `${date}T00:00:00Z`;
  let url = `https://pae-paha.pacioos.hawaii.edu/erddap/griddap/ww3_global.json?Tdir%5B(${dateWithHour}):1:(${dateWithHour})%5D%5B(0.0):1:(0.0)%5D%5B(${lat}):1:(${lat})%5D%5B(${lon}):1:(${lon})%5D,Tper%5B(${dateWithHour}):1:(${dateWithHour})%5D%5B(0.0):1:(0.0)%5D%5B(${lat}):1:(${lat})%5D%5B(${lon}):1:(${lon})%5D,Thgt%5B(${dateWithHour}):1:(${dateWithHour})%5D%5B(0.0):1:(0.0)%5D%5B(${lat}):1:(${lat})%5D%5B(${lon}):1:(${lon})%5D,sdir%5B(${dateWithHour}):1:(${dateWithHour})%5D%5B(0.0):1:(0.0)%5D%5B(${lat}):1:(${lat})%5D%5B(${lon}):1:(${lon})%5D,sper%5B(${dateWithHour}):1:(${dateWithHour})%5D%5B(0.0):1:(0.0)%5D%5B(${lat}):1:(${lat})%5D%5B(${lon}):1:(${lon})%5D,shgt%5B(${dateWithHour}):1:(${dateWithHour})%5D%5B(0.0):1:(0.0)%5D%5B(${lat}):1:(${lat})%5D%5B(${lon}):1:(${lon})%5D,wdir%5B(${dateWithHour}):1:(${dateWithHour})%5D%5B(0.0):1:(0.0)%5D%5B(${lat}):1:(${lat})%5D%5B(${lon}):1:(${lon})%5D,wper%5B(${dateWithHour}):1:(${dateWithHour})%5D%5B(0.0):1:(0.0)%5D%5B(${lat}):1:(${lat})%5D%5B(${lon}):1:(${lon})%5D,whgt%5B(${dateWithHour}):1:(${dateWithHour})%5D%5B(0.0):1:(0.0)%5D%5B(${lat}):1:(${lat})%5D%5B(${lon}):1:(${lon})%5D`;
  https
    .get(url, (response) => {
      let data = "";
      response.on("data", (chunk) => {
        data += chunk;
      });
      response.on("end", () => {
        const resultJSON = JSON.parse(data).table.rows[0];
        // console.log(resultJSON);
        const resultDataObj = {
          Tdir: resultJSON[4],
          Tper: resultJSON[5],
          Thgt: resultJSON[6],
          sdir: resultJSON[7],
          sper: resultJSON[8],
          shgt: resultJSON[9],
          wdir: resultJSON[10],
          wper: resultJSON[11],
          whgt: resultJSON[12],
        };
        m.outlet("objData", resultDataObj);
        m.outlet("Tdir", resultDataObj.Tdir);
        m.outlet("Tper", resultDataObj.Tper);
        m.outlet("Thgt", resultDataObj.Thgt);
        m.outlet("sdir", resultDataObj.sdir);
        m.outlet("sper", resultDataObj.sper);
        m.outlet("shgt", resultDataObj.shgt);
        m.outlet("wdir", resultDataObj.wdir);
        m.outlet("wper", resultDataObj.wper);
        m.outlet("whgt", resultDataObj.whgt);
      });
    })
    .on("error", (error) => {
      m.post(error);
    });
});

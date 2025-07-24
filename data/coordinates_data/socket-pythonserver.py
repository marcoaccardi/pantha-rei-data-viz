import asyncio
import json
import websockets

# read data
from ocean_currents__server import get_current_data
# from ocean_waves__server import get_waves_data
from ocean_biological__server import get_bio_data
# send data


async def geo_temporal(websocket, path):
    async for message in websocket:

        data = json.loads(message)
        print("i got this ", data)
        if "geoTemporalData" in data:
            # extract data from socket
            lat = data["geoTemporalData"]["coords"]["lat"]
            lon = data["geoTemporalData"]["coords"]["lon"]
            date = data["geoTemporalData"]["date"]
            print(f"lat_{lat}, lon_{lon}, date:{date}")

            # read data
            ocean_current_data = get_current_data(date, lat, lon)
            # ocean_waves_data = get_waves_data(date, lat, lon)
            ocean_bio_data = get_bio_data(date, lat, lon)

            # collect data
            database = {
                "ocean_currents": ocean_current_data,
                # "ocean_waves": ocean_waves_data,
                "ocean_bio": ocean_bio_data
            }

            print("function return data", ocean_current_data)

            # send data back to node server:7000
            # await websocket.send(json.dumps(ocean_current_data))
            await websocket.send(json.dumps(database))


# keep running the application
async def main():
    async with websockets.serve(geo_temporal, "localhost", 7000):
        print("WebSocket server listening on port 7000...")
        await asyncio.Future()  # keep running the server indefinitely


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json
import os
import websockets

URL = "wss://stream.pelyr.com/v1/stream"

KEY = os.environ.get("PELYR_KEY")

if not KEY:
    raise RuntimeError("PELYR_KEY is not set.")

# Strongest AI candidate
CENTER_LAT = -15.824387
CENTER_LON = 51.655060

# Approximately a 2° x 2° search area
BBOX = {
    "west": CENTER_LON - 1.0,
    "south": CENTER_LAT - 1.0,
    "east": CENTER_LON + 1.0,
    "north": CENTER_LAT + 1.0,
}


async def main():

    headers = {
        "Authorization": f"Bearer {KEY}"
    }

    print("Connecting to Pelyr AIS stream...")
    print(f"Search area:")
    print(f"  West : {BBOX['west']:.4f}")
    print(f"  South: {BBOX['south']:.4f}")
    print(f"  East : {BBOX['east']:.4f}")
    print(f"  North: {BBOX['north']:.4f}")
    print()

    async with websockets.connect(
        URL,
        additional_headers=headers,
        ping_interval=None,
    ) as ws:

        async for raw in ws:

            frame = json.loads(raw)
            frame_type = frame.get("type")

            if frame_type == "welcome":

                print("Connected successfully!")
                print()
                print("Pelyr scope:", frame.get("key", {}).get("scope"))
                print("Subscribe deadline:",
                      frame.get("subscribe_deadline_ms"), "ms")
                print()

                subscribe_message = {
                    "type": "subscribe",
                    "id": "indian-ocean-test",
                    "bbox": [BBOX],
                    "msg_types": [1, 2, 3, 18, 19],
                    "fields": "position",
                }

                await ws.send(json.dumps(subscribe_message))

                print("Subscription sent.")
                print("Waiting for vessels...")
                print("-" * 60)

            elif frame_type == "subscribed":

                print("Subscription accepted.")
                print("Effective filter:")
                print(json.dumps(
                    frame.get("effective"),
                    indent=2
                ))
                print("-" * 60)

            elif frame_type == "position":

                data = frame.get("data", {})

                print(
                    f"MMSI: {data.get('mmsi')} | "
                    f"Lat: {data.get('lat')} | "
                    f"Lon: {data.get('lon')} | "
                    f"SOG: {data.get('sog')} kn | "
                    f"COG: {data.get('cog')}° | "
                    f"Type: {data.get('msg_type')}"
                )

            elif frame_type == "heartbeat":

                print(
                    f"[Heartbeat] dropped={frame.get('dropped', 0)}"
                )

            elif frame_type == "notice":

                print("[NOTICE]")
                print(json.dumps(frame, indent=2))

            elif frame_type == "error":

                print("[ERROR]")
                print(json.dumps(frame, indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nStream stopped.")

    except Exception as e:
        print("\nConnection failed:")
        print(type(e).__name__, str(e))
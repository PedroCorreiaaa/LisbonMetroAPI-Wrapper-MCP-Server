import os
import sys
import asyncio
from typing import Any
from geopy.distance import geodesic
from dotenv import load_dotenv
import httpx
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

mcp = FastMCP("metro-lisboa")

METRO_API_BASE = "https://api.metrolisboa.pt:8243/estadoServicoML/1.0.1"
METRO_API_TOKEN = os.getenv("METRO_API_TOKEN")
USER_AGENT = "metro-lisboa"

async def make_api_request(endpoint: str) -> dict[str, Any] | list[Any] | None:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Authorization": f"Bearer {METRO_API_TOKEN}"
    }
    url = f"{METRO_API_BASE}{endpoint}"
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error requesting Metro API: {e}", file=sys.stderr)
            return None

def extract_lines(raw: str) -> set[str]:
    """Converts a string like '[Blue, Green]' to a set: {'Blue', 'Green'}"""
    return set(s.strip(" []") for s in raw.split(",") if s.strip(" []"))

async def geocode_location(location: str) -> tuple[float, float] | None:
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": location,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": USER_AGENT
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return lat, lon
        except Exception as e:
            print(f"Error during geocoding: {e}", file=sys.stderr)
            return None

async def average_wait_time_at_station(station_name: str) -> int:
    response = await make_api_request(f"/tempoEspera/{station_name}")
    if isinstance(response, dict) and "resposta" in response and isinstance(response["resposta"], list):
        waits = [int(item["tempo"]) for item in response["resposta"] if item.get("tempo", "").isdigit()]
        if waits:
            return round(sum(waits) / len(waits))
    return 4  # fallback default

async def route_between_stations(origin_station: dict, destination_station: dict) -> str:
    origin_name = origin_station["stop_name"]
    destination_name = destination_station["stop_name"]
    origin_lines = extract_lines(origin_station.get("linha", ""))
    destination_lines = extract_lines(destination_station.get("linha", ""))

    TRAVEL_TIME_BETWEEN_STATIONS = 2  # in minutes

    intersection = origin_lines & destination_lines
    if intersection:
        line = list(intersection)[0]
        estimated_time = 5 * TRAVEL_TIME_BETWEEN_STATIONS + await average_wait_time_at_station(origin_name)
        return (
            f"The nearest station is **{origin_name}**.\n"
            f"You can take the **{line}** line directly to **{destination_name}**.\n"
            f"Estimated time: **{estimated_time} minutes**."
        )

    # Look for a transfer station
    raw = await make_api_request("/infoEstacao/todos")
    stations_info = raw.get("resposta") if isinstance(raw, dict) else raw

    best_option = None
    shortest_time = float("inf")

    for station in stations_info:
        transfer_name = station["stop_name"]
        transfer_lines = extract_lines(station.get("linha", ""))

        if origin_lines & transfer_lines and destination_lines & transfer_lines:
            wait_transfer = await average_wait_time_at_station(transfer_name)
            total_time = (
                3 * TRAVEL_TIME_BETWEEN_STATIONS +
                await average_wait_time_at_station(origin_name) +
                3 * TRAVEL_TIME_BETWEEN_STATIONS +
                wait_transfer
            )
            if total_time < shortest_time:
                shortest_time = total_time
                best_option = transfer_name

    if best_option:
        origin_line = list(origin_lines)[0]
        destination_line = list(destination_lines)[0]
        return (
            f"The nearest station is **{origin_name}**.\n"
            f"There is no direct connection to **{destination_name}**.\n"
            f"You should take the **{origin_line}** line to **{best_option}**, "
            f"then transfer to the **{destination_line}** line to reach **{destination_name}**.\n"
            f"Estimated time: **{shortest_time} minutes**."
        )

    return f"The nearest station is {origin_name}, but no simple route to {destination_name} was found."

@mcp.tool()
async def route_between_locations(origin_text: str, destination_text: str) -> str:
    """
    Calculates the metro route between two locations given in plain text
    """
    origin_coords = await geocode_location(origin_text)
    if not origin_coords:
        return f"Could not find the origin location '{origin_text}'."

    destination_coords = await geocode_location(destination_text)
    if not destination_coords:
        return f"Could not find the destination location '{destination_text}'."

    raw = await make_api_request("/infoEstacao/todos")
    if not raw:
        return "Error retrieving metro stations."

    stations = raw.get("resposta") if isinstance(raw, dict) else raw

    def nearest_station(coord):
        min_dist = float("inf")
        nearest = None

        for e in stations:
            station_coord = (float(e["stop_lat"]), float(e["stop_lon"]))
            dist = geodesic(coord, station_coord).meters
            print(f"Distance to {e['stop_name']}: {dist:.1f} m", file=sys.stderr)
            if dist < min_dist:
                min_dist = dist
                nearest = e

        return nearest

    origin_station = nearest_station(origin_coords)
    destination_station = nearest_station(destination_coords)

    return await route_between_stations(origin_station, destination_station)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        async def test():
            origin = "Estádio da Luz"
            destination = "Altice Arena"
            result = await route_between_locations(origin, destination)
            print(result)

        asyncio.run(test())
    else:
        mcp.run(transport="stdio")

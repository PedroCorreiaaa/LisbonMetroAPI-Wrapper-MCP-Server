import os
import sys
import asyncio
from typing import Any
from geopy.distance import geodesic
from dotenv import load_dotenv
import httpx
from mcp.server.fastmcp import FastMCP
from neo4j import AsyncGraphDatabase

# Load environment variables
load_dotenv()

mcp = FastMCP("metro-lisboa")

USER_AGENT = "metro-lisboa"

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI")        # e.g. bolt://localhost:7687
NEO4J_USER = os.getenv("NEO4J_USER")      # e.g. neo4j
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


# -------------------------------
# Geocoding (Nominatim)
# -------------------------------
async def geocode_location(location: str) -> tuple[float, float] | None:
    """Convert free text (e.g. 'Altice Arena') into coordinates using OpenStreetMap."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": location, "format": "json", "limit": 1}
    headers = {"User-Agent": USER_AGENT}

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


# -------------------------------
# Query to Neo4j
# -------------------------------
async def get_shortest_path_from_coords(orig_lat: float, orig_lon: float, dest_lat: float, dest_lon: float) -> dict[str, Any] | None:
    """Runs the Neo4j query to compute the shortest metro path between two coordinates."""
    cypher = """
    WITH 
      $orig_lat AS orig_lat, $orig_lon AS orig_lon,
      $dest_lat AS dest_lat, $dest_lon AS dest_lon

    // Find nearest station to origin
    MATCH (s1:Stop)
    WITH s1, orig_lat, orig_lon, dest_lat, dest_lon,
         sqrt((toFloat(s1.stop_lat) - orig_lat)^2 + (toFloat(s1.stop_lon) - orig_lon)^2) AS distO
    ORDER BY distO ASC
    LIMIT 1
    WITH s1 AS startStop, orig_lat, orig_lon, dest_lat, dest_lon

    // Find nearest station to destination
    MATCH (s2:Stop)
    WITH startStop, s2, orig_lat, orig_lon, dest_lat, dest_lon,
         sqrt((toFloat(s2.stop_lat) - dest_lat)^2 + (toFloat(s2.stop_lon) - dest_lon)^2) AS distD
    ORDER BY distD ASC
    LIMIT 1
    WITH startStop, s2 AS endStop

    // Compute shortest path
    MATCH path = shortestPath((startStop)-[:NEXT*]-(endStop))
    RETURN 
        startStop.stop_name AS EstacaoOrigem,
        endStop.stop_name AS EstacaoDestino,
        [n IN nodes(path) | n.stop_name] AS Estacoes,
        [r IN relationships(path) | r.line] AS Linhas,
        length(path) AS NumeroDeParagens;
    """

    async with driver.session() as session:
        result = await session.run(
            cypher,
            orig_lat=orig_lat, orig_lon=orig_lon,
            dest_lat=dest_lat, dest_lon=dest_lon
        )
        record = await result.single()
        return record.data() if record else None


# -------------------------------
# Route calculation and output
# -------------------------------
@mcp.tool()
async def route_between_locations(origin_text: str, destination_text: str) -> str:
    """
    Calculates the metro route between two text locations (using Neo4j as data source).
    """

    # Step 1: Geocode both locations
    origin_coords = await geocode_location(origin_text)
    if not origin_coords:
        return f"Could not find the origin location '{origin_text}'."

    destination_coords = await geocode_location(destination_text)
    if not destination_coords:
        return f"Could not find the destination location '{destination_text}'."

    orig_lat, orig_lon = origin_coords
    dest_lat, dest_lon = destination_coords

    # Step 2: Query Neo4j for best route
    route_data = await get_shortest_path_from_coords(orig_lat, orig_lon, dest_lat, dest_lon)
    if not route_data:
        return "No route found between these locations."

    # Step 3: Build a nice human-readable response
    origem = route_data["EstacaoOrigem"]
    destino = route_data["EstacaoDestino"]
    estacoes = route_data["Estacoes"]
    linhas = route_data["Linhas"]
    num_paragens = route_data["NumeroDeParagens"]

    TEMPO_ENTRE_ESTACOES = 2  # minutes
    TEMPO_ESPERA = 4          # minutes
    tempo_estimado = num_paragens * TEMPO_ENTRE_ESTACOES + TEMPO_ESPERA

    texto_estacoes = " → ".join(estacoes)
    texto_linhas = ", ".join(set(linhas))

    return (
        f"The nearest station to your origin is **{origem}**.\n"
        f"The nearest station to your destination is **{destino}**.\n"
        f"Route: {texto_estacoes}.\n"
        f"Lines used: {texto_linhas}.\n"
        f"Number of stops: {num_paragens}.\n"
        f"Estimated travel time: **{tempo_estimado} minutes**."
    )


# -------------------------------
# Local testing
# -------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        async def test():
            origin = "Avenida da Liberdade"
            destination = "Terreiro do Paço"
            result = await route_between_locations(origin, destination)
            print(result)

        asyncio.run(test())
    else:
        mcp.run(transport="stdio")

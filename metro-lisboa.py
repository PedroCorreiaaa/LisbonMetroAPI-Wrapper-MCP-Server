import os
import sys
from typing import Any
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import asyncio
from geopy.distance import geodesic

# Carregar variáveis do .env
load_dotenv()

mcp = FastMCP("metro-lisboa")

METRO_API_BASE = os.getenv("METRO_API_BASE")
METRO_API_TOKEN = os.getenv("METRO_API_TOKEN")
USER_AGENT = "metro-chat/1.0"

async def make_metro_request(endpoint: str) -> dict[str, Any] | list[Any] | None:
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
            print(f"Erro ao fazer pedido à API: {e}", file=sys.stderr)
            return None


def extrair_linhas(raw: str) -> set[str]:
    """Converte string tipo '[Azul, Verde]' em set: {'Azul', 'Verde'}"""
    return set(
        s.strip(" []") for s in raw.split(",") if s.strip(" []")
    )


@mcp.tool()
async def rota_para_destino(destino: str, latitude: float, longitude: float) -> str:
    """
    Devolve a melhor rota no Metro até à estação destino,
    com base na estação mais próxima das coordenadas fornecidas,
    escolhendo a rota com menor tempo estimado.
    """

    raw = await make_metro_request("/infoEstacao/todos")
    if not raw:
        return "Não foi possível obter a lista de estações."

    estacoes_info = raw.get("resposta") if isinstance(raw, dict) and "resposta" in raw else raw
    if not isinstance(estacoes_info, list):
        return f"Formato inesperado da resposta da API: {raw}"

    # Estação mais próxima
    mais_proxima = min(
        estacoes_info,
        key=lambda e: geodesic(
            (latitude, longitude),
            (float(e["stop_lat"]), float(e["stop_lon"]))
        ).meters
    )
    estacao_origem = mais_proxima["stop_name"]
    id_origem = mais_proxima["stop_id"]
    linhas_origem = extrair_linhas(mais_proxima.get("linha", ""))

    # Estação destino
    estacao_destino = next(
        (e for e in estacoes_info if destino.lower() in e["stop_name"].lower()), None
    )
    if not estacao_destino:
        return f"A estação de destino '{destino}' não foi encontrada."

    id_destino = estacao_destino["stop_id"]
    nome_destino = estacao_destino["stop_name"]
    linhas_destino = extrair_linhas(estacao_destino.get("linha", ""))

    TEMPO_ENTRE_ESTACOES = 2  # minutos
    TEMPO_ESPERA = 4          # minutos

    # Verificar se existe linha direta
    intersecao = linhas_origem & linhas_destino
    if intersecao:
        linha = list(intersecao)[0]
        # Estimamos número de estações (não temos path real, vamos estimar com 5 estações)
        tempo_estimado = 5 * TEMPO_ENTRE_ESTACOES + TEMPO_ESPERA
        return (
            f"A estação mais próxima de ti é **{estacao_origem}**.\n"
            f"Podes apanhar a linha **{linha}** diretamente até **{nome_destino}**.\n"
            f"Tempo estimado: **{tempo_estimado} minutos**."
        )

    # Procurar estação de troca mais eficiente
    melhor_opcao = None
    menor_tempo = float("inf")

    for e in estacoes_info:
        nome_troca = e["stop_name"]
        linhas_estacao = extrair_linhas(e.get("linha", ""))

        if linhas_origem & linhas_estacao and linhas_destino & linhas_estacao:
            tempo = (
                3 * TEMPO_ENTRE_ESTACOES +    # origem -> troca
                TEMPO_ESPERA +                # espera antes da troca
                3 * TEMPO_ENTRE_ESTACOES +    # troca -> destino
                TEMPO_ESPERA                  # espera final
            )
            if tempo < menor_tempo:
                menor_tempo = tempo
                melhor_opcao = nome_troca

    if melhor_opcao:
        linha_origem = list(linhas_origem)[0]
        linha_destino = list(linhas_destino)[0]
        return (
            f"A estação mais próxima de ti é **{estacao_origem}**.\n"
            f"Não existe ligação direta até **{nome_destino}**.\n"
            f"Deves apanhar a linha **{linha_origem}** até **{melhor_opcao}**, "
            f"e mudar para a linha **{linha_destino}** até **{nome_destino}**.\n"
            f"Tempo estimado: **{menor_tempo} minutos**."
        )

    return (
        f"A estação mais próxima é {estacao_origem}, mas não foi possível encontrar uma rota simples até {nome_destino}."
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        async def test():
            # Exemplo de teste: localização perto de Alto dos Moinhos
            lat = 38.74944
            lon = -9.17917
            destino = "Chelas"
            resultado = await rota_para_destino(destino, lat, lon)
            print(resultado)

        asyncio.run(test())
    else:
        mcp.run(transport="stdio")

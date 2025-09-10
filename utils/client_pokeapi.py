import requests

from utils.registro_log import setup_logger

logger = setup_logger()

POKEAPI_BASE_URL = "https://pokeapi.co/api/v2/move/"

def ottieni_dati_mossa(nome_mossa):
    """
    Ottiene i dettagli di una mossa da PokeAPI.
    Ritorna un dizionario con power, accuracy e pp.
    """
    url = f"{POKEAPI_BASE_URL}{nome_mossa}"
    try:
        response = requests.get(url)
        if response.status_code == 404:
            logger.warning(f"Mossa non trovata su PokeAPI: {nome_mossa}")
            return None
        response.raise_for_status()

        dati = response.json()
        logger.info(f"Dati ottenuti per {nome_mossa}")
        return {
            "power": dati.get("power"),
            "accuracy": dati.get("accuracy"),
            "pp": dati.get("pp")
        }
    except requests.RequestException as e:
        logger.error(f"Errore richiesta PokeAPI per {nome_mossa}: {e}")
        return None

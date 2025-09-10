import requests

from utils.registro_log import setup_logger

logger = setup_logger()

# Endpoint SPARQL di GraphDB
ENDPOINT = "http://localhost:7200/repositories/pokemonKG"

#Metodo principale che utilizziamo
def esegui_query_sparql(percorso_file_query):
    """
    Legge una query_sparql SPARQL da file e la esegue contro GraphDB.
    Restituisce il risultato in formato JSON.
    """
    try:
        with open(percorso_file_query, "r", encoding="utf-8") as f:
            query = f.read()
        logger.info(f"Esecuzione query_sparql da file: {percorso_file_query}")
        headers = {
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/sparql-query"
        }
        response = requests.post(ENDPOINT, data=query.encode("utf-8"), headers=headers)
        response.raise_for_status()

        risultati = response.json()["results"]["bindings"]
        logger.info(f"Query completata con successo, risultati: {len(risultati)}")
        return risultati
    except requests.RequestException as e:
        logger.error(f"Errore durante l'esecuzione della query_sparql SPARQL: {e}")
        return []
    except Exception as e:
        logger.error(f"Errore generico in esegui_query_sparql: {e}")
        return []

#ATTenzione: Metodo non utilizzato perché risalente a una vecchia idea di logica
def esegui_query_sparql_da_stringa(query: str):
    headers = {
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/sparql-query_sparql"
    }
    response = requests.post(ENDPOINT, data=query.encode("utf-8"), headers=headers)
    response.raise_for_status()
    return response.json()["results"]["bindings"]

#ATTenzione: Metodo non utilizzato perché risalente a una vecchia idea di logica
def ottieni_query_mosse(squadra_uri: list[str]) -> str:
    """
    Per ogni Pokémon della squadra, ottiene le mosse (con i metadati)
    in una singola query_sparql SPARQL. Ogni riga del risultato conterrà:
    - Pokémon (URI)
    - Mossa (URI)
    - Tipo della mossa
    - Precisione (accuracy)
    - Potenza (basePower)
    - PP (basePowerPoints)
    """
    values_clause = "\n".join(f"<{uri}>" for uri in squadra_uri)

    query = f"""
    PREFIX poke: <https://pokemonkg.org/ontology#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT DISTINCT ?species ?move ?type ?accuracy ?basePower ?basePowerPoints
    WHERE {{
      VALUES ?species {{
        {values_clause}
      }}

      ?species poke:isAbleToApply ?move .
      ?move a poke:Move ;
            poke:hasType ?type ;
            poke:basePower ?basePower ;
            poke:accuracy ?accuracy ;
            poke:basePowerPoints ?basePowerPoints .
    }}
    """
    return query

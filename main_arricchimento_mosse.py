from config.costanti_globali import QUERY_SPARQL_MOSSE_SENZA_PARAMETRI, OUTPUT_TTL, OUTPUT_MISSING, BASE_DIR
from utils.client_pokeapi import ottieni_dati_mossa
from utils.client_sparql import esegui_query_sparql
from utils.registro_log import setup_logger
from utils.scrittore_rdf import scrivi_file_mosse_rdf
from visualizza_risultati import VisualizzatoreRisultati

logger = setup_logger()


def main():
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"QUERY_FILE: {QUERY_SPARQL_MOSSE_SENZA_PARAMETRI}")
    logger.info("Esecuzione query_sparql SPARQL per mosse incomplete...")
    mosse_incomplete = esegui_query_sparql(QUERY_SPARQL_MOSSE_SENZA_PARAMETRI)
    logger.info(f"Trovate {len(mosse_incomplete)} mosse incomplete")

    risultati = []
    non_trovate = []

    for mossa in mosse_incomplete:
        uri_mossa = mossa["move"]["value"]
        nome_mossa = VisualizzatoreRisultati.normalizza_uri(uri_mossa)
        logger.info(f"Recupero dati da PokeAPI per {nome_mossa}...")
        #Tramite poke API ottengo i dati della mossa
        dati_api = ottieni_dati_mossa(nome_mossa)

        if dati_api is None:
            logger.warning(f"Mossa non trovata: {nome_mossa}")
            non_trovate.append(nome_mossa)
            continue #salto la mossa e mi segno che c'è stato un problema

        triple_da_aggiungere = {"uri": uri_mossa}
        # trattamento del caso di NONE = 0
        if mossa["hasPower"]["value"] == "false":
            power_val = dati_api.get("power")
            triple_da_aggiungere["power"] = power_val if power_val is not None else 0

        if mossa["hasAccuracy"]["value"] == "false":
            acc_val = dati_api.get("accuracy")
            triple_da_aggiungere["accuracy"] = acc_val if acc_val is not None else 0

        if mossa["hasPP"]["value"] == "false":
            pp_val = dati_api.get("pp")
            triple_da_aggiungere["pp"] = pp_val if pp_val is not None else 0

        risultati.append(triple_da_aggiungere)

    scrivi_file_mosse_rdf(risultati, OUTPUT_TTL)
    logger.info(f"File NQ salvato in {OUTPUT_TTL}")

    with open(OUTPUT_MISSING, "w", encoding="utf-8") as f:
        f.write("\n".join(non_trovate))
    logger.info(f"Mosse non trovate: {len(non_trovate)}")


if __name__ == "__main__":
    main()

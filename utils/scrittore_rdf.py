from utils.registro_log import setup_logger
logger = setup_logger()


def scrivi_file_mosse_rdf(risultati, percorso_file):
    """
    Scrive le nuove quadruple RDF in formato N-Quads.
    Ogni elemento in 'risultati' è un dizionario:
    { 'uri': <uri_mossa>, 'power': <int opzionale>, 'accuracy': <int opzionale>, 'pp': <int opzionale> }
    """
    try:
        xsd_integer = "<http://www.w3.org/2001/XMLSchema#integer>"
        fonte = "<https://pokemonkg.org/dataset/pokeapi>"
        # Evita duplicati
        quadruple_scritte = set()

        with open(percorso_file, "w", encoding="utf-8") as f:
            for r in risultati:
                uri = r["uri"]
                if "power" in r:
                    quad = f"<{uri}> <https://pokemonkg.org/ontology#basePower> \"{r['power']}\"^^{xsd_integer} {fonte} ."
                    if quad not in quadruple_scritte:
                        f.write(quad + "\n")
                        quadruple_scritte.add(quad)
                if "accuracy" in r:
                    quad = f"<{uri}> <https://pokemonkg.org/ontology#accuracy> \"{r['accuracy']}\"^^{xsd_integer} {fonte} ."
                    if quad not in quadruple_scritte:
                        f.write(quad + "\n")
                        quadruple_scritte.add(quad)
                if "pp" in r:
                    quad = f"<{uri}> <https://pokemonkg.org/ontology#basePowerPoints> \"{r['pp']}\"^^{xsd_integer} {fonte} ."
                    if quad not in quadruple_scritte:
                        f.write(quad + "\n")
                        quadruple_scritte.add(quad)

        logger.info(f"Scrittura file RDF in formato N-Quads completata: {percorso_file}")
    except Exception as e:
        logger.error(f"Errore scrittura file RDF (N-Quads): {e}")

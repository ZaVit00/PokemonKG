import pandas as pd
from utils.registro_log import setup_logger
from csp.visualizza_risultati import VisualizzatoreRisultati
from entita.tipo_pokemon import TipoPokemonHelper

logger = setup_logger()

# === Costanti RDF ===
XSD_STRING = "<http://www.w3.org/2001/XMLSchema#string>"
FONTE = "<https://pokemonkg.org/dataset/archetipi-clustering>"
ONTO = "https://pokemonkg.org/ontology#"
BASE_URI_POKEMON = "https://pokemonkg.org/instance/pokemon/"

# === File input CSV ===
PERCORSO_CSV = "apprendimento/risorse/Pokemon_archetipi.csv"
# === File output N-Quads ===
PERCORSO_OUTPUT_NQ = "risorse/dataset_quadruple_pokemonKG/archetipi_pokemon.nq"

# === Mappa URI Pokémon presenti nel KG ===
mappa_uri_kg = TipoPokemonHelper.ottieni_mappa_pokemon_tipi()
nomi_pokemon_kg = set([VisualizzatoreRisultati.normalizza_uri(uri) for uri in mappa_uri_kg])

# === Lettura CSV ===
df = pd.read_csv(PERCORSO_CSV)

quadruple = []
pokemon_mancanti = []

for _, row in df.iterrows():
    nome = str(row["Name"]).strip().lower().replace(" ", "-")
    archetipo = str(row["Archetipo"]).strip()

    # SubArchetipo può essere NaN → controlliamo con pd.notna()
    subarchetipo = row["SubArchetipo"] if pd.notna(row["SubArchetipo"]) else None

    if nome not in nomi_pokemon_kg:
        pokemon_mancanti.append(nome)
        continue

    uri_pokemon = f"<{BASE_URI_POKEMON}{nome}>"

    # Aggiungi Archetipo
    quad1 = f"{uri_pokemon} <{ONTO}hasArchetype> \"{archetipo}\"^^{XSD_STRING} {FONTE} ."
    quadruple.append(quad1)

    # Aggiungi SubArchetipo solo se esiste
    # Alcuni pokemon non hanno il sub-archetipo
    if subarchetipo:
        quad2 = f"{uri_pokemon} <{ONTO}hasSubArchetype> \"{subarchetipo.strip()}\"^^{XSD_STRING} {FONTE} ."
        quadruple.append(quad2)

# === Scrittura su file N-Quads ===
with open(PERCORSO_OUTPUT_NQ, "w", encoding="utf-8") as f:
    f.write("\n".join(quadruple))

logger.info(f"Scrittura completata: {len(quadruple)} triple RDF generate da {len(df)} Pokémon")

# === Pokémon nel CSV ma non trovati nel KG ===
if pokemon_mancanti:
    logger.warning(f"⚠ Pokémon nel CSV ma NON trovati nel KG: {len(pokemon_mancanti)}")
    for p in sorted(pokemon_mancanti):
        logger.warning(f"- {p}")
else:
    logger.info("Tutti i Pokémon del CSV trovati nel KG.")

# === Pokémon nel KG ma non presenti nel CSV ===
nomi_pokemon_csv = set(str(n).strip().lower().replace(" ", "-") for n in df["Name"])
pokemon_kg_non_presenti_in_csv = nomi_pokemon_kg - nomi_pokemon_csv

logger.info(f"Totale Pokémon nel CSV: {len(nomi_pokemon_csv)}")
logger.info(f"Totale Pokémon nel KG: {len(nomi_pokemon_kg)}")
logger.info(f"Pokémon nel KG ma NON presenti nel CSV: {len(pokemon_kg_non_presenti_in_csv)}")

if pokemon_kg_non_presenti_in_csv:
    logger.warning("️Ecco alcuni Pokémon presenti nel KG ma non nel CSV:")
    for p in sorted(pokemon_kg_non_presenti_in_csv):
        logger.warning(f"- {p}")
else:
    logger.info("Tutti i Pokémon del KG sono presenti anche nel CSV.")


"""
QUERY SPARQL per ottenere tutti i pokemon con l'archetipo e il subarchetipo
PREFIX poke: <https://pokemonkg.org/ontology#>

SELECT ?pokemon ?archetipo ?subarchetipo
WHERE {
  ?pokemon poke:hasArchetype ?archetipo .
  OPTIONAL { ?pokemon poke:hasSubArchetype ?subarchetipo }
}
"""
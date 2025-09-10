import os
from enum import Enum

# Sali di un livello dalla cartella dove si trova il file corrente
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
QUERY_SPARQL_MOSSE_SENZA_PARAMETRI = os.path.join(BASE_DIR, "query_sparql", "mosse_senza_parametri.rq")
QUERY_SPARQL_TUTTE_MOSSE = os.path.join(BASE_DIR, "query_sparql", "tutte_mosse.rq")
QUERY_SPARQL_TABELLA_MOLTIPLICATORI_DANNI = os.path.join(BASE_DIR, "query_sparql", "tabella_moltiplicatori_danno.rq")
QUERY_SPARQL_POKEMON_TIPI = os.path.join(BASE_DIR, "query_sparql", "pokemon_tipi.rq")

# File di output
OUTPUT_TTL = os.path.join(OUTPUT_DIR, "mosse_arricchite.nq")
OUTPUT_MISSING = os.path.join(OUTPUT_DIR, "mosse_non_trovate.txt")
OUTPUT_TABELLA_MOLTIPLICATORI = os.path.join(OUTPUT_DIR, "tabella_moltiplicatori.nq")
FILE_CSV_TABELLA_MOLTIPLICATORI = os.path.join(BASE_DIR, "risorse", "tabella_moltiplicatori.csv")
# Creazione cartella output
os.makedirs(OUTPUT_DIR, exist_ok=True)

URI_MOSSA_CAT_STATO = "https://pokemonkg.org/ontology#StatusMove"
URI_MOSSA_CAT_FISICO = "https://pokemonkg.org/ontology#PhysicalMove"
URI_MOSSA_CAT_SPECIALE = "https://pokemonkg.org/ontology#SpecialMove"

NUM_SET_MOSSE : int = 4 # numero di quadruple di mosse da generare per ciascun pokemon
HP_MAX_AVVERSARIO = 600
TURNI_PER_RIPOSO = 4
CURE_TOTALI = 3

class Metrica(Enum):
    DANNO_TOTALE = "http://pokemonkg.org/ontology#TotalDamage"
    CAT_SPECIALE = "http://pokemonkg.org/ontology#SpecialMove"
    TIPO_FIRE = "https://pokemonkg.org/ontology#PokéType:Fire"

PESI_VALUTAZIONE = {
    Metrica.DANNO_TOTALE: 3,
    Metrica.CAT_SPECIALE: 5,
    Metrica.TIPO_FIRE: 2
}
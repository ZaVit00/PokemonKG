from enum import Enum
import random
from typing import Dict, Set

from config.costanti_globali import QUERY_SPARQL_POKEMON_TIPI
from utils.registro_log import setup_logger
from utils.client_sparql import esegui_query_sparql
logger = setup_logger(__name__)


class TipoPokemon(Enum):
    NORMAL = "https://pokemonkg.org/ontology#PokéType:Normal"
    FIRE = "https://pokemonkg.org/ontology#PokéType:Fire"
    WATER = "https://pokemonkg.org/ontology#PokéType:Water"
    ELECTRIC = "https://pokemonkg.org/ontology#PokéType:Electric"
    GRASS = "https://pokemonkg.org/ontology#PokéType:Grass"
    ICE = "https://pokemonkg.org/ontology#PokéType:Ice"
    FIGHTING = "https://pokemonkg.org/ontology#PokéType:Fighting"
    POISON = "https://pokemonkg.org/ontology#PokéType:Poison"
    GROUND = "https://pokemonkg.org/ontology#PokéType:Ground"
    FLYING = "https://pokemonkg.org/ontology#PokéType:Flying"
    PSYCHIC = "https://pokemonkg.org/ontology#PokéType:Psychic"
    BUG = "https://pokemonkg.org/ontology#PokéType:Bug"
    ROCK = "https://pokemonkg.org/ontology#PokéType:Rock"
    GHOST = "https://pokemonkg.org/ontology#PokéType:Ghost"
    DRAGON = "https://pokemonkg.org/ontology#PokéType:Dragon"
    DARK = "https://pokemonkg.org/ontology#PokéType:Dark"
    STEEL = "https://pokemonkg.org/ontology#PokéType:Steel"
    FAIRY = "https://pokemonkg.org/ontology#PokéType:Fairy"

    def __str__(self):
        return self.value


tipi_strategici = {
    TipoPokemon.FIRE.value: {TipoPokemon.GROUND.value},
    TipoPokemon.DRAGON.value: {TipoPokemon.FAIRY.value, TipoPokemon.ELECTRIC.value},
    TipoPokemon.ELECTRIC.value: set(),
    TipoPokemon.GRASS.value: set(),
    TipoPokemon.WATER.value: set(),
    TipoPokemon.GROUND.value: {TipoPokemon.DRAGON.value},
}

tipi_strategici_avversario = {
    TipoPokemon.GRASS.value: {TipoPokemon.POISON.value, TipoPokemon.FLYING.value},
    TipoPokemon.ICE.value: {TipoPokemon.WATER.value},
    TipoPokemon.PSYCHIC.value: {TipoPokemon.GHOST.value, TipoPokemon.FAIRY.value},
    TipoPokemon.BUG.value: set(),
    TipoPokemon.DARK.value: set(),
    TipoPokemon.ROCK.value: set(),
}

class TipoPokemonHelper:
    """
    Classe helper per gestire tipi Pokémon, compatibilità e mappature,
    con cache interne e incapsulamento della logica.
    """
    _mappa_pokemon_con_tipi: dict[str, list[str]] | None = None
    _mappa_tipo_to_indice: dict[str, int] | None = None

    _mappa_tipi_compatibili: dict[TipoPokemon, set[TipoPokemon]] = {
        TipoPokemon.NORMAL: {TipoPokemon.FIGHTING},
        TipoPokemon.FIRE: {TipoPokemon.FIGHTING, TipoPokemon.DRAGON},  # Fire può avere mosse Fighting/Dragon
        TipoPokemon.WATER: {TipoPokemon.ICE, TipoPokemon.GROUND, TipoPokemon.ROCK},
        TipoPokemon.ELECTRIC: {TipoPokemon.FLYING, TipoPokemon.STEEL},
        TipoPokemon.GRASS: {TipoPokemon.GROUND, TipoPokemon.ROCK, TipoPokemon.WATER},
        TipoPokemon.ICE: {TipoPokemon.GRASS, TipoPokemon.GROUND, TipoPokemon.FLYING, TipoPokemon.DRAGON},
        TipoPokemon.FIGHTING: {TipoPokemon.NORMAL, TipoPokemon.ROCK, TipoPokemon.STEEL, TipoPokemon.ICE,
                               TipoPokemon.DARK},
        TipoPokemon.POISON: {TipoPokemon.GRASS, TipoPokemon.FAIRY},
        TipoPokemon.GROUND: {TipoPokemon.ROCK, TipoPokemon.STEEL, TipoPokemon.FIRE},  # Non include Water
        TipoPokemon.FLYING: {TipoPokemon.FIGHTING, TipoPokemon.BUG, TipoPokemon.GRASS},
        TipoPokemon.PSYCHIC: {TipoPokemon.FIGHTING, TipoPokemon.POISON},
        TipoPokemon.BUG: {TipoPokemon.GRASS, TipoPokemon.PSYCHIC, TipoPokemon.DARK},
        TipoPokemon.ROCK: {TipoPokemon.FIRE, TipoPokemon.ICE, TipoPokemon.FLYING, TipoPokemon.BUG},
        TipoPokemon.GHOST: {TipoPokemon.PSYCHIC, TipoPokemon.GHOST},
        TipoPokemon.DRAGON: {TipoPokemon.FIRE, TipoPokemon.ELECTRIC, TipoPokemon.WATER},
        # compatibile con elementi canonici
        TipoPokemon.DARK: {TipoPokemon.PSYCHIC, TipoPokemon.GHOST},
        TipoPokemon.STEEL: {TipoPokemon.ICE, TipoPokemon.ROCK, TipoPokemon.FAIRY},
        TipoPokemon.FAIRY: {TipoPokemon.FIGHTING, TipoPokemon.DRAGON, TipoPokemon.DARK},
    }

    @classmethod
    def genera_tipi_strategici(cls, soglie: list[int]) -> Dict[str, Set[str]]:
        """
        Genera 6 Pokémon con tipo primario unico e tipo secondario variabile secondo le soglie fornite.
        La posizione i nella lista `soglie` definisce quanti tipi secondari provare ad assegnare al Pokémon i-esimo.
        """
        if len(soglie) != 6:
            raise ValueError("La lista deve contenere esattamente 6 soglie.")

        tutti_tipi = list(TipoPokemon)
        random.shuffle(tutti_tipi)  # Varietà nella scelta dei tipi primari

        if len(tutti_tipi) < 6:
            raise ValueError("Servono almeno 6 tipi primari unici.")

        # Seleziona 6 tipi primari unici
        tipi_primari = tutti_tipi[:6]

        vincoli: Dict[str, Set[str]] = {}

        for i, soglia in enumerate(soglie):
            tipo_principale = tipi_primari[i]
            # Lista di tipi secondari candidati (escludendo il primario)
            tipi_candidati = [t for t in tutti_tipi if t != tipo_principale]
            random.shuffle(tipi_candidati)

            secondari_selezionati = tipi_candidati[:soglia] if soglia > 0 else []
            vincoli[tipo_principale.value] = {t.value for t in secondari_selezionati}

        return vincoli

    @classmethod
    def ottieni_tipi_compatibili(cls, tipo_uri: TipoPokemon) -> list[str]:
        """
        Dato un URI tipo, restituisce la lista di tipi compatibili come URI.
        """
        #tipo_enum = cls.mappa_uri_enum(tipo_uri)
        compatibili = cls._mappa_tipi_compatibili.get(tipo_uri, set())
        return [t.value for t in compatibili]

    @classmethod
    def ottieni_mappa_tipo_indice(cls, tipo_uri: str) -> int:
        """
        Restituisce indice intero associato all'URI tipo, costruendo la mappa se necessario.
        """
        if cls._mappa_tipo_to_indice is None:
            cls._mappa_tipo_to_indice = {tipo.value: i for i, tipo in enumerate(TipoPokemon)}
        if tipo_uri not in cls._mappa_tipo_to_indice:
            raise ValueError(f"Tipo Pokémon non riconosciuto: {tipo_uri}")
        return cls._mappa_tipo_to_indice[tipo_uri]

    @classmethod
    def ottieni_mappa_pokemon_tipi(cls) -> dict[str, list[str]]:
        """
        Restituisce la mappa Pokémon->tipi caricata o la carica da KG se necessario.
        """

        if cls._mappa_pokemon_con_tipi is None:
            def _ottieni_pokemon_con_tipi_knowledge_graph() -> dict[str, list[str]]:
                """
                Interroga il KG e costruisce la mappa Pokemon URI -> lista tipi URI (max 2).
                # Funzione a uso interno della classe
                """
                risultati = esegui_query_sparql(QUERY_SPARQL_POKEMON_TIPI)
                mappa = {}
                for r in risultati:
                    pokemon_uri = r["pokemon"]["value"]
                    tipo_uri = r["type"]["value"]

                    if pokemon_uri not in mappa:
                        # aggiungi la lista vuota
                        mappa[pokemon_uri] = []

                    # Evita duplicati e tiene massimo 2 tipi
                    if tipo_uri not in mappa[pokemon_uri] and len(mappa[pokemon_uri]) < 2:
                        mappa[pokemon_uri].append(tipo_uri)

                return mappa

            cls._mappa_pokemon_con_tipi = _ottieni_pokemon_con_tipi_knowledge_graph()
            logger.info(f"Pokémon caricati: {len(cls._mappa_pokemon_con_tipi)}")

        return cls._mappa_pokemon_con_tipi

    @classmethod
    def ottieni_tipi_pokemon(cls, pokemon_uri: str) -> list[str]:
        """
        Restituisce la lista dei tipi (URI) associati a un singolo Pokémon.
        Se il Pokémon non esiste nella mappa, restituisce lista vuota.
        """
        mappa = cls.ottieni_mappa_pokemon_tipi()
        return mappa.get(pokemon_uri, [])

    @staticmethod
    def mappa_uri_enum(uri_tipo: str) -> TipoPokemon:
        """
        Mappa da URI tipo a Enum TipoPokemon, con errore se sconosciuto.
        NON utilizzato per ora
        """
        for tipo in TipoPokemon:
            if tipo.value == uri_tipo:
                return tipo
        raise ValueError(f"Tipo Pokémon sconosciuto o non supportato: {uri_tipo}")

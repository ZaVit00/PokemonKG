import logging
from typing import Optional
from constraint import Problem, AllDifferentConstraint
from entita.tipo_pokemon import TipoPokemonHelper
from utils.registro_log import setup_logger

logger = setup_logger()
logger.setLevel(logging.CRITICAL)

class GeneratoreSquadre:
    # Mappa globale Pokémon → lista tipi (primario, secondario se presente)
    _mappa_pokemon_tipi = TipoPokemonHelper.ottieni_mappa_pokemon_tipi()

    @classmethod
    def genera_squadra_personale(cls, tipi_strategici: dict[str, set[str]],
                                 squadra_precedente: set[str]) -> list[str]:
        """
        Genera una squadra in base a tipi strategici forniti dall'utente.
        tipi_strategici: dict { tipo_primario: {tipi_secondari_ammissibili} }
        squadra_precedente: lista di Pokémon da evitare se possibile.
        """
        # Controllo che siano esattamente 6 tipi strategici (uno per slot)
        if len(tipi_strategici) != 6:
            raise ValueError(f"TIPI_STRATEGICI deve contenere esattamente 6 tipi, ma ne ha {len(tipi_strategici)}")

        # Filtra Pokémon compatibili con ogni tipo strategico
        # chiave: uri del tipo -> valore: lista di uri dei pokemon con quel tipo in accordo con la struttura dati
        # tipi_strategici
        domini_per_tipo : dict [str, list[str]] = cls._filtra_pokemon_per_tipo(tipi_strategici, pokemon_da_escludere = squadra_precedente)

        # Se per un tipo strategico non ci sono Pokémon disponibili → impossibile formare squadra
        for tipo, dominio in domini_per_tipo.items():
            if not dominio:
                logger.warning(f"Nessun Pokémon disponibile per il tipo strategico: {tipo}")
                return []
            else:
                logger.info(
                    f"Pokémon disponibili per il tipo strategico {tipo}: " +
                    ", ".join(f"{uri}({', '.join(cls._mappa_pokemon_tipi[uri])})" for uri in dominio)
                )

        # Costruisce il CSP
        problem = Problem()

        # Variabili = slot squadra, valori = Pokémon compatibili con il tipo dello slot
        # i utilizzato per denotare il nome della variabile
        for i, tipo in enumerate(tipi_strategici):
            problem.addVariable(f"slot_{i}", domini_per_tipo[tipo])

        # Vincolo: tutti i Pokémon devono essere diversi
        problem.addConstraint(AllDifferentConstraint(), [f"slot_{i}" for i in range(6)])

        # Vincoli generali di diversità dei tipi (primari e secondari)
        problem.addConstraint(cls._vincoli_generali_squadra, [f"slot_{i}" for i in range(6)])


        # Risolve il CSP e restituisce la squadra
        soluzione = problem.getSolution()
        if soluzione is None:
            logger.warning("Nessuna squadra trovata con i vincoli attuali")
            return []

        return [soluzione[f"slot_{i}"] for i in range(6)]

    @classmethod
    def genera_squadra_capo_palestra(cls, tipo_tema: str) -> list[str]:
        """
        Genera una squadra a tema per un capo palestra.
        Richiede almeno 2 Pokémon con doppio tipo.
        """
        # Lista di Pokémon che hanno il tipo-tema come primario o secondario
        lista_pokemon = [
            uri for uri, tipi in cls._mappa_pokemon_tipi.items()
            if tipo_tema in tipi
        ]

        logger.debug(f"Pokémon compatibili con {tipo_tema}: {len(lista_pokemon)}")

        # Conta quanti di questi hanno doppio tipo
        num_doppio_tipo = sum(1 for uri in lista_pokemon if len(cls._mappa_pokemon_tipi[uri]) > 1)

        # Vincolo minimo: almeno 6 Pokémon disponibili e almeno 2 con doppio tipo
        if len(lista_pokemon) < 6 or num_doppio_tipo < 2:
            logger.warning(f"Non ci sono abbastanza Pokémon validi per il tipo {tipo_tema}")
            return []

        # CSP
        problem = Problem()

        # Variabili = slot squadra, dominio = tutti i Pokémon compatibili
        for i in range(6):
            problem.addVariable(f"slot_{i}", lista_pokemon)

        # Tutti diversi
        problem.addConstraint(AllDifferentConstraint(), [f"slot_{i}" for i in range(6)])

        # Almeno 2 con doppio tipo
        problem.addConstraint(cls._vincolo_doppio_tipo, [f"slot_{i}" for i in range(6)])

        soluzione = problem.getSolution()
        if soluzione is None:
            logger.warning(f"Nessuna squadra trovata per il tipo {tipo_tema}")
            return []

        return [soluzione[f"slot_{i}"] for i in range(6)]

    @classmethod
    def _filtra_pokemon_per_tipo(cls, tipi_strategici: dict[str, set[str]], pokemon_da_escludere: set[str]) -> dict[
        str, list[str]]:
        """
        Per ogni tipo strategico, restituisce i Pokémon che:
        - hanno il tipo richiesto in qualsiasi posizione
        - se il set dei secondari ammessi non è vuoto, devono avere almeno un tipo
          del set in una qualsiasi posizione (primario o secondario)
        """
        domini_per_tipo = {tipo: [] for tipo in tipi_strategici}

        for uri_pokemon, tipi_pokemon in cls._mappa_pokemon_tipi.items():
            if uri_pokemon in pokemon_da_escludere:
                continue  # Pokémon escluso

            for tipo_richiesto, secondari_ammissibili in tipi_strategici.items():
                # Deve avere il tipo richiesto
                if tipo_richiesto in tipi_pokemon:
                    # Se non ci sono restrizioni sui secondari → accettalo
                    if not secondari_ammissibili:
                        domini_per_tipo[tipo_richiesto].append(uri_pokemon)
                    else:
                        # Deve avere almeno un tipo secondario ammesso in qualsivoglia posizione diversa dal tipo richiesto
                        altri_tipi = [t for t in tipi_pokemon if t != tipo_richiesto]
                        if any(t in secondari_ammissibili for t in altri_tipi):
                            domini_per_tipo[tipo_richiesto].append(uri_pokemon)

        return domini_per_tipo

    @classmethod
    def _vincoli_generali_squadra(cls, *uri_squadra: str) -> bool:
        """
        Vincoli globali:
        - almeno 3 tipi primari distinti
        - massimo 2 Pokémon con lo stesso tipo primario
        - almeno 2 Pokémon con tipo secondario
        """
        # estrae il primo elemento della lista (il primo tipo secondo la KG)
        tipi_primari = [cls._mappa_pokemon_tipi[uri][0] for uri in uri_squadra]
        # estrae il secondo elemento della lista dei tipi (il secondo tipi secondo la KG)
        tipi_secondari = [
            cls._mappa_pokemon_tipi[uri][1]
            for uri in uri_squadra
            if len(cls._mappa_pokemon_tipi[uri]) > 1 and cls._mappa_pokemon_tipi[uri][1] is not None
        ]

        # Minimo 3 tipi primari diversi
        if len(set(tipi_primari)) < 3:
            logger.debug("Scartata squadra: meno di 3 tipi primari distinti")
            return False # scartare

        # Massimo 2 Pokémon con stesso tipo primario
        for tipo in set(tipi_primari):
            if tipi_primari.count(tipo) > 2:
                logger.debug(f"Scartata squadra: più di 2 Pokémon con tipo primario '{tipo}'")
                return False # scartare

        # Minimo 2 con tipo secondario
        if len(tipi_secondari) < 2:
            logger.debug("Scartata squadra: meno di 2 Pokémon con tipo secondario")
            return False # scartare

        # tutti i vincoli GLOBALI soddisfatti
        return True

    @classmethod
    def _vincolo_doppio_tipo(cls, *pokemon_uri: str) -> bool:
        """
        Deve esserci almeno 2 Pokémon con doppio tipo.
        Per ogni pokemon controllo se la lunghezza della lista dei tipi associata è almeno
        lunghezza 2 => pokemon ha due tipi. se la somma produce 2 allora effettivamente
        ci sono ALMENO due pokemon
        """
        doppio_tipo = sum(1 for uri in pokemon_uri if len(cls._mappa_pokemon_tipi[uri]) > 1)
        return doppio_tipo >= 2

from typing import List, Optional
from constraint import AllDifferentConstraint, Problem
from config.costanti_globali import URI_MOSSA_CAT_SPECIALE, URI_MOSSA_CAT_FISICO
from entita.mossa import Mossa
from entita.tipo_pokemon import TipoPokemon, TipoPokemonHelper
from utils.registro_log import setup_logger

logger = setup_logger(__name__)
"""
🔹 Spiegazione dei domini
Slot 0: mosse del tipo primario (sempre presenti).

Slot 1: mosse del tipo secondario, se presente; altrimenti replica del primario.

Slot 2: mosse di un tipo compatibile (scelta tra quelli compatibili con primario o secondario).

Slot 3: mosse di un altro tipo compatibile diverso dal precedente; se non ci sono, unione dei domini precedenti senza duplicati.
"""

class AssegnatoreMosseLocale:

    @classmethod
    def _costruisci_domini(cls, mosse_assegnate_globali: set["Mossa"],
                          tipo_principale: str, tipo_secondario: Optional[str] = None) -> list[list["Mossa"]]:
        """
        Costruisce i domini delle 4 mosse per un singolo Pokémon basato sui suoi tipi.
        Filtra mosse con precisione 0 o PP <= 1.
        Assicura che ogni dominio abbia almeno una mossa (fallback).
        """

        def filtra_mosse_valide(mosse: list["Mossa"]) -> list["Mossa"]:
            """Filtra mosse valide: precisione > 0, PP > 1 e non già assegnate globalmente"""
            return [m for m in mosse if m.precisione > 0 and m.pp > 1 and m not in mosse_assegnate_globali]

        domini: list[list["Mossa"]] = [[], [], [], []]

        # ---------------------------
        # Slot 0: mosse del tipo principale
        # ---------------------------
        domini[0] = filtra_mosse_valide(Mossa.ottieni_mosse_per_tipo(tipo_principale))

        # ---------------------------
        # Slot 1: mosse del tipo secondario o fallback al principale
        # ---------------------------
        if tipo_secondario:
            domini[1] = filtra_mosse_valide(Mossa.ottieni_mosse_per_tipo(tipo_secondario))
        else:
            domini[1] = domini[0][:]  # copia delle mosse del tipo principale

        # ---------------------------
        # Slot 2: mosse di un tipo compatibile
        # ---------------------------
        tipi_compatibili = TipoPokemonHelper.ottieni_tipi_compatibili(
            TipoPokemonHelper.mappa_uri_enum(tipo_principale))
        if tipo_secondario:
            tipi_compatibili += TipoPokemonHelper.ottieni_tipi_compatibili(
                TipoPokemonHelper.mappa_uri_enum(tipo_secondario))

        tipo_compat1 = tipi_compatibili[0] if tipi_compatibili else tipo_principale
        domini[2] = filtra_mosse_valide(Mossa.ottieni_mosse_per_tipo(tipo_compat1))

        # ---------------------------
        # Slot 3: mosse di un altro tipo compatibile o fallback combinato
        # ---------------------------
        tipo_compat2 = None
        for t in tipi_compatibili:
            if t != tipo_compat1:
                tipo_compat2 = t
                break

        if tipo_compat2:
            domini[3] = filtra_mosse_valide(Mossa.ottieni_mosse_per_tipo(tipo_compat2))
        else:
            # fallback: unione dei domini precedenti senza duplicati
            visti = set()
            combinato = []
            for slot_dom in domini[:3]:
                for m in filtra_mosse_valide(slot_dom):
                    if m not in visti:
                        combinato.append(m)
                        visti.add(m)
            domini[3] = combinato

        # ---------------------------
        # Assicura che nessun dominio sia vuoto
        # ---------------------------
        for i, dominio in enumerate(domini):
            if not dominio:
                logger.warning(f"Dominio per le mosse vuoto! Avvio della procedura di fallback per il dominio")
                # fallback: riempi con tutte le mosse valide dei tipi principali e secondari
                mosse_fallback = filtra_mosse_valide(Mossa.ottieni_mosse_per_tipo(tipo_principale))
                if tipo_secondario:
                    mosse_fallback += filtra_mosse_valide(Mossa.ottieni_mosse_per_tipo(tipo_secondario))
                domini[i] = mosse_fallback

        return domini

    @classmethod
    def genera_mosse(cls, mosse_assegnate_locali : set["Mossa"], tipo1: str, tipo2: Optional[str] = None) -> List[Mossa]:
        """
        Genera un set di 4 mosse per un Pokémon basato sui suoi tipi.
        Restituisce una lista di 4 oggetti Mossa.
        """
        # lista di liste di Mosse
        # Costruzione dei domini
        # Sostanzialmente fissiamo che in ogni slot ci devono andare solo mosse di un certo tipo in maniera tale
        # da scremare il lavoro del solver
        domini : list[list[Mossa]] = cls._costruisci_domini(mosse_assegnate_locali, tipo1, tipo2)
        problem = Problem()

        # aggiungi le 4 variabili (slot delle mosse) con i rispettivi domini
        for i in range(4):
            #ogni variabile ha uno specifico dominio
            if len(domini[i]) == 0:
                raise ValueError("Dominio vuoto")
            problem.addVariable(f"slot_{i}", domini[i])

        # vincolo globale: tutte le mosse devono essere  diverse
        problem.addConstraint(AllDifferentConstraint(), [f"slot_{i}" for i in range(4)])
        # vincolo globale: almeno una mossa speciale e una fisica
        problem.addConstraint(cls._vincolo_categoria, [f"slot_{i}" for i in range(4)])

        # vincolo globale: danno totale >= soglia definita internamente
        problem.addConstraint(cls._vincolo_danni, [f"slot_{i}" for i in range(4)])

        # vincolo globale: pp totali >= soglia definita internamente
        problem.addConstraint(cls._vincolo_pp, [f"slot_{i}" for i in range(4)])

        # vincolo globale: precisione totale >= soglia definita internamente
        problem.addConstraint(cls._vincolo_precisione, [f"slot_{i}" for i in range(4)])

        soluzione = problem.getSolution()
        if soluzione is None:
            logger.warn(
                f"[WARNING] Nessuna soluzione trovata per Pokémon tipo {tipo1}/{tipo2}. "
                "Usato fallback con prime mosse disponibili nei domini."
            )
            # debug: stampa dimensioni domini
            for i, dom in enumerate(domini):
                logger.debug(f"  slot_{i}: {len(dom)} possibili mosse")
            # fallback semplice: prendi la prima mossa di ogni dominio
            # Evita il crash dovuta alla mancanza di una soluzione ma logga l'errore
            return [dom[0] for dom in domini]


        # restituisce le mosse ordinate dagli slot
        return [soluzione[f"slot_{i}"] for i in range(4)]

    @classmethod
    def _vincolo_categoria(cls, *mosse) -> bool:
        # Vincolo: almeno una mossa fisica e una speciale
        categorie = {m.categoria_mossa for m in mosse}
        return URI_MOSSA_CAT_FISICO in categorie and URI_MOSSA_CAT_SPECIALE in categorie

    @classmethod
    def _vincolo_danni(cls, *mosse) -> bool:
        #Vincolo: somma dei danni > X
        soglia = 200  # definita internamente
        totale = sum(m.base_power for m in mosse if m.base_power)
        return totale >= soglia

    @classmethod
    def _vincolo_precisione(cls, *mosse) -> bool:
        #non utilizzato
        soglia = 250
        totale = sum(m.precisione for m in mosse if m.precisione)
        return totale >= soglia

    @classmethod
    def _vincolo_pp(cls, *mosse) -> bool:
        #non utilizzato
        soglia = 25
        totale = sum(m.pp for m in mosse if m.pp)
        return totale >= soglia


if __name__ == "__main__":
    # Genera mosse di test per un Pokémon di tipo Electric/Grass
    # Codice di test
    mosse = AssegnatoreMosseLocale.genera_mosse(mosse_assegnate_locali= set(),
                                                tipo1=TipoPokemon.ELECTRIC.value,
                                                tipo2=None)

    totale_danni = sum(m.base_power for m in mosse)
    totale_accuracy = sum(m.precisione for m in mosse)
    totale_pp = sum(m.pp for m in mosse if m.pp)

    print("Mosse generate:")
    for i, m in enumerate(mosse, 1):
        print(f"Mossa {i}: {m}")

    print(f"\nTotale danni: {totale_danni}")
    print(f"Totale accuracy: {totale_accuracy}")
    print(f"Totale PP: {totale_pp}")

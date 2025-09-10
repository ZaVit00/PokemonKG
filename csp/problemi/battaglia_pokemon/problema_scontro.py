import numpy as np
from config.costanti_globali import QUERY_SPARQL_TABELLA_MOLTIPLICATORI_DANNI
from entita.tipo_pokemon import TipoPokemonHelper
from utils.client_sparql import esegui_query_sparql


def _costruisci_matrice_moltiplicatori():
    """
    Costruisce la matrice NxN dei moltiplicatori di danno tra tipi di Pokémon,
    interrogando il Knowledge Graph (KG).

    Ogni cella [i][j] rappresenta l’efficacia di un tipo attaccante i
    contro un tipo difensore j.
    """
    # Esegue la query_sparql SPARQL per ottenere i moltiplicatori dal KG
    risultati = esegui_query_sparql(QUERY_SPARQL_TABELLA_MOLTIPLICATORI_DANNI)

    def normalizza_tipo(tipo_uri):
        """
        Corregge temporaneamente un errore nella base di conoscenza:
        sostituisce 'PokéType_' con 'PokéType:' all’interno della URI.
        # TODO metodo causato da un bug di sintassi
        """
        return tipo_uri.replace("PokéType_", "PokéType:")

    # Ottiene tutti i tipi unici presenti come attaccanti o difensori
    tipi = sorted(
        set(normalizza_tipo(r["attackerType"]["value"]) for r in risultati) |
        set(normalizza_tipo(r["defenderType"]["value"]) for r in risultati)
    )

    # Crea una matrice NxN inizialmente riempita di 1.0 (nessun bonus o malus)
    n = len(tipi)
    matrix = np.ones((n, n), dtype=float)

    # Riempie la matrice con i valori dei moltiplicatori provenienti dal KG
    for r in risultati:
        i = TipoPokemonHelper.ottieni_mappa_tipo_indice(normalizza_tipo(r["attackerType"]["value"]))
        j = TipoPokemonHelper.ottieni_mappa_tipo_indice(normalizza_tipo(r["defenderType"]["value"]))
        # Inserisce il moltiplicatore corretto all’incrocio attaccante -> difensore
        matrix[i, j] = float(r["multiplier"]["value"])

    return matrix


class ValutatoreScontri:
    """
    Classe che valuta il punteggio di scontri diretti tra due squadre di Pokémon
    in base ai loro tipi e alle relazioni di efficacia (moltiplicatori).
    """

    # Mappa Pokémon → tipi (caricata una sola volta)
    mappa_pokemon_tipi = TipoPokemonHelper.ottieni_mappa_pokemon_tipi()
    # Matrice globale dei moltiplicatori tra tipi
    matrice_moltiplicatori = _costruisci_matrice_moltiplicatori()

    @classmethod
    def costruisci_matrice_moltiplicatori_scontri(cls, squadra_nostra : list[str],
                                                  squadra_avversaria : list[str]):
        """
        Costruisce una matrice NxN dove ogni cella [i][j] rappresenta
        il punteggio di efficacia del nostro Pokémon i contro l’avversario j.

        Il punteggio è:
        efficacia massima nostro → avversario - efficacia massima avversario → nostro
        """
        n = len(squadra_nostra)
        m = len(squadra_avversaria)

        # Per semplicità richiediamo squadre di pari dimensione
        if n != m:
            raise ValueError("Le due squadre devono essere della stessa dimensione")

        # Matrice vuota di punteggi (float)
        matrice_punteggi = [[0.0 for _ in range(m)] for _ in range(n)]

        # Calcola punteggio per ogni coppia (nostro pokemon, avversario)
        for i, nostro_uri in enumerate(squadra_nostra):
            #tipi del nostro pokemon
            tipi_nostro = cls.mappa_pokemon_tipi[nostro_uri]
            #per ogni avversario
            for j, avv_uri in enumerate(squadra_avversaria):
                #tipi dell'avversario
                tipi_avv = cls.mappa_pokemon_tipi[avv_uri]
                score = cls.calcola_punteggio_scontro(tipi_nostro, tipi_avv)
                #0, 0 moltiplicatore pokemon 0 della mia squadra contro pokemon 0 squadra avversaria
                #0, 1 moltiplicatore pokemon 0 squadra mia contro pokemon 1 squadra avversaria
                matrice_punteggi[i][j] = score

        return matrice_punteggi

    @classmethod
    def calcola_punteggio_scontro(cls, tipi_nostro, tipi_avversario):
        """
        Calcola il punteggio dello scontro in base alle efficienze massime:

        punteggio = max efficacia (nostro → avversario)
                  - max efficacia (avversario → nostro)
        """
        max_eff_nostro = cls.efficienza(tipi_nostro, tipi_avversario)
        max_eff_avversario = cls.efficienza(tipi_avversario, tipi_nostro)
        return max_eff_nostro - max_eff_avversario

    @classmethod
    def efficienza(cls, tipi_attaccanti, tipi_difensore):
        """
        Restituisce la massima efficacia di attacco di un Pokémon
        (che può avere più tipi) contro un avversario (anche lui multi-tipo).

        La logica moltiplica i moltiplicatori contro ogni tipo del difensore
        e prende il massimo tra tutti i tipi dell’attaccante.
        """
        max_eff = 0.0
        for tipo_att in tipi_attaccanti:
            moltiplicatore = 1.0
            for tipo_dif in tipi_difensore:
                idx_att = TipoPokemonHelper.ottieni_mappa_tipo_indice(tipo_att)
                idx_dif = TipoPokemonHelper.ottieni_mappa_tipo_indice(tipo_dif)
                moltiplicatore *= cls.matrice_moltiplicatori[idx_att, idx_dif]
            max_eff = max(max_eff, moltiplicatore)
        return float(max_eff)

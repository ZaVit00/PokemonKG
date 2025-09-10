from pprint import pprint
from config.costanti_globali import QUERY_SPARQL_TUTTE_MOSSE
from entita.tipo_pokemon import TipoPokemon
from utils.client_sparql import esegui_query_sparql

class Mossa:
    # Cache interna tipo_mossa -> set di Mossa
    _mappa_mosse_tipo: dict[str, set["Mossa"]] | None = None

    def __init__(self, move, base_power, precisione, pp, tipo_mossa, categoria_mossa):
        """
        Rappresenta una mossa Pokémon.
        """
        self.move = move #uri
        self.base_power = base_power
        self.precisione = precisione
        self.pp = pp
        self.tipo_mossa = tipo_mossa       # es. "URI:Electric"
        self.categoria_mossa = categoria_mossa  # es. "Special", "Physical", "Status"

    def set_base_power(self, base_power):
        self.base_power = base_power

    def __eq__(self, other) -> bool:
        if not isinstance(other, Mossa):
            return False
        # Due mosse sono uguali se hanno lo stesso nome, tipo e categoria
        return (self.move == other.move
                and self.tipo_mossa == other.tipo_mossa
                and self.categoria_mossa == other.categoria_mossa)

    def __hash__(self):
        # Necessario per usare la mossa in set/dizionario e AllDifferentConstraint
        return hash((self.move, self.tipo_mossa))

    def __repr__(self):
        return (
            f"Mossa(move={self.move!r}, basePower={self.base_power!r}, "
            f"accuracy={self.precisione!r}, pp={self.pp!r}, "
            f"tipo_mossa={self.tipo_mossa!r}, categoria_mossa={self.categoria_mossa!r})"
        )

    @classmethod
    def ottieni_mosse_per_tipo(cls, tipo_mossa: str) -> list["Mossa"]:
        """
        Restituisce tutte le mosse di un certo tipo (es. 'Electric').
        Usa cache interna per non interrogare più volte il KG.
        """
        # Funzione annidata: recupera tutte le mosse dal KG
        def _ottieni_mosse_da_kg() -> list["Mossa"]:
            risultati = esegui_query_sparql(QUERY_SPARQL_TUTTE_MOSSE)
            _mosse = []
            for r in risultati:
                move = r.get("move", {}).get("value", "Unknown move")
                base_power = int(r.get("basePower", {}).get("value", 0))
                accuracy = int(r.get("accuracy", {}).get("value", 0))
                pp = int(r.get("pp", {}).get("value", 0))
                tipo = r.get("moveType", {}).get("value", "N/A")
                categoria = r.get("catMove", {}).get("value", "N/A") # special, fisico, status
                _mosse.append(Mossa(move, base_power, accuracy, pp, tipo, categoria))
            return _mosse

        # Se la cache non è inizializzata, popolala
        if cls._mappa_mosse_tipo is None:
            cls._mappa_mosse_tipo = {}
            mosse = _ottieni_mosse_da_kg()

            # Organizza per tipo
            for mossa in mosse:
                tipo = mossa.tipo_mossa
                if tipo not in cls._mappa_mosse_tipo:
                    cls._mappa_mosse_tipo[tipo] = set()
                cls._mappa_mosse_tipo[tipo].add(mossa)

        # Restituisce le mosse del tipo richiesto, o lista vuota
        return list(cls._mappa_mosse_tipo.get(tipo_mossa, []))


if __name__ == "__main__":
    #main di test
    # Esempio: mosse Electric
    mosse_electric = Mossa.ottieni_mosse_per_tipo(TipoPokemon.ELECTRIC.value)
    pprint(mosse_electric)
    print("\n")
    # Esempio: mosse Ice
    mosse_ice = Mossa.ottieni_mosse_per_tipo(TipoPokemon.FAIRY.value)
    pprint(mosse_ice)

import pprint
from dataclasses import dataclass

from config.costanti_globali import URI_MOSSA_CAT_SPECIALE, URI_MOSSA_CAT_FISICO, URI_MOSSA_CAT_STATO, PESI_VALUTAZIONE, Metrica
from entita.mossa import Mossa
from typing import List, Dict

from entita.tipo_pokemon import TipoPokemon
from problemi.battaglia_pokemon.problema_scontro import ValutatoreScontri


@dataclass
class SetMosse:
    mossa1: "Mossa"
    mossa2: "Mossa"
    mossa3: "Mossa"
    mossa4: "Mossa"

    def __post_init__(self):
        self._mosse: List["Mossa"] = [self.mossa1, self.mossa2, self.mossa3, self.mossa4]

        # Metriche aggregate
        self.danno_totale = sum(m.base_power for m in self._mosse)
        self.pp_totali = sum(m.pp for m in self._mosse)
        self.precisione_totale = sum(m.precisione for m in self._mosse)

        # Conteggio per categoria (usando URI)
        self.mosse_per_categoria = {
            URI_MOSSA_CAT_SPECIALE : sum(1 for m in self._mosse if m.categoria_mossa == URI_MOSSA_CAT_SPECIALE),
            URI_MOSSA_CAT_FISICO : sum(1 for m in self._mosse if m.categoria_mossa == URI_MOSSA_CAT_FISICO),
            URI_MOSSA_CAT_STATO : sum(1 for m in self._mosse if m.categoria_mossa == URI_MOSSA_CAT_STATO)
        }

        ## Conteggio per tipo
        tipi_presenti = set(m.tipo_mossa for m in self._mosse)
        self.mosse_per_tipo = {tipo: sum(1 for m in self._mosse if m.tipo_mossa == tipo) for tipo in tipi_presenti}

    def numero_mosse_di_tipo(self, tipo: str) -> int:
        """
        Restituisce il numero di mosse di un certo tipo all'interno del set.
        Se il tipo non è presente, restituisce 0.
        """
        return self.mosse_per_tipo.get(tipo, 0)

    def lista_mosse(self) -> List["Mossa"]:
        return self._mosse

    def ottieni_uri_mosse_tuple(self) -> tuple[str, str, str, str]:
        return (
            self.mossa1.move,
            self.mossa2.move,
            self.mossa3.move,
            self.mossa4.move
        )

    def ottieni_uri_mosse_str(self) -> str:
        return ", ".join(self.ottieni_uri_mosse_tuple())

    def __repr__(self):
        return (
            "SetMosse(\n"
            f"  mossa1: {self.mossa1},\n"
            f"  mossa2: {self.mossa2},\n"
            f"  mossa3: {self.mossa3},\n"
            f"  mossa4: {self.mossa4},\n"
            f"  stats: {{\n"
            f"    danno_totale: {self.danno_totale},\n"
            f"    pp_totali: {self.pp_totali},\n"
            f"    precisione_totale: {self.precisione_totale}\n"
            f"  }},\n"
            f"  mosse_per_categoria: {pprint.pformat(self.mosse_per_categoria, indent=4)},\n"
            f"  mosse_per_tipo: {pprint.pformat(self.mosse_per_tipo, indent=4)}\n"
            ")"
        )

    def valuta_set_mosse(self) -> int:
        return (
                PESI_VALUTAZIONE[Metrica.DANNO_TOTALE] * self.danno_totale +
                PESI_VALUTAZIONE[Metrica.CAT_SPECIALE] * self.mosse_per_categoria.get(URI_MOSSA_CAT_SPECIALE, 0) +
                PESI_VALUTAZIONE[Metrica.TIPO_FIRE] * self.numero_mosse_di_tipo(TipoPokemon.FIRE.value)
        )

    def inizializza_pp_da_mosse(self) -> list[int]:
        pp = []
        for mossa in self.lista_mosse():
            bp = mossa.base_power
            if bp < 90:
                pp.append(10)
            elif 90 <= bp <= 120:
                pp.append(5)
            else:  # basePower > 120
                pp.append(3)
        return pp

    def calcola_moltiplicatori_mosse(self, tipi_avversario: list[str]) -> list[float]:
        """
        Restituisce una lista di moltiplicatori (uno per ogni mossa nel SetMosse),
        calcolati sulla base dell'efficacia del tipo della mossa contro i tipi dell'avversario.
        """
        moltiplicatori = []
        for mossa in self.lista_mosse():
            tipo_attaccante = [mossa.tipo_mossa]  # la funzione `efficienza` si aspetta una lista
            moltiplicatore = ValutatoreScontri.efficienza(tipo_attaccante, tipi_avversario)
            moltiplicatori.append(moltiplicatore)
        return moltiplicatori

    def normalizza_danni_attesi(self):
        """
        Calcola il danno atteso per ciascuna mossa, applica una penalità per danni alti,
        e arrotonda al valore basePower Pokémon più vicino.
        """
        BASE_POWER_STANDARD = [20, 25, 30, 35, 40, 50, 60, 70, 75, 80, 85, 90,
                               95, 100, 110, 120, 130, 140, 150]

        def arrotonda_base_power(valore: float) -> int:
            return min(BASE_POWER_STANDARD, key=lambda x: abs(x - valore))

        for mossa in self.lista_mosse():
            # Danno atteso
            danno_atteso = mossa.base_power * (mossa.precisione / 100)

            # Penalità per mosse con potenza alta
            if mossa.base_power > 100:
                # 0.25 penalità aggiuntiva
                penalita = (mossa.base_power - 100) * 0.25
                danno_atteso -= penalita

            # Arrotondamento al valore standard più vicino
            nuovo_valore = arrotonda_base_power(danno_atteso)
            mossa.basePower = nuovo_valore

    @classmethod
    def somma_danno_totale(cls, set_mosse_list: List["SetMosse"]) -> int:
        """Somma il danno totale di tutti i SetMosse nella lista."""
        return sum(s.danno_totale for s in set_mosse_list)

    @classmethod
    def somma_pp_totali(cls, set_mosse_list: List["SetMosse"]) -> int:
        """Somma i PP totali di tutti i SetMosse nella lista."""
        return sum(s.pp_totali for s in set_mosse_list)

    @classmethod
    def somma_precisione_totale(cls, set_mosse_list: List["SetMosse"]) -> int:
        """Somma la precisione totale di tutti i SetMosse nella lista."""
        return sum(s.precisione_totale for s in set_mosse_list)

    @classmethod
    def mosse_totali_per_categoria(cls, set_mosse_list: List["SetMosse"]) -> Dict[str, int]:
        """
        Restituisce un dizionario che mappa ogni categoria URI
        al numero totale di mosse presenti nella lista di SetMosse.
        """
        result = {URI_MOSSA_CAT_SPECIALE: 0,
                  URI_MOSSA_CAT_FISICO: 0,
                  URI_MOSSA_CAT_STATO: 0}
        for s in set_mosse_list:
            for cat, count in s.mosse_per_categoria.items():
                result[cat] += count
        return result

    @classmethod
    def mosse_totali_per_tipo(cls, set_mosse_list: List["SetMosse"]) -> Dict[str, int]:
        """
        Restituisce un dizionario che mappa ogni tipo al numero totale di mosse
        presenti nella lista di SetMosse.
        """
        result: Dict[str, int] = {}
        for s in set_mosse_list:
            for tipo, count in s.mosse_per_tipo.items():
                result[tipo] = result.get(tipo, 0) + count
        return result


    @classmethod
    def somma_mosse_di_tipo(cls, sets: list["SetMosse"], tipo: str) -> int:
        """
        Restituisce la somma del numero di mosse di un certo tipo in una lista di SetMosse.
        """
        return sum(s.numero_mosse_di_tipo(tipo) for s in sets)

class ValutatoreSetMosse:
    def __init__(self, pesi: dict[Metrica, int]):
        self.pesi = pesi

    def valuta(self, set_mosse: "SetMosse") -> int:
        score = 0

        if Metrica.DANNO_TOTALE in self.pesi:
            score += self.pesi[Metrica.DANNO_TOTALE] * set_mosse.danno_totale

        if Metrica.CAT_SPECIALE in self.pesi:
            score += self.pesi[Metrica.CAT_SPECIALE] * set_mosse.mosse_per_categoria.get(URI_MOSSA_CAT_SPECIALE, 0)

        if Metrica.TIPO_FIRE in self.pesi:
            score += self.pesi[Metrica.TIPO_FIRE] * set_mosse.numero_mosse_di_tipo(TipoPokemon.FIRE.value)
        # altri score possibili implementabili
        return score
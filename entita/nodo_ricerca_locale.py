from config.costanti_globali import PESI_VALUTAZIONE
from entita.set_mosse import SetMosse, ValutatoreSetMosse
import random
from typing import List, Any, Optional
from abc import ABC, abstractmethod
from typing import Any, List

#La classe NodoRicercaLocale implementata è orientata a:
#Problemi di ottimizzazione e Ricerca locale
#nel caso della ricerca pura in spazio di stati è necessario implementare
#un altro nodo. é parzialmente utilizzata per l'assegnazione parziale
class NodoRicercaLocale(ABC):

    """Classe astratta che rappresenta un NodoRicercaLocale generico."""
    @abstractmethod
    def funzione_valutazione(self) -> float:
        """Valutazione del nodo."""
        pass

    @abstractmethod
    def ottieni_vicini(self) -> List["NodoRicercaLocale"]:
        """Genera nodi vicini."""
        pass

    @abstractmethod
    def ottieni_soluzione(self) -> Any:
        """Restituisce la soluzione rappresentata da questo nodo."""
        pass

    def ottieni_rappresentazione_soluzione(self) -> str:
        """
        Ritorna una rappresentazione leggibile della soluzione.
        Override opzionale nei sottotipi.
        """
        return str(self.ottieni_soluzione())

    def __lt__(self, other: "NodoRicercaLocale") -> bool:
        """Un nodo è considerato 'minore' se ha euristica minore"""
        return self.funzione_valutazione() < other.funzione_valutazione()

    def __le__(self, other: "NodoRicercaLocale") -> bool:
        return self.funzione_valutazione() <= other.funzione_valutazione()

    def __eq__(self, other: "NodoRicercaLocale") -> bool:
        return self.funzione_valutazione() == other.funzione_valutazione()

    def completo(self) -> bool:
        # Da utilizzare solo nel caso di assegnazione parziale e non per le ricerche locali
        pass

    def state_key(self):
        pass

class NodoMosseAssegnamentoTotale(NodoRicercaLocale):
    """
    Rappresenta il nodo utilizzato dagli algoritmi di ricerca globale.

    Ogni NodoMosseAssegnamentoTotale descrive un assegnamento completo di sei indici numerici.
    Ogni indice seleziona una quadrupla di mosse (SetMosse) da una delle sottoliste,
    le quali sono state generate dal CSP locale per ciascun Pokémon.
    Il compito del CSP globale è determinare la combinazione di indici che massimizza
    una funzione di valutazione basata esclusivamente su preferenze (vincoli flessibili),
    senza l'applicazione di vincoli rigidi.
    """

    _set_mosse_per_pokemon: list[list[SetMosse]] = [[], [], [], [], [], []]
    # Funzione di valutazione personalizzabile
    _valutatore_set_mossa : "ValutatoreSetMosse"

    @classmethod
    def imposta_valutatore(cls, valutatore: "ValutatoreSetMosse"):
        cls._valutatore_set_mossa = valutatore

    @classmethod
    def imposta_set_mosse_per_pokemon(cls, set_mosse : list[list[SetMosse]]):
        #setto l'attributo di classe
        cls._set_mosse_per_pokemon = set_mosse

    def __init__(self, s0=None, s1=None, s2=None, s3=None, s4=None, s5=None):
        if not self._set_mosse_per_pokemon:
            raise ValueError("set_mosse_per_pokemon non è stato ancora popolato!")

        # Verifica che ci siano esattamente 6 sottoliste
        if len(self._set_mosse_per_pokemon) != 6:
            raise ValueError("set_mosse_per_pokemon deve contenere esattamente 6 sottoliste")

        # Calcola la lunghezza (numero di set disponibili) per ciascun slot disponibile
        self.num_set = [len(mosse) for mosse in self._set_mosse_per_pokemon]

        # Se non vengono passati, genera indici casuali
        self.s0 = s0 if s0 is not None else random.randint(0, self.num_set[0] - 1)
        self.s1 = s1 if s1 is not None else random.randint(0, self.num_set[1] - 1)
        self.s2 = s2 if s2 is not None else random.randint(0, self.num_set[2] - 1)
        self.s3 = s3 if s3 is not None else random.randint(0, self.num_set[3] - 1)
        self.s4 = s4 if s4 is not None else random.randint(0, self.num_set[4] - 1)
        self.s5 = s5 if s5 is not None else random.randint(0, self.num_set[5] - 1)

    def ottieni_set_mosse_selezionati(self) -> list[SetMosse]:
        """Restituisce la lista dei SetMosse selezionati per ciascun Pokémon."""
        indici = [self.s0, self.s1, self.s2, self.s3, self.s4, self.s5]
        set_mosse_selezionati = []  # lista vuota dove metteremo i SetMosse scelti dalla ricerca locale

        for indice_slot, indice_set_mosse in enumerate(indici):
            # Prendo la lista di set di mosse del Pokémon numero_pokemon
            set_possibili = self._set_mosse_per_pokemon[indice_slot]
            # Seleziono il set scelto in base all'indice indicato
            set_scelto = set_possibili[indice_set_mosse]
            # Aggiungo il set selezionato alla lista finale
            set_mosse_selezionati.append(set_scelto)

        return set_mosse_selezionati

    def funzione_valutazione(self) -> int:
        # ValutatoreSetMosse ci consente di variare la funzione di valutazione utilizzata
        cls = type(self)  # oppure self.__class__
        if cls._valutatore_set_mossa is None:
            # fallback: usa PESI_VALUTAZIONE di default
            cls._valutatore_set_mossa = ValutatoreSetMosse(PESI_VALUTAZIONE)

        valutatore = cls._valutatore_set_mossa

        score = 0
        for s in self.ottieni_set_mosse_selezionati():
            score += valutatore.valuta(s)
        return score

    def ottieni_vicini(self) -> list["NodoMosseAssegnamentoTotale"]:
        """
        Genera TUTTI i nodi vicini cambiando un solo set di mosse per slot alla volta.
        Ogni nodo vicino differisce dal nodo corrente per l'indice del set
        selezionato di uno dei 6 Pokémon.
        Sto cambiando i vicini UNO alla volta non insieme
        la complessità è (n-1) + N-1 + n-1..... = 6 * n-1
        """
        vicini = []
        # Raccogliamo gli indici correnti in una lista
        set_correnti = [self.s0, self.s1, self.s2, self.s3, self.s4, self.s5]

        # Ciclo su ciascun Pokémon
        for i in range(len(set_correnti)):
            current_value = set_correnti[i] # valore corrente
            # Provo tutti gli altri set (vario l'indice) disponibili per questo Pokémon
            for nuovo_idx in range(self.num_set[i]):
                # se l'indice è diverso
                if nuovo_idx != current_value:
                    # Copia degli indici correnti
                    nuovi_set = list(set_correnti)
                    # per generare un nodo vicino, cambio solo il set scelto del
                    # Pokémon corrente,
                    # lasciando tutto il resto uguale”
                    nuovi_set[i] = nuovo_idx
                    # Creo una nuova istanza usando i nuovi indici
                    nuovo_nodo = NodoMosseAssegnamentoTotale(*nuovi_set)
                    vicini.append(nuovo_nodo)

        return vicini

    def ottieni_soluzione(self) -> List[SetMosse]:
        """Restituisce la soluzione concreta: i SetMosse selezionati per ciascun Pokémon."""
        return self.ottieni_set_mosse_selezionati()

    def __repr__(self):
        return (f"NodoMosseAssegnamentoTotale(s0={self.s0}, s1={self.s1}, s2={self.s2}, "
                f"s3={self.s3}, s4={self.s4}, s5={self.s5}, euristica={self.funzione_valutazione()})")

    def state_key(self):
        return self.s0, self.s1, self.s2, self.s3, self.s4, self.s5

class NodoMosseAssegnamentoParziale(NodoMosseAssegnamentoTotale):
    """
    NodoRicercaLocale parziale per ricerca con DFS.
    Risoluzione del CSP utilizzando la mappatura in spazi di stati
    Può avere alcuni slot non ancora assegnati (None).
    Eredita da NodoMosseAssegnamentoTotale per riutilizzare funzione di valutazione
    e per la generazione vicini/successori
    """
    def __init__(
        self,
        s0: Optional[int] = None,
        s1: Optional[int] = None,
        s2: Optional[int] = None,
        s3: Optional[int] = None,
        s4: Optional[int] = None,
        s5: Optional[int] = None,
    ):
        # Chiama il costruttore padre per avere num_set, ecc.
        super().__init__(s0, s1, s2, s3, s4, s5)

        # Sovrascrive gli slot direttamente, anche None
        self.s0 = s0
        self.s1 = s1
        self.s2 = s2
        self.s3 = s3
        self.s4 = s4
        self.s5 = s5

    def ottieni_vicini(self) -> List["NodoMosseAssegnamentoParziale"]:
        """
        Override del metodo ereditato per lavorare su assegnazioni parziali
        Trova il primo indice None (non assegnato) ed espande per tutti i valori possibili
        che posso assegnare a quel nodo. L'euristica utilizzata è il primo elemento
        non ancora assegnato dagli un valore (e poi fermati)
        """
        vicini = []
        slot_correnti = [self.s0, self.s1, self.s2, self.s3, self.s4, self.s5]

        # Espandi SOLO il primo slot ancora None
        for i in range(len(slot_correnti)):
            # None => non ancora assegnato
            if slot_correnti[i] is None:
                for nuovo_idx in range(self.num_set[i]):
                    nuovi_slot = list(slot_correnti)
                    nuovi_slot[i] = nuovo_idx
                    vicini.append(NodoMosseAssegnamentoParziale(*nuovi_slot))
                break  # fermati dopo aver assegnato il primo slot libero

        return vicini

    def completo(self) -> bool:
        """Restituisce True se tutti gli slot sono stati assegnati."""
        return None not in [self.s0, self.s1, self.s2, self.s3, self.s4, self.s5]
from collections import deque

from config.costanti_globali import HP_MAX_AVVERSARIO, TURNI_PER_RIPOSO, CURE_TOTALI
from entita.set_mosse import SetMosse
from abc import ABC, abstractmethod
from typing import List, Any

class NodoSpazioStati(ABC):
    """
    Classe astratta per un nodo generico nello spazio degli stati.
    Le ricerche (BFS, DFS, IDDFS...)
    possono lavorare su qualunque nodo che implementa questa interfaccia.
    """

    @abstractmethod
    def is_goal(self) -> bool:
        pass

    @abstractmethod
    def genera_successori(self) -> List["NodoSpazioStati"]:
        pass

    @abstractmethod
    def state_key(self) -> Any:
        """
        Ritorna una rappresentazione hashabile dello stato, utile per pruning o caching.
        """
        pass

    @abstractmethod
    def __repr__(self) -> str:
        pass



class StatoCombattimento(NodoSpazioStati):
    """
        Modella uno stato all'interno di uno spazio di stati per la simulazione
        e pianificazione ottimale di uno scontro Pokémon 1 vs 1, dove l'obiettivo
        è mandare KO l'avversario nel minor numero di turni.

        Ogni stato rappresenta un singolo istante della battaglia, definito da:

        - hp_avversario: HP rimanenti dell'avversario (valore intero)
        - pp: lista dei PP rimanenti per ciascuna delle 4 mosse del proprio Pokémon
        - turni_rimanenti_per_riposo: contatore che decreta ogni quanti turni l’avversario si cura completamente
        - cure_rimaste: numero di cure totali ancora disponibili per l’avversario
        - moltiplicatori: lista dei moltiplicatori di danno applicati a ciascuna mossa, che crescono di +0.5 dopo ogni cura
        - set_mosse: oggetto `SetMosse` contenente le 4 mosse assegnate al proprio Pokémon

        Regole principali del modello:
        --------------------------------
        - Il combattimento inizia con l’avversario a HP massimi (`HP_MAX_AVVERSARIO`), tipicamente 600.
        - Ogni mossa consumata riduce di 1 il relativo PP.
        - Il danno inflitto da una mossa è deterministico: basePower * moltiplicatore corrente.
        - Ogni 4 turni (`TURNI_PER_RIPOSO`), l’avversario si cura completamente (se ha cure disponibili):
            - Gli HP tornano al massimo.
            - Il contatore dei turni viene resettato.
            - Tutti i moltiplicatori aumentano di +0.5.
            - Le cure rimanenti si decrementano.
        - Le mosse con `basePower = 0` (status move) non vengono considerate nei successori (pruning).
        - Il combattimento termina quando `hp_avversario <= 0` (stato goal).
        - Le mosse possono essere utilizzate al massimo due volte consecutivamente.
          Poi siamo costretti a cambiare mossa.
        Utilizzo:
        ---------
        Questa classe è progettata per essere usata all'interno di algoritmi di ricerca sistematica
        (es. DFS, BFS, IDDFS) che esplorano lo spazio degli stati, con l'obiettivo di trovare
        la sequenza ottimale di mosse (piano) per sconfiggere l'avversario.
        La sequenza ottimale è il numero minimo di mosse per sconfiggere l'avversario.
        La DFS e IDDFS si prestano bene a questo scopo, meno la DFS che non è pensata per questo

        È compatibile con l'interfaccia NodoSpazioStati, e può essere usata con strategie di ricerca
        generalizzate, confronto tra percorsi e generazione automatica di soluzioni multiple.

        Nota:
        -----
        - I moltiplicatori iniziali possono essere impostati in base all'efficacia di tipo (es. Fire vs Grass = 2.0).
        - È possibile estendere il modello includendo accuracy, effetti secondari o costi differenti per ogni azione.
        """
    def __init__(
        self,
        hp_avversario: int,
        turni_rimanenti_per_riposo: int,
        cure_totali: int,
        moltiplicatori: list[float],
        pp: list[int],
        set_mosse: SetMosse,
        ultime_mosse_usate: deque = None
    ):
        self.hp_avversario = hp_avversario
        self.pp = pp
        self.turni_rimanenti_per_riposo = turni_rimanenti_per_riposo
        self.cure_rimaste = cure_totali
        self.moltiplicatori = moltiplicatori
        self.set_mosse = set_mosse
        self.ultime_mosse_usate = ultime_mosse_usate or deque(maxlen=2)

    def __repr__(self):
        return (f"StatoCombattimento(HP={self.hp_avversario}, "
                f"PP={self.pp}, Cure={self.cure_rimaste}, "
                f"TurniRiposo={self.turni_rimanenti_per_riposo}, "
                f"Mult={self.moltiplicatori})")

    def copia(self) -> "StatoCombattimento":
        return StatoCombattimento(
            hp_avversario=self.hp_avversario,
            pp=self.pp[:],
            turni_rimanenti_per_riposo=self.turni_rimanenti_per_riposo,
            cure_totali=self.cure_rimaste,
            moltiplicatori=self.moltiplicatori[:],
            set_mosse=self.set_mosse,
            ultime_mosse_usate=deque(self.ultime_mosse_usate, maxlen=2)
        )


    def is_goal(self) -> bool:
        return self.hp_avversario <= 0

    def state_key(self) -> tuple:
        """
        Restituisce una rappresentazione hashabile dello stato per il pruning.
        NOTA: non facciamo pruning su tutti gli stati, ma potremmo usarlo per debug/controlli.
        """
        return (
            self.hp_avversario,
            tuple(self.pp),
            tuple(self.moltiplicatori),
            tuple(self.ultime_mosse_usate),
            self.turni_rimanenti_per_riposo,
            self.cure_rimaste,
        )

    def genera_successori(self) -> List["StatoCombattimento"]:
        successori = []

        for i, mossa in enumerate(self.set_mosse.lista_mosse()):
            # Le due condizioni di pruning:
            # - PP uguali a 0 (non possiamo scendere sotto lo zero)
            # - Base_power = 0 (mossa che non infligge danni, possibile ciclo di mosse senza danno)
            # N.B una mossa che con danno = 0, non crea un ciclo infinito perché prima o poi
            # i pp della mossa termineranno comunque; g
            if self.pp[i] == 0 or mossa.base_power == 0:
                continue  #skip della mossa -> pruning (non genero quello stato)

            # Blocco spam di 3 usi consecutivi della stessa mossa
            # Questo controllo impedisce che venga utilizzata la stessa mossa per più di due
            # volte consecutivamente (al massimo due volte poi devi cambiare)
            # ciò significa che questa mossa verrà saltata in questo step.
            # AL prossimo step potremmo comunque riutilizzare la mossa i
            if list(self.ultime_mosse_usate) == [i, i]:
                continue #pruning della mossa negli stati successori


            danno = int(mossa.base_power * self.moltiplicatori[i]) #danno da calcolare
            nuovo_hp = self.hp_avversario - danno

            nuovi_pp = list(self.pp) #copia esplicita
            nuovi_pp[i] -= 1 # decremento dei pp

            nuovi_moltiplicatori = list(self.moltiplicatori) #copia dei moltiplicatori
            nuove_cure_rimaste = self.cure_rimaste
            nuovo_turni_rimanenti_per_riposo = self.turni_rimanenti_per_riposo - 1
            #aggiorna la struttura dati che contiene l'indice delle mosse usate
            #scartando l'indice della mossa più vecchie
            nuove_ultime_mosse_usate = deque(list(self.ultime_mosse_usate) + [i], maxlen=2)

            #gestione delle cure dell'avversario
            if nuovo_turni_rimanenti_per_riposo == 0 and nuove_cure_rimaste > 0:
                nuovo_hp = HP_MAX_AVVERSARIO #ripristino degli HP
                nuove_cure_rimaste -= 1 #decremento delle cure rimaste
                nuovo_turni_rimanenti_per_riposo = TURNI_PER_RIPOSO #turni fissati in cui avviene il riposo
                # incremento dinamico dinamici dei moltiplicatori
                # più cure ha usato, più aumentiamo
                moltiplicatore_base = 0.5
                boost_aggiuntivo = (CURE_TOTALI- nuove_cure_rimaste) * 0.25
                incremento = moltiplicatore_base + boost_aggiuntivo
                nuovi_moltiplicatori = [x + incremento for x in nuovi_moltiplicatori]

            #nuova istanza da creare (del nodo)
            nuovo_stato = StatoCombattimento(
                hp_avversario=nuovo_hp,
                pp=nuovi_pp,
                turni_rimanenti_per_riposo=nuovo_turni_rimanenti_per_riposo,
                cure_totali=nuove_cure_rimaste,
                moltiplicatori=nuovi_moltiplicatori,
                set_mosse=self.set_mosse,
                ultime_mosse_usate=nuove_ultime_mosse_usate
            )
            #creazione dei successori e aggiunta alla lista da restituire
            successori.append(nuovo_stato)

        return successori



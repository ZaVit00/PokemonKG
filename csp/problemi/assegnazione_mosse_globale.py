# === Solver globale con lista di liste ===
import heapq
import math
import random
import threading
import time
from collections import deque
from copy import deepcopy
from typing import Any, Tuple, Type, List
from ortools.sat.python import cp_model
from config.costanti_globali import URI_MOSSA_CAT_SPECIALE, PESI_VALUTAZIONE, Metrica
from entita.nodo_ricerca_locale import NodoMosseAssegnamentoTotale, NodoRicercaLocale
from entita.set_mosse import SetMosse
from visualizza_risultati import StatisticheRicerca
from entita.tipo_pokemon import TipoPokemon
from utils.registro_log import setup_logger

logger = setup_logger(__name__)

class AssegnatoreMosseGlobale:

    @classmethod
    def or_tools_ottimizza_mosse_globali(cls, set_mosse_per_pokemon: list[list[SetMosse]]) -> tuple[
        list[SetMosse], StatisticheRicerca]:
        stat = StatisticheRicerca("OttimizzazioneGlobale")
        model = cp_model.CpModel()
        variables = []

        for i, sets in enumerate(set_mosse_per_pokemon):
            var = model.NewIntVar(0, len(sets) - 1, f'pokemon_{i}')
            variables.append(var)

        objective_terms = []
        for i, sets in enumerate(set_mosse_per_pokemon):
            for j, set_mosse in enumerate(sets):
                indicator = model.NewBoolVar(f"pokemon_{i}_set_{j}")
                model.Add(variables[i] == j).OnlyEnforceIf(indicator)
                model.Add(variables[i] != j).OnlyEnforceIf(indicator.Not())

                term1 = PESI_VALUTAZIONE[Metrica.CAT_SPECIALE] * set_mosse.mosse_per_categoria[
                    URI_MOSSA_CAT_SPECIALE] * indicator
                term2 = PESI_VALUTAZIONE[Metrica.DANNO_TOTALE] * set_mosse.danno_totale * indicator
                term3 = (PESI_VALUTAZIONE[Metrica.TIPO_FIRE] *
                         set_mosse.numero_mosse_di_tipo(TipoPokemon.FIRE.value)
                         * indicator)

                objective_terms.extend([term1, term2, term3])

        model.Maximize(sum(objective_terms))
        solver = cp_model.CpSolver()

        start_time = time.time()
        status = solver.Solve(model)
        stat.tempo_esecuzione = time.time() - start_time

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            soluzione = [set_mosse_per_pokemon[i][solver.Value(var)] for i, var in enumerate(variables)]
            punteggio_totale = solver.ObjectiveValue()

            # Estrai gli indici scelti per ciascun Pokémon
            s0 = solver.Value(variables[0])
            s1 = solver.Value(variables[1])
            s2 = solver.Value(variables[2])
            s3 = solver.Value(variables[3])
            s4 = solver.Value(variables[4])
            s5 = solver.Value(variables[5])

            # Crea il nodo finale con i 6 indici
            nodo_finale = NodoMosseAssegnamentoTotale(s0=s0, s1=s1, s2=s2, s3=s3, s4=s4, s5=s5)
            stat.set_nodo_finale(nodo_finale)
            stat.aggiungi_valutazione(punteggio_totale)

            return soluzione, stat

        else:
            stat.aggiungi_valutazione(0.0)
            return [], stat

    @classmethod
    def ricerca_sistematica_dfs(cls, nodo_cls: Type[
        "NodoRicercaLocale"]) -> tuple[NodoRicercaLocale, StatisticheRicerca]:
        """
        Ricerca sistematica completa su nodi parziali:
        - parte da un nodo iniziale completamente vuoto (tutti None)
        - esplora ricorsivamente tutti gli assegnamenti completi (DFS)
        - tiene traccia del nodo con punteggio massimo (funzione_valutazione)
        - registra statistiche (numero valutazioni, tempo, nodo finale)
        La profondità dell'albero è fissa: 6 livelli massimi
        """
        stat = StatisticheRicerca("RicercaSistematica+DFS")
        start_time = time.time()

        miglior_valore = float("-inf")  # Valore massimo trovato finora
        nodo_migliore = nodo_cls()  # NodoRicercaLocale corrispondente alla soluzione migliore trovata

        # Per contare nodi massimi
        nodi_massimi_unici = set()
        totali_massimi = 0

        def esplora(nodo_corrente):
            nonlocal miglior_valore, nodo_migliore, totali_massimi

            # Si valuta solo se il nodo è completamente assegnato
            if nodo_corrente.completo():
                valore_corrente = nodo_corrente.funzione_valutazione()
                stat.aggiungi_valutazione(valore_corrente)

                if valore_corrente > miglior_valore:
                    miglior_valore = valore_corrente
                    nodo_migliore = deepcopy(nodo_corrente)  # Evita aliasing
                    # reset dei contatori quando si trova un massimo migliore
                    nodi_massimi_unici.clear()
                    totali_massimi = 0

                if valore_corrente == miglior_valore:
                    totali_massimi += 1
                    nodi_massimi_unici.add(nodo_corrente.state_key())

                return  # Non espandere oltre un nodo completo

            # Espansione dei vicini (prossimi assegnamenti validi)
            for figlio in nodo_corrente.ottieni_vicini():
                esplora(figlio)

        nodo_iniziale = nodo_cls()  # NodoRicercaLocale iniziale con tutti i campi None
        esplora(nodo_iniziale)

        stat.set_nodo_finale(nodo_migliore)
        stat.tempo_esecuzione = time.time() - start_time

        logger.debug(f"Totale nodi con valutazione massima {miglior_valore}: {totali_massimi}")
        logger.debug(f"Nodi unici con valutazione massima: {len(nodi_massimi_unici)}")

        return nodo_migliore, stat


class RicercaLocale:
    @classmethod
    def greedy_ascent_random_step(
            cls, nodo_cls: Type[NodoRicercaLocale], max_passi: int = 200,
            k_restart: int = 20,
            k_no_progress: int = 50
    ) -> Tuple[NodoRicercaLocale, StatisticheRicerca]:
        """
        Ricerca locale con:
        - Greedy Ascent (salita deterministica se trovi un vicino migliore)
        - Random Step (se nessun vicino è migliore)
        - Random Restart (dopo k passi senza miglioramento locale)
        - Stop anticipato se troppi passi senza miglioramento globale

        Args:
            nodo_cls: Classe del nodo (es. NodoMosseAssegnamentoTotale)
            max_passi: Numero massimo di passi totali (hard cap)
            k_restart: Passi senza miglioramento locale → restart
            k_no_progress: Passi senza miglioramento globale → uscita anticipata

        Returns:
            NodoRicercaLocale migliore trovato e statistiche di ricerca
        miglioramento locale → per decidere quando restartare,
        miglioramento globale → per decidere quando interrompere.
        """

        nodo_corrente = nodo_cls()  # NodoRicercaLocale iniziale casuale
        nodo_migliore = deepcopy(nodo_corrente)  # Traccia del miglior nodo globale

        stat = StatisticheRicerca("GreedyAscent+RandomStep")
        stat.aggiungi_valutazione(nodo_corrente.funzione_valutazione())

        passi = 0
        passi_senza_miglioramenti_locali = 0  # Per innescare il restart locale
        passi_senza_miglioramenti_globale = 0  # Per uscita anticipata se stagnazione
        # stagnazione significa che l'algoritmo non sta trovando nuovi massimi locali

        start_time = time.time()

        while passi < max_passi and passi_senza_miglioramenti_globale < k_no_progress:
            vicini = nodo_corrente.ottieni_vicini()
            if not vicini:
                break  # Nessun vicino → fine

            # Trova il migliore tra i vicini
            vicino_migliore = max(vicini, key=lambda n: n.funzione_valutazione())

            if vicino_migliore.funzione_valutazione() > nodo_corrente.funzione_valutazione():
                nodo_corrente = vicino_migliore  # passo greedy
                passi_senza_miglioramenti_locali = 0 #reset del contatore
            else: #accetto un passo peggiorativo perché sono un massimo locale
                nodo_corrente = random.choice(vicini)  # passo random step
                passi_senza_miglioramenti_locali += 1

            valutazione_corrente = nodo_corrente.funzione_valutazione()
            stat.aggiungi_valutazione(valutazione_corrente)

            # Se è il migliore globale → aggiorna e resetta stagnazione globale
            if valutazione_corrente > nodo_migliore.funzione_valutazione():
                nodo_migliore = deepcopy(nodo_corrente)
                passi_senza_miglioramenti_globale = 0
            else:
                passi_senza_miglioramenti_globale += 1

            # Se stagnazione locale → restart
            if passi_senza_miglioramenti_locali >= k_restart:
                nodo_corrente = nodo_cls()
                passi_senza_miglioramenti_locali = 0

            passi += 1

        stat.set_nodo_finale(nodo_migliore)
        stat.tempo_esecuzione = time.time() - start_time
        return nodo_migliore, stat

    @classmethod
    def tabu_search(
            cls,
            nodo_cls: Type[NodoRicercaLocale],
            max_passi: int = 200,
            lunghezza_tabu: int = 10,
            k_no_progress: int = 50,  # Nuovo parametro per stagnazione globale
    ) -> Tuple[NodoRicercaLocale, StatisticheRicerca]:
        """
        Tabu Search con:
        - memoria FIFO per evitare cicli
        - meccanismo di aspiration (accetta anche soluzioni tabù se bloccati)
        - interruzione anticipata in caso di stagnazione globale

        Args:
            nodo_cls: Classe del nodo (es. NodoMosseAssegnamentoTotale)
            max_passi: Numero massimo di iterazioni
            lunghezza_tabu: Lunghezza della lista tabù
            k_no_progress: Numero massimo di passi senza miglioramenti globali

        Returns:
            miglior_nodo: NodoRicercaLocale con valutazione massima trovato
            stat: Statistiche della ricerca
        """

        nodo_corrente = nodo_cls()
        miglior_nodo = deepcopy(nodo_corrente)

        tabu_queue = deque(maxlen=lunghezza_tabu)
        tabu_set = set()

        stat = StatisticheRicerca("TabuSearch")
        stat.aggiungi_valutazione(nodo_corrente.funzione_valutazione())

        passi = 0
        passi_senza_miglioramenti = 0  # Stagnazione globale

        start_time = time.time()

        while passi < max_passi and passi_senza_miglioramenti < k_no_progress:
            vicini = nodo_corrente.ottieni_vicini()
            if not vicini:
                break

            vicini_non_tabu = [v for v in vicini if v.state_key() not in tabu_set]
            if not vicini_non_tabu:
                vicini_non_tabu = vicini  # Aspiration: accetta anche tabù se bloccato

            vicino_migliore = max(vicini_non_tabu, key=lambda n: n.funzione_valutazione())
            nodo_corrente = vicino_migliore
            valutazione_corrente = nodo_corrente.funzione_valutazione()

            # Aggiorna miglior nodo globale se necessario
            if valutazione_corrente > miglior_nodo.funzione_valutazione():
                miglior_nodo = deepcopy(nodo_corrente)
                passi_senza_miglioramenti = 0  # reset stagnazione
            else:
                passi_senza_miglioramenti += 1

            # Aggiorna tabu list
            chiave = nodo_corrente.state_key()
            if chiave not in tabu_set:
                if len(tabu_queue) == tabu_queue.maxlen:
                    chiave_rimossa = tabu_queue.popleft()
                    tabu_set.discard(chiave_rimossa)
                tabu_queue.append(chiave)
                tabu_set.add(chiave)

            stat.aggiungi_valutazione(valutazione_corrente)
            passi += 1

        stat.set_nodo_finale(miglior_nodo)
        stat.tempo_esecuzione = time.time() - start_time
        return miglior_nodo, stat

    @classmethod
    def simulated_annealing(
            cls,
            nodo_cls: Type[NodoRicercaLocale],
            temperatura_iniziale: float = 100.0,
            temperatura_minima: float = 0.1,
            alpha: float = 0.99,
            max_passi: int = 200
    ) -> Tuple[NodoRicercaLocale, StatisticheRicerca]:
        """
        Simulated Annealing con logging nodi con valore massimo.

        - Parte da assegnamento casuale.
        - A ogni passo esplora un vicino casuale.
        - Accetta se migliora, o con probabilità se peggiora.
        - Raffreddamento geometrico: T ← T * alpha
        """
        nodo_corrente = nodo_cls()
        valore_corrente = nodo_corrente.funzione_valutazione()
        nodo_migliore = deepcopy(nodo_corrente)

        T = temperatura_iniziale
        passi = 0
        stat = StatisticheRicerca("SimulatedAnnealing")
        stat.aggiungi_valutazione(valore_corrente)

        start_time = time.time()

        # Per debug statistico su quanti nodi toccano il massimo
        max_val = valore_corrente
        nodi_massimi = []
        nodi_massimi_unici = set()

        while T > temperatura_minima and passi < max_passi:
            vicini = nodo_corrente.ottieni_vicini()
            if not vicini:
                break

            vicino = random.choice(vicini)
            valore_vicino = vicino.funzione_valutazione()
            delta = valore_vicino - valore_corrente

            if delta > 0:
                nodo_corrente = vicino
                valore_corrente = valore_vicino
            else:
                # caso di massimizzazione, quindi il meno non serve
                probabilita = math.exp(delta / T)  # delta < 0 ⇒ P ∈ (0,1)
                if random.random() < probabilita:
                    nodo_corrente = vicino
                    valore_corrente = valore_vicino

            # Statistiche
            stat.aggiungi_valutazione(valore_corrente)

            # Tracciamento del miglior nodo globale
            if valore_corrente > nodo_migliore.funzione_valutazione():
                nodo_migliore = deepcopy(nodo_corrente)

            # Tracciamento nodi che raggiungono il valore massimo
            if valore_corrente > max_val:
                max_val = valore_corrente
                nodi_massimi = [nodo_corrente]
                nodi_massimi_unici = {nodo_corrente.state_key()}
            elif valore_corrente == max_val:
                nodi_massimi.append(nodo_corrente)
                nodi_massimi_unici.add(nodo_corrente.state_key())

            T *= alpha
            passi += 1

        stat.set_nodo_finale(nodo_migliore)
        stat.tempo_esecuzione = time.time() - start_time

        # Logging risultati
        logger.debug(f"[DEBUG] Totale occorrenze valore massimo {max_val}: {len(nodi_massimi)}")
        logger.debug(f"[DEBUG] Nodi unici con valore massimo: {len(nodi_massimi_unici)}")

        return nodo_migliore, stat


    @classmethod
    def beam_search(cls, nodo_cls: Type[NodoRicercaLocale], beam_width: int = 5, max_livelli: int = 6) -> Tuple[
        NodoRicercaLocale, StatisticheRicerca]:
        """
        Beam Search con coda a priorità (heap):
        - beam_width: quanti nodi mantenere a ogni livello
        - max_livelli: quanti livelli esplorare

        Ritorna il miglior nodo trovato e le statistiche.
        """
        stat = StatisticheRicerca("BeamSearch")
        start_time = time.time()

        # Beam iniziale (max-heap con valutazione negativa per simulare max)
        primo_nodo = nodo_cls()
        valutazione_iniziale = primo_nodo.funzione_valutazione()
        heap = [(-valutazione_iniziale, primo_nodo)]

        max_val = valutazione_iniziale
        nodo_migliore = deepcopy(primo_nodo)
        nodi_massimi = [primo_nodo]
        nodi_massimi_unici = {primo_nodo.state_key()}
        stat.aggiungi_valutazione(valutazione_iniziale)

        for _ in range(max_livelli):
            candidati_heap = []

            # Espansione dei nodi nel beam
            for _, nodo in heap:
                vicini = nodo.ottieni_vicini()
                for vicino in vicini:
                    val = vicino.funzione_valutazione()
                    heapq.heappush(candidati_heap, (-val, vicino))

            if not candidati_heap:
                break

            # Seleziona i top beam_width nodi
            heap = heapq.nsmallest(beam_width, candidati_heap)

            for neg_val, nodo in heap:
                val = -neg_val
                stat.aggiungi_valutazione(val)

                if val > max_val:
                    max_val = val
                    nodo_migliore = deepcopy(nodo)
                    nodi_massimi = [nodo]
                    nodi_massimi_unici = {nodo.state_key()}
                elif val == max_val:
                    nodi_massimi.append(nodo)
                    nodi_massimi_unici.add(nodo.state_key())

        stat.set_nodo_finale(nodo_migliore)
        stat.tempo_esecuzione = time.time() - start_time

        print(f"[DEBUG] Totale occorrenze valore massimo {max_val}: {len(nodi_massimi)}")
        print(f"[DEBUG] Nodi unici con valore massimo: {len(nodi_massimi_unici)}")

        return nodo_migliore, stat
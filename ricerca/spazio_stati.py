from collections import deque
from typing import List, Optional
from entita.nodo_stato_combattimento import StatoCombattimento, NodoSpazioStati
from utils.registro_log import setup_logger
logger = setup_logger(__name__)

class RicercaSpazioStati:
    """
    Classe per esplorare lo ricerca con ricerca DFS ricorsiva (senza pruning).
    """

    @classmethod
    def ricerca_dfs(cls, stato_iniziale: NodoSpazioStati, profondita_massima: int = 60) -> Optional[
        List[NodoSpazioStati]]:
        def esplora(stato_corrente: NodoSpazioStati, percorso: List[NodoSpazioStati]) -> Optional[
            List[NodoSpazioStati]]:
            # Interruzione per profondità massima
            if len(percorso) >= profondita_massima:
                return None

            # Condizione di goal
            if stato_corrente.is_goal():
                return percorso + [stato_corrente]

            # Espansione dei successori
            for successore in stato_corrente.genera_successori():
                risultato = esplora(successore, percorso + [stato_corrente])
                if risultato is not None:
                    return risultato

            return None  # Nessun percorso valido

        return esplora(stato_iniziale, [])


    @classmethod
    def ricerca_iddfs(cls, stato_iniziale: NodoSpazioStati, profondita_massima: int = 50,
                      num_percorsi : int = 3) -> List[
        List[NodoSpazioStati]]:
        """
        Versione IDDFS che restituisce le prime num_percorsi soluzioni trovate alla profondità minima.
        """
        #variabile globale
        soluzioni: List[List[NodoSpazioStati]] = []

        def dfs_limitata(stato_corrente: NodoSpazioStati, limite: int, percorso: List[StatoCombattimento]):
            if stato_corrente.is_goal():
                soluzioni.append(percorso + [stato_corrente])
                return #trovata soluzione stop
            if limite == 0 or len(soluzioni) >= num_percorsi:
                return #stop
            for successore in stato_corrente.genera_successori():
                dfs_limitata(successore, limite - 1, percorso + [stato_corrente])
                if len(soluzioni) >= num_percorsi:
                    return  # early stop dopo aver raccolto 3 soluzioni

        #profondità che viene incrementata passo passo
        for profondita in range(profondita_massima + 1):
            dfs_limitata(stato_iniziale, profondita, [])
            if soluzioni:
                # abbiamo trovato almeno una soluzione alla profondità corrente
                break

        return soluzioni

    @classmethod
    def ricerca_bfs(cls, stato_iniziale: NodoSpazioStati, profondita_massima: int = 60,
                    num_percorsi: int = 3) -> List[List[NodoSpazioStati]]:
        """
        BFS: restituisce i primi `num_percorsi` percorsi verso uno stato goal,
        con profondità (numero di mosse) minima garantita.

        - Evita cicli rivedendo i nodi già presenti nel percorso.
        - Limita l'esplorazione a una profondità massima.
        """
        soluzioni: List[List[NodoSpazioStati]] = []
        coda = deque()
        coda.append([stato_iniziale])  # solo il percorso (la testa è il nodo corrente)

        while coda and len(soluzioni) < num_percorsi:
            cammino = coda.popleft()
            nodo = cammino[-1] #estrazione dell'ultimo nodo dalla lista di nodi

            # Condizione di goal
            if nodo.is_goal():
                soluzioni.append(cammino)
                continue

            if len(cammino) >= profondita_massima + 1:
                break  # condizione di interruzione

            # Espansione
            for successore in nodo.genera_successori():
                if successore not in cammino:  # evita cicli
                    nuovo_cammino = cammino + [successore]
                    coda.append(nuovo_cammino)

        return soluzioni
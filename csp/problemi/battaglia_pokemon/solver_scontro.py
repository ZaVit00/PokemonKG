from ortools.linear_solver import pywraplp

class SolverScontro:
    """
    Classe per risolvere l'assegnamento tra due squadre di Pokémon
    basandosi su una matrice di punteggi.
    Offre due strategie:
    - assegnamento ottimale (con programmazione lineare intera, usando OR-Tools)
    - assegnamento greedy (euristica semplice)
    """

    @staticmethod
    def assegnamento_ottimale(matrice_punteggi):
        """
        Trova l'assegnamento ottimale massimizzando il punteggio totale.
        Usa un problema di Programmazione Lineare Intera.
        """
        n = len(matrice_punteggi)  # numero di Pokémon per squadra (dimensione matrice)

        # Creazione del solver con SCIP (uno dei solver supportati da OR-Tools)
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:
            raise RuntimeError("Impossibile creare il solver OR-Tools.")

        # Variabili binarie x[i][j]:
        # x[i][j] = 1 se il Pokémon i della nostra squadra è assegnato
        # contro il Pokémon j dell'altra squadra, 0 altrimenti.
        x = [[solver.IntVar(0, 1, f"x_{i}_{j}") for j in range(n)] for i in range(n)]

        # Vincolo 1: ogni nostro Pokémon (i) deve combattere contro esattamente un avversario
        for i in range(n):
            solver.Add(sum(x[i][j] for j in range(n)) == 1)

        # Vincolo 2: ogni avversario (j) deve combattere contro esattamente un nostro Pokémon
        for j in range(n):
            solver.Add(sum(x[i][j] for i in range(n)) == 1)

        # Funzione obiettivo: massimizzare la somma dei punteggi corrispondenti agli accoppiamenti
        solver.Maximize(
            sum(matrice_punteggi[i][j] * x[i][j] for i in range(n) for j in range(n))
        )

        # Risoluzione del problema
        status = solver.Solve()
        if status != pywraplp.Solver.OPTIMAL:
            raise RuntimeError("Nessuna soluzione ottimale trovata.")

        # Ricostruzione dell'assegnamento dai valori delle variabili binarie
        assegnamento = [-1] * n  # assegnamento[j] = i → il Pokémon j avversario viene affrontato da i
        for i in range(n):
            for j in range(n):
                if x[i][j].solution_value() > 0.5:  # variabile binaria = 1
                    assegnamento[j] = i

        # Calcolo del punteggio totale della soluzione ottimale
        punteggio_totale = solver.Objective().Value()

        return assegnamento, punteggio_totale

    @staticmethod
    def assegnamento_greedy(matrice_punteggi):
        """
        Trova un assegnamento greedy:
        per ogni avversario j, assegna il nostro Pokémon i con il punteggio migliore disponibile.
        """
        n = len(matrice_punteggi)
        assegnamento = [-1] * n  # assegnamento[j] = i
        nostri_usati = set()  # insieme dei Pokémon già usati

        # Per ogni avversario j...
        for j in range(n):
            best_score = float('-inf')
            best_i = -1

            # Trova il PRIMO nostro Pokémon con indice i ancora disponibile con il punteggio massimo
            for i in range(n):
                if i not in nostri_usati and matrice_punteggi[i][j] > best_score:
                    best_score = matrice_punteggi[i][j]
                    best_i = i

            # Assegna il Pokémon scelto all'avversario j
            assegnamento[j] = best_i
            nostri_usati.add(best_i)

        # Calcola il punteggio totale della soluzione greedy
        punteggio_totale = sum(matrice_punteggi[assegnamento[j]][j] for j in range(n))

        return assegnamento, punteggio_totale

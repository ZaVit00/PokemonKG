from typing import List, Optional
from matplotlib import pyplot as plt
import logging
from tabulate import tabulate
from entita.nodo_ricerca_locale import NodoRicercaLocale
from entita.tipo_pokemon import TipoPokemonHelper

logging.getLogger('matplotlib').setLevel(logging.WARNING)

# Contenitore di una singola RUN
class StatisticheRicerca:

    def __init__(self, algoritmo: str):
        self.algoritmo = algoritmo
        self.valori_iterazioni: List[float] = []
        self.iterazioni = 0
        self.nodo_finale: NodoRicercaLocale | None = None
        self.tempo_esecuzione = 0.0

    def aggiungi_valutazione(self, val: float):
        """Registra il valore della funzione euristica in questa iterazione"""
        self.valori_iterazioni.append(val)
        self.iterazioni += 1

    def set_nodo_finale(self, nodo: Optional[NodoRicercaLocale]):
        self.nodo_finale = nodo

    def __repr__(self):
        finale = self.valori_iterazioni[-1] if self.valori_iterazioni else None
        return (f"{self.algoritmo}: valore finale={finale}, "
                f"iterazioni={self.iterazioni}, tempo={self.tempo_esecuzione:.4f}s")

    def plot_valutazioni(self, valore_massimo_assoluto: Optional[float] = None):
        # Linea principale: andamento delle valutazioni
        plt.plot(self.valori_iterazioni, label="Valutazioni nodo", linewidth=0.7)

        # Punto rosso: primo nodo valutato
        if self.valori_iterazioni:
            plt.scatter(0, self.valori_iterazioni[0],
                        color='red', label='Primo nodo', zorder=5)

        # Linea orizzontale: massimo globale trovato dall'algoritmo
        if self.nodo_finale is not None:
            valore_max = self.nodo_finale.funzione_valutazione()
            plt.axhline(valore_max, color='green',
                        linestyle='--', linewidth=1.2,
                        label=f'Massimo trovato ({valore_max:.0f})')

            # Punti verdi: tutti i punti che toccano il massimo trovato
            indici_max = [i for i, v in enumerate(self.valori_iterazioni) if v == valore_max]
            valori_max = [valore_max] * len(indici_max)
            plt.scatter(indici_max, valori_max, color='green', s=20, label='Massimo raggiunto', zorder=4)

            num_max = len(indici_max)
            # Testo nel grafico: quanti picchi massimi sono stati raggiunti
            plt.text(len(self.valori_iterazioni) * 0.02, valore_max + 1,
                     f"Raggiunto {num_max} volta{'e' if num_max != 1 else ''}",
                     color='green', fontsize=9, weight='bold')

        # Se disponibile, mostra il massimo assoluto ottenuto da DFS
        if valore_massimo_assoluto is not None:
            plt.axhline(valore_massimo_assoluto, color='blue',
                        linestyle=':', linewidth=1.5,
                        label=f'Massimo assoluto (DFS: {valore_massimo_assoluto})')

        # Decorazioni grafiche
        plt.xlabel("Ordine di esplorazione (i-esimo nodo)")
        plt.ylabel("Valutazione nodo")
        plt.title(f"Andamento valutazioni - {self.algoritmo}")
        plt.legend(loc="center left", bbox_to_anchor=(1, 0.5))
        plt.tight_layout()
        plt.show()


# Contenitore di più run
class RisultatiEsperimento:
    def __init__(self, massimo_dfs: float):
        """
        Args:
            massimo_dfs: valore massimo trovato dalla DFS, usato come riferimento nel grafico.
            N.B la dfs ci consente di esplorare tutti i possibili elementi del grafo
        """
        self.statistiche: List[StatisticheRicerca] = []
        self.massimo_dfs = massimo_dfs

    def aggiungi(self, stat: StatisticheRicerca):
        self.statistiche.append(stat)

    def aggiungi_tutte(self, lista: List[StatisticheRicerca]):
        """Aggiunge una lista di statistiche"""
        self.statistiche.extend(lista)

    def unisci(self, altro: "RisultatiEsperimento"):
        self.statistiche.extend(altro.statistiche)

    def migliore_esecuzione(self) -> StatisticheRicerca:
        """Restituisce la statistica con nodo finale di valutazione massima"""
        return max(
            self.statistiche,
            key=lambda s: s.nodo_finale.funzione_valutazione() if s.nodo_finale is not None else float('-inf')
        )

    def plot_confronto(self):
        """Plotta l’andamento di tutte le strategie confrontate"""
        for stat in self.statistiche:
            label = stat.algoritmo
            plt.plot(stat.valori_iterazioni, label=label, linewidth=1)

        # Linea orizzontale con massimo trovato dalla DFS
        plt.axhline(
            y=self.massimo_dfs,
            color='green',
            linestyle='--',
            linewidth=1.2,
            label=f'Massimo DFS ({self.massimo_dfs})'
        )

        plt.title("Confronto strategie di ricerca")
        plt.xlabel("Passi / Nodi valutati")
        plt.ylabel("Valutazione")
        plt.legend(loc="center left", bbox_to_anchor=(1, 0.5))
        plt.tight_layout()
        plt.grid(True)
        plt.show()


class VisualizzatoreRisultati:
    """
    Classe contenente metodi statici per visualizzare squadre,
    risultati assegnamenti, matrici punteggi e confronti.
    """

    mappa_pokemon_tipi = TipoPokemonHelper.ottieni_mappa_pokemon_tipi()

    @staticmethod
    def normalizza_uri(uri_pokemon: str) -> str:
        return uri_pokemon.rsplit('/', 1)[-1]

    @classmethod
    def visualizza_squadre_generata(cls, label: str, squadra_pokemon: list[str]) -> None:
        print(f"\n--- {label} ---")
        for i, uri_pokemon in enumerate(squadra_pokemon):
            tipi = cls.mappa_pokemon_tipi.get(uri_pokemon, [])
            tipi_leggibili = "/".join(VisualizzatoreRisultati.normalizza_uri(t) for t in tipi)
            print(f"pokemon_{i}: {uri_pokemon}  →  tipi: {tipi_leggibili if tipi else 'N/D'}")

    @classmethod
    def confronta_assegnamenti(cls, matrice_punteggi, assegnamento1: list[int], assegnamento2: list[int],
                               URI_squadra_nostra: list[str], URI_squadra_avversaria: list[str],
                               label_ass1: str, label_ass2: str) -> None:
        def short(uri: str) -> str:
            return cls.normalizza_uri(uri)

        table = []
        punteggio1 = 0.0
        punteggio2 = 0.0

        for avv_idx, (idx1, idx2) in enumerate(zip(assegnamento1, assegnamento2)):
            avv = short(URI_squadra_avversaria[avv_idx])
            n1 = short(URI_squadra_nostra[idx1])
            n2 = short(URI_squadra_nostra[idx2])

            s1 = matrice_punteggi[idx1][avv_idx]
            s2 = matrice_punteggi[idx2][avv_idx]

            punteggio1 += s1
            punteggio2 += s2

            diff = s2 - s1
            table.append([avv, n1, n2, f"{diff:+.2f}"])

        # Aggiungi i totali
        table.append(["-" * 10, "-" * 10, "-" * 10, "-" * 10])
        table.append(["Totale", f"{punteggio1:.2f}", f"{punteggio2:.2f}", f"{(punteggio2 - punteggio1):+.2f}"])

        headers = ["Avversario", label_ass1, label_ass2, f"Differenza {label_ass2} - {label_ass1}"]

        print("\n📊 Confronto tra assegnamenti\n")
        print(tabulate(table, headers=headers, tablefmt="fancy_grid"))

    @classmethod
    def stampa_set_mosse_per_pokemon(cls, uri_pokemon: list[str],
                                     mosse_per_pokemon: list[list[tuple[str, str, str, str]]]) -> None:
        """
        uri_pokemon: lista di URI dei Pokémon
        mosse_per_pokemon: lista di liste di tuple da 4 URI di mosse
        """
        headers = ["Pokémon", "Set", "Mossa 1", "Mossa 2", "Mossa 3", "Mossa 4", "Totale Set"]
        rows = []

        for idx, uri_pk in enumerate(uri_pokemon):
            nome_pk = cls.normalizza_uri(uri_pk)
            set_mosse = mosse_per_pokemon[idx]
            tot_set = len(set_mosse)

            if not set_mosse:
                rows.append([nome_pk, "—", "—", "—", "—", "—", "0"])
            else:
                for i, quadrupla_uri in enumerate(set_mosse, start=1):
                    # Converte URI → nomi leggibili
                    mosse = [cls.normalizza_uri(uri) for uri in quadrupla_uri]
                    mosse = (mosse + [""] * 4)[:4]
                    nome_cell = nome_pk if i == 1 else ""
                    tot_cell = str(tot_set) if i == 1 else ""
                    rows.append([nome_cell, f"Set {i}"] + mosse + [tot_cell])

            # Riga vuota tra Pokémon
            rows.append([""] * len(headers))

        print("\n Set di mosse generati dal CSP locale (colonne separate per mossa)\n")
        print(tabulate(rows, headers=headers, tablefmt="fancy_grid",
                       colalign=("left", "center", "left", "left", "left", "left", "right")))

    @classmethod
    def stampa_set_mosse_finali(cls, uri_pokemon: list[str],
                                mosse_per_pokemon: list[tuple[str, str, str, str]]) -> None:
        """
        uri_pokemon: lista degli URI dei Pokémon
        mosse_per_pokemon: lista di tuple (mossa1_uri, mossa2_uri, mossa3_uri, mossa4_uri)
            -> già una sola tupla per ciascun Pokémon
        """
        headers = ["Pokémon", "Mossa 1", "Mossa 2", "Mossa 3", "Mossa 4"]
        rows = []

        for uri_pk, tuple_mosse in zip(uri_pokemon, mosse_per_pokemon):
            nome_pk = cls.normalizza_uri(uri_pk)
            mosse_nomi = [cls.normalizza_uri(m) for m in tuple_mosse]
            rows.append([nome_pk] + mosse_nomi)

        print("\n=== Soluzione globale ottimizzata per le mosse ===")
        print("\nAssegnazione delle mosse dal solver globale\n")
        print(tabulate(rows, headers=headers, tablefmt="fancy_grid", colalign=("left", "left", "left", "left", "left")))

    @classmethod
    def visualizza_assegnamento_scontro(cls, titolo: str, assegnamento: list[int], squadra_nostra: list[str],
                                        squadra_avversaria: list[str], matrice_punteggi) -> None:
        print(f"\n--- {titolo.upper()} ---")
        for avv_idx, nostro_idx in enumerate(assegnamento):
            URI_pokemon_avv = cls.normalizza_uri(squadra_avversaria[avv_idx])
            URI_nostro_pokemon = cls.normalizza_uri(squadra_nostra[nostro_idx])
            score = matrice_punteggi[nostro_idx][avv_idx]
            print(f"Avversario {avv_idx}: {URI_pokemon_avv} \t↔ Nostro {URI_nostro_pokemon} (score = {score:.2f} -> {cls._interpreta_score(score)})")

    @staticmethod
    def visualizza_punteggio_finale(label: str, punteggio: float) -> None:
        print(f"Punteggio totale {label.lower()}: {punteggio:.2f}")

    @staticmethod
    def _interpreta_score(score: float) -> str:
        if score >= 1.0:
            return "Fortemente avvantaggiato"
        elif 0.5 <= score < 1.0:
            return "Moderatamente avvantaggiato"
        elif 0.0 < score < 0.5:
            return "Leggermente avvantaggiato"
        elif score == 0.0:
            return "Neutro"
        elif -0.5 < score < 0.0:
            return "Leggermente svantaggiato"
        elif -1.0 < score <= -0.5:
            return "Moderatamente svantaggiato"
        else:
            return "Fortemente svantaggiato"

    @classmethod
    def visualizza_matrice_punteggi(cls, matrice, squadra_nostra: list[str], squadra_avversaria: list[str]) -> None:
        def estrai_nome(uri_pokemon: str) -> str:
            return uri_pokemon.split("/")[-1].split("#")[-1]

        header = [" "] + [estrai_nome(uri) for uri in squadra_avversaria]
        table = []

        for i, uri_mio in enumerate(squadra_nostra):
            row = [estrai_nome(uri_mio)] + [f"{val:.2f}" for val in matrice[i]]
            table.append(row)

        print("\n Matrice dei punteggi di efficacia")
        print("   Cella [i][j] = max_eff(nostro_i → avversario_j) - max_eff(avversario_j → nostro_i)")
        print("   Valore > 0 → vantaggio nostro | Valore < 0 → vantaggio avversario\n")
        print(tabulate(table, headers=header, tablefmt="fancy_grid"))

    @classmethod
    def stampa_statistiche_ricerca(cls, stat: StatisticheRicerca):

        print(f"\n=== Statistiche: {stat.algoritmo} ===")

        # NodoRicercaLocale finale
        if stat.nodo_finale:
            #print("Miglior nodo trovato:")
            #print(stat.nodo_finale.ottieni_rappresentazione_soluzione())
            print(f"Valore funzione obiettivo: {stat.nodo_finale.funzione_valutazione()}")
        else:
            print("Nessuna soluzione trovata.")

        # Metriche di performance
        print(f"Iterazioni totali       : {stat.iterazioni}")
        print(f"Ultimi valori della funzione di valutazione durante la ricerca: {stat.valori_iterazioni[-30:]}")
        print(f"Tempo impiegato (s)     : {stat.tempo_esecuzione:.4f}\n\n")

    @classmethod
    def visualizza_esito_ricerca_spazio_stati(cls, alg_ricerca: str, risultati: dict):
        """
        Visualizza il riepilogo della battaglia per ciascun Pokémon in una tabella formattata.

        Parametri:
        - alg_ricerca: nome dell'algoritmo di ricerca utilizzato
        - risultati: dizionario {indice_pokemon: lista_lunghezze_percorsi_trovati}
        """
        riepilogo = []

        for idx in range(6):
            soluzioni = risultati.get(idx, [])
            if soluzioni:
                riepilogo.append([idx+1, "SI", soluzioni[0]])
            else:
                riepilogo.append([idx+1, "NO", "-"])

        print("\n Riepilogo battaglia per Pokémon:\n")
        print(f"Algoritmo di ricerca utilizzato: {alg_ricerca}\n")

        headers = ["Scontro #", "Soluzione trovata", "Lunghezza"]
        print(tabulate(riepilogo, headers=headers, tablefmt="fancy_grid", stralign="center", numalign="center"))
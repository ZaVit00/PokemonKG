import itertools
from pprint import pprint
from config.costanti_globali import QUERY_SPARQL_TABELLA_MOLTIPLICATORI_DANNI, URI_MOSSA_CAT_SPECIALE, NUM_SET_MOSSE, \
    PESI_VALUTAZIONE, CURE_TOTALI, HP_MAX_AVVERSARIO, TURNI_PER_RIPOSO
from entita.mossa import Mossa
from entita.nodo_ricerca_locale import NodoMosseAssegnamentoTotale, NodoMosseAssegnamentoParziale
from entita.set_mosse import SetMosse, ValutatoreSetMosse
from entita.pokemon import Pokemon
from entita.nodo_stato_combattimento import StatoCombattimento
from entita.tipo_pokemon import TipoPokemonHelper, tipi_strategici_avversario, tipi_strategici, TipoPokemon
from problemi.assegnazione_mosse_globale import AssegnatoreMosseGlobale, RicercaLocale
from problemi.battaglia_pokemon.problema_scontro import ValutatoreScontri
from problemi.generazione_squadra import GeneratoreSquadre
from problemi.assegnazione_mosse_locale import AssegnatoreMosseLocale
from csp.problemi.battaglia_pokemon.solver_scontro import SolverScontro
from ricerca.spazio_stati import RicercaSpazioStati
from utils.registro_log import setup_logger
from visualizza_risultati import VisualizzatoreRisultati, RisultatiEsperimento
from collections import defaultdict
logger = setup_logger(__name__)



def main():
    # 1. Generazione squadre
    #in slot 0, voglio un pokemon con zeri tipi secondari (quindi solo primario)
    #in slot 5, metti come candidati cinque tipi secondari poi ci pensa il solver a scegliere
    MAX_TENTATIVI = 3
    # Poiché i vincoli sui tipi che devono essere assegnati alla squadra
    # sono casuali ci potrebbero essere dei casi in cui abbiamo assegnati combinazioni
    # impossibili.
    # Seppur è un caso raro, evita loop infiniti in caso di vincoli impossibili
    # Creazione Squadra 1
    for _ in range(MAX_TENTATIVI):
        squadra1: list[str] = GeneratoreSquadre.genera_squadra_personale(
            tipi_strategici=TipoPokemonHelper.genera_tipi_strategici([1, 2, 0, 1, 3, 4]),
            squadra_precedente=set()
        )
        if squadra1:
            break
    else:
        raise ValueError("Impossibile generare squadra 1 con i vincoli impostati dopo 10 tentativi.")

    # Squadra 2
    for _ in range(MAX_TENTATIVI):
        squadra2: list[str] = GeneratoreSquadre.genera_squadra_personale(
            tipi_strategici=TipoPokemonHelper.genera_tipi_strategici([2, 3, 1, 0, 3, 0]),
            squadra_precedente=set(squadra1)
        )
        if squadra2:
            break
    else:
        raise ValueError("Impossibile generare squadra 2 con i vincoli impostati dopo 10 tentativi.")

    # Visualizzazione squadre generate
    VisualizzatoreRisultati.visualizza_squadre_generata("Squadra personale 1", squadra1)
    VisualizzatoreRisultati.visualizza_squadre_generata("Squadra personale 2", squadra2)

    # 2. Calcolo matrice punteggi scontro
    # La matrice contiene i moltiplicatori effettivi del nostro Pokémon contro quello avversario.
    # I moltiplicatori in questo caso dipendono solo dal match-up (tipi del nostro Pokémon vs tipi dell’avversario)
    # e non dal danno della mossa per semplificazione.
    # La logica di calcolo dei moltiplicatori segue quella classica dei giochi Pokémon,
    # con la differenza che qui, per semplicità, prima calcoliamo i moltiplicatori
    # e solo successivamente moltiplicheremo il danno della mossa per il moltiplicatore.
    matrice_punteggi = ValutatoreScontri.costruisci_matrice_moltiplicatori_scontri(squadra1, squadra2)
    # Visualizzazione matrice punteggi che abbiamo calcolato
    VisualizzatoreRisultati.visualizza_matrice_punteggi(matrice_punteggi, squadra1, squadra2)

    # 3. Calcolo assegnamenti ottimale e greedy
    """
    L'assegnamento ottimale (ma anche il greedy) sono il miglior modo per ordinare la NOSTRA squadra
    pokemon, fissato l'ordine della squadra avversaria in modo coerente con quanto accade nei giochi.
    l'ordine dipende dalla tabella dei moltiplicatori (che sono slegati dalle mosse come scritto sopra)
    Sostanzialmente l'obiettivo è mettere contro un pokemon di tipo Fuoco della squadra avversaria, 
    un nostro pokemon superefficace. Questo deve essere fatto per tutti i gli scontri. Ci sono due possibilità:
    1) ricerca sistematica in modo da considerare tutte le possibili permutazioni in totale sono 6! = 720
    2) Ricerca greedy: ad ogni passo seleziono il pokemon con il miglior moltiplicatore contro l'avversario
    Non tengo conto del futuro quindi potrei fare un ottimo passo che si rivela un pessimo passo in futuro
    """
    ass_ottimale, punteggio_ass_ottimale = SolverScontro.assegnamento_ottimale(matrice_punteggi)
    ass_greedy, punteggio_ass_greedy = SolverScontro.assegnamento_greedy(matrice_punteggi)

    # 5. Visualizzazione assegnamenti
    VisualizzatoreRisultati.visualizza_assegnamento_scontro("Matchup ottimale", ass_ottimale, squadra1, squadra2, matrice_punteggi)
    VisualizzatoreRisultati.visualizza_punteggio_finale("punteggio assegnamento ottimale", punteggio_ass_ottimale)

    VisualizzatoreRisultati.visualizza_assegnamento_scontro("Matchup greedy", ass_greedy, squadra1, squadra2, matrice_punteggi)
    VisualizzatoreRisultati.visualizza_punteggio_finale("punteggio assegnamento greedy", punteggio_ass_greedy)

    # 6. Confronto assegnamenti
    VisualizzatoreRisultati.confronta_assegnamenti(
        matrice_punteggi,
        assegnamento1=ass_ottimale,
        assegnamento2=ass_greedy,
        label_ass1="assegnamento_ottimale",
        label_ass2="assegnamento_greedy",
        URI_squadra_nostra=squadra1,
        URI_squadra_avversaria=squadra2
    )

    # Squadre ordinate secondo assegnamento
    #la squadra è una lista di stringhe (ogni stringa l'uri identificativo del pokemon nella KG
    # l'assegnamento ottimale produce una sequenza di interi che corrispondono alle posizioni
    # dei nostri pokemon e squadra1 ordinata contiene gli uri inseriti nelle posizioni secondo
    # l'ordine di indici fornito dal solver
    squadra1_ordinata_ottimale : list[str] = [squadra1[i] for i in ass_ottimale]
    VisualizzatoreRisultati.visualizza_squadre_generata("Squadra 1 ordinata secondo assegnamento ottimale", squadra1_ordinata_ottimale)

    squadra1_ordinata_greedy : list[str] = [squadra1[i] for i in ass_greedy]
    VisualizzatoreRisultati.visualizza_squadre_generata("Squadra 1 ordinata secondo assegnamento greedy", squadra1_ordinata_greedy)

    # === PARTE DUE => Generazione dei set di mosse (quadruple) per ogni Pokémon ===

    # Lista di liste: ogni sottolista corrisponde a un Pokémon, posizione fissa
    # In ogni sottolista ci sono i SetMosse possibili (fino a NUM_SET_MOSSE)
    # L'ordine delle sottoliste rappresenta implicitamente l'ordine dei pokemon nella squadra
    set_mosse_per_pokemon: list[list[SetMosse]] = [[], [], [], [], [], []]

    # Ciclo su ogni Pokémon secondo l'ordine prefissato della squadra
    for idx, uri_pokemon in enumerate(squadra1_ordinata_ottimale):
        tipi: list[str] = TipoPokemonHelper.ottieni_tipi_pokemon(uri_pokemon)
        tipo1 = tipi[0]  # primo tipo
        tipo2 = tipi[1] if len(tipi) > 1 else None  # secondo tipo se presente
        # evita duplicati di mosse tra gli stessi set di mosse
        # di un pokemon
        mosse_assegnate_locali = set()

        # Genera NUM_SET_MOSSE combinazioni di mosse per CIASCUN Pokémon
        # Sostanzialmente stiamo generando attraverso il CSP locale delle quadruple di mosse
        # La scelta di quale quadrupla verrà effettivamente scelta dipende dal CSP globale
        for _ in range(NUM_SET_MOSSE):
            try:
                mosse: list[Mossa] = AssegnatoreMosseLocale.genera_mosse(
                    mosse_assegnate_locali, tipo1=tipo1, tipo2=tipo2
                )
            except ValueError as e:
                # Interrompiamo il ciclo se non è possibile generare un set valido
                logger.warning(f"⚠️ Errore nella generazione delle mosse per {tipo1}, {tipo2}: {e}")
                break

            # Aggiunge la quadrupla di mosse alla lista del Pokémon
            # con idx riusciamo a mantenere l'ordine naturale
            set_mosse_per_pokemon[idx].append(SetMosse(*mosse))
            # Aggiorna il set globale per evitare duplicati tra le mosse dello
            # STESS
            mosse_assegnate_locali.update(mosse)

    uri_set_mosse = []
    for lista_set in set_mosse_per_pokemon:
        mosse_pk = [s.ottieni_uri_mosse_tuple() for s in lista_set]
        uri_set_mosse.append(mosse_pk)

    VisualizzatoreRisultati.stampa_set_mosse_per_pokemon(squadra1_ordinata_ottimale, uri_set_mosse)

    # Ottimizzazione globale delle mosse con OR Tools (CSP globale)
    # mosse globali: lista di setMosse. Ogni sottolista di indice i
    # corrisponde al pokemon i
    """
    Obiettivo: Ogni pokemon avrà un insieme fisso per ciascuno di quadruple di mosse.
    Vogliamo assegnare le quadruple a ciascun pokemon (esattamente una per pokemon)
    in modo da massimizzare una funzione di qualità definita da noi.
    La funzione di qualità è definita globalmente quindi vogliamo l'assegnamento TOTALE di quadruple
    per tutti i pokemon che massimizza la funzione di guadagno. In primis utilizziamo il solver di OR tools che siamo sicuri
    ci dia la soluzione migliore in modo efficiente. Proviamo poi una ricerca sistematica utilizzando la DFS e poi metodi
    di ricerca locale per risolvere il problema di ottimizzazione.
    """
    mosse_globali, stat_or_tools = AssegnatoreMosseGlobale.or_tools_ottimizza_mosse_globali(set_mosse_per_pokemon)
    if not mosse_globali:
        raise ValueError("[WARNING] Nessun ordinamento che massimizza la funzione di guadagno per"
                         "le mosse trovate")
    # Stampa della soluzione globale e creazione degli oggetti Pokémon
    pokemon_team = []
    for i, set_mosse in enumerate(mosse_globali):
        uri = squadra1_ordinata_ottimale[i]
        #print(f"{uri}: {set_mosse}\n")  # stampa la quadrupla di mosse
        # Ottieni i tipi del Pokémon
        tipi: list[str] = TipoPokemonHelper.ottieni_tipi_pokemon(uri)
        tipo1 = tipi[0]
        tipo2 = tipi[1] if len(tipi) > 1 else None
        # Crea l'oggetto Pokémon con le mosse selezionate
        pokemon = Pokemon(
            uri=uri,
            tipo1=tipo1,
            tipo2=tipo2,
            set_mosse= SetMosse(*set_mosse.lista_mosse())
        )
        pokemon_team.append(pokemon)
    VisualizzatoreRisultati.stampa_set_mosse_finali(squadra1_ordinata_ottimale,
                                                    [m.ottieni_uri_mosse_tuple() for m in mosse_globali])
    print("Creazione della squadra pokemon con mosse assegnate")
    pprint(pokemon_team)

    #=== PARTE RICERCA LOCALE ===#
    """
    Anziché provare una ricerca sistematica per trovare tutte l'assegnazione globale di indici che massimizza
    le statistiche finali per del set di mosse per ogni pokemon 
    possiamo utilizzare la ricerca locale. In questo caso si tratta di un problema di massimizzazione
    perché vogliamo l'assegnamento totale di mosse che massimizza la funzione 
    """
    #Definizione degli attributi di classe condivisi tra tutte le istanze
    NodoMosseAssegnamentoTotale.imposta_set_mosse_per_pokemon(set_mosse_per_pokemon)
    # Funzione di valutazione custom definita
    NodoMosseAssegnamentoTotale.imposta_valutatore(ValutatoreSetMosse(PESI_VALUTAZIONE))

    # Metodo standard per risolvere un CSP: una ricerca DFS che esplora tutte le possibili assegnamenti e
    # si memorizza il migliore.
    # Prima di utilizzare la ricerca locale capiamo quanti massimi globali
    # sono presenti. A differenza della ricerca locale sappiamo che la DFS lavora su assegnamenti parziali
    # e non su assegnazioni totali come i classici metodi di ricerca locale.
    # Attenzione il numero di nodi è esponenziale. La profondità dell'albero è fissa ovvero 6, ma ogni nodo
    # può generare num_set figli. Quindi O(num_set^6) complessità temporale dell'algoritmo che deve
    # necessariamente arrivare alla profondità 6 per verificare se l'assegnamento totale è un miglioramento o meno
    # si tratta di un approccio a forza bruta per trovare l'assegnamento totale migliore che esplora l'intero spazio
    # delle soluzioni possibili per trovare quella che massimizza la funzione di valutazione
    print("\n\n[RICERCA SISTEMATICA COMPLETA] DFS")
    nodo_finale_dfs, stats_dfs = AssegnatoreMosseGlobale.ricerca_sistematica_dfs(NodoMosseAssegnamentoParziale)
    VisualizzatoreRisultati.stampa_statistiche_ricerca(stats_dfs)
    stats_dfs.plot_valutazioni()

    max_valore_f_valutazione_dfs = stats_dfs.nodo_finale.funzione_valutazione()

    print("\n\n[RICERCA LOCALE] Greedy Ascent + Random Step")
    nodo_finale_locale, stats_greedy = RicercaLocale.greedy_ascent_random_step(NodoMosseAssegnamentoTotale, max_passi=200, k_restart=10)
    VisualizzatoreRisultati.stampa_statistiche_ricerca(stats_greedy)
    stats_greedy.plot_valutazioni(max_valore_f_valutazione_dfs)

    print("\n\n[RICERCA LOCALE] Tabu Search")
    nodo_finale_tabu, stats_tabu = RicercaLocale.tabu_search(NodoMosseAssegnamentoTotale, max_passi=200)
    VisualizzatoreRisultati.stampa_statistiche_ricerca(stats_tabu)
    stats_tabu.plot_valutazioni(max_valore_f_valutazione_dfs)

    print("\n\n[RICERCA LOCALE] Simulated Annealing Search")
    nodo_finale_simulated_annealing, stats_sim_ann = RicercaLocale.simulated_annealing(NodoMosseAssegnamentoTotale, max_passi=200)
    VisualizzatoreRisultati.stampa_statistiche_ricerca(stats_sim_ann)
    stats_sim_ann.plot_valutazioni(max_valore_f_valutazione_dfs)

    print("\n\n[RICERCA LOCALE] Beam Search")
    nodo_finale_beam_search, stats_beam_search = RicercaLocale.beam_search(NodoMosseAssegnamentoTotale)
    VisualizzatoreRisultati.stampa_statistiche_ricerca(stats_beam_search)
    stats_beam_search.plot_valutazioni(max_valore_f_valutazione_dfs)

    print("\nConfronto valori finali delle strategie:")
    for stats in [stats_greedy, stats_tabu, stats_dfs, stat_or_tools, stats_sim_ann, stats_beam_search]:
        print(
            f"- {stats.algoritmo}: valore massimo trovato = "
            f"{stats.nodo_finale.funzione_valutazione()},"
            f" tempo = {stats.tempo_esecuzione:.4f}s")

    rs = RisultatiEsperimento(max_valore_f_valutazione_dfs)
    rs.aggiungi_tutte([stats_greedy, stats_tabu, stats_sim_ann, stats_beam_search])
    rs.plot_confronto()

    print("\n" * 3)
    print("=== RICERCA 1-VS-1: OGNI POKÉMON CON IL RISPETTIVO AVVERSARIO ===")
    risultati_iddfs = defaultdict(list)

    for i in range(6):
        pk_nostro = pokemon_team[i]
        uri_pokemon_avversario = squadra2[i]

        print(f"\n--- ⚔️ Scontro {i + 1}: {pk_nostro.uri} vs {uri_pokemon_avversario} ---")
        # Preparazione dati
        pk_nostro.set_mosse.normalizza_danni_attesi()
        pp_iniziali = pk_nostro.set_mosse.inizializza_pp_da_mosse()
        tipi_avversario = TipoPokemonHelper.ottieni_tipi_pokemon(uri_pokemon_avversario)
        moltiplicatori = pk_nostro.set_mosse.calcola_moltiplicatori_mosse(tipi_avversario)

        print("\nMosse a disposizione con PP originali:")
        # Attenzione i PP delle mosse vengono modificati esternamente.
        # In questo modo evitiamo di modificare i pp originali delle mosse
        pprint(pk_nostro.set_mosse.lista_mosse())
        #print(f"- Tipi delle nostre mosse: {SetMosse.mosse_totali_per_tipo([pk_nostro.set_mosse])}")
        #print(f"- Tipi nostro: {pk_nostro.lista_tipi()}")
        print(f"- Tipi avversario: {tipi_avversario}")
        print(f"- Moltiplicatori calcolati tenendo conto tipi avversario: {moltiplicatori}")
        print(f"- PP di partenza  {pp_iniziali}\n")

        # Stato iniziale
        stato_iniziale = StatoCombattimento(
            hp_avversario=HP_MAX_AVVERSARIO,
            pp=pp_iniziali,
            turni_rimanenti_per_riposo= TURNI_PER_RIPOSO,
            cure_totali= CURE_TOTALI,
            moltiplicatori=moltiplicatori,
            set_mosse=pk_nostro.set_mosse
        )

        # Ricerca IDDFS
        # AL più un limite superiore ai PP è rappresentato da un 40 (fissato da codice)
        # ma già una soluzione con profondità di mosse 18 la possiamo scartare
        #in quanto sicuramente poco efficiente
        percorsi_iddfs = RicercaSpazioStati.ricerca_iddfs(
            stato_iniziale,
            profondita_massima=18,
            num_percorsi=1 # Numero di percorsi che vogliamo trovare. Se = 1 ci basta la prima soluzione
        )

        if percorsi_iddfs:
            print(f"✅ IDDFS ha trovato {len(percorsi_iddfs)} percorso/i.")
            for j, percorso in enumerate(percorsi_iddfs, 1):
                num_mosse = len(percorso) - 1 # -1 perché c'è lo stato iniziale
                # salva il numero di mosse per il Pokémon i
                risultati_iddfs[i].append(num_mosse)
                print(f"\n🔁 Percorso soluzione {j} (KO in {num_mosse} mosse):")
                for turno, stato in enumerate(percorso):
                    print(f"Turno {turno}: {stato}")
        else:
            print("❌ IDDFS: Nessuna soluzione trovata.")

    VisualizzatoreRisultati.visualizza_esito_ricerca_spazio_stati(risultati=risultati_iddfs, alg_ricerca="IDDFS")
# # Ricerca BFS
# percorsi_bfs = RicercaSpazioStati.ricerca_bfs(
#     stato_iniziale,
#     profondita_massima=60,
#     num_percorsi=2
# )

# if percorsi_bfs:
#     print(f"✅ BFS ha trovato {len(percorsi_bfs)} percorso/i.")
#     for j, percorso in enumerate(percorsi_bfs, 1):
#         print(f"  Soluzione {j}: KO in {len(percorso) - 1} mosse")
# else:
#     print("❌ BFS: Nessuna soluzione trovata.")

if __name__ == "__main__":
    main()

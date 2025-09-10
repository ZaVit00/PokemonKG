import pandas as pd

from config.costanti_globali import OUTPUT_TABELLA_MOLTIPLICATORI, FILE_CSV_TABELLA_MOLTIPLICATORI


def main():
    """
    Legge un file CSV con la tabella dei moltiplicatori (18x18)
    e genera un file N-Quads con relazioni reificate:
    - moveType (tipo della mossa)
    - targetType (tipo del Pokémon difensore)
    - damageMultiplierValue (valore numerico)
    Tutti i quad hanno come grafo: <https://pokemonkg.org/dataset/bulbapedia>
    perché sono presi da questa fonte
    """
    SOURCE_GRAPH = "<https://pokemonkg.org/dataset/bulbapedia>"

    # Carica la tabella dal CSV (prima colonna = index)
    df = pd.read_csv(FILE_CSV_TABELLA_MOLTIPLICATORI, index_col=0)

    lines = []
    rel_counter = 1
    for move_uri, row in df.iterrows():
        for target_uri, multiplier in row.items():
            relation_uri = f"<https://pokemonkg.org/instance/damageRel_{rel_counter:03d}>"
            lines.append(
                f"{relation_uri} <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://pokemonkg.org/ontology#DamageMultiplierRelation> {SOURCE_GRAPH} .")
            lines.append(f"{relation_uri} <https://pokemonkg.org/ontology#moveType> <{move_uri}> {SOURCE_GRAPH} .")
            lines.append(f"{relation_uri} <https://pokemonkg.org/ontology#targetType> <{target_uri}> {SOURCE_GRAPH} .")
            lines.append(
                f"{relation_uri} <https://pokemonkg.org/ontology#damageMultiplierValue> \"{multiplier}\"^^<http://www.w3.org/2001/XMLSchema#decimal> {SOURCE_GRAPH} .")
            rel_counter += 1

    with open(OUTPUT_TABELLA_MOLTIPLICATORI, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("File damage_multipliers.nq generato con successo!")


if __name__ == "__main__":
    main()

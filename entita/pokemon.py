from dataclasses import dataclass
from typing import Optional, List
from entita.set_mosse import SetMosse



@dataclass
class Pokemon:
    uri: str
    tipo1: str
    tipo2: Optional[str] # il secondo tipo può essere assente per un dato pokemon
    set_mosse : "SetMosse"

    def __init__(self, uri: str, tipo1: str, tipo2: Optional[str],
                 set_mosse: SetMosse):
        self.uri = uri
        self.tipo1 = tipo1
        self.tipo2 = tipo2
        self.set_mosse = set_mosse

    def lista_tipi(self) -> List[str]:
        """Restituisce una lista con i tipi del Pokémon."""
        return [self.tipo1] if self.tipo2 is None else [self.tipo1, self.tipo2]


    def __repr__(self) -> str:
        tipi_str = "/".join(self.lista_tipi())
        return f"Pokemon({self.uri}, Tipi: {tipi_str},\n Mosse:\n  {self.set_mosse} \n)"

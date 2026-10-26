from dataclasses import dataclass, field

from BackEnd.objects.sharing import Move


@dataclass
class SearchResult:
    algorithm: str
    status: str
    actions: list[Move] = field(default_factory=list)
    expanded_nodes: int | None = 0
    search_time_s: float = 0.0
    peak_memory_bytes: int | None = None
    message: str = ""

    @property
    def path_cost(self) -> int | None:
        if self.status == "solved":
            return len(self.actions)
        return None

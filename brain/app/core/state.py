from dataclasses import dataclass, field


class Status:
    STARTING = "starting"
    READY = "ready"
    ERROR = "error"


@dataclass
class ServerState:
    status: str = Status.STARTING
    loaded: list[str] = field(default_factory=list)  # models loaded so far
    error: str | None = None

    def mark_loaded(self, name: str) -> None:
        self.loaded.append(name)

    def mark_ready(self) -> None:
        self.status = Status.READY

    def mark_error(self, msg: str) -> None:
        self.status = Status.ERROR
        self.error = msg

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "loaded": self.loaded,
            **({"error": self.error} if self.error else {}),
        }


# Single shared instance imported everywhere
state = ServerState()

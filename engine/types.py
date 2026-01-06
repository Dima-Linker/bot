from dataclasses import dataclass, asdict
from typing import Literal, Optional

Direction = Literal['long', 'short', 'both']
Strength = Literal['weak', 'medium', 'strong', 'elite']


@dataclass
class FeatureResult:
    module: str
    symbol: str
    timeframe: str
    candle_ts: int
    direction: Direction
    strength: Strength
    score: int
    reasons: list[str]
    levels: Optional[dict] = None
    tags: Optional[list[str]] = None

    def to_dict(self) -> dict:
        return asdict(self)
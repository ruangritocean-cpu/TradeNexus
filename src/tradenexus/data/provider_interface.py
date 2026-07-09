from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Optional

class DataProvider(ABC):
    """
    Abstract interface for all TradeNexus data providers.
    """
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Returns the unique identifier name of the provider.
        """
        pass

    @property
    @abstractmethod
    def supported_intervals(self) -> List[str]:
        """
        Returns a list of supported timeframe intervals (e.g. ['15m', '1h', '1d']).
        """
        pass

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        period: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetches historical price data.
        Returns a pandas DataFrame with normalized columns.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Performs a ping or query to verify if the provider is operational.
        """
        pass

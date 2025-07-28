"""
OpenSky Network Data Source for Apache Spark - Academic/Private Use Example

This module provides a custom Spark data source for streaming real-time aircraft tracking data from the OpenSky Network API (https://opensky-network.org/). The OpenSky Network is a community-based receiver network that collects air traffic surveillance data and makes it available as open data to researchers and enthusiasts.

Features:
- Real-time streaming of aircraft positions, velocities, and flight data
- Support for multiple geographic regions (Europe, North America, Asia, etc.)
- OAuth2 authentication for higher API rate limits (4000 vs 100 calls/day)
- Robust error handling with automatic retries and rate limiting
- Data validation and type-safe parsing of aircraft state vectors
- Configurable bounding boxes for focused data collection

Usage Example (Academic/Research):
    # Basic usage with region NORTH_AMERICA
    df = spark.readStream.format("opensky").load()
    
    # With specific region and authentication
    df = spark.readStream.format("opensky") \
        .option("region", "EUROPE") \
        .option("client_id", "your_research_client_id") \
        .option("client_secret", "your_research_client_secret") \
        .load()

Data Schema:
    Each record contains comprehensive aircraft information including position (lat/lon),altitude, velocity, heading, call sign, ICAO identifier, and various flight status flags. All timestamps are in UTC timezone for consistency.

Feed your own data to OpenSky Network https://opensky-network.org/feed

Rate Limits & Responsible Usage:
    - Anonymous access: 100 API calls per day
    - Authenticated access: 4000 API calls per day (research accounts)
    - Minimum 5-second interval between requests
    - 8000 API calls if you feed your own data to the OpenSky Network feed (https://opensky-network.org/feed)

Data Attribution:
    When using this data in research or publications, please cite:
    "The OpenSky Network, https://opensky-network.org"

Author: Frank Munz, Databricks  - Example Only, No Warranty
Purpose: Educational Example / Academic Research Tool
Version: 1.0
Last Updated: July-2025

================================================================================
LEGAL NOTICES & TERMS OF USE

USAGE RESTRICTIONS:
- Academic research and educational purposes only
- Commercial use requires explicit permission from OpenSky Network
- Must comply with OpenSky Network Terms of Use: https://opensky-network.org/about/terms-of-use

If you create a publication (including web pages, papers published by a third party, and publicly available presentations) using data from the OpenSky Network data set, you should cite the original OpenSky paper as follows:

Matthias Schäfer, Martin Strohmeier, Vincent Lenders, Ivan Martinovic and Matthias Wilhelm.
"Bringing Up OpenSky: A Large-scale ADS-B Sensor Network for Research".
In Proceedings of the 13th IEEE/ACM International Symposium on Information Processing in Sensor Networks (IPSN), pages 83-94, April 2014.


DISCLAIMER & LIABILITY:
This code is provided "AS IS" for educational purposes only. The author and Databricks make no warranties, express or implied, and disclaim all liability for any damages, losses, or issues arising from the use of this code. Users assume full responsibility for compliance with all applicable terms of service, laws, and regulations. Use at your own risk.

For commercial use, contact OpenSky Network directly.
================================================================================


"""


import requests
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional, Iterator
from dataclasses import dataclass
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from enum import Enum

from pyspark.sql.datasource import SimpleDataSourceStreamReader, DataSource
from pyspark.sql.types import *

DS_NAME = "opensky"

@dataclass
class BoundingBox:
    lamin: float  # Minimum latitude
    lamax: float  # Maximum latitude
    lomin: float  # Minimum longitude
    lomax: float  # Maximum longitude

class Region(Enum):
    EUROPE = BoundingBox(35.0, 72.0, -25.0, 45.0)
    NORTH_AMERICA = BoundingBox(7.0, 72.0, -168.0, -60.0)
    SOUTH_AMERICA = BoundingBox(-56.0, 15.0, -90.0, -30.0)
    ASIA = BoundingBox(-10.0, 82.0, 45.0, 180.0)
    AUSTRALIA = BoundingBox(-50.0, -10.0, 110.0, 180.0)
    AFRICA = BoundingBox(-35.0, 37.0, -20.0, 52.0)
    GLOBAL = BoundingBox(-90.0, 90.0, -180.0, 180.0)

class OpenSkyAPIError(Exception):
    """Base exception for OpenSky API errors"""
    pass

class RateLimitError(OpenSkyAPIError):
    """Raised when API rate limit is exceeded"""
    pass

class OpenSkyStreamReader(SimpleDataSourceStreamReader):
    
    DEFAULT_REGION = "NORTH_AMERICA"
    MIN_REQUEST_INTERVAL = 5.0  # seconds between requests
    ANONYMOUS_RATE_LIMIT = 100  # calls per day
    AUTHENTICATED_RATE_LIMIT = 4000  # calls per day
    MAX_RETRIES = 3
    RETRY_BACKOFF = 2
    RETRY_STATUS_CODES = [429, 500, 502, 503, 504]
    
    def __init__(self, schema: StructType, options: Dict[str, str]):
        super().__init__()
        self.schema = schema
        self.options = options
        self.session = self._create_session()
        self.last_request_time = 0
        
        region_name = options.get('region', self.DEFAULT_REGION).upper()
        try:
            self.bbox = Region[region_name].value
        except KeyError:
            print(f"Invalid region '{region_name}'. Defaulting to {self.DEFAULT_REGION}.")
            self.bbox = Region[self.DEFAULT_REGION].value
        
        self.client_id = options.get('client_id')
        self.client_secret = options.get('client_secret')
        self.access_token = None
        self.token_expires_at = 0
        
        if self.client_id and self.client_secret:
            self._get_access_token()  # OAuth2 authentication
            self.rate_limit = self.AUTHENTICATED_RATE_LIMIT
        else:
            self.rate_limit = self.ANONYMOUS_RATE_LIMIT

    def _get_access_token(self):
        """Get OAuth2 access token using client credentials flow"""
        current_time = time.time()
        if self.access_token and current_time < self.token_expires_at:
            return  # Token still valid
            
        token_url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()
            
            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 1800)
            self.token_expires_at = current_time + expires_in - 300
            
        except requests.exceptions.RequestException as e:
            raise OpenSkyAPIError(f"Failed to get access token: {str(e)}")

    def _create_session(self) -> requests.Session:
        """Create and configure requests session with retry logic"""
        session = requests.Session()
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=self.RETRY_BACKOFF,
            status_forcelist=self.RETRY_STATUS_CODES
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def initialOffset(self) -> Dict[str, int]:
        return {'last_fetch': 0}

    def _handle_rate_limit(self):
        """Ensure e MIN_REQUEST_INTERVAL seconds between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.MIN_REQUEST_INTERVAL:
            sleep_time = self.MIN_REQUEST_INTERVAL - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def _fetch_states(self) -> requests.Response:
        """Fetch states from OpenSky API with error handling"""
        self._handle_rate_limit()
        
        if self.client_id and self.client_secret:
            self._get_access_token()
        
        params = {
            'lamin': self.bbox.lamin,
            'lamax': self.bbox.lamax,
            'lomin': self.bbox.lomin,
            'lomax': self.bbox.lomax
        }
        
        headers = {}
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        try:
            response = self.session.get(
                "https://opensky-network.org/api/states/all",
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 429:
                raise RateLimitError("API rate limit exceeded")
            response.raise_for_status()
            
            return response
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            if isinstance(e, requests.exceptions.Timeout):
                error_msg = "API request timed out"
            elif isinstance(e, requests.exceptions.ConnectionError):
                error_msg = "Connection error occurred"
            raise OpenSkyAPIError(error_msg) from e

    def valid_state(self, state: List) -> bool:
        """Validate state data"""
        if not state or len(state) < 17:
            return False
        
        return (state[0] is not None and  # icao24
                state[5] is not None and  # longitude
                state[6] is not None)     # latitude

    def parse_state(self, state: List, timestamp: int) -> Tuple:
        """Parse state data with safe type conversion"""
        def safe_float(value: Any) -> Optional[float]:
            try:
                return float(value) if value is not None else None
            except (ValueError, TypeError):
                return None

        def safe_int(value: Any) -> Optional[int]:
            try:
                return int(value) if value is not None else None
            except (ValueError, TypeError):
                return None

        def safe_bool(value: Any) -> Optional[bool]:
            return bool(value) if value is not None else None

        return (
            datetime.fromtimestamp(timestamp, tz=timezone.utc),
            state[0],  # icao24
            state[1],  # callsign
            state[2],  # origin_country
            datetime.fromtimestamp(state[3], tz=timezone.utc),
            datetime.fromtimestamp(state[4], tz=timezone.utc),
            safe_float(state[5]),  # longitude
            safe_float(state[6]),  # latitude
            safe_float(state[7]),  # geo_altitude
            safe_bool(state[8]),  # on_ground
            safe_float(state[9]),  # velocity
            safe_float(state[10]),  # true_track
            safe_float(state[11]),  # vertical_rate
            state[12],  # sensors
            safe_float(state[13]),  # baro_altitude
            state[14],  # squawk
            safe_bool(state[15]),  # spi
            safe_int(state[16])  # category
        )

    def readBetweenOffsets(self, start: Dict[str, int], end: Dict[str, int]) -> Iterator[Tuple]:
        data, _ = self.read(start)
        return iter(data)
        
    def read(self, start: Dict[str, int]) -> Tuple[List[Tuple], Dict[str, int]]:
        """Read states with error handling and backoff"""
        try:
            response = self._fetch_states()
            data = response.json()
            
            valid_states = [
                self.parse_state(s, data['time'])
                for s in data.get('states', [])
                if self.valid_state(s)
            ]
            
            return (
                valid_states,
                {'last_fetch': data.get('time', int(time.time()))}
            )
            
        except OpenSkyAPIError as e:
            print(f"OpenSky API Error: {str(e)}")
            return ([], start)
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return ([], start)

class OpenSkyDataSource(DataSource):
    def __init__(self, options: Dict[str, str] = None):
        super().__init__(options or {})
        self.options = options or {}
        
        if 'client_id' in self.options and not self.options.get('client_secret'):
            raise ValueError("client_secret must be provided when client_id is set")
        
        if 'region' in self.options and self.options['region'].upper() not in Region.__members__:
            raise ValueError(f"Invalid region. Must be one of: {', '.join(Region.__members__.keys())}")

    @classmethod
    def name(cls) -> str:
        return DS_NAME

    def schema(self) -> StructType:
        return StructType([
            StructField("time_ingest", TimestampType()),
            StructField("icao24", StringType()),
            StructField("callsign", StringType()),
            StructField("origin_country", StringType()),
            StructField("time_position", TimestampType()),
            StructField("last_contact", TimestampType()),
            StructField("longitude", DoubleType()),
            StructField("latitude", DoubleType()),
            StructField("geo_altitude", DoubleType()),
            StructField("on_ground", BooleanType()),
            StructField("velocity", DoubleType()),
            StructField("true_track", DoubleType()),
            StructField("vertical_rate", DoubleType()),
            StructField("sensors", ArrayType(IntegerType())),
            StructField("baro_altitude", DoubleType()),
            StructField("squawk", StringType()),
            StructField("spi", BooleanType()),
            StructField("category", IntegerType())
        ])

    def simpleStreamReader(self, schema: StructType) -> OpenSkyStreamReader:
        return OpenSkyStreamReader(schema, self.options)

spark.dataSource.register(OpenSkyDataSource)
"""
DAY 1: COMMODITY DATA INGESTION ENGINE
=======================================

Purpose: Download, normalize, and store commodity datasets

Functions:
- download_dataset: Fetch from various sources
- normalize_structure: Standardize data format
- store_locally: Save to database and cache

Supported Formats:
- CSV
- JSON
- API endpoints
"""

from db.samruddhi_memory import Base, FinancialMemoryManager
import hashlib
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Text, JSON
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import requests
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE SCHEMA FOR COMMODITY DATA
# ============================================================================

class CommodityPrice(Base):
    """Commodity price data - normalized structure"""
    __tablename__ = 'commodity_prices'

    id = Column(Integer, primary_key=True)
    commodity_id = Column(String(100), index=True,
                          nullable=False)  # e.g., 'GOLD', 'WHEAT'
    commodity_name = Column(String(255))
    source = Column(String(100), nullable=False)  # 'FAO', 'WORLDBANK', 'MCX'
    dataset_id = Column(String(100), index=True)  # Dataset identifier

    timestamp = Column(DateTime, index=True, nullable=False)
    price = Column(Numeric(18, 4), nullable=False)
    currency = Column(String(3), default='USD')
    unit = Column(String(50))  # 'USD/tonne', 'USD/oz', etc.

    # Additional metrics
    open_price = Column(Numeric(18, 4))
    high_price = Column(Numeric(18, 4))
    low_price = Column(Numeric(18, 4))
    close_price = Column(Numeric(18, 4))
    volume = Column(Float)
    change_pct = Column(Float)

    # Metadata
    region = Column(String(100))  # 'Global', 'India', 'Asia'
    category = Column(String(100))  # 'Energy', 'Agriculture', 'Metals'
    quality_grade = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CommodityPrice(commodity={self.commodity_id}, price={self.price}, date={self.timestamp})>"


class CommodityIndex(Base):
    """Commodity indices (FFPI, BCOM, etc.)"""
    __tablename__ = 'commodity_indices'

    id = Column(Integer, primary_key=True)
    index_id = Column(String(100), unique=True, index=True, nullable=False)
    index_name = Column(String(255), nullable=False)
    source = Column(String(100), nullable=False)  # 'FAO', 'WORLDBANK'

    timestamp = Column(DateTime, index=True, nullable=False)
    value = Column(Numeric(18, 4), nullable=False)
    change_mom = Column(Float)  # Month-over-month change
    change_yoy = Column(Float)  # Year-over-year change

    # Sub-indices (for FAO FFPI)
    meat_index = Column(Numeric(18, 4))
    dairy_index = Column(Numeric(18, 4))
    sugar_index = Column(Numeric(18, 4))
    cereals_index = Column(Numeric(18, 4))
    vegoil_index = Column(Numeric(18, 4))

    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CommodityIndex(index={self.index_name}, value={self.value})>"


class DatasetMetadata(Base):
    """Track dataset downloads and updates"""
    __tablename__ = 'dataset_metadata'

    id = Column(Integer, primary_key=True)
    dataset_id = Column(String(100), unique=True, index=True, nullable=False)
    dataset_name = Column(String(255), nullable=False)
    source = Column(String(100), nullable=False)

    last_download = Column(DateTime)
    last_update = Column(DateTime)
    download_count = Column(Integer, default=0)

    # File tracking
    file_path = Column(Text)
    file_hash = Column(String(64))  # SHA-256 for integrity check
    record_count = Column(Integer)

    # Update schedule
    update_frequency = Column(String(50))  # 'daily', 'monthly', etc.
    next_scheduled_update = Column(DateTime)

    # Status
    # 'active', 'deprecated', 'error'
    status = Column(String(50), default='active')
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DatasetMetadata(dataset={self.dataset_name}, status={self.status})>"


# ============================================================================
# DATA INGESTION ENGINE
# ============================================================================

class CommodityDataIngestor:
    """
    Ingest commodity data from multiple sources.

    Supports:
    - FAO datasets (CSV/API)
    - World Bank datasets (CSV/JSON)
    - MCX data (CSV/API)
    - Generic CSV/JSON files
    """

    def __init__(self, memory_manager: FinancialMemoryManager, base_dir: str = None):
        self.memory = memory_manager
        self.base_dir = Path(base_dir) if base_dir else Path(
            __file__).parent / 'data'

        # Create directory structure
        (self.base_dir / 'raw').mkdir(parents=True, exist_ok=True)
        (self.base_dir / 'processed').mkdir(parents=True, exist_ok=True)
        (self.base_dir / 'cache').mkdir(parents=True, exist_ok=True)

        logger.info("✓ CommodityDataIngestor initialized")

    # ========================================================================
    # CORE INGESTION FUNCTIONS
    # ========================================================================

    def download_dataset(self,
                         dataset_id: str,
                         source: str,
                         url: str,
                         format: str = 'csv',
                         params: Dict = None) -> Path:
        """
        Download dataset from URL.

        Args:
            dataset_id: Unique dataset identifier
            source: Source name ('FAO', 'WORLDBANK', 'MCX')
            url: Download URL
            format: 'csv', 'json', or 'api'
            params: Optional request parameters

        Returns:
            Path to downloaded file
        """
        try:
            logger.info(f"Downloading {dataset_id} from {source}...")

            # Create source directory
            source_dir = self.base_dir / 'raw' / source.lower()
            source_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{dataset_id}_{timestamp}.{format}"
            filepath = source_dir / filename

            # Download
            if format == 'api':
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            else:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()

                with open(filepath, 'wb') as f:
                    f.write(response.content)

            # Calculate file hash for integrity
            file_hash = self._calculate_file_hash(filepath)

            # Update metadata
            self._update_dataset_metadata(
                dataset_id=dataset_id,
                dataset_name=f"{source} - {dataset_id}",
                source=source,
                file_path=str(filepath),
                file_hash=file_hash,
                update_frequency='monthly' if 'fao' in source.lower(
                ) or 'worldbank' in source.lower() else 'daily'
            )

            logger.info(f"✓ Downloaded {dataset_id} to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"✗ Download failed: {e}")
            raise

    def normalize_structure(self,
                            input_file: Path,
                            source: str,
                            mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Normalize dataset structure to standard schema.

        Args:
            input_file: Path to raw data file
            source: Source name
            mapping: Column mapping {raw_column: standard_column}

        Returns:
            Normalized DataFrame
        """
        try:
            logger.info(f"Normalizing {input_file.name} from {source}...")

            # Read file
            if input_file.suffix == '.csv':
                df = pd.read_csv(input_file)
            elif input_file.suffix == '.json':
                df = pd.read_json(input_file)
            else:
                raise ValueError(f"Unsupported format: {input_file.suffix}")

            # Rename columns using mapping
            df = df.rename(columns=mapping)

            # Add source tracking
            df['source'] = source
            df['normalized_at'] = datetime.utcnow()

            # Validate required columns
            required = ['timestamp', 'commodity_id', 'price']
            missing = [col for col in required if col not in df.columns]
            if missing:
                raise ValueError(
                    f"Missing required columns after mapping: {missing}")

            logger.info(f"✓ Normalized {len(df)} records")
            return df

        except Exception as e:
            logger.error(f"✗ Normalization failed: {e}")
            raise

    def store_locally(self,
                      df: pd.DataFrame,
                      storage_type: str = 'database',
                      output_path: Path = None) -> None:
        """
        Store processed data.

        Args:
            df: Normalized DataFrame
            storage_type: 'database', 'csv', 'parquet'
            output_path: Output path for file-based storage
        """
        try:
            if storage_type == 'database':
                # Store in SQLite via SQLAlchemy
                session = self.memory.get_session()

                stored_count = 0
                for _, row in df.iterrows():
                    try:
                        record = CommodityPrice(**row.to_dict())
                        session.add(record)
                        stored_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert row: {e}")

                session.commit()
                session.close()

                logger.info(f"✓ Stored {stored_count} records in database")

            elif storage_type == 'csv':
                if output_path is None:
                    output_path = self.base_dir / 'processed' / \
                        f"commodities_{datetime.now().strftime('%Y%m%d')}.csv"

                df.to_csv(output_path, index=False)
                logger.info(f"✓ Saved CSV to {output_path}")

            elif storage_type == 'parquet':
                if output_path is None:
                    output_path = self.base_dir / 'processed' / \
                        f"commodities_{datetime.now().strftime('%Y%m%d')}.parquet"

                df.to_parquet(output_path, index=False)
                logger.info(f"✓ Saved Parquet to {output_path}")

        except Exception as e:
            logger.error(f"✗ Storage failed: {e}")
            raise

    # ========================================================================
    # SOURCE-SPECIFIC DOWNLOADERS
    # ========================================================================

    def download_fao_ffpi(self) -> Path:
        """Download FAO Food Price Index data"""
        # FAO FFPI API endpoint (example - actual URL may vary)
        url = "https://www.fao.org/giews/data/food-prices/ffpi.csv"

        return self.download_dataset(
            dataset_id='FAO_FFPI',
            source='FAO',
            url=url,
            format='csv'
        )

    def download_world_bank_pink_sheet(self) -> Path:
        """Download World Bank Pink Sheet data"""
        # World Bank API endpoint
        url = "https://api.worldbank.org/v2/en/indicator/PX.REX.REER?downloadformat=csv"

        return self.download_dataset(
            dataset_id='WB_PINK_SHEET',
            source='WORLDBANK',
            url=url,
            format='csv'
        )

    def download_mcx_bhavcopy(self, date: str = None) -> Path:
        """Download MCX Bhavcopy for specified date"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        # MCX Bhavcopy URL pattern
        url = f"https://www.mcxindia.com/market-data/bhavcopy?date={date}"

        return self.download_dataset(
            dataset_id='MCX_BHAVCOPY',
            source='MCX',
            url=url,
            format='csv'
        )

    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================

    def _calculate_file_hash(self, filepath: Path) -> str:
        """Calculate SHA-256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _update_dataset_metadata(self, **kwargs):
        """Update dataset metadata in database"""
        session = self.memory.get_session()
        try:
            # Check if exists
            metadata = session.query(DatasetMetadata).filter(
                DatasetMetadata.dataset_id == kwargs['dataset_id']
            ).first()

            if metadata:
                # Update existing
                for key, value in kwargs.items():
                    if hasattr(metadata, key):
                        setattr(metadata, key, value)
                metadata.last_update = datetime.utcnow()
                metadata.download_count += 1
            else:
                # Create new
                metadata = DatasetMetadata(
                    **kwargs, last_download=datetime.utcnow())
                session.add(metadata)

            session.commit()
            logger.info(f"✓ Updated metadata for {kwargs['dataset_id']}")

        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def get_dataset_status(self, dataset_id: str) -> Optional[Dict]:
        """Get dataset download status and metadata"""
        session = self.memory.get_session()
        try:
            metadata = session.query(DatasetMetadata).filter(
                DatasetMetadata.dataset_id == dataset_id
            ).first()

            if metadata:
                return {
                    'dataset_id': metadata.dataset_id,
                    'dataset_name': metadata.dataset_name,
                    'source': metadata.source,
                    'last_download': metadata.last_download.isoformat() if metadata.last_download else None,
                    'last_update': metadata.last_update.isoformat() if metadata.last_update else None,
                    'download_count': metadata.download_count,
                    'status': metadata.status,
                    'file_path': metadata.file_path,
                    'record_count': metadata.record_count
                }
            return None

        finally:
            session.close()


def main():
    """Demo and test data ingestion"""
    logging.basicConfig(level=logging.INFO)

    print("\n" + "="*80)
    print("DAY 1: COMMODITY DATA INGESTION ENGINE")
    print("="*80)

    # Initialize
    memory = FinancialMemoryManager()
    ingestor = CommodityDataIngestor(memory)

    print("\n✓ Commodity Data Ingestor initialized")

    print("\n" + "="*80)
    print("AVAILABLE DATASETS (per COMMODITY_DATA_SOURCES.md)")
    print("="*80)

    datasets = [
        ("FAO Food Price Index", "FAO_FFPI", "Monthly"),
        ("World Bank Pink Sheet", "WB_PINK_SHEET", "Monthly"),
        ("MCX Bhavcopy", "MCX_BHAVCOPY", "Daily"),
        ("FAO Cereal Supply/Demand", "FAO_CEREAL_SD", "Quarterly"),
        ("LME Metal Prices", "LME_PRICES", "Daily"),
    ]

    for name, dataset_id, frequency in datasets:
        print(f"  • {name:30s} | ID: {dataset_id:20s} | {frequency}")

    print("\n" + "="*80)
    print("INGESTION CAPABILITIES")
    print("="*80)

    print("\n✓ Supported Formats:")
    print("  • CSV files")
    print("  • JSON files")
    print("  • API endpoints")

    print("\n✓ Functions:")
    print("  • download_dataset() - Fetch from URLs")
    print("  • normalize_structure() - Standardize format")
    print("  • store_locally() - Save to database/files")

    print("\n✓ Source-specific downloaders:")
    print("  • download_fao_ffpi()")
    print("  • download_world_bank_pink_sheet()")
    print("  • download_mcx_bhavcopy()")

    print("\n" + "="*80)
    print("✓ DAY 1 COMPLETE - DATA INGESTION ENGINE READY")
    print("="*80)
    print("\nNext: Day 2 — Feature Engineering Pipeline")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

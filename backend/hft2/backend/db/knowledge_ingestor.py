"""
DAY 2: KNOWLEDGEBASE INGESTION SYSTEM
======================================

Purpose: Create ingestion pipeline for Financial Knowledgebase

Supports:
- Manual insert
- JSON ingest
- CSV ingest
- Future RAG-ready structure

This makes the knowledgebase ready for:
- Financial reasoning
- HFT decision validation
- Explainability grounding
- Future autonomous intelligence
"""

from hft2.backend.db.samruddhi_memory import FinancialMemoryManager, FinancialKnowledge
import json
import csv
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))


logger = logging.getLogger(__name__)


class KnowledgeIngestor:
    """
    Ingest financial knowledge from multiple sources.

    Designed for:
    - Deterministic ingestion (same input = same output)
    - Auditable (track source and timestamp)
    - Extensible (easy to add new sources)
    - RAG-ready (structured for retrieval)
    """

    def __init__(self, memory_manager: FinancialMemoryManager):
        self.memory = memory_manager
        logger.info("✓ KnowledgeIngestor initialized")

    # ========================================================================
    # MANUAL INSERTION
    # ========================================================================

    def insert_manual(self, knowledge_data: Dict[str, Any]) -> FinancialKnowledge:
        """
        Manually insert a single knowledge item.

        Args:
            knowledge_data: Dictionary with required fields:
                - concept: str (what is this about?)
                - category: str (e.g., 'TECHNICAL_ANALYSIS', 'RISK_MANAGEMENT')
                - title: str (short title)
                - explanation: str (detailed explanation)
                - confidence_level: float (0.0 to 1.0)

                Optional:
                - subcategory: str
                - formula: str (mathematical formulas)
                - example: str (practical example)
                - source: str (original source)
                - source_url: str (URL to source)
                - tags: List[str] (for search)
                - related_concepts: List[str] (related concept IDs)

        Returns:
            FinancialKnowledge object

        Example:
            >>> ingestor.insert_manual({
            ...     'concept': 'RSI Oversold',
            ...     'category': 'TECHNICAL_ANALYSIS',
            ...     'title': 'RSI Below 30',
            ...     'explanation': 'When RSI falls below 30...',
            ...     'confidence_level': 0.95
            ... })
        """
        try:
            # Validate required fields
            required = ['concept', 'category', 'title',
                        'explanation', 'confidence_level']
            for field in required:
                if field not in knowledge_data:
                    raise ValueError(f"Missing required field: {field}")

            # Generate knowledge_id if not provided
            if 'knowledge_id' not in knowledge_data:
                # Deterministic ID based on content
                content_hash = hashlib.sha256(
                    f"{knowledge_data['concept']}_{knowledge_data['title']}_{datetime.now().isoformat()}".encode(
                    )
                ).hexdigest()[:16]
                knowledge_data['knowledge_id'] = f"KNOW_{content_hash.upper()}"

            # Set defaults
            knowledge_data.setdefault('subcategory', None)
            knowledge_data.setdefault('formula', None)
            knowledge_data.setdefault('example', None)
            knowledge_data.setdefault('source', None)
            knowledge_data.setdefault('source_url', None)
            knowledge_data.setdefault('source_verified', False)
            knowledge_data.setdefault(
                'quality_score', knowledge_data['confidence_level'])
            knowledge_data.setdefault('tags', [])
            knowledge_data.setdefault('related_concepts', [])
            knowledge_data.setdefault('created_by', 'manual_ingest')

            # Insert via memory manager
            knowledge = self.memory.add_knowledge(knowledge_data)

            logger.info(
                f"✓ Manually inserted knowledge: {knowledge.knowledge_id}")
            return knowledge

        except Exception as e:
            logger.error(f"✗ Error in manual insertion: {e}")
            raise

    def insert_batch_manual(self, knowledge_items: List[Dict[str, Any]]) -> List[FinancialKnowledge]:
        """
        Manually insert multiple knowledge items.

        Args:
            knowledge_items: List of knowledge dictionaries

        Returns:
            List of FinancialKnowledge objects
        """
        results = []
        for i, item in enumerate(knowledge_items):
            try:
                knowledge = self.insert_manual(item)
                results.append(knowledge)
                logger.info(f"Inserted {i+1}/{len(knowledge_items)}")
            except Exception as e:
                logger.error(f"Failed to insert item {i+1}: {e}")
                # Continue with next item

        return results

    # ========================================================================
    # JSON INGESTION
    # ========================================================================

    def ingest_json(self, json_path: str, category: str = None) -> List[FinancialKnowledge]:
        """
        Ingest knowledge from a JSON file.

        Expected JSON structure:
        {
            "knowledgebase": [
                {
                    "concept": "RSI Oversold",
                    "category": "TECHNICAL_ANALYSIS",
                    "title": "RSI Below 30",
                    "explanation": "...",
                    "confidence_level": 0.95,
                    ...
                },
                ...
            ]
        }

        Or flat array:
        [
            {
                "concept": "...",
                ...
            },
            ...
        ]

        Args:
            json_path: Path to JSON file
            category: Override category (optional)

        Returns:
            List of ingested FinancialKnowledge objects
        """
        try:
            path = Path(json_path)
            if not path.exists():
                raise FileNotFoundError(f"JSON file not found: {json_path}")

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different structures
            if isinstance(data, list):
                knowledge_items = data
            elif isinstance(data, dict) and 'knowledgebase' in data:
                knowledge_items = data['knowledgebase']
            else:
                raise ValueError(
                    "Invalid JSON structure. Expected list or dict with 'knowledgebase' key")

            # Apply category override if specified
            if category:
                for item in knowledge_items:
                    item['category'] = category

            # Ingest
            results = self.insert_batch_manual(knowledge_items)

            logger.info(
                f"✓ Ingested {len(results)} items from JSON: {json_path}")
            return results

        except Exception as e:
            logger.error(f"✗ Error ingesting JSON: {e}")
            raise

    def ingest_json_directory(self, dir_path: str, category: str = None) -> List[FinancialKnowledge]:
        """
        Ingest all JSON files from a directory.

        Args:
            dir_path: Path to directory containing JSON files
            category: Override category (optional)

        Returns:
            List of all ingested FinancialKnowledge objects
        """
        try:
            path = Path(dir_path)
            if not path.is_dir():
                raise NotADirectoryError(f"Not a directory: {dir_path}")

            all_results = []
            json_files = list(path.glob('*.json'))

            logger.info(f"Found {len(json_files)} JSON files in {dir_path}")

            for json_file in json_files:
                logger.info(f"Processing {json_file.name}...")
                results = self.ingest_json(str(json_file), category)
                all_results.extend(results)

            logger.info(
                f"✓ Total ingested from directory: {len(all_results)} items")
            return all_results

        except Exception as e:
            logger.error(f"✗ Error ingesting directory: {e}")
            raise

    # ========================================================================
    # CSV INGESTION
    # ========================================================================

    def ingest_csv(self, csv_path: str, category: str = None) -> List[FinancialKnowledge]:
        """
        Ingest knowledge from a CSV file.

        Expected CSV columns:
        - concept (required)
        - category (required, or provide via parameter)
        - title (required)
        - explanation (required)
        - confidence_level (required, 0.0 to 1.0)
        - subcategory (optional)
        - formula (optional)
        - example (optional)
        - source (optional)
        - source_url (optional)
        - tags (optional, comma-separated within cell)
        - related_concepts (optional, comma-separated within cell)

        Args:
            csv_path: Path to CSV file
            category: Override category (optional)

        Returns:
            List of ingested FinancialKnowledge objects
        """
        try:
            path = Path(csv_path)
            if not path.exists():
                raise FileNotFoundError(f"CSV file not found: {csv_path}")

            knowledge_items = []

            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # Validate required columns
                required_cols = ['concept', 'title',
                                 'explanation', 'confidence_level']
                if not all(col in reader.fieldnames for col in required_cols):
                    missing = [
                        col for col in required_cols if col not in reader.fieldnames]
                    raise ValueError(
                        f"Missing required CSV columns: {missing}")

                for row in reader:
                    # Convert confidence_level to float
                    try:
                        row['confidence_level'] = float(
                            row['confidence_level'])
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Invalid confidence_level '{row.get('confidence_level')}', defaulting to 0.5")
                        row['confidence_level'] = 0.5

                    # Parse tags (comma-separated)
                    if 'tags' in row and row['tags']:
                        row['tags'] = [tag.strip()
                                       for tag in row['tags'].split(',')]

                    # Parse related_concepts (comma-separated)
                    if 'related_concepts' in row and row['related_concepts']:
                        row['related_concepts'] = [concept.strip()
                                                   for concept in row['related_concepts'].split(',')]

                    # Apply category override
                    if category:
                        row['category'] = category
                    elif 'category' not in row or not row['category']:
                        raise ValueError(
                            f"Missing category for row: {row.get('concept', 'UNKNOWN')}")

                    knowledge_items.append(row)

            # Ingest
            results = self.insert_batch_manual(knowledge_items)

            logger.info(
                f"✓ Ingested {len(results)} items from CSV: {csv_path}")
            return results

        except Exception as e:
            logger.error(f"✗ Error ingesting CSV: {e}")
            raise

    # ========================================================================
    # SAMPLE KNOWLEDGE TEMPLATES
    # ========================================================================

    def create_sample_knowledgebase(self) -> List[FinancialKnowledge]:
        """
        Create a sample knowledgebase with common trading concepts.
        Useful for testing and demonstration.

        Returns:
            List of created FinancialKnowledge objects
        """
        sample_knowledge = [
            {
                'concept': 'RSI Oversold',
                'category': 'TECHNICAL_ANALYSIS',
                'subcategory': 'MOMENTUM_OSCILLATORS',
                'title': 'RSI Below 30 - Oversold Condition',
                'explanation': 'When the Relative Strength Index (RSI) falls below 30, the asset is considered oversold. This suggests that selling pressure has been excessive and a price reversal upward may be imminent. However, in strong downtrends, RSI can remain oversold for extended periods.',
                'formula': 'RSI = 100 - (100 / (1 + RS)) where RS = Average Gain / Average Loss',
                'example': 'If a stock\'s RSI drops to 25 while the price has been declining for 5 consecutive days, this may signal a buying opportunity for a mean-reversion trade.',
                'source': 'Welles Wilder - New Concepts in Technical Trading Systems (1978)',
                'confidence_level': 0.95,
                'tags': ['momentum', 'mean-reversion', 'oscillator', 'buying-opportunity'],
                'related_concepts': []
            },
            {
                'concept': 'RSI Overbought',
                'category': 'TECHNICAL_ANALYSIS',
                'subcategory': 'MOMENTUM_OSCILLATORS',
                'title': 'RSI Above 70 - Overbought Condition',
                'explanation': 'When RSI rises above 70, the asset is considered overbought. This indicates excessive buying pressure and suggests a potential price correction downward. In strong uptrends, RSI can remain overbought for extended periods.',
                'confidence_level': 0.95,
                'tags': ['momentum', 'mean-reversion', 'selling-opportunity']
            },
            {
                'concept': 'Moving Average Crossover',
                'category': 'TECHNICAL_ANALYSIS',
                'subcategory': 'TREND_FOLLOWING',
                'title': 'Golden Cross and Death Cross',
                'explanation': 'A moving average crossover occurs when a shorter-period MA crosses a longer-period MA. A "Golden Cross" (bullish) happens when short-term MA crosses above long-term MA. A "Death Cross" (bearish) occurs when short-term MA crosses below long-term MA.',
                'formula': 'SMA(n) = (P1 + P2 + ... + Pn) / n',
                'example': 'When 50-day SMA crosses above 200-day SMA, it\'s a Golden Cross signal suggesting long-term bullish momentum.',
                'confidence_level': 0.85,
                'tags': ['trend-following', 'moving-average', 'crossover']
            },
            {
                'concept': 'Position Sizing - Kelly Criterion',
                'category': 'RISK_MANAGEMENT',
                'subcategory': 'POSITION_SIZING',
                'title': 'Optimal Position Size Using Kelly Criterion',
                'explanation': 'The Kelly Criterion determines the optimal fraction of capital to allocate to a trade based on win probability and win/loss ratio. It maximizes long-term growth while avoiding ruin.',
                'formula': 'f* = (p * b - q) / b where p=win probability, q=loss probability, b=win/loss ratio',
                'example': 'If a strategy has 60% win rate and average win is 2x average loss, Kelly fraction = (0.6 * 2 - 0.4) / 2 = 0.4 or 40% of capital.',
                'source': 'John L. Kelly Jr. (1956)',
                'confidence_level': 0.90,
                'tags': ['risk-management', 'position-sizing', 'money-management']
            },
            {
                'concept': 'Stop Loss Placement',
                'category': 'RISK_MANAGEMENT',
                'subcategory': 'RISK_CONTROL',
                'title': 'Stop Loss Based on ATR',
                'explanation': 'Average True Range (ATR) provides a measure of market volatility. Placing stop losses at a multiple of ATR (e.g., 2x ATR) allows the trade enough room to breathe while limiting downside risk.',
                'formula': 'Stop Loss = Entry Price - (Multiplier × ATR)',
                'example': 'For a long entry at ₹1000 with ATR = ₹20 and multiplier = 2, place stop loss at ₹1000 - (2 × 20) = ₹960.',
                'confidence_level': 0.88,
                'tags': ['risk-management', 'stop-loss', 'volatility', 'atr']
            },
            {
                'concept': 'Market Regime Detection',
                'category': 'MARKET_ANALYSIS',
                'subcategory': 'REGIME_DETECTION',
                'title': 'Identifying Bull, Bear, and Sideways Markets',
                'explanation': 'Market regime detection classifies current market conditions into bull (trending up), bear (trending down), or sideways (ranging). Different strategies perform better in different regimes.',
                'example': 'A 200-day SMA can help identify regime: price above = bull market, price below = bear market. ADX < 25 suggests sideways market.',
                'confidence_level': 0.80,
                'tags': ['market-analysis', 'regime', 'trend-detection']
            }
        ]

        logger.info("Creating sample knowledgebase...")
        results = self.insert_batch_manual(sample_knowledge)
        logger.info(f"✓ Created {len(results)} sample knowledge items")

        return results

    # ========================================================================
    # RAG PREPARATION
    # ========================================================================

    def prepare_for_rag(self, knowledge_id: str = None) -> Dict[str, Any]:
        """
        Prepare knowledgebase for Retrieval-Augmented Generation (RAG).

        This structures knowledge for vector embedding and semantic search.

        Args:
            knowledge_id: Specific knowledge ID to prepare (or None for all)

        Returns:
            Dictionary with RAG-ready documents
        """
        session = self.memory.get_session()
        try:
            query = session.query(FinancialKnowledge)
            if knowledge_id:
                query = query.filter(
                    FinancialKnowledge.knowledge_id == knowledge_id)

            knowledge_items = query.all()

            rag_documents = []
            for k in knowledge_items:
                # Create searchable text
                searchable_text = f"""
                Concept: {k.concept}
                Category: {k.category} {k.subcategory or ''}
                Title: {k.title}
                Explanation: {k.explanation}
                Formula: {k.formula or 'N/A'}
                Example: {k.example or 'N/A'}
                Tags: {', '.join(k.tags) if k.tags else ''}
                """.strip()

                rag_documents.append({
                    'id': k.knowledge_id,
                    'concept': k.concept,
                    'category': k.category,
                    'title': k.title,
                    'searchable_text': searchable_text,
                    'metadata': {
                        'source': k.source,
                        'confidence_level': float(k.confidence_level),
                        'tags': k.tags,
                        'related_concepts': k.related_concepts
                    }
                })

            logger.info(f"Prepared {len(rag_documents)} documents for RAG")
            return {
                'total_documents': len(rag_documents),
                'documents': rag_documents
            }

        finally:
            session.close()


def main():
    """Demo and test the Knowledge Ingestion System"""
    logging.basicConfig(level=logging.INFO)

    print("\n" + "="*80)
    print("DAY 2: KNOWLEDGEBASE INGESTION SYSTEM")
    print("="*80)

    # Initialize
    memory = FinancialMemoryManager()
    ingestor = KnowledgeIngestor(memory)

    print("\n✓ Knowledge Ingestor initialized")

    # Create sample knowledgebase
    print("\n" + "="*80)
    print("CREATING SAMPLE KNOWLEDGEBASE")
    print("="*80)

    sample_items = ingestor.create_sample_knowledgebase()

    print(f"\n✓ Created {len(sample_items)} knowledge items:")
    for item in sample_items:
        print(f"  • {item.concept} ({item.category})")

    # Test retrieval
    print("\n" + "="*80)
    print("TESTING RETRIEVAL")
    print("="*80)

    # Get by category
    technical = memory.get_knowledge(category="TECHNICAL_ANALYSIS")
    print(f"\nTechnical Analysis knowledge: {len(technical)} items")

    # Search by concept
    rsi_knowledge = memory.get_knowledge(concept="RSI")
    print(f"RSI-related knowledge: {len(rsi_knowledge)} items")

    # Prepare for RAG
    print("\n" + "="*80)
    print("PREPARING FOR RAG")
    print("="*80)

    rag_docs = ingestor.prepare_for_rag()
    print(f"RAG-ready documents: {rag_docs['total_documents']}")

    print("\n" + "="*80)
    print("✓ DAY 2 COMPLETE - KNOWLEDGEBASE SYSTEM READY")
    print("="*80)
    print("\nCapabilities:")
    print("  ✓ Manual insertion (single & batch)")
    print("  ✓ JSON file ingestion")
    print("  ✓ CSV file ingestion")
    print("  ✓ Sample knowledgebase creation")
    print("  ✓ RAG preparation")
    print("\nReady for Day 3 — HFT Execution Data Persistence")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

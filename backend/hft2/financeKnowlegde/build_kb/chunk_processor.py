#!/usr/bin/env python3
"""
Knowledge Base Chunk Processor
==============================
Converts raw extraction notes into structured markdown chunks (300-500 tokens each).
Prepares content for LLM ingestion with proper formatting.
"""

import re
from pathlib import Path
from typing import List, Dict
import json


class KBChunkProcessor:
    """Processes raw notes into knowledge base chunks"""

    def __init__(self, raw_notes_dir="day1_raw_notes", output_kb_dir="../Finance_KB"):
        self.raw_notes_dir = Path(raw_notes_dir)
        self.output_kb_dir = Path(output_kb_dir)
        self.output_kb_dir.mkdir(parents=True, exist_ok=True)

        # Target chunk size: 300-500 tokens (approximately 400-650 words)
        self.target_chunk_words = 500
        self.chunk_overlap_words = 50

    def load_raw_notes(self, filename):
        """Load raw notes from markdown file"""
        filepath = self.raw_notes_dir / filename
        if not filepath.exists():
            print(f"⚠️  File not found: {filepath}")
            return None

        content = filepath.read_text(encoding='utf-8')
        return content

    def split_into_chunks(self, text, max_words=500, overlap=50):
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []

        start = 0
        while start < len(words):
            end = start + max_words
            chunk_words = words[start:end]

            # Try to break at sentence boundary
            if end < len(words):
                last_sentence_idx = None
                for i in range(len(chunk_words) - 1, -1, -1):
                    if chunk_words[i].endswith(('.', '!', '?', '\n')):
                        last_sentence_idx = i
                        break

                if last_sentence_idx and last_sentence_idx > max_words * 0.7:
                    chunk_words = chunk_words[:last_sentence_idx + 1]

            chunk_text = ' '.join(chunk_words)
            if chunk_text.strip():
                chunks.append(chunk_text)

            start += max_words - overlap

        return chunks

    def create_knowledge_block(self, title, topic_id, content, source_ids):
        """Create formatted knowledge block for LLM ingestion"""
        block = f"""<!-- BEGIN KNOWLEDGE BLOCK: {topic_id.upper().replace(' ', '_')} -->

# {title}

**Topic ID:** `{topic_id}`

{content}

**Sources:** {', '.join(source_ids)}

<!-- END KNOWLEDGE BLOCK: {topic_id.upper().replace(' ', '_')} -->
"""
        return block

    def process_nse_rules(self):
        """Process NSE rules into knowledge base files"""
        print("📊 Processing NSE rules...")

        raw_content = self.load_raw_notes("nse_market_rules_raw.md")
        if not raw_content:
            return

        # Split by major sections
        sections = re.split(r'## (NSE [^(]+)', raw_content)

        equities_dir = self.output_kb_dir / "equities"
        equities_dir.mkdir(parents=True, exist_ok=True)

        # Create nse_basics.md
        nse_basics_content = []
        for i in range(1, len(sections), 3):
            section_title = sections[i]
            section_content = sections[i + 1]

            if any(keyword in section_title.lower() for keyword in ['market structure', 'trading mechanism', 'timings']):
                nse_basics_content.append(
                    f"## {section_title}\n{section_content}")

        if nse_basics_content:
            nse_basics_file = equities_dir / "nse_basics.md"
            nse_basics_file.write_text(
                "# NSE Market Basics\n\n" + "\n".join(nse_basics_content[:3]),
                encoding='utf-8'
            )
            print(f"✅ Created: {nse_basics_file}")

        # Create circuit_breakers.md
        circuit_breaker_content = []
        for i in range(1, len(sections), 3):
            section_title = sections[i]
            section_content = sections[i + 1]

            if 'circuit breaker' in section_title.lower():
                circuit_breaker_content.append(
                    f"## {section_title}\n{section_content}")

        if circuit_breaker_content:
            cb_file = equities_dir / "circuit_breakers.md"
            cb_file.write_text(
                "# NSE Circuit Breaker Mechanism\n\n" +
                "\n".join(circuit_breaker_content),
                encoding='utf-8'
            )
            print(f"✅ Created: {cb_file}")

    def process_sebi_compliance(self):
        """Process SEBI compliance into knowledge base files"""
        print("📋 Processing SEBI compliance...")

        raw_content = self.load_raw_notes("sebi_compliance_raw.md")
        if not raw_content:
            return

        sebi_dir = self.output_kb_dir / "equities"
        sebi_dir.mkdir(parents=True, exist_ok=True)

        # Extract listing requirements
        listing_sections = re.findall(r'## (SEBI [^{]+)', raw_content)

        sebi_compliance_content = []
        for section in listing_sections[:2]:  # Take first 2 major sections
            pattern = rf"(## {re.escape(section)}.*?)(?=## |\Z)"
            matches = re.findall(pattern, raw_content, re.DOTALL)
            if matches:
                sebi_compliance_content.append(matches[0])

        if sebi_compliance_content:
            sebi_file = sebi_dir / "sebi_compliance.md"
            sebi_file.write_text(
                "# SEBI Compliance Requirements\n\n" +
                "\n".join(sebi_compliance_content),
                encoding='utf-8'
            )
            print(f"✅ Created: {sebi_file}")

    def process_ta_indicators(self):
        """Process TA indicators into knowledge base files"""
        print("📈 Processing TA indicators...")

        raw_content = self.load_raw_notes("ta_indicators_raw.md")
        if not raw_content:
            return

        ta_dir = self.output_kb_dir / "ta_indicators"
        ta_dir.mkdir(parents=True, exist_ok=True)

        # Split into trend and momentum
        trend_pattern = r"(## Trend-Following Technical Indicators.*?)(?=## Momentum|\Z)"
        momentum_pattern = r"(## Momentum Oscillators.*?)(?=\Z)"

        trend_matches = re.findall(trend_pattern, raw_content, re.DOTALL)
        momentum_matches = re.findall(momentum_pattern, raw_content, re.DOTALL)

        # Create trend indicators file
        if trend_matches:
            trend_file = ta_dir / "trend_indicators.md"
            trend_file.write_text(
                "# Trend-Following Indicators\n\n" + trend_matches[0],
                encoding='utf-8'
            )
            print(f"✅ Created: {trend_file}")

        # Create momentum indicators file
        if momentum_matches:
            momentum_file = ta_dir / "momentum_indicators.md"
            momentum_file.write_text(
                "# Momentum Oscillators\n\n" + momentum_matches[0],
                encoding='utf-8'
            )
            print(f"✅ Created: {momentum_file}")

    def process_risk_management(self):
        """Process risk management into knowledge base files"""
        print("💰 Processing risk management...")

        raw_content = self.load_raw_notes("risk_management_raw.md")
        if not raw_content:
            return

        risk_dir = self.output_kb_dir / "risk_models"
        risk_dir.mkdir(parents=True, exist_ok=True)

        # Extract position sizing
        position_pattern = r"(## Position Sizing and Capital Allocation Framework.*?)(?=## Stop-Loss|\Z)"
        position_matches = re.findall(position_pattern, raw_content, re.DOTALL)

        if position_matches:
            position_file = risk_dir / "position_sizing.md"
            position_file.write_text(
                "# Position Sizing Framework\n\n" + position_matches[0],
                encoding='utf-8'
            )
            print(f"✅ Created: {position_file}")

        # Extract stop-loss rules
        stop_pattern = r"(## Stop-Loss Implementation and Exit Strategies.*?)(?=## Drawdown|\Z)"
        stop_matches = re.findall(stop_pattern, raw_content, re.DOTALL)

        if stop_matches:
            stop_file = risk_dir / "stop_loss_rules.md"
            stop_file.write_text(
                "# Stop-Loss Implementation Rules\n\n" + stop_matches[0],
                encoding='utf-8'
            )
            print(f"✅ Created: {stop_file}")

        # Extract drawdown limits
        drawdown_pattern = r"(## Drawdown Control and Capital Preservation Framework.*?)(?=\Z)"
        drawdown_matches = re.findall(drawdown_pattern, raw_content, re.DOTALL)

        if drawdown_matches:
            drawdown_file = risk_dir / "drawdown_limits.md"
            drawdown_file.write_text(
                "# Drawdown Control Framework\n\n" + drawdown_matches[0],
                encoding='utf-8'
            )
            print(f"✅ Created: {drawdown_file}")

    def run_full_processing(self):
        """Run complete processing pipeline"""
        print("=" * 70)
        print("🚀 KNOWLEDGE BASE CHUNK PROCESSING")
        print("=" * 70)
        print()

        self.process_nse_rules()
        self.process_sebi_compliance()
        self.process_ta_indicators()
        self.process_risk_management()

        print()
        print("=" * 70)
        print("PROCESSING COMPLETE")
        print("=" * 70)
        print()
        print(f"Output Directory: {self.output_kb_dir.absolute()}")
        print()


def main():
    processor = KBChunkProcessor()
    processor.run_full_processing()


if __name__ == "__main__":
    main()

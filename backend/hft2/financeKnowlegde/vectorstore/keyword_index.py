#!/usr/bin/env python3
"""
Keyword Index System for Finance KB
====================================
Basic keyword-based search as alternative to semantic embeddings.
Fast, lightweight, no external dependencies.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import math


class KeywordIndex:
    """
    Inverted index for keyword search across Finance KB

    Features:
    - TF-IDF weighting for better relevance
    - Fast lookups
    - No external dependencies
    - Supports phrase matching
    """

    def __init__(self, kb_path: str = "../Finance_KB"):
        self.kb_path = Path(kb_path)

        # Index structures
        # term -> [(doc_id, tf, positions)]
        self.inverted_index = defaultdict(list)
        self.document_lengths = {}  # doc_id -> word count
        self.documents = {}  # doc_id -> {text, title, source, category}
        self.idf = {}  # term -> IDF score

        # Statistics
        self.num_documents = 0
        self.total_words = 0
        self.vocabulary_size = 0

        # Stopwords (common English words to ignore)
        self.stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'this', 'that', 'these', 'those', 'it', 'its', 'of', 'in', 'to',
            'for', 'with', 'on', 'at', 'by', 'from', 'as', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'between', 'under',
            'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
            'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
            'too', 'very', 'just', 'can', 'now', 'also', 'what', 'which', 'who'
        }

    def build_index(self):
        """Build complete index from all markdown files in KB"""
        print("🔨 Building keyword index...")

        # Find all markdown files
        md_files = list(self.kb_path.rglob("*.md"))

        if not md_files:
            print(f"⚠️  No markdown files found in {self.kb_path}")
            return False

        print(f"📄 Found {len(md_files)} markdown files")

        # Process each file
        for file_path in md_files:
            self._process_document(file_path)

        # Calculate IDF scores
        self._calculate_idf()

        # Print statistics
        self._print_statistics()

        print("✅ Index built successfully!")
        return True

    def _process_document(self, file_path: Path):
        """Process single document and add to index"""
        doc_id = str(file_path.relative_to(self.kb_path))

        # Read content
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"⚠️  Error reading {file_path}: {e}")
            return

        # Extract metadata
        title = self._extract_title(content)
        category = file_path.parent.name
        topic_id = self._extract_topic_id(content)

        # Tokenize content
        words = self._tokenize(content)

        # Store document info
        self.documents[doc_id] = {
            'text': content,
            'title': title,
            'category': category,
            'topic_id': topic_id,
            'word_count': len(words)
        }

        self.document_lengths[doc_id] = len(words)
        self.num_documents += 1
        self.total_words += len(words)

        # Build term frequency for this document
        term_freq = defaultdict(int)
        term_positions = defaultdict(list)

        for pos, word in enumerate(words):
            term_freq[word] += 1
            term_positions[word].append(pos)

            # Add to inverted index
            if doc_id not in [item[0] for item in self.inverted_index[word]]:
                self.inverted_index[word].append((doc_id, 0, []))

        # Update inverted index with actual values
        for term, freq in term_freq.items():
            for i, (d_id, _, _) in enumerate(self.inverted_index[term]):
                if d_id == doc_id:
                    self.inverted_index[term][i] = (
                        doc_id, freq, term_positions[term])
                    break

        self.vocabulary_size = len(self.inverted_index)

    def _tokenize(self, text: str) -> List[str]:
        """Convert text to lowercase words, removing stopwords and punctuation"""
        # Convert to lowercase
        text = text.lower()

        # Remove markdown formatting
        text = re.sub(r'[#*_`~]', ' ', text)
        text = re.sub(r'\[\[.*?\]\]', '', text)  # Remove wiki links
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # Remove URLs

        # Remove numbers and special characters
        text = re.sub(r'\d+', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)

        # Split into words
        words = text.split()

        # Remove stopwords and short words
        words = [w for w in words if w not in self.stopwords and len(w) > 2]

        return words

    def _extract_title(self, content: str) -> str:
        """Extract document title from first H1 heading"""
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "Untitled"

    def _extract_topic_id(self, content: str) -> Optional[str]:
        """Extract topic ID from metadata"""
        match = re.search(r'\*\*Topic ID:\*\*\s+`([^`]+)`', content)
        if match:
            return match.group(1).strip()
        return None

    def _calculate_idf(self):
        """Calculate Inverse Document Frequency for all terms"""
        for term, postings in self.inverted_index.items():
            # Number of documents containing this term
            df = len(postings)

            # IDF formula: log(N / df) + 1
            self.idf[term] = math.log(self.num_documents / df) + 1

    def _print_statistics(self):
        """Print index statistics"""
        print(f"\n📊 Index Statistics:")
        print(f"   Documents: {self.num_documents}")
        print(f"   Total words: {self.total_words:,}")
        print(f"   Vocabulary size: {self.vocabulary_size:,}")
        print(
            f"   Average doc length: {self.total_words // max(self.num_documents, 1):.0f} words")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for documents matching query

        Args:
            query: Search query string
            top_k: Number of results to return

        Returns:
            List of matching documents with scores
        """
        # Tokenize query
        query_terms = self._tokenize(query)

        if not query_terms:
            return []

        # Calculate query term weights
        query_weights = {}
        for term in query_terms:
            if term in self.idf:
                # Simple TF-IDF (assume TF=1)
                query_weights[term] = self.idf[term]

        # Score documents
        doc_scores = defaultdict(float)

        for term, weight in query_weights.items():
            for doc_id, tf, positions in self.inverted_index.get(term, []):
                # BM25-style scoring (simplified)
                doc_scores[doc_id] += weight * \
                    (tf / self.document_lengths.get(doc_id, 1))

        # Sort by score
        sorted_docs = sorted(doc_scores.items(),
                             key=lambda x: x[1], reverse=True)

        # Return top-k results
        results = []
        for doc_id, score in sorted_docs[:top_k]:
            doc_info = self.documents[doc_id]
            results.append({
                'doc_id': doc_id,
                'score': score,
                'title': doc_info['title'],
                'category': doc_info['category'],
                'topic_id': doc_info.get('topic_id'),
                'snippet': self._get_snippet(doc_info['text'], query_terms)
            })

        return results

    def _get_snippet(self, text: str, query_terms: List[str], context_chars: int = 200) -> str:
        """Extract relevant snippet from document"""
        text_lower = text.lower()

        # Find first occurrence of any query term
        best_pos = -1
        for term in query_terms:
            pos = text_lower.find(term)
            if pos != -1 and (best_pos == -1 or pos < best_pos):
                best_pos = pos

        # Extract snippet around match
        if best_pos != -1:
            start = max(0, best_pos - context_chars // 2)
            end = min(len(text), best_pos + context_chars // 2)
            snippet = text[start:end].strip()

            # Add ellipsis if truncated
            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet = snippet + "..."

            return snippet
        else:
            # Return beginning of document
            return text[:context_chars].strip() + "..."

    def save_index(self, output_path: str = "keyword_index.json"):
        """Save index to JSON file"""
        print(f"💾 Saving index to {output_path}...")

        # Convert to serializable format
        index_data = {
            'inverted_index': {k: v for k, v in self.inverted_index.items()},
            'document_lengths': self.document_lengths,
            'documents': self.documents,
            'idf': self.idf,
            'statistics': {
                'num_documents': self.num_documents,
                'total_words': self.total_words,
                'vocabulary_size': self.vocabulary_size
            }
        }

        # Save to file
        output_file = Path(output_path)
        output_file.write_text(json.dumps(
            index_data, indent=2), encoding='utf-8')

        print(f"✅ Index saved ({len(index_data['inverted_index'])} terms)")

    def load_index(self, input_path: str = "keyword_index.json"):
        """Load index from JSON file"""
        print(f"📂 Loading index from {input_path}...")

        input_file = Path(input_path)
        if not input_file.exists():
            print(f"⚠️  Index file not found: {input_file}")
            return False

        try:
            index_data = json.loads(input_file.read_text(encoding='utf-8'))

            # Restore data structures
            self.inverted_index = defaultdict(
                list, index_data['inverted_index'])
            self.document_lengths = index_data['document_lengths']
            self.documents = index_data['documents']
            self.idf = index_data['idf']

            stats = index_data['statistics']
            self.num_documents = stats['num_documents']
            self.total_words = stats['total_words']
            self.vocabulary_size = stats['vocabulary_size']

            print(f"✅ Index loaded ({len(self.inverted_index)} terms)")
            return True

        except Exception as e:
            print(f"❌ Error loading index: {e}")
            return False


def main():
    """Test keyword index"""
    print("=" * 70)
    print("KEYWORD INDEX SYSTEM TEST")
    print("=" * 70)

    # Initialize
    index = KeywordIndex("../Finance_KB")

    # Build index
    if not index.build_index():
        print("\n❌ Failed to build index")
        return

    # Save index
    index.save_index("keyword_index.json")

    # Test searches
    test_queries = [
        "NSE circuit breaker rules",
        "position sizing methods",
        "stop loss implementation",
        "RSI divergence trading",
        "SEBI compliance requirements"
    ]

    print("\n" + "=" * 70)
    print("TEST SEARCHES")
    print("=" * 70)

    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        results = index.search(query, top_k=3)

        for i, result in enumerate(results, 1):
            print(f"\n  {i}. {result['title']}")
            print(f"     Category: {result['category']}")
            print(f"     Score: {result['score']:.4f}")
            print(f"     Snippet: {result['snippet'][:100]}...")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Part 3: Natural Language Processing & Text Analysis
=====================================================
Multi-Modal Document Intelligence System

This module extracts text from the PDF and performs comprehensive
NLP analysis using NLTK, including:
- Text extraction and cleaning
- Tokenization (sentences and words)
- Stopword removal and lemmatization
- Statistical analysis (word counts, frequencies)
- POS tagging and named entity recognition
- Word cloud and frequency distribution visualization

Required Libraries: NLTK, pdfplumber, matplotlib, wordcloud, numpy
"""

import os
import sys
import re
import time
import string
import logging
from typing import List, Dict, Tuple, Optional
from collections import Counter

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber is required. Install with: pip install pdfplumber")
    sys.exit(1)

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer, PorterStemmer
    from nltk.probability import FreqDist
    from nltk import pos_tag, ne_chunk
    from nltk.tree import Tree
except ImportError:
    print("Error: NLTK is required. Install with: pip install nltk")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for saving plots
    import matplotlib.pyplot as plt
except ImportError:
    print("Error: matplotlib is required. Install with: pip install matplotlib")
    sys.exit(1)

try:
    from wordcloud import WordCloud
except ImportError:
    print("Error: wordcloud is required. Install with: pip install wordcloud")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("Error: NumPy is required. Install with: pip install numpy")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# NLTK Data Download
# ============================================================

def download_nltk_data():
    """
    Download all required NLTK data packages.
    
    Downloads tokenizers, corpora, and taggers needed for
    the NLP analysis pipeline. Skips already-downloaded packages.
    """
    required_packages = [
        'punkt',           # Sentence tokenizer
        'punkt_tab',       # Updated punkt tokenizer data
        'averaged_perceptron_tagger',      # POS tagger
        'averaged_perceptron_tagger_eng',  # English POS tagger
        'maxent_ne_chunker',               # Named entity chunker
        'maxent_ne_chunker_tab',           # NE chunker data
        'words',           # Words corpus (for NE chunker)
        'stopwords',       # Stopwords corpus
        'wordnet',         # WordNet lemmatizer data
        'omw-1.4',         # Open Multilingual WordNet
    ]
    
    print("Downloading required NLTK data...")
    for package in required_packages:
        try:
            nltk.download(package, quiet=True)
        except Exception as e:
            logger.warning(f"Could not download NLTK package '{package}': {e}")
    
    print("NLTK data download complete.")


# ============================================================
# Constants
# ============================================================

# Pages to extract text from (1-indexed)
TEXT_EXTRACTION_PAGES: List[int] = [1, 2, 3, 4]

# Number of top frequent words to display
TOP_N_WORDS: int = 20

# Number of sentences for POS tagging
POS_TAG_SENTENCES: int = 3


# ============================================================
# Text Extraction
# ============================================================

def extract_text_from_pages(
    pdf_path: str,
    pages: List[int]
) -> Dict[int, str]:
    """
    Extract text content from specified pages of a PDF file.

    Uses pdfplumber for accurate text extraction with layout
    preservation.

    Args:
        pdf_path (str): Path to the input PDF file.
        pages (List[int]): List of 1-indexed page numbers.

    Returns:
        Dict[int, str]: Dictionary mapping page numbers to their
            extracted text content.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    page_texts = {}

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        for page_num in tqdm(pages, desc="Extracting text"):
            if page_num < 1 or page_num > total_pages:
                logger.warning(
                    f"Page {page_num} out of range (1-{total_pages}). "
                    f"Skipping."
                )
                continue

            # pdfplumber uses 0-indexed pages
            page = pdf.pages[page_num - 1]
            text = page.extract_text()

            if text:
                page_texts[page_num] = text
                logger.info(
                    f"  Page {page_num}: Extracted {len(text)} characters."
                )
            else:
                page_texts[page_num] = ""
                logger.warning(f"  Page {page_num}: No text found.")

    return page_texts


def clean_text(text: str) -> str:
    """
    Clean extracted text by removing noise and normalizing whitespace.

    Cleaning operations include:
    - Removing extra whitespace and newlines
    - Removing special characters (keeping basic punctuation)
    - Normalizing Unicode characters
    - Removing page numbers and headers/footers patterns

    Args:
        text (str): Raw extracted text.

    Returns:
        str: Cleaned text.
    """
    if not text:
        return ""

    # Replace multiple newlines with single space
    cleaned = re.sub(r'\n+', ' ', text)

    # Replace multiple spaces with single space
    cleaned = re.sub(r'\s+', ' ', cleaned)

    # Remove special characters but keep letters, numbers,
    # basic punctuation, and spaces
    cleaned = re.sub(r'[^a-zA-Z0-9\s.,;:!?\'\"-()]', ' ', cleaned)

    # Remove standalone numbers (likely page numbers)
    cleaned = re.sub(r'\b\d{1,3}\b', '', cleaned)

    # Clean up extra spaces again
    cleaned = re.sub(r'\s+', ' ', cleaned)

    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()

    return cleaned


def combine_page_texts(page_texts: Dict[int, str]) -> str:
    """
    Combine text from multiple pages into a single string.

    Args:
        page_texts (Dict[int, str]): Page number to text mapping.

    Returns:
        str: Combined text from all pages.
    """
    # Sort by page number and combine
    sorted_pages = sorted(page_texts.keys())
    combined = " ".join(page_texts[p] for p in sorted_pages if page_texts[p])
    return combined


# ============================================================
# Tokenization & Basic Analysis
# ============================================================

def tokenize_text(text: str) -> Tuple[List[str], List[str]]:
    """
    Tokenize text into sentences and words.

    Args:
        text (str): Input text to tokenize.

    Returns:
        Tuple[List[str], List[str]]: A tuple containing:
            - List of sentences
            - List of word tokens
    """
    sentences = sent_tokenize(text)
    words = word_tokenize(text)

    logger.info(f"  Tokenization: {len(sentences)} sentences, {len(words)} words.")
    return sentences, words


def remove_stopwords(words: List[str]) -> List[str]:
    """
    Remove English stopwords and punctuation from a list of word tokens.

    Also converts all words to lowercase and filters out
    tokens that are purely punctuation or very short.

    Args:
        words (List[str]): List of word tokens.

    Returns:
        List[str]: Filtered list with stopwords removed.
    """
    stop_words = set(stopwords.words('english'))

    # Additional custom stopwords for academic papers
    custom_stopwords = {
        'also', 'would', 'could', 'may', 'might', 'shall',
        'use', 'used', 'using', 'one', 'two', 'three',
        'et', 'al', 'fig', 'figure', 'table', 'ref',
        'e.g', 'i.e', 'etc', 'vs'
    }
    stop_words.update(custom_stopwords)

    filtered = [
        word.lower()
        for word in words
        if (
            word.lower() not in stop_words
            and word not in string.punctuation
            and len(word) > 2
            and word.isalpha()
        )
    ]

    logger.info(
        f"  Stopword removal: {len(words)} -> {len(filtered)} words "
        f"({len(words) - len(filtered)} removed)."
    )
    return filtered


def lemmatize_words(words: List[str]) -> List[str]:
    """
    Apply lemmatization to a list of words using WordNet.

    Lemmatization reduces words to their base/dictionary form
    (e.g., 'running' -> 'run', 'better' -> 'good').

    Args:
        words (List[str]): List of word tokens.

    Returns:
        List[str]: List of lemmatized words.
    """
    lemmatizer = WordNetLemmatizer()
    lemmatized = [lemmatizer.lemmatize(word) for word in words]
    logger.info(f"  Lemmatization applied to {len(words)} words.")
    return lemmatized


def stem_words(words: List[str]) -> List[str]:
    """
    Apply Porter stemming to a list of words.

    Stemming reduces words to their root form by removing
    suffixes (e.g., 'running' -> 'run', 'studies' -> 'studi').

    Args:
        words (List[str]): List of word tokens.

    Returns:
        List[str]: List of stemmed words.
    """
    stemmer = PorterStemmer()
    stemmed = [stemmer.stem(word) for word in words]
    logger.info(f"  Stemming applied to {len(words)} words.")
    return stemmed


# ============================================================
# Statistical Analysis
# ============================================================

def calculate_statistics(
    words: List[str],
    filtered_words: List[str],
    sentences: List[str],
    top_n: int = TOP_N_WORDS
) -> Dict:
    """
    Calculate comprehensive text statistics.

    Args:
        words (List[str]): All word tokens (before filtering).
        filtered_words (List[str]): Words after stopword removal.
        sentences (List[str]): List of sentences.
        top_n (int): Number of top frequent words to include.

    Returns:
        Dict: Dictionary containing all calculated statistics.
    """
    # Word frequency distribution (on filtered words)
    freq_dist = FreqDist(filtered_words)

    # Calculate average sentence length
    sentence_lengths = [len(word_tokenize(s)) for s in sentences]
    avg_sentence_length = (
        sum(sentence_lengths) / len(sentence_lengths)
        if sentence_lengths else 0
    )

    statistics = {
        "total_word_count": len(words),
        "unique_word_count": len(set(words)),
        "filtered_word_count": len(filtered_words),
        "unique_filtered_words": len(set(filtered_words)),
        "total_sentences": len(sentences),
        "average_sentence_length": round(avg_sentence_length, 2),
        "longest_sentence_length": max(sentence_lengths) if sentence_lengths else 0,
        "shortest_sentence_length": min(sentence_lengths) if sentence_lengths else 0,
        "top_n_words": freq_dist.most_common(top_n),
        "vocabulary_richness": round(
            len(set(filtered_words)) / len(filtered_words), 4
        ) if filtered_words else 0,
    }

    return statistics


def display_statistics(stats: Dict):
    """
    Display text statistics in a formatted manner.

    Args:
        stats (Dict): Statistics dictionary from calculate_statistics().
    """
    print("\n" + "-" * 50)
    print("  TEXT STATISTICS")
    print("-" * 50)
    print(f"  Total word count:          {stats['total_word_count']}")
    print(f"  Unique word count:         {stats['unique_word_count']}")
    print(f"  Filtered word count:       {stats['filtered_word_count']}")
    print(f"  Unique filtered words:     {stats['unique_filtered_words']}")
    print(f"  Total sentences:           {stats['total_sentences']}")
    print(f"  Average sentence length:   {stats['average_sentence_length']} words")
    print(f"  Longest sentence:          {stats['longest_sentence_length']} words")
    print(f"  Shortest sentence:         {stats['shortest_sentence_length']} words")
    print(f"  Vocabulary richness:       {stats['vocabulary_richness']}")
    print(f"\n  Top {len(stats['top_n_words'])} Most Frequent Words:")
    print(f"  {'Rank':<6} {'Word':<20} {'Frequency':<10}")
    print(f"  {'-'*36}")
    for rank, (word, freq) in enumerate(stats['top_n_words'], 1):
        print(f"  {rank:<6} {word:<20} {freq:<10}")


# ============================================================
# Advanced NLP: POS Tagging
# ============================================================

def perform_pos_tagging(
    page_texts: Dict[int, str],
    num_sentences: int = POS_TAG_SENTENCES
) -> Dict[int, List]:
    """
    Perform Part-of-Speech tagging on the first N sentences
    of each page.

    Tags each word with its grammatical role (noun, verb,
    adjective, etc.) using NLTK's averaged perceptron tagger.

    Args:
        page_texts (Dict[int, str]): Page number to text mapping.
        num_sentences (int): Number of sentences to tag per page.

    Returns:
        Dict[int, List]: Page number to list of tagged sentences,
            where each sentence is a list of (word, tag) tuples.
    """
    pos_results = {}

    for page_num in sorted(page_texts.keys()):
        text = page_texts[page_num]
        if not text:
            continue

        # Tokenize into sentences
        sentences = sent_tokenize(text)

        # Take first N sentences
        selected_sentences = sentences[:num_sentences]

        tagged_sentences = []
        for sentence in selected_sentences:
            words = word_tokenize(sentence)
            tagged = pos_tag(words)
            tagged_sentences.append(tagged)

        pos_results[page_num] = tagged_sentences
        logger.info(
            f"  POS tagged {len(tagged_sentences)} sentences "
            f"from page {page_num}."
        )

    return pos_results


def display_pos_results(pos_results: Dict[int, List]):
    """
    Display POS tagging results in a readable format.

    Args:
        pos_results (Dict[int, List]): POS tagging results from
            perform_pos_tagging().
    """
    # POS tag descriptions for common tags
    tag_descriptions = {
        'NN': 'Noun (singular)',
        'NNS': 'Noun (plural)',
        'NNP': 'Proper noun (singular)',
        'NNPS': 'Proper noun (plural)',
        'VB': 'Verb (base form)',
        'VBD': 'Verb (past tense)',
        'VBG': 'Verb (gerund)',
        'VBN': 'Verb (past participle)',
        'VBP': 'Verb (non-3rd person)',
        'VBZ': 'Verb (3rd person)',
        'JJ': 'Adjective',
        'JJR': 'Adjective (comparative)',
        'JJS': 'Adjective (superlative)',
        'RB': 'Adverb',
        'DT': 'Determiner',
        'IN': 'Preposition',
        'CC': 'Coordinating conjunction',
        'PRP': 'Personal pronoun',
    }

    print("\n" + "-" * 50)
    print("  POS TAGGING RESULTS")
    print("-" * 50)

    for page_num, tagged_sentences in pos_results.items():
        print(f"\n  Page {page_num}:")
        for sent_idx, tagged_sent in enumerate(tagged_sentences, 1):
            print(f"    Sentence {sent_idx}:")
            for word, tag in tagged_sent[:15]:  # Show first 15 tokens
                desc = tag_descriptions.get(tag, tag)
                print(f"      {word:<20} -> {tag:<6} ({desc})")
            if len(tagged_sent) > 15:
                print(f"      ... and {len(tagged_sent) - 15} more tokens")


# ============================================================
# Advanced NLP: Named Entity Recognition
# ============================================================

def extract_named_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract named entities from text using NLTK's NE chunker.

    Identifies persons, organizations, locations, and other
    entity types in the text.

    Args:
        text (str): Input text for entity extraction.

    Returns:
        Dict[str, List[str]]: Dictionary mapping entity types
            (PERSON, ORGANIZATION, GPE/LOCATION) to lists of
            entity names found.
    """
    entities = {
        "PERSON": [],
        "ORGANIZATION": [],
        "GPE": [],        # Geo-Political Entity (locations)
        "FACILITY": [],
        "OTHER": [],
    }

    # Tokenize and tag
    sentences = sent_tokenize(text)

    for sentence in sentences:
        words = word_tokenize(sentence)
        tagged = pos_tag(words)

        # Apply named entity chunker
        chunked = ne_chunk(tagged)

        for subtree in chunked:
            if isinstance(subtree, Tree):
                entity_type = subtree.label()
                entity_name = " ".join(
                    word for word, tag in subtree.leaves()
                )

                if entity_type in entities:
                    if entity_name not in entities[entity_type]:
                        entities[entity_type].append(entity_name)
                else:
                    if entity_name not in entities["OTHER"]:
                        entities["OTHER"].append(entity_name)

    # Log summary
    total_entities = sum(len(v) for v in entities.values())
    logger.info(f"  Found {total_entities} unique named entities.")

    return entities


def display_named_entities(entities: Dict[str, List[str]]):
    """
    Display extracted named entities grouped by type.

    Args:
        entities (Dict[str, List[str]]): Entity extraction results.
    """
    print("\n" + "-" * 50)
    print("  NAMED ENTITIES")
    print("-" * 50)

    type_labels = {
        "PERSON": "Persons",
        "ORGANIZATION": "Organizations",
        "GPE": "Locations (GPE)",
        "FACILITY": "Facilities",
        "OTHER": "Other Entities",
    }

    for entity_type, entity_list in entities.items():
        label = type_labels.get(entity_type, entity_type)
        if entity_list:
            print(f"\n  {label} ({len(entity_list)}):")
            for entity in entity_list[:20]:  # Limit display
                print(f"    - {entity}")
            if len(entity_list) > 20:
                print(f"    ... and {len(entity_list) - 20} more")
        else:
            print(f"\n  {label}: None found")


# ============================================================
# Visualization: Word Frequency Distribution
# ============================================================

def plot_frequency_distribution(
    filtered_words: List[str],
    top_n: int,
    output_path: str
) -> str:
    """
    Generate and save a bar chart of word frequency distribution.

    Args:
        filtered_words (List[str]): Filtered word tokens.
        top_n (int): Number of top words to plot.
        output_path (str): Path to save the plot image.

    Returns:
        str: Path to the saved plot.
    """
    freq_dist = FreqDist(filtered_words)
    most_common = freq_dist.most_common(top_n)

    words = [word for word, _ in most_common]
    frequencies = [freq for _, freq in most_common]

    # Create the plot
    fig, ax = plt.subplots(figsize=(14, 7))

    # Create bar chart with gradient colors
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(words)))
    bars = ax.bar(range(len(words)), frequencies, color=colors, edgecolor='white')

    # Customize the plot
    ax.set_xlabel('Words', fontsize=12, fontweight='bold')
    ax.set_ylabel('Frequency', fontsize=12, fontweight='bold')
    ax.set_title(
        f'Top {top_n} Most Frequent Words (Excluding Stopwords)',
        fontsize=14, fontweight='bold', pad=15
    )
    ax.set_xticks(range(len(words)))
    ax.set_xticklabels(words, rotation=45, ha='right', fontsize=10)

    # Add frequency labels on bars
    for bar, freq in zip(bars, frequencies):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            str(freq),
            ha='center', va='bottom', fontsize=9, fontweight='bold'
        )

    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"  Frequency distribution plot saved: {output_path}")
    return output_path


# ============================================================
# Visualization: Word Cloud
# ============================================================

def generate_word_cloud(
    filtered_words: List[str],
    output_path: str
) -> str:
    """
    Generate and save a word cloud from the most frequent terms.

    Args:
        filtered_words (List[str]): Filtered word tokens.
        output_path (str): Path to save the word cloud image.

    Returns:
        str: Path to the saved word cloud.
    """
    # Combine words into a single string
    text = " ".join(filtered_words)

    # Create word cloud
    wordcloud = WordCloud(
        width=1200,
        height=600,
        background_color='white',
        max_words=100,
        max_font_size=120,
        min_font_size=10,
        colormap='viridis',
        contour_width=2,
        contour_color='steelblue',
        random_state=42,
    ).generate(text)

    # Save the word cloud
    fig, ax = plt.subplots(figsize=(16, 8))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    ax.set_title(
        'Word Cloud - Key Terms from Research Paper',
        fontsize=16, fontweight='bold', pad=15
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"  Word cloud saved: {output_path}")
    return output_path


# ============================================================
# Topic Summary Generation
# ============================================================

def generate_topic_summary(
    filtered_words: List[str],
    top_n: int = 10
) -> str:
    """
    Generate a summary of key topics based on word frequency analysis.

    Uses frequency-based heuristics to identify the main topics
    discussed in the text.

    Args:
        filtered_words (List[str]): Filtered and lemmatized words.
        top_n (int): Number of top terms to consider.

    Returns:
        str: Generated topic summary text.
    """
    freq_dist = FreqDist(filtered_words)
    top_words = freq_dist.most_common(top_n)

    summary_lines = [
        "TOPIC SUMMARY (Based on Frequency Analysis)",
        "=" * 45,
        "",
        "The document primarily discusses the following topics:",
        "",
    ]

    for rank, (word, freq) in enumerate(top_words, 1):
        # Calculate relative frequency as a percentage
        percentage = (freq / len(filtered_words)) * 100
        summary_lines.append(
            f"  {rank}. '{word}' - appears {freq} times "
            f"({percentage:.1f}% of content)"
        )

    summary_lines.extend([
        "",
        f"The text contains {len(set(filtered_words))} unique terms "
        f"out of {len(filtered_words)} total words,",
        f"indicating a vocabulary richness of "
        f"{len(set(filtered_words)) / len(filtered_words):.2%}.",
        "",
        "Key themes appear to revolve around: "
        + ", ".join(word for word, _ in top_words[:5]) + ".",
    ])

    return "\n".join(summary_lines)


# ============================================================
# NLP Analysis Report
# ============================================================

def save_nlp_report(
    stats: Dict,
    pos_results: Dict,
    entities: Dict[str, List[str]],
    topic_summary: str,
    output_path: str
) -> str:
    """
    Save comprehensive NLP analysis results to a text file.

    Args:
        stats (Dict): Text statistics.
        pos_results (Dict): POS tagging results.
        entities (Dict): Named entities.
        topic_summary (str): Generated topic summary.
        output_path (str): Path to save the report.

    Returns:
        str: Path to the saved report.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("    NLP ANALYSIS REPORT\n")
        f.write("=" * 70 + "\n\n")

        # Statistics
        f.write("--- Text Statistics ---\n")
        f.write(f"Total word count:        {stats['total_word_count']}\n")
        f.write(f"Unique word count:       {stats['unique_word_count']}\n")
        f.write(f"Filtered word count:     {stats['filtered_word_count']}\n")
        f.write(f"Total sentences:         {stats['total_sentences']}\n")
        f.write(f"Avg sentence length:     {stats['average_sentence_length']}\n")
        f.write(f"Vocabulary richness:     {stats['vocabulary_richness']}\n\n")

        # Top words
        f.write(f"--- Top {len(stats['top_n_words'])} Most Frequent Words ---\n")
        for rank, (word, freq) in enumerate(stats['top_n_words'], 1):
            f.write(f"  {rank:>3}. {word:<20} {freq}\n")
        f.write("\n")

        # Named Entities
        f.write("--- Named Entities ---\n")
        for etype, elist in entities.items():
            f.write(f"  {etype}: {', '.join(elist) if elist else 'None found'}\n")
        f.write("\n")

        # Topic Summary
        f.write("--- Topic Summary ---\n")
        f.write(topic_summary + "\n\n")

        f.write("=" * 70 + "\n")

    logger.info(f"  NLP report saved: {output_path}")
    return output_path


# ============================================================
# Main NLP Processing Function
# ============================================================

def process_nlp(pdf_path: str, output_dir: str) -> Dict:
    """
    Main function to run the complete NLP analysis pipeline.

    Orchestrates the Part 3 workflow:
    1. Extract text from pages 1-4
    2. Clean and tokenize text
    3. Remove stopwords and lemmatize
    4. Calculate statistics
    5. Perform POS tagging
    6. Extract named entities
    7. Generate visualizations
    8. Create topic summary and report

    Args:
        pdf_path (str): Path to the input PDF file.
        output_dir (str): Root output directory for results.

    Returns:
        Dict: Summary of NLP analysis results.
    """
    start_time = time.time()

    print("\n" + "=" * 60)
    print("  PART 3: NLP & TEXT ANALYSIS")
    print("=" * 60)

    # Download NLTK data
    download_nltk_data()

    # Create NLP output directory
    nlp_dir = os.path.join(output_dir, "nlp_analysis")
    os.makedirs(nlp_dir, exist_ok=True)

    # Step 1: Extract text from pages 1-4
    print("\n[Step 1/7] Extracting text from pages 1-4...")
    page_texts = extract_text_from_pages(pdf_path, TEXT_EXTRACTION_PAGES)

    # Step 2: Clean and combine text
    print("[Step 2/7] Cleaning text...")
    cleaned_pages = {p: clean_text(t) for p, t in page_texts.items()}
    combined_text = combine_page_texts(cleaned_pages)

    # Save cleaned text
    cleaned_path = os.path.join(nlp_dir, "cleaned_text.txt")
    with open(cleaned_path, "w", encoding="utf-8") as f:
        f.write(combined_text)
    logger.info(f"  Cleaned text saved: {cleaned_path}")

    # Step 3: Tokenize
    print("[Step 3/7] Tokenizing text...")
    sentences, words = tokenize_text(combined_text)

    # Step 4: Remove stopwords and lemmatize
    print("[Step 4/7] Removing stopwords and lemmatizing...")
    filtered_words = remove_stopwords(words)
    lemmatized_words = lemmatize_words(filtered_words)

    # Step 5: Calculate statistics
    print("[Step 5/7] Calculating statistics...")
    stats = calculate_statistics(words, lemmatized_words, sentences, TOP_N_WORDS)
    display_statistics(stats)

    # Step 6: POS tagging and NER
    print("[Step 6/7] Performing POS tagging and NER...")
    pos_results = perform_pos_tagging(
        cleaned_pages, num_sentences=POS_TAG_SENTENCES
    )
    display_pos_results(pos_results)

    entities = extract_named_entities(combined_text)
    display_named_entities(entities)

    # Step 7: Visualizations
    print("[Step 7/7] Generating visualizations...")

    # Word frequency distribution plot
    freq_plot_path = os.path.join(nlp_dir, "word_frequency_distribution.png")
    plot_frequency_distribution(lemmatized_words, TOP_N_WORDS, freq_plot_path)

    # Word cloud
    wordcloud_path = os.path.join(nlp_dir, "word_cloud.png")
    generate_word_cloud(lemmatized_words, wordcloud_path)

    # Topic summary
    topic_summary = generate_topic_summary(lemmatized_words)
    print("\n" + topic_summary)

    # Save comprehensive report
    report_path = os.path.join(nlp_dir, "nlp_analysis_report.txt")
    save_nlp_report(stats, pos_results, entities, topic_summary, report_path)

    # Summary
    total_time = time.time() - start_time

    results = {
        "statistics": stats,
        "pos_results": pos_results,
        "named_entities": entities,
        "topic_summary": topic_summary,
        "output_files": {
            "cleaned_text": cleaned_path,
            "freq_plot": freq_plot_path,
            "word_cloud": wordcloud_path,
            "report": report_path,
        },
        "processing_time": total_time,
    }

    print(f"\n  NLP Analysis Complete!")
    print(f"  Words analyzed: {stats['total_word_count']}")
    print(f"  Entities found: {sum(len(v) for v in entities.values())}")
    print(f"  Time elapsed: {total_time:.2f}s")

    return results


# ============================================================
# Script Entry Point
# ============================================================

if __name__ == "__main__":
    """
    Run Part 3 as a standalone script.
    
    Usage:
        python nlp_analysis.py <input_pdf> [output_directory]
    
    Examples:
        python nlp_analysis.py research_paper.pdf
        python nlp_analysis.py research_paper.pdf ./output
    """
    if len(sys.argv) < 2:
        print("Usage: python nlp_analysis.py <input_pdf> [output_directory]")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_directory = sys.argv[2] if len(sys.argv) > 2 else "./output"

    try:
        results = process_nlp(input_pdf, output_directory)
        print("\nPart 3 completed successfully!")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error during NLP analysis: {e}")
        sys.exit(1)

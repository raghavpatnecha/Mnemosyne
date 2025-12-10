"""
RAGFlow Utility Functions.

Shared utilities ported from RAGFlow's rag/nlp/__init__.py for:
- Number conversion (Arabic, Roman numerals, English words)
- Tree-based document merging
- Bullet pattern detection (English only)
- Position-aware Q&A detection

These are production-tested algorithms that provide the foundation
for accurate document structure recognition.

Note: Chinese language patterns have been removed. This module
supports English-only document processing.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Optional dependencies for number conversion
try:
    from word2number import w2n
    W2N_AVAILABLE = True
except ImportError:
    W2N_AVAILABLE = False
    w2n = None

try:
    import cn2an as cn2an_module
    CN2AN_AVAILABLE = True
except ImportError:
    CN2AN_AVAILABLE = False
    cn2an_module = None

try:
    import roman_numbers as roman
    ROMAN_AVAILABLE = True
except ImportError:
    ROMAN_AVAILABLE = False
    roman = None


# Bullet patterns for hierarchical document structure (English only)
# Ported from RAGFlow's BULLET_PATTERN
BULLET_PATTERNS = [
    # Pattern Set 0: Numeric patterns with decimals
    [
        r"[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}",  # 1.1.1.1
        r"[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}",  # 1.1.1
        r"[0-9]{1,2}\.[0-9]{1,2}[^a-zA-Z/%~-]",  # 1.1
        r"[0-9]{1,2}[\.\s]",  # 1. or 1
    ],
    # Pattern Set 1: English legal/formal patterns
    [
        r"PART (ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)",
        r"Chapter (I+V?|VI*|XI|IX|X|\d+)",
        r"Section [0-9]+",
        r"Article [0-9]+",
    ],
    # Pattern Set 2: Markdown headings
    [
        r"^#[^#]",
        r"^##[^#]",
        r"^###.*",
        r"^####.*",
        r"^#####.*",
        r"^######.*",
    ],
    # Pattern Set 3: Parenthesized patterns
    [
        r"\([0-9]{1,2}\)",  # (1), (2)
        r"\([a-z]\)",  # (a), (b)
        r"\([A-Z]\)",  # (A), (B)
        r"[a-z]\)",  # a), b)
        r"[A-Z]\)",  # A), B)
    ],
]

# Question patterns for Q&A detection (English only)
# Ported from RAGFlow's QUESTION_PATTERN
QUESTION_PATTERNS = [
    r"QUESTION (ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)",
    r"QUESTION (I+V?|VI*|XI|IX|X)",
    r"QUESTION ([0-9]+)",
    r"Q([0-9]+)[:.)\s]",
    r"([0-9]{1,2})[\.\s]",
    r"\(([0-9]{1,2})\)",
]


def index_int(index_str: str) -> int:
    """Convert various number formats to integer.

    Ported from RAGFlow's index_int() in rag/nlp/__init__.py.
    Supports:
    - Arabic numerals (1, 2, 3)
    - English words (one, two, three)
    - Roman numerals (I, II, III)

    Args:
        index_str: Number string to convert

    Returns:
        Integer value, or -1 if conversion fails
    """
    if not index_str:
        return -1

    index_str = str(index_str).strip()

    # Try Arabic numerals first
    try:
        return int(index_str)
    except ValueError:
        pass

    # Try English words (one, two, three, etc.)
    if W2N_AVAILABLE and w2n:
        try:
            return w2n.word_to_num(index_str.lower())
        except (ValueError, IndexError):
            pass

    # Try Roman numerals
    if ROMAN_AVAILABLE and roman:
        try:
            return roman.number(index_str.upper())
        except (ValueError, KeyError):
            pass

    # Simple Roman numeral fallback
    roman_map = {
        "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
        "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    }
    if index_str.upper() in roman_map:
        return roman_map[index_str.upper()]

    return -1


def not_bullet(line: str) -> bool:
    """Filter false positives for bullet detection.

    Ported from RAGFlow's not_bullet() in rag/nlp/__init__.py.

    Args:
        line: Line to check

    Returns:
        True if line should NOT be considered a bullet
    """
    patterns = [
        r"^0",  # Lines starting with 0
        r"[0-9]+ +[0-9~-]",  # Number ranges
        r"[0-9]+\.{2,}",  # Ellipsis patterns
    ]
    return any(re.match(p, line) for p in patterns)


def not_title(txt: str) -> bool:
    """Filter false positives for title detection.

    Ported from RAGFlow's not_title() in rag/nlp/__init__.py.

    Args:
        txt: Text to check

    Returns:
        True if text should NOT be considered a title
    """
    # Too many words or too long without spaces
    if len(txt.split()) > 12 or (txt.find(" ") < 0 and len(txt) >= 32):
        return True

    # Contains sentence-ending punctuation
    return bool(re.search(r"[,;?!]", txt))


def bullets_category(sections: List[str]) -> int:
    """Detect which bullet pattern set best matches the document.

    Ported from RAGFlow's bullets_category() in rag/nlp/__init__.py.

    Args:
        sections: List of text sections to analyze

    Returns:
        Index of best matching pattern set, or -1 if none match
    """
    hits = [0] * len(BULLET_PATTERNS)

    for i, pattern_set in enumerate(BULLET_PATTERNS):
        for sec in sections:
            sec = sec.strip()
            for pattern in pattern_set:
                if re.match(pattern, sec) and not not_bullet(sec):
                    hits[i] += 1
                    break

    maximum = 0
    result = -1

    for i, h in enumerate(hits):
        if h > maximum:
            result = i
            maximum = h

    return result


def title_frequency(
    bull: int, sections: List[Tuple[str, str]]
) -> Tuple[int, List[int]]:
    """Determine title hierarchy levels based on frequency.

    Ported from RAGFlow's title_frequency() in rag/nlp/__init__.py.

    Args:
        bull: Detected bullet pattern category
        sections: List of (text, layout_type) tuples

    Returns:
        Tuple of (most_common_level, list_of_levels_per_section)
    """
    if bull < 0 or bull >= len(BULLET_PATTERNS):
        return len(BULLET_PATTERNS[0]) + 1, [0] * len(sections)

    bullets_size = len(BULLET_PATTERNS[bull])
    levels = [bullets_size + 1 for _ in range(len(sections))]

    for i, (txt, layout) in enumerate(sections):
        for j, p in enumerate(BULLET_PATTERNS[bull]):
            if re.match(p, txt.strip()) and not not_bullet(txt):
                levels[i] = j
                break
        else:
            if re.search(r"(title|head)", layout) and not not_title(txt.split("@")[0]):
                levels[i] = bullets_size

    # Find most common level
    most_level = bullets_size + 1
    for level, count in sorted(Counter(levels).items(), key=lambda x: -x[1]):
        if level <= bullets_size:
            most_level = level
            break

    return most_level, levels


@dataclass
class Node:
    """Tree node for hierarchical document structure.

    Ported from RAGFlow's Node class in rag/nlp/__init__.py.
    Used for tree-based section merging.
    """

    level: int
    depth: int = -1
    texts: List[str] = field(default_factory=list)
    children: List["Node"] = field(default_factory=list)

    def add_child(self, child_node: "Node") -> None:
        """Add a child node."""
        self.children.append(child_node)

    def add_text(self, text: str) -> None:
        """Add text to this node."""
        self.texts.append(text)

    def build_tree(self, lines: List[Tuple[int, str]]) -> "Node":
        """Build tree structure from level-tagged lines.

        Ported from RAGFlow's Node.build_tree().

        Args:
            lines: List of (level, text) tuples

        Returns:
            Self for chaining
        """
        stack = [self]

        for level, text in lines:
            if self.depth != -1 and level > self.depth:
                # Beyond target depth: merge into current leaf
                stack[-1].add_text(text)
                continue

            # Move up until we find proper parent
            while len(stack) > 1 and level <= stack[-1].level:
                stack.pop()

            node = Node(level=level, texts=[text])
            stack[-1].add_child(node)
            stack.append(node)

        return self

    def get_tree(self) -> List[str]:
        """Flatten tree into merged chunks.

        Ported from RAGFlow's Node.get_tree().

        Returns:
            List of merged text chunks
        """
        tree_list: List[str] = []
        self._dfs(self, tree_list, [])
        return tree_list

    def _dfs(
        self, node: "Node", tree_list: List[str], titles: List[str]
    ) -> None:
        """Depth-first traversal for tree flattening.

        Args:
            node: Current node
            tree_list: Output list to append chunks
            titles: Current title path
        """
        level = node.level
        texts = node.texts
        children = node.children

        if level == 0 and texts:
            tree_list.append("\n".join(titles + texts))

        # Accumulate titles within depth
        if 1 <= level <= self.depth:
            path_titles = titles + texts
        else:
            path_titles = titles

        # Body outside depth limit becomes own chunk
        if level > self.depth and texts:
            tree_list.append("\n".join(path_titles + texts))
        # Leaf title within depth emits header-only section
        elif not children and (1 <= level <= self.depth):
            tree_list.append("\n".join(path_titles))

        for child in children:
            self._dfs(child, tree_list, path_titles)


def tree_merge(
    bull: int,
    sections: List[Tuple[str, str]],
    depth: int,
) -> List[str]:
    """Merge sections using tree-based hierarchical structure.

    Ported from RAGFlow's tree_merge() in rag/nlp/__init__.py.
    This is the core algorithm for intelligent document chunking.

    Args:
        bull: Bullet pattern category index
        sections: List of (text, layout_type) tuples
        depth: Target depth for merging

    Returns:
        List of merged text chunks
    """
    if not sections or bull < 0:
        return [s[0] if isinstance(s, tuple) else s for s in sections]

    if isinstance(sections[0], str):
        sections = [(s, "") for s in sections]

    # Filter out position info and empty sections
    sections = [
        (t, o) for t, o in sections
        if t and len(t.split("@")[0].strip()) > 1
        and not re.match(r"[0-9]+$", t.split("@")[0].strip())
    ]

    def get_level(bull: int, section: Tuple[str, str]) -> Tuple[int, str]:
        """Get hierarchy level for a section."""
        text, layout = section
        text = re.sub(r"\u3000", " ", text).strip()

        for i, title in enumerate(BULLET_PATTERNS[bull]):
            if re.match(title, text.strip()):
                return i + 1, text
        else:
            if re.search(r"(title|head)", layout) and not not_title(text):
                return len(BULLET_PATTERNS[bull]) + 1, text
            else:
                return len(BULLET_PATTERNS[bull]) + 2, text

    level_set = set()
    lines = []

    for section in sections:
        level, text = get_level(bull, section)
        if not text.strip("\n"):
            continue
        lines.append((level, text))
        level_set.add(level)

    sorted_levels = sorted(list(level_set))

    if depth <= len(sorted_levels):
        target_level = sorted_levels[depth - 1]
    else:
        target_level = sorted_levels[-1] if sorted_levels else 1

    # Avoid body-level as target
    if target_level == len(BULLET_PATTERNS[bull]) + 2:
        target_level = sorted_levels[-2] if len(sorted_levels) > 1 else sorted_levels[0]

    root = Node(level=0, depth=target_level, texts=[])
    root.build_tree(lines)

    return [element for element in root.get_tree() if element]


def hierarchical_merge(
    bull: int,
    sections: List[Tuple[str, str]],
    depth: int,
) -> List[List[str]]:
    """Merge sections using hierarchical grouping.

    Ported from RAGFlow's hierarchical_merge() in rag/nlp/__init__.py.
    Groups sections by their hierarchy level.

    Args:
        bull: Bullet pattern category index
        sections: List of (text, layout_type) tuples
        depth: Target depth for merging

    Returns:
        List of grouped section chunks
    """
    if not sections or bull < 0:
        return []

    if isinstance(sections[0], str):
        sections = [(s, "") for s in sections]

    sections = [
        (t, o) for t, o in sections
        if t and len(t.split("@")[0].strip()) > 1
        and not re.match(r"[0-9]+$", t.split("@")[0].strip())
    ]

    bullets_size = len(BULLET_PATTERNS[bull])
    levels = [[] for _ in range(bullets_size + 2)]

    for i, (txt, layout) in enumerate(sections):
        for j, p in enumerate(BULLET_PATTERNS[bull]):
            if re.match(p, txt.strip()):
                levels[j].append(i)
                break
        else:
            if re.search(r"(title|head)", layout) and not not_title(txt):
                levels[bullets_size].append(i)
            else:
                levels[bullets_size + 1].append(i)

    sections_text = [t for t, _ in sections]

    def binary_search(arr: List[int], target: int) -> int:
        """Find largest index <= target."""
        if not arr:
            return -1
        if target > arr[-1]:
            return len(arr) - 1
        if target < arr[0]:
            return -1

        s, e = 0, len(arr)
        while e - s > 1:
            mid = (e + s) // 2
            if target > arr[mid]:
                s = mid
            elif target < arr[mid]:
                e = mid
            else:
                return mid - 1
        return s

    chunks = []
    read = [False] * len(sections_text)
    levels = levels[::-1]

    for i, arr in enumerate(levels[:depth]):
        for j in arr:
            if read[j]:
                continue
            read[j] = True
            chunks.append([j])

            if i + 1 == len(levels) - 1:
                continue

            for ii in range(i + 1, len(levels)):
                jj = binary_search(levels[ii], j)
                if jj < 0:
                    continue
                if levels[ii][jj] > chunks[-1][-1]:
                    chunks[-1].pop(-1)
                chunks[-1].append(levels[ii][jj])

            for ii in chunks[-1]:
                read[ii] = True

    if not chunks:
        return []

    # Convert indices to text
    for i in range(len(chunks)):
        chunks[i] = [sections_text[j] for j in chunks[i][::-1]]

    return chunks


def has_qbullet(
    reg: str,
    box: Dict[str, Any],
    last_box: Dict[str, Any],
    last_index: int,
    last_bull: Optional[Any],
    bull_x0_list: List[float],
) -> Tuple[Optional[Any], int]:
    """Position-aware question bullet detection.

    Ported from RAGFlow's has_qbullet() in rag/nlp/__init__.py.
    Uses positional information for more accurate bullet detection.

    Args:
        reg: Regex pattern for question bullets
        box: Current text box with 'text', 'x0', 'top', 'layout_type'
        last_box: Previous text box
        last_index: Last detected bullet index
        last_bull: Last detected bullet match
        bull_x0_list: List of x0 positions for bullets

    Returns:
        Tuple of (match_object or None, index)
    """
    section = box.get("text", "")
    last_section = last_box.get("text", "")

    # Question pattern with optional question mark
    q_reg = r'(\w|\W)*?(?:？|\?|\n|$)+'
    full_reg = reg + q_reg

    has_bull = re.match(full_reg, section)
    if not has_bull:
        return None, last_index

    # Initialize position info if missing
    if "x0" not in last_box:
        last_box["x0"] = box.get("x0", 0)
    if "top" not in last_box:
        last_box["top"] = box.get("top", 0)

    box_x0 = box.get("x0", 0)
    box_top = box.get("top", 0)
    last_x0 = last_box.get("x0", 0)
    last_top = last_box.get("top", 0)

    # Check indentation consistency
    if last_bull and box_x0 - last_x0 > 10:
        return None, last_index

    if not last_bull and box_x0 >= last_x0 and box_top - last_top < 20:
        return None, last_index

    # Check against average bullet x0 position
    avg_bull_x0 = sum(bull_x0_list) / len(bull_x0_list) if bull_x0_list else box_x0
    if box_x0 - avg_bull_x0 > 10:
        return None, last_index

    # Extract and validate index
    index_str = has_bull.group(1) if has_bull.groups() else None
    index = index_int(index_str) if index_str else -1

    # Check if last section ends with colon (continuation)
    if last_section and last_section[-1] in ":：":
        return None, last_index

    # Validate sequence or special cases
    if not last_index or index >= last_index:
        bull_x0_list.append(box_x0)
        return has_bull, index

    # Question mark at end is valid
    if section and section[-1] in "?？":
        bull_x0_list.append(box_x0)
        return has_bull, index

    # Title layout type is valid
    if box.get("layout_type") == "title":
        bull_x0_list.append(box_x0)
        return has_bull, index

    # Check for question words (English only)
    pure_section = section.lstrip(re.match(reg, section).group()).lower()
    ask_patterns = r"(what|when|where|how|why|which|who|whose)"
    if re.match(ask_patterns, pure_section):
        bull_x0_list.append(box_x0)
        return has_bull, index

    return None, last_index


def qbullets_category(sections: List[str]) -> Tuple[int, str]:
    """Detect which question pattern set best matches the document.

    Ported from RAGFlow's qbullets_category() in rag/nlp/__init__.py.

    Args:
        sections: List of text sections to analyze

    Returns:
        Tuple of (pattern_index, pattern_regex) or (-1, "") if no match
    """
    hits = [0] * len(QUESTION_PATTERNS)

    for i, pattern in enumerate(QUESTION_PATTERNS):
        for sec in sections:
            if re.match(pattern, sec) and not not_bullet(sec):
                hits[i] += 1
                break

    maximum = 0
    result = -1

    for i, h in enumerate(hits):
        if h > maximum:
            result = i
            maximum = h

    if result >= 0:
        return result, QUESTION_PATTERNS[result]
    return -1, ""


def column_data_type(arr: List[Any]) -> Tuple[List[Any], str]:
    """Infer and convert column data types.

    Ported from RAGFlow's column_data_type() in rag/app/table.py.
    Performs runtime type conversion on column values.

    Args:
        arr: List of column values

    Returns:
        Tuple of (converted_values, type_name)
    """
    arr = list(arr)
    counts = {"int": 0, "float": 0, "text": 0, "datetime": 0, "bool": 0}

    def trans_datetime(s: str) -> Optional[str]:
        """Try to parse datetime string."""
        try:
            from dateutil.parser import parse as datetime_parse
            return datetime_parse(s.strip()).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

    def trans_bool(s: str) -> Optional[str]:
        """Convert boolean-like values (English only)."""
        s_str = str(s).strip()
        if re.match(r"(true|yes|\*|✓|✔|☑|✅|√)$", s_str, re.IGNORECASE):
            return "yes"
        if re.match(r"(false|no|⍻|×)$", s_str, re.IGNORECASE):
            return "no"
        return None

    trans = {
        "int": int,
        "float": float,
        "datetime": trans_datetime,
        "bool": trans_bool,
        "text": str,
    }

    float_flag = False
    for a in arr:
        if a is None:
            continue

        a_str = str(a).replace("%%", "")

        # Check int
        if re.match(r"[+-]?[0-9]+$", a_str) and not a_str.startswith("0"):
            try:
                if int(a_str) > 2**63 - 1:
                    float_flag = True
                    break
                counts["int"] += 1
            except ValueError:
                counts["text"] += 1
        # Check float
        elif re.match(r"[+-]?[0-9.]{,19}$", a_str) and not a_str.startswith("0"):
            counts["float"] += 1
        # Check bool (English only)
        elif re.match(
            r"(true|yes|\*|✓|✔|☑|✅|√|false|no|⍻|×)$",
            str(a), re.IGNORECASE
        ):
            counts["bool"] += 1
        # Check datetime
        elif trans_datetime(str(a)):
            counts["datetime"] += 1
        else:
            counts["text"] += 1

    # Determine type
    if float_flag:
        ty = "float"
    else:
        sorted_counts = sorted(counts.items(), key=lambda x: -x[1])
        ty = sorted_counts[0][0]

    # Convert values
    for i in range(len(arr)):
        if arr[i] is None:
            continue
        try:
            result = trans[ty](str(arr[i]))
            if result is not None:
                arr[i] = result
            else:
                arr[i] = None
        except Exception:
            arr[i] = None

    return arr, ty

import os
import re
from collections import defaultdict
from typing import List, Pattern

import utils.constants as constants
from utils.tools import get_real_path, resource_path
from utils.types import WhitelistMaps


def load_whitelist_maps(path: str = constants.whitelist_path) -> WhitelistMaps:
    """
    Load whitelist maps from the given path.
    Returns two dictionaries:
      - exact: channel_name -> list of exact whitelist entries
      - keywords: channel_name -> list of keyword whitelist entries
    The special key "" (empty string) is used for global entries.
    """

    exact = defaultdict(list)
    keywords = defaultdict(list)
    in_keyword_section = False

    real_path = get_real_path(resource_path(path))
    if not os.path.exists(real_path):
        return exact, keywords

    with open(real_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            s = line.strip()
            if not s or s.startswith("#"):
                continue

            if re.match(r"^\[.*\]$", s):
                in_keyword_section = s.upper() == "[KEYWORDS]"
                continue

            if "," in s:
                name, value = map(str.strip, s.split(",", 1))
                key = name or ""
            else:
                key = ""
                value = s

            if not value:
                continue

            if in_keyword_section:
                if value not in keywords[key]:
                    keywords[key].append(value)
            else:
                if value not in exact[key]:
                    exact[key].append(value)

    return exact, keywords


def is_url_whitelisted(data_map: WhitelistMaps, url: str, channel_name: str | None = None) -> bool:
    """
    Check if the given URL is whitelisted for the specified channel.
    If channel_name is None, only global whitelist entries are considered.
    1. Exact match (channel-specific)
    2. Exact match (global)
    3. Keyword match (channel-specific)
    4. Keyword match (global)
    5. If none match, return False
    """
    if not url or not data_map:
        return False

    exact_map, keyword_map = data_map
    channel_key = channel_name or ""

    def check_exact_for(key):
        for candidate in exact_map.get(key, []):
            if not candidate:
                continue
            c = candidate.strip()
            if c == url:
                return True
        return False

    if check_exact_for(channel_key) or check_exact_for(""):
        return True

    for kw in keyword_map.get(channel_key, []) + keyword_map.get("", []):
        if not kw:
            continue
        if kw in url:
            return True

    return False


def get_whitelist_url(data_map: WhitelistMaps, channel_name: str | None = None) -> List[str]:
    """
    Get the list of whitelisted URLs for the specified channel.
    If channel_name is None, only global whitelist entries are considered.
    """
    exact_map, _ = data_map
    channel_key = channel_name or ""
    whitelist_urls = set()

    for candidate in exact_map.get(channel_key, []) + exact_map.get("", []):
        c = candidate.strip()
        if c:
            whitelist_urls.add(c)

    return list(whitelist_urls)


def get_whitelist_total_count(data_map: WhitelistMaps) -> int:
    """
    Get the total count of unique whitelist entries across all channels.
    """
    exact_map, keyword_map = data_map
    unique_entries = set()

    for entries in exact_map.values():
        for entry in entries:
            unique_entries.add(entry.strip())

    for entries in keyword_map.values():
        for entry in entries:
            unique_entries.add(entry.strip())

    return len(unique_entries)


def get_section_entries(path: str = constants.whitelist_path, section: str = "WHITELIST",
                        pattern: Pattern[str] = None) -> tuple[List[str], List[str]]:
    """
    Get URLs from a specific section in the whitelist file.
    Returns a tuple: (inside_section_list, outside_section_list).
    """
    real_path = get_real_path(resource_path(path))
    if not os.path.exists(real_path):
        return [], []

    inside: List[str] = []
    outside: List[str] = []
    in_section = False
    header_re = re.compile(r"^\[.*\]$")

    with open(real_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            s = line.strip()
            if not s:
                continue

            if header_re.match(s):
                in_section = s.upper() == f"[{section.upper()}]"
                continue

            if s.startswith("#"):
                continue

            if s:
                target = inside if in_section else outside
                if pattern:
                    match = pattern.search(s)
                    if match:
                        target.append(match.group())
                else:
                    target.append(s)

    return inside, outside

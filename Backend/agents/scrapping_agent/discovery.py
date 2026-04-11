from __future__ import annotations

from typing import Set, Tuple, List

from config import CATEGORY_SEEDS
from wikihow_api import resolve_category_title, iter_category_members, title_to_url
from utils import normalize_url


def _seed_url_to_category_title(seed_url: str) -> str | None:
    marker = "/Category:"
    if marker not in seed_url:
        return None
    slug = seed_url.split(marker, 1)[1].strip("/")
    if not slug:
        return None
    return f"Category:{slug.replace('-', ' ')}"

def discover_category_graph_api(
    desired_category_name: str,
    max_categories_to_expand: int = 400,
) -> Tuple[str | None, Set[str], Set[str]]:
    """
    desired_category_name: your canonical label like "HVAC" or "Electrical"
    returns: (resolved_category_title, category_urls, article_urls)
    """
    resolved = resolve_category_title(desired_category_name)
    if not resolved:
        resolved = _seed_url_to_category_title(CATEGORY_SEEDS.get(desired_category_name, ""))
        if resolved:
            print(
                f"[discovery:{desired_category_name}] "
                f"falling back to configured seed category {resolved}"
            )
    if not resolved:
        return None, set(), set()

    to_expand = [resolved]
    seen = set()
    category_urls: Set[str] = set()
    article_urls: Set[str] = set()

    while to_expand and len(seen) < max_categories_to_expand:
        cat_title = to_expand.pop(0)
        if cat_title in seen:
            continue
        seen.add(cat_title)

        for m in iter_category_members(cat_title, cmtype=("page", "subcat")):
            if m.ns == 14 and m.title.startswith("Category:"):
                u = normalize_url(title_to_url(m.title))
                category_urls.add(u)
                if m.title not in seen:
                    to_expand.append(m.title)
            elif m.ns == 0:
                u = normalize_url(title_to_url(m.title))
                article_urls.add(u)

    return resolved, category_urls, article_urls

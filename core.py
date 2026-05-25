from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
import collections
from typing import Iterable, List, Optional, Sequence, Tuple

import pandas as pd


PATTERN_COLUMNS = ["id", "access_resource_id", "url_pattern", "created", "updated"]
RESOURCE_COLUMNS = ["id", "name", "access_resource_group_id", "level", "created", "updated"]

ACTION_WORDS = {
    "get", "fetch", "create", "edit", "update", "delete", "remove", "add",
    "search", "view", "open", "close", "preview", "print", "assign", "allocate",
    "approve", "reject", "cancel", "hold", "unhold", "upload", "download",
    "show", "list", "run", "check", "complete", "discard", "edit", "manage",
}

GENERIC_WORDS = {
    "data", "admin", "oms", "api", "v1", "v2", "tasks", "task", "report", "reports",
    "system", "default", "internal", "service", "services", "show", "view", "get",
    "fetch", "create", "edit", "update", "search", "add", "remove", "open", "close",
    "preview", "print", "assign", "allocate", "approve", "reject", "cancel", "hold",
    "unhold", "upload", "download", "list", "run", "check", "complete", "discard",
}

STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "to", "of", "in", "on", "with", "from",
    "by", "is", "are", "be", "as", "at", "it", "this", "that", "all", "any",
    "access", "resource", "resources", "required", "need", "needed", "help",
    "helps", "helping", "activity", "activities", "doing", "do", "perform",
    "performing", "issue", "issues", "check", "please", "can", "could", "would",
}

TOKEN_RE = re.compile(r"[a-z0-9]+")


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def _parse_pipe_row(line: str) -> Optional[List[str]]:
    line = line.strip()
    if not line.startswith("|"):
        return None
    # separator rows such as |----|----|
    if re.fullmatch(r"\|[\s\-:\+\|]+\|?", line):
        return None
    parts = [p.strip() for p in line.strip("|").split("|")]
    return parts


def parse_master_text(text: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Parse the single master file into:
      1) access patterns table
      2) access resources table

    The file contains two pipe-style sections:
      - url_pattern mapping table
      - access resource master table
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]

    pattern_rows: List[List[str]] = []
    resource_rows: List[List[str]] = []
    section = None

    for ln in lines:
        stripped = ln.strip()

        if "access_resource_id" in stripped and "url_pattern" in stripped:
            section = "patterns"
            continue
        if "access_resource_group_id" in stripped and "level" in stripped and "name" in stripped:
            section = "resources"
            continue

        row = _parse_pipe_row(stripped)
        if not row:
            continue

        if section == "patterns":
            # expected: id | access_resource_id | url_pattern | created | updated
            if len(row) >= 5:
                pattern_rows.append(row[:5])
        elif section == "resources":
            # expected: id | name | access_resource_group_id | level | created | updated
            if len(row) >= 6:
                resource_rows.append(row[:6])

    patterns = pd.DataFrame(pattern_rows, columns=PATTERN_COLUMNS) if pattern_rows else pd.DataFrame(columns=PATTERN_COLUMNS)
    resources = pd.DataFrame(resource_rows, columns=RESOURCE_COLUMNS) if resource_rows else pd.DataFrame(columns=RESOURCE_COLUMNS)

    patterns = normalize_access_patterns(patterns)
    resources = normalize_access_resources(resources)
    return patterns, resources


def load_master_file(uploaded_file=None, default_path: Optional[str | Path] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load from an uploaded file or a bundled default file.
    """
    if uploaded_file is not None:
        raw = uploaded_file.getvalue()
        text = raw.decode("utf-8", errors="ignore")
        return parse_master_text(text)

    if default_path is not None:
        text = Path(default_path).read_text(errors="ignore")
        return parse_master_text(text)

    return pd.DataFrame(columns=PATTERN_COLUMNS), pd.DataFrame(columns=RESOURCE_COLUMNS)


def normalize_access_patterns(df: pd.DataFrame) -> pd.DataFrame:
    df = _clean_columns(df)
    rename_map = {}
    if "access_resource" in df.columns and "access_resource_id" not in df.columns:
        rename_map["access_resource"] = "access_resource_id"
    if "pattern" in df.columns and "url_pattern" not in df.columns:
        rename_map["pattern"] = "url_pattern"
    if rename_map:
        df = df.rename(columns=rename_map)

    for col in ["id", "access_resource_id"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    if "url_pattern" in df.columns:
        df["url_pattern"] = df["url_pattern"].astype(str).str.strip()

    return df


def normalize_access_resources(df: pd.DataFrame) -> pd.DataFrame:
    df = _clean_columns(df)
    rename_map = {}
    if "resource_name" in df.columns and "name" not in df.columns:
        rename_map["resource_name"] = "name"
    if "parent" in df.columns and "access_resource_group_id" not in df.columns:
        rename_map["parent"] = "access_resource_group_id"
    if "module" in df.columns and "level" not in df.columns:
        rename_map["module"] = "level"
    if rename_map:
        df = df.rename(columns=rename_map)

    for col in ["id", "access_resource_group_id"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    if "name" in df.columns:
        df["name"] = df["name"].astype(str).str.strip()
    if "level" in df.columns:
        df["level"] = df["level"].astype(str).str.strip()

    return df


def tokenize(text: str) -> List[str]:
    tokens = TOKEN_RE.findall(str(text).lower())
    out = []
    for tok in tokens:
        if tok in STOPWORDS:
            continue
        if len(tok) <= 1:
            continue
        out.append(tok)
    return out


def _extract_url_tokens(url: str) -> List[str]:
    url = str(url).strip().lower()
    url = url.replace("*", " ")
    tokens = re.split(r"[^a-z0-9]+", url)
    out = []
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if tok in STOPWORDS or tok in GENERIC_WORDS:
            continue
        if tok.isdigit():
            continue
        out.append(tok)
    return out


def enrich_resources(resources: pd.DataFrame, patterns: pd.DataFrame) -> pd.DataFrame:
    if resources.empty:
        return resources.copy()

    res = resources.copy()
    pat = patterns.copy()
    if not pat.empty:
        pat["access_resource_id"] = pd.to_numeric(pat["access_resource_id"], errors="coerce").astype("Int64")

    labels = []
    keyword_lists = []
    sample_urls = []
    url_counts = []

    for _, row in res.iterrows():
        rid = row["id"]
        rid_patterns = pat[pat["access_resource_id"] == rid] if not pat.empty else pd.DataFrame()
        urls = rid_patterns["url_pattern"].dropna().astype(str).tolist() if not rid_patterns.empty else []

        # Build a friendly label from resource name + URLs.
        name_tokens = [t.lower() for t in re.split(r"[_\s]+", str(row.get("name", ""))) if t]
        name_tokens = [t for t in name_tokens if t not in GENERIC_WORDS and t not in STOPWORDS]
        url_tokens = []
        for u in urls:
            url_tokens.extend(_extract_url_tokens(u))

        counts = {}
        for tok in name_tokens + url_tokens:
            counts[tok] = counts.get(tok, 0) + 1

        # Prefer name tokens, then repeated url tokens.
        ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        keywords = [tok for tok, _ in ordered if tok not in ACTION_WORDS][:4]
        if not keywords:
            keywords = name_tokens[:2] or url_tokens[:2] or [f"access-{rid}"]

        # Friendly label: prefer the strongest URL tokens, then fall back to the resource name.
        label_parts = []
        token_counts = collections.Counter(
            t for t in url_tokens if t not in ACTION_WORDS and t not in GENERIC_WORDS
        )
        for tok, _ in token_counts.most_common(2):
            label_parts.append(tok)
        if not label_parts and name_tokens:
            label_parts = name_tokens[:2]
        elif len(label_parts) == 1 and name_tokens:
            for tok in name_tokens:
                if tok not in label_parts and tok not in GENERIC_WORDS:
                    label_parts.append(tok)
                    break
        if not label_parts:
            label_parts = keywords[:2]
        label = " / ".join(p.replace("_", " ").title() for p in label_parts) if label_parts else f"Access {rid}"

        labels.append(label)
        keyword_lists.append(keywords)
        sample_urls.append(urls[:5])
        url_counts.append(len(urls))

    res["friendly_label"] = labels
    res["keywords"] = keyword_lists
    res["url_count"] = url_counts
    res["sample_urls"] = sample_urls

    return res


def _join_patterns_resources(patterns: pd.DataFrame, resources: pd.DataFrame) -> pd.DataFrame:
    if patterns.empty:
        return patterns.copy()
    df = patterns.copy()
    if not resources.empty:
        res = resources.rename(columns={"id": "access_resource_id"})
        keep_cols = [c for c in ["access_resource_id", "name", "friendly_label", "level", "access_resource_group_id", "keywords", "url_count"] if c in res.columns]
        df = df.merge(res[keep_cols].drop_duplicates("access_resource_id"), on="access_resource_id", how="left")
    return df


def build_index(patterns: pd.DataFrame, resources: pd.DataFrame) -> pd.DataFrame:
    if patterns.empty and resources.empty:
        return pd.DataFrame()
    resources = enrich_resources(resources, patterns)
    return _join_patterns_resources(patterns, resources)


def resource_details(access_resource_id: int | str, patterns: pd.DataFrame, resources: pd.DataFrame) -> dict:
    rid = int(access_resource_id)
    res = enrich_resources(resources, patterns)
    row = res[res["id"] == rid]
    urls = patterns[pd.to_numeric(patterns["access_resource_id"], errors="coerce") == rid].copy() if not patterns.empty else pd.DataFrame()

    if row.empty:
        return {
            "id": rid,
            "name": None,
            "friendly_label": f"Access {rid}",
            "level": None,
            "group_id": None,
            "url_count": int(len(urls)),
            "urls": urls,
            "keywords": [],
            "description": f"Access resource {rid} controls {len(urls)} route(s).",
        }

    r = row.iloc[0]
    name = str(r.get("name", "")).strip()
    friendly_label = str(r.get("friendly_label", name or f"Access {rid}"))
    level = r.get("level", None)
    group_id = r.get("access_resource_group_id", None)
    keywords = r.get("keywords", [])

    description = f"{friendly_label} is used by {len(urls)} route(s)."
    if name and name != friendly_label:
        description = f"{name} ({friendly_label}) is used by {len(urls)} route(s)."

    return {
        "id": rid,
        "name": name,
        "friendly_label": friendly_label,
        "level": level,
        "group_id": group_id,
        "url_count": int(len(urls)),
        "urls": urls,
        "keywords": keywords if isinstance(keywords, list) else [],
        "description": description,
    }


def explain_access(access_resource_id: int | str, patterns: pd.DataFrame, resources: pd.DataFrame) -> str:
    details = resource_details(access_resource_id, patterns, resources)
    parts = [f"Access {details['id']}"]
    if details.get("name"):
        parts.append(f"{details['name']}")
    if details.get("level"):
        parts.append(f"module {details['level']}")
    parts.append(f"covers {details['url_count']} route(s)")
    return " • ".join(parts)


def search_resources(query: str, patterns: pd.DataFrame, resources: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    resources = enrich_resources(resources, patterns)
    if resources.empty:
        return pd.DataFrame()

    q = query.strip().lower()
    q_tokens = set(tokenize(q))
    q_tokens |= set(_extract_url_tokens(q))
    try:
        q_int = int(q)
    except Exception:
        q_int = None

    rows = []
    for _, r in resources.iterrows():
        rid = int(r["id"])
        rid_patterns = patterns[pd.to_numeric(patterns["access_resource_id"], errors="coerce") == rid] if not patterns.empty else pd.DataFrame()
        urls = rid_patterns["url_pattern"].dropna().astype(str).tolist() if not rid_patterns.empty else []
        haystack = " ".join([str(r.get("name", "")), str(r.get("friendly_label", "")), str(r.get("level", ""))] + urls).lower()

        score = 0
        if q_int is not None and q_int == rid:
            score += 1000
        for tok in q_tokens:
            if tok and tok in haystack:
                score += 5
        # Slight bonus for URL hits and name hits
        if any(tok in str(r.get("name", "")).lower() for tok in q_tokens):
            score += 10
        if any(tok in str(r.get("friendly_label", "")).lower() for tok in q_tokens):
            score += 8
        if any(tok in " ".join(urls).lower() for tok in q_tokens):
            score += 6

        if score > 0 or not q_tokens:
            rows.append({
                "id": rid,
                "name": r.get("name", ""),
                "friendly_label": r.get("friendly_label", ""),
                "level": r.get("level", ""),
                "group_id": r.get("access_resource_group_id", ""),
                "url_count": len(urls),
                "score": score,
                "sample_urls": urls[:4],
            })

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out.sort_values(["score", "url_count", "id"], ascending=[False, False, True]).head(limit).reset_index(drop=True)
    return out


def related_resources(access_resource_id: int | str, patterns: pd.DataFrame, resources: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    resources = enrich_resources(resources, patterns)
    rid = int(access_resource_id)
    base = resources[resources["id"] == rid]
    if base.empty:
        return pd.DataFrame()
    base = base.iloc[0]
    base_level = str(base.get("level", "")).lower()
    base_group = base.get("access_resource_group_id", None)
    base_keywords = set(base.get("keywords", []) or [])

    rows = []
    for _, r in resources.iterrows():
        other_id = int(r["id"])
        if other_id == rid:
            continue
        score = 0
        if str(r.get("level", "")).lower() == base_level and base_level:
            score += 3
        if pd.notna(base_group) and pd.notna(r.get("access_resource_group_id", None)) and int(r.get("access_resource_group_id")) == int(base_group):
            score += 5
        other_kw = set(r.get("keywords", []) or [])
        overlap = len(base_keywords & other_kw)
        score += overlap * 2
        if score > 0:
            rows.append({
                "id": other_id,
                "name": r.get("name", ""),
                "friendly_label": r.get("friendly_label", ""),
                "level": r.get("level", ""),
                "group_id": r.get("access_resource_group_id", ""),
                "score": score,
            })

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["score", "id"], ascending=[False, True]).head(limit).reset_index(drop=True)


def module_options(resources: pd.DataFrame) -> List[str]:
    if resources.empty or "level" not in resources.columns:
        return []
    vals = [str(v).strip() for v in resources["level"].dropna().tolist() if str(v).strip()]
    return ["All"] + sorted(set(vals))


def resource_options(resources: pd.DataFrame, module: str = "All") -> pd.DataFrame:
    if resources.empty:
        return pd.DataFrame()
    df = enrich_resources(resources, pd.DataFrame(columns=PATTERN_COLUMNS))
    if module and module != "All" and "level" in df.columns:
        df = df[df["level"].astype(str) == module]
    return df.sort_values(["friendly_label", "id"], ascending=[True, True]).reset_index(drop=True)


def urls_for_resource(access_resource_id: int | str, patterns: pd.DataFrame) -> pd.DataFrame:
    rid = int(access_resource_id)
    if patterns.empty:
        return pd.DataFrame(columns=PATTERN_COLUMNS)
    df = patterns[pd.to_numeric(patterns["access_resource_id"], errors="coerce") == rid].copy()
    return df.sort_values(["url_pattern", "id"], ascending=[True, True]).reset_index(drop=True)


def export_resource_csv(access_resource_id: int | str, patterns: pd.DataFrame, resources: pd.DataFrame) -> pd.DataFrame:
    d = resource_details(access_resource_id, patterns, resources)
    urls = d["urls"]
    if urls.empty:
        return pd.DataFrame([{
            "access_resource_id": d["id"],
            "resource_name": d.get("name", ""),
            "friendly_label": d.get("friendly_label", ""),
            "level": d.get("level", ""),
            "group_id": d.get("group_id", ""),
            "url_pattern": "",
        }])
    out = urls.copy()
    out["resource_name"] = d.get("name", "")
    out["friendly_label"] = d.get("friendly_label", "")
    out["level"] = d.get("level", "")
    out["group_id"] = d.get("group_id", "")
    return out


def preview_tables(patterns: pd.DataFrame, resources: pd.DataFrame, n: int = 20) -> Tuple[pd.DataFrame, pd.DataFrame]:
    resources = enrich_resources(resources, patterns)
    p = patterns.head(n).copy() if not patterns.empty else pd.DataFrame()
    r = resources.head(n).copy() if not resources.empty else pd.DataFrame()
    return p, r

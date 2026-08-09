import hashlib
import re


def normalize_source_identifier(source_path: str | None, title: str) -> str:
    source = (source_path or title).replace("\\", "/").rsplit("/", 1)[-1]
    source = re.sub(r"\.(md|markdown|txt|pdf)$", "", source.lower())
    return re.sub(r"[^a-z0-9]+", "_", source).strip("_") or "document"


def stable_passage_key(
    *,
    source_path: str | None,
    title: str,
    version: str | None,
    content: str,
) -> str:
    source = normalize_source_identifier(source_path, title)
    normalized_content = " ".join(content.lower().split())
    stable_version = version or "unversioned"
    digest_input = f"{source}\n{stable_version}\n{normalized_content}"
    digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:24]
    return f"{source}:{stable_version}:{digest}"

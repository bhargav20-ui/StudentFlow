import ast
import json
import math
import operator
import re

from .storage import load_documents, RESULTS_DIR

_ALLOWED = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
    ast.UAdd: operator.pos, ast.Mod: operator.mod,
}
_RUN_ID = re.compile(r"^[0-9a-fA-F-]{36}$")


def safe_calculate(expression):
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Expression must be a non-empty string")
    if len(expression) > 100:
        raise ValueError("Expression too long")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise ValueError("Invalid arithmetic expression") from exc
    if sum(1 for _ in ast.walk(tree)) > 40:
        raise ValueError("Expression is too complex")

    def walk(node, depth=0):
        if depth > 12:
            raise ValueError("Expression is too deeply nested")
        if isinstance(node, ast.Expression):
            return walk(node.body, depth + 1)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
            if abs(value) > 1e100:
                raise ValueError("Number too large")
            return value
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED:
            left, right = walk(node.left, depth + 1), walk(node.right, depth + 1)
            if isinstance(node.op, ast.Pow) and (abs(right) > 8 or abs(left) > 1e12):
                raise ValueError("Exponentiation exceeds the allowed limit")
            try:
                value = _ALLOWED[type(node.op)](left, right)
            except (ArithmeticError, OverflowError) as exc:
                raise ValueError("Arithmetic operation is not valid") from exc
            if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 1e100:
                raise ValueError("Result is outside the allowed range")
            return value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED:
            return _ALLOWED[type(node.op)](walk(node.operand, depth + 1))
        raise ValueError("Only basic arithmetic is allowed")

    return walk(tree)


def search_sources(query, limit=5):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query must be non-empty")
    try:
        limit = max(1, min(int(limit), 10))
    except (TypeError, ValueError):
        raise ValueError("Limit must be an integer")
    terms = {word.lower() for word in query.split() if len(word) > 2}
    if not terms:
        return []
    found = []
    for document in load_documents():
        text = (document.get('title', '') + ' ' + document.get('text', '')).lower()
        overlap = sum(term in text for term in terms)
        if overlap:
            found.append({**document, "relevance": round(overlap / len(terms), 3)})
    return sorted(found, key=lambda item: item['relevance'], reverse=True)[:limit]


def get_document(document_id):
    return next((doc for doc in load_documents() if doc.get('document_id') == document_id), {"error": "document_not_found"})


def _validated_run_path(run_id, suffix):
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise ValueError("Invalid run ID")
    return RESULTS_DIR / f"{run_id}{suffix}"


def save_evidence(run_id, evidence):
    if not isinstance(evidence, list) or len(evidence) > 100:
        raise ValueError("Evidence must be a list containing at most 100 records")
    path = _validated_run_path(run_id, "_evidence.json")
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True, "count": len(evidence)}


def get_run_metrics(run_id):
    path = _validated_run_path(run_id, ".json")
    return json.loads(path.read_text(encoding="utf-8")).get('metrics', {}) if path.exists() else {"error": "run_not_found"}

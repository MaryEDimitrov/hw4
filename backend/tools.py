"""Database tools available to the Campus Customs shopping agent."""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
from pydantic_ai import RunContext
try:
    from .models import ProductDetails, ProductSearchHit, StockLookupResult
except ImportError:  # Supports direct imports when Uvicorn runs from backend/.
    from models import ProductDetails, ProductSearchHit, StockLookupResult

@dataclass
class AgentDeps:
    db_path: Path
    user_id: int | None = None
    user_name: str | None = None
    user_email: str | None = None
    page_context: str | None = None

def _connect(path: Path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def write_audit_event(path: Path, event_type: str, user_id: int | None = None, details: dict | None = None) -> None:
    """Write non-sensitive operational metadata to SQLite and append-only JSONL."""
    safe_details = details or {}
    with _connect(path) as conn:
        conn.execute(
            'INSERT INTO audit_events (user_id,event_type,details_json) VALUES (?,?,?)',
            (user_id, event_type, json.dumps(safe_details, separators=(',', ':'))),
        )
        conn.commit()
    audit_path = path.parent.parent / 'output' / 'audit_trail.json'
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    stop_reason = 'completed' if event_type.endswith('completed') else 'error' if event_type.endswith('failed') else 'tool_returned'
    event = {
        'time': datetime.now(timezone.utc).isoformat(),
        'tool_name': event_type,
        'args': safe_details,
        'result': {'recorded': True},
        'stop_reason': stop_reason,
    }
    with audit_path.open('a', encoding='utf-8') as audit_file:
        audit_file.write(json.dumps(event, separators=(',', ':')) + '\n')

def _json_list(value: str | None) -> list[str]:
    try:
        result = json.loads(value or '[]')
        return [str(item) for item in result] if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []

async def search_products(ctx: RunContext[AgentDeps], query: str, limit: int = 6) -> list[ProductSearchHit]:
    """Search product names, types, descriptions, colors, and tags. Use for shopping recommendations."""
    terms = [term.lower() for term in query.split() if term.strip()][:12]
    limit = max(1, min(limit, 10))
    with _connect(ctx.deps.db_path) as conn:
        rows = conn.execute('SELECT product_id,name,garment_type,description,colors,search_tags,image_file_path,price FROM catalogue').fetchall()
    scored = []
    for row in rows:
        haystack = ' '.join(str(row[key]) for key in ('name', 'garment_type', 'description', 'colors', 'search_tags')).lower()
        score = sum(term in haystack for term in terms)
        if score:
            scored.append((score, ProductSearchHit(product_id=row['product_id'], name=row['name'], garment_type=row['garment_type'], price=row['price'], description=row['description'], image_file_path=row['image_file_path'])))
    scored.sort(key=lambda item: (-item[0], item[1].name))
    results = [hit for _, hit in scored[:limit]]
    write_audit_event(ctx.deps.db_path, 'tool.search_products', ctx.deps.user_id, {'query_length': len(query), 'limit': limit, 'result_count': len(results)})
    return results

async def get_product_details(ctx: RunContext[AgentDeps], product_id: str) -> ProductDetails:
    """Get full product copy, colors, price, and size availability for one product."""
    with _connect(ctx.deps.db_path) as conn:
        row = conn.execute('SELECT product_id,name,garment_type,description,colors,price FROM catalogue WHERE product_id=?', (product_id,)).fetchone()
        if row is None:
            write_audit_event(ctx.deps.db_path, 'tool.get_product_details.not_found', ctx.deps.user_id, {'product_id': product_id[:120]})
            return ProductDetails(product_id=product_id, name='Unknown product', garment_type='', description='Product not found.', price=0)
    sizes = conn.execute('SELECT size,quantity FROM inventory WHERE product_id=? ORDER BY id', (product_id,)).fetchall()
    stock_by_size = [f"{size['size']} ({size['quantity']} in stock)" if size['quantity'] > 0 else f"{size['size']} (out of stock)" for size in sizes]
    write_audit_event(ctx.deps.db_path, 'tool.get_product_details', ctx.deps.user_id, {'product_id': product_id[:120], 'size_count': len(stock_by_size)})
    return ProductDetails(product_id=row['product_id'], name=row['name'], garment_type=row['garment_type'], description=row['description'], colors=_json_list(row['colors']), price=row['price'], sizes=stock_by_size)

async def check_stock(ctx: RunContext[AgentDeps], product_id: str, size: str | None = None) -> StockLookupResult:
    """Look up exact inventory quantities for a product, optionally for one size."""
    query = 'SELECT size,quantity FROM inventory WHERE product_id=?'
    params: tuple[str, ...] = (product_id,)
    if size:
        query += ' AND lower(size)=lower(?)'
        params += (size,)
    query += ' ORDER BY id'
    with _connect(ctx.deps.db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    if not rows:
        write_audit_event(ctx.deps.db_path, 'tool.check_stock.not_found', ctx.deps.user_id, {'product_id': product_id[:120], 'requested_size': size[:20] if size else None})
        return StockLookupResult(product_id=product_id, requested_size=size, stock=["No inventory record was found."])
    result = [f"{row['size']}: {row['quantity']} in stock" if row['quantity'] > 0 else f"{row['size']}: out of stock" for row in rows]
    write_audit_event(ctx.deps.db_path, 'tool.check_stock', ctx.deps.user_id, {'product_id': product_id[:120], 'requested_size': size[:20] if size else None, 'size_count': len(result)})
    return StockLookupResult(product_id=product_id, requested_size=size, stock=result)

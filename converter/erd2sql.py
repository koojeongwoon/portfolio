#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERD → SQL (MariaDB/MySQL) — SQL-only emitter
- 입력: PlantUML(.puml, entity {...}, "field : TYPE" 지원) / (옵션) Mermaid(erDiagram)
- 도메인 규칙: 외부 JSON/YAML 설정파일로 타입/default/check/인덱스 등 적용 가능
- 산출: 순수 SQL (CREATE TABLE → 인덱스/체크 → 외래키)

우선순위(컬럼 타입 결정):
  1) .puml의 명시 타입 : "field : TYPE"
  2) config.entities.<table>.fields.<col>.sql_type
  3) 도메인(domain) 규칙 (config.domains.*)
  4) 휴리스틱(필드명 기반)

사용 예)
  python3 erd2sql.py ../product/db/db.puml \
  --format plantuml \
  --config core_domains.yaml \
  --config ../product/db/product_domains.yaml \
  --outdir ../product/db/sql \
  --name schema
"""

from __future__ import annotations
import re, sys, os, argparse, json, fnmatch
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    import yaml  # 선택사항
    HAS_YAML = True
except Exception:
    HAS_YAML = False

# =========================
# 데이터 모델
# =========================
@dataclass
class FieldDef:
    name: str
    is_pk: bool = False
    is_fk: bool = False
    annotations: List[str] = field(default_factory=list)
    declared_type: Optional[str] = None  # .puml/.mmd에 명시된 타입
    domain_tag: Optional[str] = None     # <<D:Status(220)>> 같은 도메인 태그

@dataclass
class EntityDef:
    name: str
    fields: List[FieldDef] = field(default_factory=list)
    pks: List[str] = field(default_factory=list)
    fks: List[Tuple[str, str, str]] = field(default_factory=list)  # (fk_field, ref_table, ref_field)

# =========================
# 설정 로더 (domains.json / .yaml)
# =========================
def load_config(path: Optional[str]) -> dict:
    if not path:
        return {}
    if not os.path.exists(path):
        raise FileNotFoundError(f"config file not found: {path}")
    _, ext = os.path.splitext(path.lower())
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    if ext in (".json",):
        return json.loads(data)
    if ext in (".yaml", ".yml"):
        if not HAS_YAML:
            raise RuntimeError("YAML config needs PyYAML. Install with: pip install pyyaml")
        return yaml.safe_load(data)
    # fallback
    try:
        return json.loads(data)
    except Exception:
        if HAS_YAML:
            return yaml.safe_load(data)
        raise ValueError("Unsupported config format. Use .json (recommended) or .yaml")

def get_cfg(d: dict, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

# =========================
# 타입 매핑 / 휴리스틱
# =========================
KNOWN_SQL_PREFIXES = (
    "BIGINT","INT","INTEGER","SMALLINT","TINYINT","FLOAT","DOUBLE","REAL",
    "DECIMAL","NUMERIC","CHAR","VARCHAR","TEXT","MEDIUMTEXT","LONGTEXT",
    "DATE","TIME","DATETIME","TIMESTAMP","BLOB","LONGBLOB","MEDIUMBLOB","ENUM"
)

def infer_type(field_name: str) -> str:
    fn = field_name.lower()
    if fn.endswith("_id") or fn in ("id","pk"):
        return "BIGINT UNSIGNED"
    if fn in ("price","compare_at_price","amount","min_price"):
        return "DECIMAL(12,2)"
    if "qty" in fn or fn in ("sort_order","score_popular","weight_gram"):
        return "INT"
    if fn == "slug":
        return "VARCHAR(220)"
    if fn in ("status",):
        return "VARCHAR(50)"
    if fn in ("name","brand_name","primary_cat","option_summary"):
        return "VARCHAR(200)"
    if fn in ("url","main_image_url","alt_text"):
        return "VARCHAR(500)"
    if fn in ("sku","barcode"):
        return "VARCHAR(80)"
    return "VARCHAR(255)"

def normalize_sql_type(decl: str, field_name: str) -> str:
    if not decl:
        return infer_type(field_name)
    up = decl.strip().upper()
    if any(up.startswith(p) for p in KNOWN_SQL_PREFIXES) or "UNSIGNED" in up:
        return up
    # generic → mapping
    m_v = re.match(r'VARCHAR\((\d+)\)', up)
    m_d = re.match(r'DECIMAL\((\d+)\s*,\s*(\d+)\)', up)
    if m_v: return f"VARCHAR({m_v.group(1)})"
    if m_d: return f"DECIMAL({m_d.group(1)},{m_d.group(2)})"
    if up in ("STRING",): return "VARCHAR(255)"
    if up in ("BOOLEAN","BOOL"): return "TINYINT(1)"
    if up in ("UUID",): return "CHAR(36)"
    if up in ("NUMBER",): return "DECIMAL(12,2)"
    return infer_type(field_name)

# =========================
# 파서 (PlantUML / Mermaid)
# =========================
PLANTUML_ENTITY_RE = re.compile(r'entity\s+(\w+)\s*\{(.*?)\}', re.DOTALL | re.MULTILINE)
PLANTUML_REL_RE    = re.compile(r'^\s*(\w+)\s+([|o}{\-\s]+)\s+(\w+)', re.MULTILINE)
DOMAIN_TAG_RE      = re.compile(r'^(?:D|DOMAIN)\s*:\s*([A-Za-z_]\w*(?:\([^)]*\))?)$', re.IGNORECASE)

def parse_plantuml(text: str) -> Dict[str, EntityDef]:
    entities: Dict[str, EntityDef] = {}
    for m in PLANTUML_ENTITY_RE.finditer(text):
        name, body = m.group(1), m.group(2)
        e = EntityDef(name=name)
        for raw in body.splitlines():
            line = raw.strip()
            if not line or line.startswith("'"):
                continue
            is_pk = False
            is_fk = False
            if line.startswith('*'):
                is_pk = True
                line = line[1:].strip()
            anns = re.findall(r'<<\s*([^>]+?)\s*>>', line)
            if any(a.upper()=="PK" for a in anns): is_pk = True
            if any(a.upper()=="FK" for a in anns): is_fk = True
            # 도메인 태그 추출 (<<D:Status(220)>>)
            dom_tag = None
            for a in anns:
                mm = DOMAIN_TAG_RE.match(a.strip())
                if mm:
                    dom_tag = mm.group(1)
                    break
            line = re.sub(r'<<[^>]+>>','',line).strip()
            # "필드 : 타입" 지원
            mt = re.match(r'([A-Za-z_]\w*)\s*:\s*([A-Za-z0-9_(),\s]+)$', line)
            declared_type = None
            if mt:
                field_name = mt.group(1)
                declared_type = mt.group(2).strip()
            else:
                field_name = re.split(r'[\s;]+', line)[0]
            if field_name:
                e.fields.append(FieldDef(field_name, is_pk, is_fk, anns, declared_type, dom_tag))
        e.pks = [f.name for f in e.fields if f.is_pk]
        entities[name] = e

    rels = []
    for m in PLANTUML_REL_RE.finditer(text):
        left, sym, right = m.groups()
        sym = "".join(sym.split())
        rels.append((left, sym, right))
    process_relationships(entities, rels)
    return entities

# Mermaid (선택)
MERMAID_HEADER_RE  = re.compile(r'\berDiagram\b', re.IGNORECASE)
MERMAID_BLOCK_RE   = re.compile(r'(\w+)\s*\{(.*?)\}', re.DOTALL | re.MULTILINE)
MERMAID_REL_RE     = re.compile(r'^\s*(\w+)\s+([|o}{\-\s]+)\s+(\w+)\s*(?::.*)?$', re.MULTILINE)

def parse_mermaid(text: str) -> Dict[str, EntityDef]:
    if not MERMAID_HEADER_RE.search(text):
        raise ValueError("Mermaid erDiagram header not found")
    entities: Dict[str, EntityDef] = {}
    for m in MERMAID_BLOCK_RE.finditer(text):
        name, body = m.group(1), m.group(2)
        e = EntityDef(name=name)
        for raw in body.splitlines():
            line = raw.strip()
            if not line or line.startswith("%"):
                continue
            tokens = re.split(r'\s+', line.split('"')[0].strip())
            if len(tokens) >= 2:
                decl_type, fname = tokens[0], tokens[1]
                flags = set(t.upper() for t in tokens[2:])
                is_pk = 'PK' in flags or fname.lower() in ('id', f"{name.lower()}_id")
                is_fk = 'FK' in flags
                e.fields.append(FieldDef(fname, is_pk, is_fk, list(flags), decl_type, None))
        explicit = [f.name for f in e.fields if f.is_pk]
        if explicit:
            e.pks = explicit
        else:
            for f in e.fields:
                if f.name.lower() in ('id', f"{name.lower()}_id"):
                    f.is_pk = True
                    e.pks = [f.name]
                    break
        entities[name] = e
    rels = []
    for m in MERMAID_REL_RE.finditer(text):
        left, sym, right = m.groups()
        sym = "".join(sym.split())
        rels.append((left, sym, right))
    process_relationships(entities, rels)
    return entities

# =========================
# 관계 처리
# =========================
def get_pk_name(entities: Dict[str, EntityDef], table: str) -> str:
    pks = entities[table].pks
    return pks[0] if pks else "id"

def ensure_field(entities: Dict[str, EntityDef], table: str, field: str, mark_fk: bool):
    e = entities[table]
    names = [f.name for f in e.fields]
    if field not in names:
        e.fields.insert(0, FieldDef(field, False, mark_fk, ["FK"] if mark_fk else [], None, None))

def process_relationships(entities: Dict[str, EntityDef], rels: List[Tuple[str,str,str]]):
    for left, sym, right in rels:
        if sym.endswith("o{"):
            if left == right:
                ref_pk = get_pk_name(entities, left)
                ensure_field(entities, right, "parent_id", True)
                entities[right].fks.append(("parent_id", left, ref_pk))
            else:
                fk_field = f"{left.lower()}_id"
                ensure_field(entities, right, fk_field, True)
                ref_pk = get_pk_name(entities, left)
                entities[right].fks.append((fk_field, left, ref_pk))
        elif sym.startswith("o{"):
            fk_field = f"{right.lower()}_id"
            ensure_field(entities, left, fk_field, True)
            ref_pk = get_pk_name(entities, right)
            entities[left].fks.append((fk_field, right, ref_pk))
        elif "||--||" in sym:
            left_pk = get_pk_name(entities, left)
            rnames = [f.name for f in entities[right].fields]
            fk_field = left_pk if left_pk in rnames else f"{left.lower()}_id"
            ensure_field(entities, right, fk_field, True)
            entities[right].fks.append((fk_field, left, left_pk))

# =========================
# 도메인 적용
# =========================
def parse_domain_call(s: str) -> Tuple[str, dict]:
    """
    'Slug(220)' -> ('Slug', {'p1': '220'})
    """
    m = re.match(r'^([A-Za-z_]\w*)\s*\(([^)]*)\)\s*$', s)
    if not m:
        return s.strip(), {}
    name = m.group(1).strip()
    args = [a.strip() for a in m.group(2).split(",") if a.strip() != ""]
    return name, {f"p{i+1}": v for i, v in enumerate(args)}

def resolve_domain_for_field(cfg: dict, ename: str, field: FieldDef) -> Tuple[Optional[str], dict, dict]:
    domains = get_cfg(cfg, "domains", default={})
    # 1) .puml 태그 <<D:...>>
    dom_raw = field.domain_tag
    # 2) 엔티티/필드 오버라이드
    dom_raw = dom_raw or get_cfg(cfg, "entities", ename, "fields", field.name, "domain")
    # 3) 패턴 적용
    if not dom_raw:
        fps = get_cfg(cfg, "field_patterns", default=[]) or []
        for fp in fps:
            pat = fp.get("match")
            dom = fp.get("domain")
            if pat and dom and fnmatch.fnmatch(field.name.lower(), pat.lower()):
                dom_raw = dom
                break
    # 4) declared_type이 도메인명과 같을 때
    if not dom_raw and field.declared_type:
        dt = field.declared_type.strip()
        if dt in domains:
            dom_raw = dt

    if not dom_raw:
        return None, {}, {}

    name, params = parse_domain_call(dom_raw)
    spec = domains.get(name)
    if not spec:
        return None, {}, {}

    # params 이름 매핑
    named = {}
    param_names = spec.get("params", [])
    if param_names:
        # p1, p2 ...를 순서대로 params 이름에 매핑
        for i, pname in enumerate(param_names):
            key = f"p{i+1}"
            if key in params:
                named[pname] = params[key]
    else:
    # 선언적 파라미터가 없으면 그대로 둠
        named = params

    # 기본값 보충(.puml에 없으면 defaults 사용)
    for k, v in (spec.get("defaults", {}) or {}).items():
        named.setdefault(k, str(v))

    return name, named, spec

def field_sql_type(cfg: dict, ename: str, field: FieldDef) -> str:
    # 1) .puml 명시 타입 (도메인명일 수도 있으니 도메인 우선 확인)
    if field.declared_type and field.declared_type.strip():
        dom_name, dom_params, dom_spec = resolve_domain_for_field(cfg, ename, field)
        if dom_name:
            t = dom_spec.get("sql_type")
            if t:
                return fill_template(t, field.name, dom_params)
        return normalize_sql_type(field.declared_type, field.name)
    # 2) 엔티티/필드 오버라이드
    ov_type = get_cfg(cfg, "entities", ename, "fields", field.name, "sql_type")
    if ov_type:
        return normalize_sql_type(ov_type, field.name)
    # 3) 도메인 규칙
    dom_name, dom_params, dom_spec = resolve_domain_for_field(cfg, ename, field)
    if dom_name:
        t = dom_spec.get("sql_type")
        if t:
            return fill_template(t, field.name, dom_params)
    # 4) 휴리스틱
    return infer_type(field.name)

def field_overrides(cfg: dict, ename: str, field: FieldDef) -> dict:
    """
    not_null / unique / default / check / index
    + 도메인 규칙에서의 default/index/unique/check 반영
    """
    ov = {"not_null": None, "unique": None, "default": None, "checks": [], "index": False}
    # entity/field override
    fcfg = get_cfg(cfg, "entities", ename, "fields", field.name, default={}) or {}
    if "not_null" in fcfg: ov["not_null"] = bool(fcfg["not_null"])
    if "unique"   in fcfg: ov["unique"]   = bool(fcfg["unique"])
    if "default"  in fcfg: ov["default"]  = str(fcfg["default"])

    # domain
    dom_name, dom_params, dom_spec = resolve_domain_for_field(cfg, ename, field)
    if dom_name:
        if "default" in dom_spec and ov["default"] is None:
            ov["default"] = dom_spec["default"]
        if dom_spec.get("unique") is True and ov["unique"] is None:
            ov["unique"] = True
        if dom_spec.get("index") is True:
            ov["index"] = True
        if "check" in dom_spec:
            ov["checks"].append(fill_template(dom_spec["check"], field.name, dom_params))
    return ov

def fill_template(tmpl: str, col: str, params: dict) -> str:
    s = tmpl.replace("{col}", f"`{col}`")
    for k, v in params.items():
        s = s.replace("{"+k+"}", str(v))
    return s

# =========================
# SQL 출력
# =========================
def emit_sql(entities: Dict[str, EntityDef], cfg: dict) -> str:
    engine  = get_cfg(cfg, "globals", "engine",  default="InnoDB")
    charset = get_cfg(cfg, "globals", "charset", default="utf8mb4")
    pk_auto = bool(get_cfg(cfg, "globals", "pk_auto_increment", default=True))
    fk_def_on_delete = get_cfg(cfg, "globals", "fk_on_delete", default="CASCADE")
    fk_def_on_update = get_cfg(cfg, "globals", "fk_on_update", default="CASCADE")

    pending_indexes = []  # (table, index_name, columns, unique)
    pending_checks  = []  # (table, expr, name)

    lines: List[str] = []
    lines.append("SET NAMES utf8mb4;")
    lines.append("SET FOREIGN_KEY_CHECKS=0;")
    lines.append("")

    # CREATE TABLE
    for ename, e in entities.items():
        cols: List[str] = []
        seen = set()
        for f in e.fields:
            if f.name in seen:
                continue
            seen.add(f.name)

            coltype = field_sql_type(cfg, ename, f)
            ov = field_overrides(cfg, ename, f)

            col = f"`{f.name}` {coltype}"
            if f.name in e.pks:
                col += " NOT NULL"
                if pk_auto and len(e.pks) == 1 and (f.name.endswith("_id") or f.name.lower()=="id"):
                    col += " AUTO_INCREMENT"
            else:
                if ov["not_null"] is True:
                    col += " NOT NULL"

            if ov["default"] is not None:
                col += f" DEFAULT {ov['default']}"

            cols.append(col)

            # post: unique/index/check
            if ov["unique"] is True:
                pending_indexes.append((ename, f"uk_{ename}_{f.name}", [f.name], True))
            if ov["index"] is True:
                pending_indexes.append((ename, f"ix_{ename}_{f.name}", [f.name], False))
            for i, expr in enumerate(ov["checks"], start=1):
                pending_checks.append((ename, expr, f"chk_{ename}_{f.name}_{i}"))

        constraints = []
        if e.pks:
            constraints.append("PRIMARY KEY (" + ", ".join(f"`{c}`" for c in e.pks) + ")")
        inner = "  " + ",\n  ".join(cols + constraints)
        lines.append(f"CREATE TABLE `{ename}` (\n{inner}\n) ENGINE={engine} DEFAULT CHARSET={charset};")
        lines.append("")

    # 전역 인덱스 (config.indexes)
    for idx in (get_cfg(cfg, "indexes", default=[]) or []):
        t = idx.get("table")
        cols = idx.get("columns", [])
        unique = bool(idx.get("unique", False))
        if t and cols:
            iname = idx.get("name") or f"{'uk' if unique else 'ix'}_{t}_" + "_".join(cols)
            pending_indexes.append((t, iname, cols, unique))

    # 엔티티별 인덱스 (config.entities.<table>.indexes)
    for ename, e in entities.items():
        einx = get_cfg(cfg, "entities", ename, "indexes", default=[]) or []
        for idx in einx:
            cols = idx.get("columns", [])
            unique = bool(idx.get("unique", False))
            if cols:
                iname = idx.get("name") or f"{'uk' if unique else 'ix'}_{ename}_" + "_".join(cols)
                pending_indexes.append((ename, iname, cols, unique))

    # FK 컬럼 인덱스(기본)
    for ename, e in entities.items():
        for (fk_field, _, _) in e.fks:
            iname = f"ix_{ename}_{fk_field}"
            pending_indexes.append((ename, iname, [fk_field], False))

    # Emit indexes (중복 제거)
    seen_idx = set()
    for t, iname, cols, unique in pending_indexes:
        key = (t, iname)
        if key in seen_idx:
            continue
        seen_idx.add(key)
        cols_sql = ", ".join(f"`{c}`" for c in cols)
        if unique:
            lines.append(f"ALTER TABLE `{t}` ADD UNIQUE `{iname}` ({cols_sql});")
        else:
            lines.append(f"ALTER TABLE `{t}` ADD INDEX `{iname}` ({cols_sql});")
    if pending_indexes:
        lines.append("")

    # Emit checks
    for t, expr, cname in pending_checks:
        lines.append(f"ALTER TABLE `{t}` ADD CONSTRAINT `{cname}` CHECK ({expr});")
    if pending_checks:
        lines.append("")

    # Foreign keys
    for ename, e in entities.items():
        for (fk_field, ref_table, ref_field) in e.fks:
            fcfg = get_cfg(cfg, "entities", ename, "fields", fk_field, "fk", default={}) or {}
            on_del = fcfg.get("on_delete", fk_def_on_delete)
            on_upd = fcfg.get("on_update", fk_def_on_update)
            lines.append(
                f"ALTER TABLE `{ename}` ADD CONSTRAINT `fk_{ename}_{fk_field}_{ref_table}` "
                f"FOREIGN KEY (`{fk_field}`) REFERENCES `{ref_table}`(`{ref_field}`) "
                f"ON DELETE {on_del} ON UPDATE {on_upd};"
            )
        if e.fks:
            lines.append("")

    lines.append("SET FOREIGN_KEY_CHECKS=1;")
    return "\n".join(lines)

# =========================
# 포맷 감지 & 메인
# =========================
def detect_format(text: str) -> str:
    if "erDiagram" in text:
        return "mermaid"
    if "@startuml" in text or "entity " in text:
        return "plantuml"
    return "auto"

def convert_entities(text: str, fmt: str="auto") -> Dict[str, EntityDef]:
    if fmt == "plantuml":
        return parse_plantuml(text)
    if fmt == "mermaid":
        return parse_mermaid(text)
    try:
        return parse_plantuml(text)
    except Exception:
        return parse_mermaid(text)

def sanitize_filename(name: str) -> str:
    base = re.sub(r'[^\w\-.]+', '_', name.strip())
    return base or "schema"

def now_kst_ts() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d_%H%M%S")

def derive_outfile(path_arg: str, base: Optional[str]) -> str:
    # base가 주어지면 그 이름을 쓰고, 아니면 입력 파일명(또는 'schema')
    stem = base or (os.path.splitext(os.path.basename(path_arg))[0] if path_arg != "-" else "schema")
    stem = sanitize_filename(stem)
    return f"{stem}_{now_kst_ts()}.sql"

def deep_merge(a: dict, b: dict) -> dict:
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            deep_merge(a[k], v)
        elif isinstance(v, list) and isinstance(a.get(k), list):
            a[k].extend(v)  # 단순 이어붙이기(중복 제거가 필요하면 여기서 처리)
        else:
            a[k] = v
    return a

def load_configs(paths: List[str]) -> dict:
    cfg = {}
    for p in paths:
        part = load_config(p)
        deep_merge(cfg, part)  # 뒤에 오는 파일이 이전 설정을 덮어씀/추가함
    return cfg

def main():
    ap = argparse.ArgumentParser(description="ERD(PlantUML/Mermaid) → SQL (MariaDB/MySQL) — SQL only")
    ap.add_argument("path", help="입력 파일 경로 또는 '-'(stdin)")
    ap.add_argument("--format", choices=["auto","plantuml","mermaid"], default="auto")
    ap.add_argument("--config", action="append", default=[], help="도메인/오버라이드 설정 파일 (여러 번 지정 가능)")
    ap.add_argument("--outdir", default=None, help="자동 타임스탬프 파일 저장 디렉터리")
    ap.add_argument("--name", default=None, help="파일명 접두(base) 지정 (확장자/타임스탬프는 자동)")
    args = ap.parse_args()

    # 입력
    if args.path == "-":
        text = sys.stdin.read()
    else:
        with open(args.path, "r", encoding="utf-8") as f:
            text = f.read()

    # 기존: cfg = load_config(args.config) if args.config else {}
    cfg = load_configs(args.config) if args.config else {}
    fmt = args.format if args.format != "auto" else detect_format(text)
    entities = convert_entities(text, fmt)

    sql = emit_sql(entities, cfg)

    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
        fname = derive_outfile(args.path, args.name)   # ← 자동: <base>_YYYYMMDD_HHMM.sql
        outpath = os.path.join(args.outdir, fname)
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(sql)
        sys.stdout.write(f"-- saved: {outpath}\n")
    else:
        # outdir 없으면 예전처럼 STDOUT (원하면 여기서도 timestamp 주석 등을 찍을 수 있음)
        sys.stdout.write(sql)

if __name__ == "__main__":
    main()
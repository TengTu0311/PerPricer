from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import pymysql
from sqlglot import exp, parse_one

from dbSettings import database
from dbUtils import connect, get_fields_of_all_tables


def _default_hash_fn(k: int) -> int:
    """Default hash-style perturbation: always add at least one tuple."""
    return k % 3 + 1


@dataclass(frozen=True)
class _Relation:
    table: str
    alias: str


class PerPricer:
    """
    Masking wrapper that perturbs tuples before delegating to an underlying pricer.

    The class follows the PerPricer framework: for each query, it determines how many
    additional tuples should satisfy the predicates, rewrites a subset of tuples to mimic
    those satisfying values, asks the base pricer for the price, and finally rolls the
    changes back. The base pricer can be either PVPricer (PBP) or QAPricer (IBP).
    """

    def __init__(
        self,
        base_pricer,
        hash_fn: Optional[Callable[[int], int]] = None,
        db_name: Optional[str] = None,
    ) -> None:
        self._base_pricer = base_pricer
        self._hash_fn = hash_fn or _default_hash_fn
        self._db_name = db_name or database

        table_list, size_map, field_map = get_fields_of_all_tables(database=self._db_name)
        self._table_sizes = size_map
        self._table_fields = field_map
        self._table_set = set(table_list)

        # Cache positive-price tuples for IBP (QAPricer) upfront if possible.
        self._ibp_positive_cache: Dict[str, Set[int]] = defaultdict(set)
        if hasattr(self._base_pricer, "support_sets"):
            for table, support_set in getattr(self._base_pricer, "support_sets").items():
                candidates: Set[int] = set()
                for entry in support_set:
                    # support tuple format: [attr, aid, bid, ...]
                    if len(entry) >= 3:
                        try:
                            candidates.add(int(entry[1]))
                        except (TypeError, ValueError):
                            continue
                        try:
                            candidates.add(int(entry[2]))
                        except (TypeError, ValueError):
                            continue
                self._ibp_positive_cache[table] = candidates

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def price_SQL_query(
        self,
        sql: str,
        *,
        include_real_price: bool = False,
        with_details: bool = False,
    ):
        """
        Return the masked price for `sql`. Optionally return the real price and
        perturbation details.
        """
        normalized_sql = self._normalize_sql(sql)

        real_price = None
        if include_real_price:
            real_price = self._base_pricer.price_SQL_query(normalized_sql)

        conn = connect(database=self._db_name)
        modifications: List[Dict[str, object]] = []
        try:
            modifications = self._apply_perturbation(conn, normalized_sql)
            conn.commit()
            masked_price = self._base_pricer.price_SQL_query(normalized_sql)
        finally:
            try:
                if modifications:
                    self._rollback(conn, modifications)
                    conn.commit()
            finally:
                conn.close()

        if include_real_price or with_details:
            result = {"masked_price": masked_price}
            if include_real_price:
                result["real_price"] = real_price
            if with_details:
                result["perturbations"] = modifications
            return result
        return masked_price

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize_sql(self, sql: str) -> str:
        stripped = sql.strip()
        if stripped.endswith(";"):
            stripped = stripped[:-1]
        return stripped

    def _apply_perturbation(
        self,
        conn: pymysql.connections.Connection,
        sql: str,
    ) -> List[Dict[str, object]]:
        """
        Modify the database so that additional tuples satisfy the query predicates.
        Returns a list of modifications for later rollback.
        """
        expression = parse_one(sql, read="mysql")
        base_expr = self._strip_non_predicate_clauses(expression)
        relations = self._extract_relations(base_expr)
        if not relations:
            return []

        qualifier_map = self._collect_qualifier_ids(conn, base_expr, relations)
        updates: List[Dict[str, object]] = []

        for relation in relations:
            table = relation.table
            alias = relation.alias

            if table not in self._table_set:
                continue

            qualifiers = qualifier_map.get(alias, set())
            k = len(qualifiers)
            extra = max(self._hash_fn(k), 0)
            if extra == 0:
                continue

            # Adjust by available capacity.
            capacity = max(self._table_sizes.get(table, 0) - k, 0)
            if capacity == 0:
                continue
            extra = min(extra, capacity)
            if extra == 0:
                continue

            fields = self._table_fields.get(table, [])
            if not fields:
                continue

            sample_values = self._determine_sample_values(conn, table, fields, qualifiers)
            if sample_values is None:
                continue

            require_positive = bool(self._ibp_positive_cache)
            target_ids = self._choose_target_ids(conn, table, qualifiers, extra, require_positive)
            if not target_ids:
                continue

            for aid in target_ids:
                old_values = self._fetch_row_values(conn, table, fields, aid)
                if old_values is None:
                    continue
                self._update_row(conn, table, fields, aid, sample_values)
                updates.append(
                    {"table": table, "aid": aid, "old_values": old_values, "fields": fields}
                )

        return updates

    def _rollback(
        self,
        conn: pymysql.connections.Connection,
        modifications: Sequence[Dict[str, object]],
    ) -> None:
        for entry in modifications:
            table = entry["table"]
            aid = entry["aid"]
            fields = entry["fields"]
            old_values = entry["old_values"]
            self._update_row(conn, table, fields, aid, old_values)

    # ------------------------------------------------------------------
    # Query parsing and analysis
    # ------------------------------------------------------------------

    def _strip_non_predicate_clauses(self, expression: exp.Expression) -> exp.Expression:
        """Remove ORDER, LIMIT, OFFSET to expose predicate structure."""
        expr = expression.copy()
        expr.set("order", None)
        expr.set("limit", None)
        expr.set("offset", None)
        return expr

    def _extract_relations(self, expression: exp.Expression) -> List[_Relation]:
        relations: Dict[str, _Relation] = {}
        for table in expression.find_all(exp.Table):
            base_name = table.name
            alias = table.alias_or_name
            if alias not in relations:
                relations[alias] = _Relation(table=base_name, alias=alias)
        return list(relations.values())

    def _collect_qualifier_ids(
        self,
        conn: pymysql.connections.Connection,
        expression: exp.Expression,
        relations: Sequence[_Relation],
    ) -> Dict[str, Set[int]]:
        results: Dict[str, Set[int]] = {}

        from_clause = expression.args.get("from")
        if not from_clause:
            return results
        from_sql = from_clause.sql(dialect="mysql")

        where_expr = expression.args.get("where")
        if where_expr:
            condition_sql = where_expr.this.sql(dialect="mysql")
            where_sql = f" WHERE {condition_sql}"
        else:
            where_sql = ""

        for relation in relations:
            query = f"SELECT DISTINCT {relation.alias}.aID {from_sql}{where_sql}"
            rows = self._fetchall(conn, query)
            qualifier_ids: Set[int] = set()
            for row in rows:
                try:
                    qualifier_ids.add(int(row[0]))
                except (TypeError, ValueError):
                    continue
            results[relation.alias] = qualifier_ids
        return results

    # ------------------------------------------------------------------
    # Tuple selection and updates
    # ------------------------------------------------------------------

    def _determine_sample_values(
        self,
        conn: pymysql.connections.Connection,
        table: str,
        fields: Sequence[str],
        qualifiers: Set[int],
    ) -> Optional[Tuple]:
        """
        Choose field values that satisfy the predicates.
        Prefer copying an actual qualifying tuple; otherwise fall back to the first tuple.
        """
        candidate_aid: Optional[int] = None
        if qualifiers:
            candidate_aid = next(iter(qualifiers))

        if candidate_aid is not None:
            values = self._fetch_row_values(conn, table, fields, candidate_aid)
            if values is not None:
                return values

        # Fallback: reuse the first tuple in the table.
        query = f"SELECT {', '.join(fields)} FROM {table} ORDER BY aID LIMIT 1"
        rows = self._fetchall(conn, query)
        if not rows:
            return None
        return rows[0]

    def _choose_target_ids(
        self,
        conn: pymysql.connections.Connection,
        table: str,
        qualifiers: Set[int],
        count: int,
        require_positive: bool,
    ) -> List[int]:
        """Pick tuple IDs to overwrite so they mimic qualifying tuples."""
        exclude = set(qualifiers)
        positive_candidates = self._ibp_positive_cache.get(table, set()) if require_positive else set()

        candidates: List[int] = []
        if positive_candidates:
            positive = [aid for aid in positive_candidates if aid not in exclude]
            candidates.extend(sorted(positive))

        if len(candidates) < count:
            needed = count - len(candidates)
            clause = ""
            if exclude:
                exclude_clause = ", ".join(str(int(aid)) for aid in sorted(exclude))
                clause = f" WHERE aID NOT IN ({exclude_clause})"
            query = f"SELECT aID FROM {table}{clause} ORDER BY aID LIMIT {needed * 3}"
            rows = self._fetchall(conn, query)
            for row in rows:
                try:
                    aid = int(row[0])
                except (TypeError, ValueError):
                    continue
                if aid in exclude or aid in candidates:
                    continue
                candidates.append(aid)
                if len(candidates) >= count:
                    break

        return candidates[:count]

    def _fetch_row_values(
        self,
        conn: pymysql.connections.Connection,
        table: str,
        fields: Sequence[str],
        aid: int,
    ) -> Optional[Tuple]:
        if not fields:
            return None
        placeholders = ", ".join(fields)
        query = f"SELECT {placeholders} FROM {table} WHERE aID = %s"
        rows = self._fetchall(conn, query, (aid,))
        return rows[0] if rows else None

    def _update_row(
        self,
        conn: pymysql.connections.Connection,
        table: str,
        fields: Sequence[str],
        aid: int,
        values: Sequence,
    ) -> None:
        assignments = ", ".join(f"{field} = %s" for field in fields)
        sql = f"UPDATE {table} SET {assignments} WHERE aID = %s"
        params = tuple(values) + (aid,)
        with conn.cursor() as cursor:
            cursor.execute(sql, params)

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _fetchall(
        self,
        conn: pymysql.connections.Connection,
        sql: str,
        params: Optional[Sequence] = None,
    ) -> List[Tuple]:
        with conn.cursor() as cursor:
            if params is None:
                cursor.execute(sql)
            else:
                cursor.execute(sql, params)
            return cursor.fetchall()

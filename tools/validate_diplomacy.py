#!/usr/bin/env python3
"""Read-only checks for Dawn of Terra's native diplomacy scripts.

This is a deliberately limited Clausewitz AST evaluator for regression tests.
It executes the *mod's scripts*, not a second diplomacy scoring implementation.
Unsupported evaluated effects/triggers fail loudly. It does not simulate HOI4's
AI, event scheduler, military estimates, saves, localization, or actual runtime.
The mod must additionally be tested in the game with -debug enabled.

Run from anywhere: python3 tools/validate_diplomacy.py
No dependencies; this tool never writes to the mod or changes source files.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import re
import sys
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
MOD = REPOSITORY / "MOD" / "Dawn_of_Terra"
TOKEN = re.compile(r'\s+|#[^\n]*|"(?:\\.|[^"\\])*"|[{}]|>=|<=|!=|[=<>]|[^\s{}=<>#]+')
COUNTRY_FACTS = frozenset({
    "exists", "is_ai", "is_subject", "has_civil_war", "has_capitulated",
    "has_war", "has_offensive_war", "has_defensive_war", "has_government",
    "num_divisions", "num_of_factories", "num_of_military_factories", "num_of_civilian_factories", "is_major",
    "is_in_faction", "has_manpower", "surrender_progress", "threat",
    "is_dynamic_country", "has_political_power", "has_stability", "has_war_support",
    "is_faction_leader",
})


class ScriptError(ValueError):
    pass


@dataclass(frozen=True)
class Node:
    key: str
    op: str
    value: str | tuple["Node", ...]
    line: int = 0
    source: str = "<script>"

    @property
    def children(self) -> tuple["Node", ...]:
        if isinstance(self.value, str):
            raise ScriptError(f"Expected block at {self.source}:{self.line}: {self.key}")
        return self.value

    def fields(self, key: str) -> tuple["Node", ...]:
        return tuple(child for child in self.children if child.key == key)

    def one(self, key: str, default=None):
        values = self.fields(key)
        if len(values) > 1:
            raise ScriptError(f"Duplicate {key} in {self.key} at {self.source}:{self.line}")
        return values[0] if values else default

    def scalar(self, key: str, default=None):
        node = self.one(key)
        if node is None:
            return default
        if not isinstance(node.value, str):
            raise ScriptError(f"Expected scalar: {key}")
        return node.value


def parse(text: str, source: str = "<script>") -> tuple[Node, ...]:
    text = text.lstrip("\ufeff")
    tokens = []
    position = 0
    line = 1
    for match in TOKEN.finditer(text):
        if match.start() != position:
            raise ScriptError(f"Unrecognized text at {source}:{position}")
        position = match.end()
        token = match.group()
        token_line = line
        line += token.count("\n")
        if token.isspace() or token.startswith("#"):
            continue
        if token.startswith('"'):
            token = token[1:-1].replace('\\"', '"')
        tokens.append((token, token_line))
    index = 0

    def block(nested: bool = False) -> tuple[Node, ...]:
        nonlocal index
        nodes = []
        while index < len(tokens):
            key, line = tokens[index]
            if key == "}":
                if not nested:
                    raise ScriptError(f"Unexpected closing brace at {source}:{line}")
                index += 1
                return tuple(nodes)
            if key in {"{", "=", "<", ">", "<=", ">=", "!="}:
                raise ScriptError(f"Expected key at {source}:{line}")
            index += 1
            if index >= len(tokens) or tokens[index][0] not in {"=", "<", ">", "<=", ">=", "!="}:
                nodes.append(Node(key, "", "", line, source))
                continue
            op = tokens[index][0]
            index += 1
            if index >= len(tokens):
                raise ScriptError(f"Missing value at {source}:{line}")
            value = tokens[index][0]
            index += 1
            if value == "{":
                value = block(True)
            elif value in {"}", "=", "<", ">", "<=", ">=", "!="}:
                raise ScriptError(f"Invalid value at {source}:{line}")
            nodes.append(Node(key, op, value, line, source))
        if nested:
            raise ScriptError(f"Unclosed block in {source}")
        return tuple(nodes)

    return block()


def read(path: Path) -> tuple[Node, ...]:
    info = path.stat()
    return _read_cached(path, info.st_mtime_ns, info.st_size)


@lru_cache(maxsize=128)
def _read_cached(path: Path, modified: int, size: int) -> tuple[Node, ...]:
    return parse(path.read_text(encoding="utf-8-sig"), str(path.relative_to(REPOSITORY)))


def walk(nodes: tuple[Node, ...]):
    for node in nodes:
        yield node
        if not isinstance(node.value, str):
            yield from walk(node.children)


def expand(node: Node, arguments: dict[str, str]) -> Node:
    def replace(value: str) -> str:
        return re.sub(r"\$([A-Za-z_0-9]+)\$", lambda m: arguments.get(m[1], m[0]), value)
    value = replace(node.value) if isinstance(node.value, str) else tuple(expand(n, arguments) for n in node.children)
    return Node(replace(node.key), node.op, value, node.line, node.source)


@dataclass
class Country:
    tag: str
    variables: dict[str, float] = field(default_factory=dict)
    temp_variables: dict[str, float] = field(default_factory=dict)
    flags: set[str] = field(default_factory=set)
    flag_days: dict[str, float] = field(default_factory=dict)
    attrs: dict[str, float | bool | str] = field(default_factory=lambda: {
        "exists": True, "is_ai": True, "is_subject": False,
        "has_civil_war": False, "has_capitulated": False,
        "has_war": False, "has_offensive_war": False, "has_defensive_war": False,
        "has_government": "monarchism", "political_power": 200,
        "stability": 0.7, "war_support": 0.7, "surrender_progress": 0,
        "num_divisions": 30, "num_of_factories": 40, "army_strength": 100,
        "threat": 0, "is_major": False,
        "is_in_faction": False, "has_manpower": 200000,
        "is_faction_leader": False,
        "num_of_military_factories": 20, "num_of_civilian_factories": 20, "industrial_capacity": 40,
    })
    relations: dict[str, set[str]] = field(default_factory=dict)
    opinions: dict[str, float] = field(default_factory=dict)
    equipment: dict[str, float] = field(default_factory=lambda: {"infantry_equipment": 1})
    stockpiles: dict[str, float] = field(default_factory=lambda: {"infantry_equipment": 10000})
    owned_state_cores: list[set[str]] = field(default_factory=lambda: [set()])
    leaders: set[str] = field(default_factory=set)
    ruling_leader: str | None = None
    technologies: set[str] = field(default_factory=set)
    completed_focuses: set[str] = field(default_factory=set)
    intelligence: dict[str, dict[str, float]] = field(default_factory=dict)
    rules: dict[str, bool] = field(default_factory=dict)
    effects: list[tuple[str, object]] = field(default_factory=list)

    def relation(self, kind: str, target: str, value: bool = True) -> None:
        targets = self.relations.setdefault(kind, set())
        targets.add(target) if value else targets.discard(target)


@dataclass(frozen=True)
class Scope:
    current: str
    root: str
    from_country: str | None = None
    previous: str | None = None

    def switch(self, tag: str) -> "Scope":
        return Scope(tag, self.root, self.from_country, self.current)


@dataclass(frozen=True)
class EventDelivery:
    recipient: str
    sender: str
    event_id: str
    days: str


class Runtime:
    """The supported deterministic native primitives only; no engine emulation."""
    def __init__(self, mod: Path = MOD):
        self.mod = mod
        self.date = "1028.1.1"
        self.countries: dict[str, Country] = {}
        self.country_ids: dict[str, int] = {}
        self.effects = self._definitions("scripted_effects")
        self.triggers = self._definitions("scripted_triggers")
        # Read real ideology defaults instead of inventing positive faction rights.
        self.ideology_rules: dict[str, dict[str, bool]] = {}
        for path in sorted((self.mod / "common/ideologies").glob("*.txt")):
            for root in read(path):
                if root.key == "ideologies":
                    for ideology in root.children:
                        block = ideology.one("rules")
                        self.ideology_rules[ideology.key] = {
                            rule.key: rule.value == "yes" for rule in block.children
                        } if block is not None else {}
        self.global_flags: set[str] = set()
        self.global_variables: dict[str, float] = {}
        self.deliveries: list[EventDelivery] = []
        self.factions: dict[str, set[str]] = {}
        self.random_choice_index = 0
        self.faction_creation_failures: set[str] = set()
        self.faction_join_failures: set[str] = set()
        self.dlcs: set[str] = set()
        for path in sorted((self.mod / "common" / "country_tags").glob("*.txt")):
            for node in read(path):
                if re.fullmatch(r"[A-Z][A-Z0-9]{2}", node.key):
                    country = self.country(node.key)
                    country.attrs["exists"] = False

    def _definitions(self, directory: str) -> dict[str, Node]:
        result = {}
        for path in sorted((self.mod / "common" / directory).glob("*.txt")):
            for node in read(path):
                if node.key in result:
                    raise ScriptError(f"Duplicate definition: {node.key}")
                result[node.key] = node
        return result

    def country(self, tag: str) -> Country:
        if tag not in self.countries:
            self.countries[tag] = Country(tag)
            self.country_ids[tag] = len(self.country_ids) + 1000
            self.countries[tag].attrs["original_tag"] = tag
            self.countries[tag].attrs["is_dynamic_country"] = bool(re.fullmatch("D[0-9]{2}", tag))
        return self.countries[tag]

    def scope(self, tag: str, from_country: str | None = None) -> Scope:
        self.country(tag).attrs["exists"] = True
        if from_country is not None:
            self.country(from_country).attrs["exists"] = True
        return Scope(tag, tag, from_country)

    def resolve(self, name: str, scope: Scope) -> str:
        if name in {"ROOT", "FROM", "PREV", "THIS"}:
            target = {"ROOT": scope.root, "FROM": scope.from_country, "PREV": scope.previous, "THIS": scope.current}[name]
            if target is None:
                raise ScriptError(f"Unbound country scope: {name}")
            return target
        if re.fullmatch(r"[A-Z][A-Z0-9]{2}", name):
            return name
        raise ScriptError(f"Unsupported country scope: {name}")

    def number(self, value: str, scope: Scope) -> float:
        try:
            return float(value)
        except ValueError:
            if value in {"ROOT", "FROM", "PREV", "THIS"} or re.fullmatch(r"[A-Z][A-Z0-9]{2}", value):
                tag = self.resolve(value, scope)
                self.country(tag)
                return self.country_ids[tag]
            if value.startswith("global."):
                return self.global_variables.get(value[7:], 0)
            if "." in value:
                country, variable = value.split(".", 1)
                return self.country(self.resolve(country, scope)).variables.get(variable, 0)
            value = value.removeprefix("var:")
            country = self.country(scope.current)
            if value == "num_owned_states":
                return len(country.owned_state_cores)
            if value in country.attrs and isinstance(country.attrs[value], (int, float)):
                return float(country.attrs[value])
            if "$" in value:
                raise ScriptError(f"Unexpanded macro: {value}")
            return country.temp_variables.get(value, country.variables.get(value, 0))

    @staticmethod
    def compare(left, op: str, right) -> bool:
        return {"=": lambda: left == right, "<": lambda: left < right,
                ">": lambda: left > right, "<=": lambda: left <= right,
                ">=": lambda: left >= right, "!=": lambda: left != right}[op]()

    def parameters(self, value: Node) -> dict[str, str]:
        if isinstance(value.value, str):
            return {}
        result = {}
        for node in value.children:
            if node.op != "=" or not isinstance(node.value, str):
                raise ScriptError(f"Invalid macro parameter at {node.source}:{node.line}")
            result[node.key] = node.value
        return result

    def call(self, name: str, scope: Scope, **parameters: str) -> None:
        if name not in self.effects:
            raise ScriptError(f"Unknown scripted effect: {name}")
        self.execute(expand(self.effects[name], parameters).children, scope)

    def trigger(self, name: str, scope: Scope, **parameters: str) -> bool:
        if name not in self.triggers:
            raise ScriptError(f"Unknown scripted trigger: {name}")
        return self.check(expand(self.triggers[name], parameters).children, scope)

    def check(self, nodes: tuple[Node, ...], scope: Scope) -> bool:
        return all(self.condition(node, scope) for node in nodes)

    def condition(self, node: Node, scope: Scope) -> bool:
        key, value = node.key, node.value
        if scope.current.startswith("state:"):
            owner, index = scope.current[6:].split(":")
            if key == "always":
                return value == "yes"
            if key == "is_core_of":
                return self.resolve(value, scope) in self.country(owner).owned_state_cores[int(index)]
            if key == "AND":
                return self.check(node.children, scope)
            if key == "OR":
                return any(self.condition(child, scope) for child in node.children)
            if key == "NOT":
                return not self.check(node.children, scope)
            raise ScriptError(f"Unsupported state trigger {key} at {node.source}:{node.line}")
        country = self.country(scope.current)
        if key in self.triggers:
            result = self.trigger(key, scope, **self.parameters(node))
            return not result if value == "no" else result
        if key == "AND":
            return self.check(node.children, scope)
        if key == "custom_trigger_tooltip":
            return self.check(tuple(child for child in node.children if child.key != "tooltip"), scope)
        if key == "OR":
            return any(self.condition(child, scope) for child in node.children)
        if key == "NOT":
            return not self.check(node.children, scope)
        if key == "always":
            return value == "yes"
        if key == "date":
            def date_parts(text):
                parts = tuple(int(n) for n in text.split("."))
                return parts + (0,) * (4 - len(parts))
            return self.compare(date_parts(self.date), node.op, date_parts(value))
        if key == "has_rule":
            return country.rules.get(value, self.ideology_rules.get(country.attrs["has_government"], {}).get(value, False))
        if key == "tag" or key == "original_tag":
            actual = scope.current if key == "tag" else country.attrs["original_tag"]
            return actual == self.resolve(str(value), scope)
        if key == "country_exists":
            return bool(self.country(self.resolve(value, scope)).attrs["exists"])
        if key == "has_country_flag":
            if isinstance(value, str):
                return value in country.flags
            flag = node.scalar("flag")
            if flag not in country.flags:
                return False
            days = node.one("days")
            return days is None or self.compare(country.flag_days.get(flag, 0), days.op, self.number(days.value, scope))
        if key == "has_global_flag":
            return value in self.global_flags
        if key == "has_variable":
            return value in country.variables
        if key == "has_tech":
            return value in country.technologies
        if key == "has_completed_focus":
            return value in country.completed_focuses
        if key == "has_dlc":
            return value in self.dlcs
        if key == "intel_level_over":
            target = self.resolve(node.scalar("target"), scope)
            fields = [child for child in node.children if child.key != "target"]
            if any(child.key not in {"army_intel", "civilian_intel", "navy_intel"} for child in fields):
                raise ScriptError("Unsupported intelligence fixture field")
            return all(self.compare(country.intelligence.get(target, {}).get(child.key, 0), ">=" if child.op == "=" else child.op, self.number(child.value, scope)) for child in fields)
        if key == "has_country_leader":
            leader = value if isinstance(value, str) else node.scalar("character")
            if leader is None:
                raise ScriptError("Only character-token leader fixtures are supported")
            return leader == country.ruling_leader if not isinstance(value, str) and node.scalar("ruling_only", "no") == "yes" else leader in country.leaders or leader == country.ruling_leader
        if key == "check_variable":
            variable = node.scalar("var")
            names = {"equals": "=", "not_equals": "!=", "less_than": "<", "less_than_or_equals": "<=", "greater_than": ">", "greater_than_or_equals": ">="}
            if variable is not None:
                return self.compare(self.number(variable, scope), names[node.scalar("compare", "greater_than_or_equals")], self.number(node.scalar("value"), scope))
            children = tuple(child for child in node.children if child.key not in {"tooltip", "compare"})
            if len(children) != 1:
                raise ScriptError("Short check_variable must contain exactly one comparison")
            child = children[0]
            operator = names[node.scalar("compare")] if node.scalar("compare") is not None else (">=" if child.op == "=" else child.op)
            return self.compare(self.number(child.key, scope), operator, self.number(child.value, scope))
        if key == "strength_ratio":
            target = self.country(self.resolve(node.scalar("tag"), scope))
            ratio = node.one("ratio")
            actual = float(country.attrs["army_strength"]) / max(float(target.attrs["army_strength"]), 1e-9)
            return self.compare(actual, ">=" if ratio.op == "=" else ratio.op, self.number(ratio.value, scope))
        if key == "stockpile_ratio":
            archetype = node.scalar("archetype")
            ratio = node.one("ratio")
            return self.compare(country.equipment.get(archetype, 0), ">=" if ratio.op == "=" else ratio.op, self.number(ratio.value, scope))
        if key == "has_equipment":
            return all(self.compare(country.stockpiles.get(child.key, 0), ">=" if child.op == "=" else child.op, self.number(child.value, scope)) for child in node.children)
        if key == "any_owned_state":
            return any(self.check(node.children, scope.switch(f"state:{scope.current}:{index}")) for index in range(len(country.owned_state_cores)))
        if key == "has_opinion":
            target = self.resolve(node.scalar("target"), scope)
            opinion = node.one("value")
            return self.compare(country.opinions.get(target, 0), ">=" if opinion.op == "=" else opinion.op, self.number(opinion.value, scope))
        if key in {"has_war_with", "is_neighbor_of", "is_in_faction_with", "is_subject_of", "is_guaranteed_by", "has_guaranteed", "has_non_aggression_pact_with", "has_defensive_war_with", "has_offensive_war_with", "has_wargoal_against", "can_declare_war_on", "has_subject", "has_war_together_with"}:
            return self.resolve(str(value), scope) in country.relations.get(key, set())
        if key in {"any_country", "any_neighbor_country", "any_other_country", "any_enemy_country"}:
            countries = list(self.countries)
            if key == "any_neighbor_country":
                countries = list(country.relations.get("is_neighbor_of", set()))
            elif key == "any_other_country":
                countries = [tag for tag in countries if tag != scope.current]
            elif key == "any_enemy_country":
                countries = list(country.relations.get("has_war_with", set()))
            return any(self.check(node.children, scope.switch(tag)) for tag in countries if self.country(tag).attrs["exists"])
        if key in {"all_country", "all_neighbor_country"}:
            countries = list(self.countries) if key == "all_country" else list(country.relations.get("is_neighbor_of", set()))
            return all(self.check(node.children, scope.switch(tag)) for tag in countries if self.country(tag).attrs["exists"])
        if key in COUNTRY_FACTS:
            attribute = {"has_political_power": "political_power", "has_stability": "stability", "has_war_support": "war_support"}.get(key, key)
            actual = country.attrs[attribute]
            if value in {"yes", "no"}:
                return bool(actual) == (value == "yes")
            if isinstance(actual, str):
                if key == "has_government" and re.fullmatch(r"[A-Z][A-Z0-9]{2}|ROOT|FROM|PREV|THIS", value):
                    value = self.country(self.resolve(value, scope)).attrs["has_government"]
                return self.compare(actual, node.op, value)
            return self.compare(actual, ">=" if node.op == "=" else node.op, self.number(value, scope))
        if key in {"ROOT", "FROM", "PREV", "THIS"} or re.fullmatch(r"[A-Z][A-Z0-9]{2}", key):
            return self.check(node.children, scope.switch(self.resolve(key, scope)))
        raise ScriptError(f"Unsupported trigger {key} at {node.source}:{node.line}")

    def execute(self, nodes: tuple[Node, ...], scope: Scope) -> None:
        country = self.country(scope.current)
        branch_taken = False
        for node in nodes:
            key, value = node.key, node.value
            if key in {"if", "else_if", "else"}:
                if key == "if":
                    branch_taken = False
                limit = node.one("limit")
                take = not branch_taken and (limit is None or self.check(limit.children, scope))
                if take:
                    self.execute(tuple(child for child in node.children if child.key != "limit"), scope)
                    branch_taken = True
                continue
            branch_taken = False
            if key in self.effects:
                self.call(key, scope, **self.parameters(node))
            elif key in {"hidden_effect", "effect"}:
                self.execute(node.children, scope)
            elif key in {"set_variable", "add_to_variable", "subtract_from_variable", "multiply_variable", "divide_variable", "set_temp_variable", "add_to_temp_variable", "subtract_from_temp_variable", "multiply_temp_variable", "divide_temp_variable"}:
                variable = node.scalar("var")
                amount = node.scalar("value")
                if variable is None:
                    child = next(child for child in node.children if child.key not in {"tooltip", "if_zero"})
                    variable, amount = child.key, child.value
                result = self.number(amount, scope)
                variable_pool = country.temp_variables if "temp_variable" in key else country.variables
                previous = variable_pool.get(variable, 0)
                if key.startswith("add_to"):
                    result = previous + result
                elif key.startswith("subtract_from"):
                    result = previous - result
                elif key.startswith("multiply"):
                    result = previous * result
                elif key.startswith("divide"):
                    result = previous / result if result else self.number(node.scalar("if_zero", "0"), scope)
                variable_pool[variable] = result
            elif key == "clamp_variable":
                variable = node.scalar("var")
                low = self.number(node.scalar("min", "-inf"), scope)
                high = self.number(node.scalar("max", "inf"), scope)
                if high < low:
                    raise ScriptError("Invalid clamp interval")
                country.variables[variable] = max(low, min(high, country.variables.get(variable, 0)))
            elif key == "clear_variable":
                country.variables.pop(value, None)
            elif key == "clear_temp_variable":
                country.temp_variables.pop(value, None)
            elif key in {"set_country_flag", "clr_country_flag"}:
                flag = value if isinstance(value, str) else node.scalar("flag")
                if key == "set_country_flag":
                    country.flags.add(flag)
                    country.flag_days[flag] = 0
                else:
                    country.flags.discard(flag)
                    country.flag_days.pop(flag, None)
            elif key == "set_global_flag":
                self.global_flags.add(value)
            elif key == "clr_global_flag":
                self.global_flags.discard(value)
            elif key in {"every_country", "every_neighbor_country"}:
                tags = list(self.countries) if key == "every_country" else list(country.relations.get("is_neighbor_of", set()))
                for tag in tags:
                    child_scope = scope.switch(tag)
                    limit = node.one("limit")
                    if self.country(tag).attrs["exists"] and (limit is None or self.check(limit.children, child_scope)):
                        self.execute(tuple(child for child in node.children if child.key != "limit"), child_scope)
            elif key in {"ROOT", "FROM", "PREV", "THIS"} or re.fullmatch(r"[A-Z][A-Z0-9]{2}", key):
                self.execute(node.children, scope.switch(self.resolve(key, scope)))
            elif key == "add_political_power":
                country.attrs["political_power"] += self.number(value, scope)
            elif key == "add_stability":
                country.attrs["stability"] += self.number(value, scope)
            elif key == "add_war_support":
                country.attrs["war_support"] += self.number(value, scope)
            elif key == "add_manpower":
                country.attrs["has_manpower"] += self.number(value, scope)
            elif key == "delete_unit":
                # Only an unfiltered country-wide deletion is modeled. Native
                # disband refunds and training queues require the actual engine.
                if any(n.key != "disband" for n in node.children):
                    raise ScriptError("Filtered unit deletion needs an explicit fixture")
                country.attrs["num_divisions"] = 0
                country.effects.append((key, node))
            elif key == "country_lock_all_division_template":
                country.effects.append((key, node))
            elif key == "send_equipment":
                # Native transfer inputs are explicit fixture stockpiles. This
                # checks script conservation, not HOI4's variants or delivery.
                equipment = node.scalar("type", node.scalar("equipment"))
                if equipment is None:
                    raise ScriptError("send_equipment requires an explicit fixture equipment type")
                amount = self.number(node.scalar("amount"), scope)
                recipient = self.country(self.resolve(node.scalar("target"), scope))
                available = country.stockpiles.get(equipment, 0)
                if amount < 0 or amount > available:
                    raise ScriptError(f"Transfer requests unavailable equipment: {equipment} {amount}/{available}")
                country.stockpiles[equipment] = available - amount
                recipient.stockpiles[equipment] = recipient.stockpiles.get(equipment, 0) + amount
                country.effects.append((key, node))
            elif key == "add_equipment_to_stockpile":
                equipment = node.scalar("type")
                amount = self.number(node.scalar("amount"), scope)
                total = country.stockpiles.get(equipment, 0) + amount
                if total < 0:
                    raise ScriptError(f"Negative fixture stockpile: {equipment}")
                country.stockpiles[equipment] = total
                country.effects.append((key, node))
            elif key == "country_event":
                # The expected documented ROOT/FROM handoff is captured; the
                # actual scheduler and engine source scopes require playtesting.
                self.deliveries.append(EventDelivery(scope.current, scope.root, node.scalar("id"), node.scalar("days", "0")))
                country.effects.append((key, node))
            elif key == "declare_war_on":
                # Model the direct bilateral relation only, not native war
                # legality, faction participation, scheduling or combat.
                target = self.country(self.resolve(node.scalar("target"), scope))
                country.relation("has_war_with", target.tag)
                country.relation("has_offensive_war_with", target.tag)
                target.relation("has_war_with", country.tag)
                target.relation("has_defensive_war_with", country.tag)
                country.attrs.update({"has_war": True, "has_offensive_war": True})
                target.attrs.update({"has_war": True, "has_defensive_war": True})
                country.relation("has_wargoal_against", target.tag, False)
                country.effects.append((key, node))
            elif key == "random_list":
                # Deterministic fixture branch, not a simulation of engine randomness.
                choices = [child for child in node.children if child.key.isdigit()]
                if not choices or not 0 <= self.random_choice_index < len(choices):
                    raise ScriptError("Missing fixture random-list choice")
                self.execute(choices[self.random_choice_index].children, scope)
            elif key == "set_rule":
                for rule in node.children:
                    if rule.key == "desc":
                        continue
                    if rule.value not in {"yes", "no"}:
                        raise ScriptError("Only boolean country-rule fixtures are supported")
                    country.rules[rule.key] = rule.value == "yes"
                country.effects.append((key, node))
            elif key == "complete_national_focus":
                focus = value if isinstance(value, str) else node.scalar("focus")
                if focus not in country.completed_focuses:
                    country.completed_focuses.add(focus)
                    if not hasattr(self, "focus_rewards"):
                        self.focus_rewards = {}
                        for path in (self.mod / "common/national_focus").glob("*.txt"):
                            for root in read(path):
                                if isinstance(root.value, str):
                                    continue
                                for definition in root.fields("focus"):
                                    self.focus_rewards[definition.scalar("id")] = definition.one("completion_reward")
                    reward = self.focus_rewards.get(focus)
                    if reward is not None:
                        self.execute(reward.children, scope)
                country.effects.append((key, node))
            elif key in {"remove_from_faction", "leave_faction"}:
                member = self.country(self.resolve(value, scope)) if key == "remove_from_faction" else country
                leader = member.attrs.get("faction_leader")
                if leader in self.factions:
                    roster = self.factions[leader]
                    roster.discard(member.tag)
                    for tag in roster:
                        self.country(tag).relation("is_in_faction_with", member.tag, False)
                        member.relation("is_in_faction_with", tag, False)
                member.attrs.update({"is_in_faction": False, "is_faction_leader": False})
                member.attrs.pop("faction_leader", None)
                country.effects.append((key, node))
            elif key in {"create_faction", "create_faction_from_template"}:
                # Model only roster facts needed to test guards and repeated enrollment.
                if scope.current in self.faction_creation_failures:
                    country.effects.append((key, node))
                    continue
                if country.attrs["is_in_faction"]:
                    raise ScriptError("Fixture country already has a faction")
                country.attrs.update({"is_in_faction": True, "is_faction_leader": True, "faction_leader": scope.current})
                self.factions[scope.current] = {scope.current}
                country.effects.append((key, node))
            elif key == "add_to_faction":
                target = self.country(self.resolve(value, scope))
                if target.tag in self.faction_join_failures:
                    country.effects.append((key, node))
                    continue
                if not country.attrs["is_faction_leader"] or target.attrs["is_in_faction"]:
                    raise ScriptError("Invalid fixture faction enrollment")
                roster = self.factions[scope.current]
                for member in roster:
                    target.relation("is_in_faction_with", member)
                    self.country(member).relation("is_in_faction_with", target.tag)
                roster.add(target.tag)
                target.attrs.update({"is_in_faction": True, "is_faction_leader": False, "faction_leader": scope.current})
                country.effects.append((key, node))
            elif key in {"add_opinion_modifier", "remove_opinion_modifier", "add_ideas", "remove_ideas", "create_wargoal", "set_truce", "diplomatic_relation"}:
                # Captured for assertions, not treated as simulated engine behavior.
                country.effects.append((key, node))
            elif key in {"custom_effect_tooltip", "log", "tooltip", "save_event_target_as"}:
                if key == "save_event_target_as":
                    raise ScriptError("Event-target simulation is not implemented")
            else:
                raise ScriptError(f"Unsupported effect {key} at {node.source}:{node.line}")


def main() -> int:
    tests = unittest.defaultTestLoader.discover(str(REPOSITORY / "tests"), pattern="test_*.py", top_level_dir=str(REPOSITORY))
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    print("\nScope: native script AST regression checks only. HOI4 engine/playtesting is still required.")
    return 0 if result.wasSuccessful() and result.testsRun else 1


if __name__ == "__main__":
    sys.exit(main())

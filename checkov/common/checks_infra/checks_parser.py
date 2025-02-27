from __future__ import annotations

from typing import Dict, Any, List, Optional, Type, TYPE_CHECKING

from checkov.common.checks_infra.solvers import (
    EqualsAttributeSolver,
    NotEqualsAttributeSolver,
    RegexMatchAttributeSolver,
    NotRegexMatchAttributeSolver,
    ExistsAttributeSolver,
    AnyResourceSolver,
    ContainsAttributeSolver,
    NotExistsAttributeSolver,
    WithinAttributeSolver,
    NotContainsAttributeSolver,
    StartingWithAttributeSolver,
    NotStartingWithAttributeSolver,
    EndingWithAttributeSolver,
    NotEndingWithAttributeSolver,
    AndSolver,
    OrSolver,
    ConnectionExistsSolver,
    ConnectionNotExistsSolver,
    AndConnectionSolver,
    OrConnectionSolver,
    WithinFilterSolver,
    GreaterThanAttributeSolver,
    GreaterThanOrEqualAttributeSolver,
    LessThanAttributeSolver,
    LessThanOrEqualAttributeSolver,
    JsonpathEqualsAttributeSolver,
    JsonpathExistsAttributeSolver,
    JsonpathNotExistsAttributeSolver,
    SubsetAttributeSolver,
    NotSubsetAttributeSolver
)
from checkov.common.checks_infra.solvers.connections_solvers.connection_one_exists_solver import \
    ConnectionOneExistsSolver
from checkov.common.graph.checks_infra.base_check import BaseGraphCheck
from checkov.common.graph.checks_infra.base_parser import BaseGraphCheckParser
from checkov.common.graph.checks_infra.enums import SolverType
from checkov.common.graph.checks_infra.solvers.base_solver import BaseSolver

if TYPE_CHECKING:
    from checkov.common.checks_infra.solvers.attribute_solvers.base_attribute_solver import BaseAttributeSolver
    from checkov.common.checks_infra.solvers.complex_solvers.base_complex_solver import BaseComplexSolver
    from checkov.common.checks_infra.solvers.connections_solvers.base_connection_solver import BaseConnectionSolver
    from checkov.common.checks_infra.solvers.connections_solvers.complex_connection_solver import ComplexConnectionSolver
    from checkov.common.checks_infra.solvers.filter_solvers.base_filter_solver import BaseFilterSolver


operators_to_attributes_solver_classes: dict[str, Type[BaseAttributeSolver]] = {
    "equals": EqualsAttributeSolver,
    "not_equals": NotEqualsAttributeSolver,
    "regex_match": RegexMatchAttributeSolver,
    "not_regex_match": NotRegexMatchAttributeSolver,
    "exists": ExistsAttributeSolver,
    "any": AnyResourceSolver,
    "contains": ContainsAttributeSolver,
    "not_exists": NotExistsAttributeSolver,
    "within": WithinAttributeSolver,
    "not_contains": NotContainsAttributeSolver,
    "starting_with": StartingWithAttributeSolver,
    "not_starting_with": NotStartingWithAttributeSolver,
    "ending_with": EndingWithAttributeSolver,
    "not_ending_with": NotEndingWithAttributeSolver,
    "greater_than": GreaterThanAttributeSolver,
    "greater_than_or_equal": GreaterThanOrEqualAttributeSolver,
    "less_than": LessThanAttributeSolver,
    "less_than_or_equal": LessThanOrEqualAttributeSolver,
    "subset": SubsetAttributeSolver,
    "not_subset": NotSubsetAttributeSolver,
    "jsonpath_equals": JsonpathEqualsAttributeSolver,
    "jsonpath_exists": JsonpathExistsAttributeSolver,
    "jsonpath_not_exists": JsonpathNotExistsAttributeSolver
}

operators_to_complex_solver_classes: dict[str, Type[BaseComplexSolver]] = {
    "and": AndSolver,
    "or": OrSolver,
}

operator_to_connection_solver_classes: dict[str, Type[BaseConnectionSolver]] = {
    "exists": ConnectionExistsSolver,
    "one_exists": ConnectionOneExistsSolver,
    "not_exists": ConnectionNotExistsSolver
}

operator_to_complex_connection_solver_classes: dict[str, Type[ComplexConnectionSolver]] = {
    "and": AndConnectionSolver,
    "or": OrConnectionSolver,
}

operator_to_filter_solver_classes: dict[str, Type[BaseFilterSolver]] = {
    "within": WithinFilterSolver,
}

condition_type_to_solver_type = {
    "": SolverType.ATTRIBUTE,
    "attribute": SolverType.ATTRIBUTE,
    "connection": SolverType.CONNECTION,
    "filter": SolverType.FILTER,
}


class NXGraphCheckParser(BaseGraphCheckParser):
    def parse_raw_check(self, raw_check: Dict[str, Dict[str, Any]], **kwargs: Any) -> BaseGraphCheck:
        policy_definition = raw_check.get("definition", {})
        check = self._parse_raw_check(policy_definition, kwargs.get("resources_types"))
        check.id = raw_check.get("metadata", {}).get("id", "")
        check.bc_id = raw_check.get("metadata", {}).get("id", "")
        check.name = raw_check.get("metadata", {}).get("name", "")
        check.category = raw_check.get("metadata", {}).get("category", "")
        check.frameworks = raw_check.get("metadata", {}).get("frameworks", [])
        solver = self.get_check_solver(check)
        check.set_solver(solver)

        return check

    def _parse_raw_check(self, raw_check: Dict[str, Any], resources_types: Optional[List[str]]) -> BaseGraphCheck:
        check = BaseGraphCheck()
        complex_operator = get_complex_operator(raw_check)
        if complex_operator:
            check.type = SolverType.COMPLEX
            check.operator = complex_operator
            sub_solvers = raw_check.get(complex_operator, [])
            for sub_solver in sub_solvers:
                check.sub_checks.append(self._parse_raw_check(sub_solver, resources_types))
            resources_types_of_sub_solvers = [
                q.resource_types for q in check.sub_checks if q is not None and q.resource_types is not None
            ]
            check.resource_types = list(set(sum(resources_types_of_sub_solvers, [])))
            if any(q.type in [SolverType.CONNECTION, SolverType.COMPLEX_CONNECTION] for q in check.sub_checks):
                check.type = SolverType.COMPLEX_CONNECTION

        else:
            resource_type = raw_check.get("resource_types", [])
            if (
                    not resource_type
                    or (isinstance(resource_type, str) and resource_type.lower() == "all")
                    or (isinstance(resource_type, list) and resource_type[0].lower() == "all")
            ):
                check.resource_types = resources_types or []
            else:
                check.resource_types = resource_type

            connected_resources_type = raw_check.get("connected_resource_types", [])
            if connected_resources_type == ["All"] or connected_resources_type == "all":
                check.connected_resources_types = resources_types or []
            else:
                check.connected_resources_types = connected_resources_type

            condition_type = raw_check.get("cond_type", "")
            check.type = condition_type_to_solver_type.get(condition_type)
            if condition_type == "":
                check.operator = "any"
            else:
                check.operator = raw_check.get("operator", "")
            check.attribute = raw_check.get("attribute")
            check.attribute_value = raw_check.get("value")

        return check

    def get_check_solver(self, check: BaseGraphCheck) -> BaseSolver:
        sub_solvers: List[BaseSolver] = []
        if check.sub_checks:
            sub_solvers = []
            for sub_solver in check.sub_checks:
                sub_solvers.append(self.get_check_solver(sub_solver))

        type_to_solver = {
            SolverType.COMPLEX_CONNECTION: operator_to_complex_connection_solver_classes.get(
                check.operator, lambda *args: None
            )(sub_solvers, check.operator),
            SolverType.COMPLEX: operators_to_complex_solver_classes.get(check.operator, lambda *args: None)(
                sub_solvers, check.resource_types
            ),
            SolverType.ATTRIBUTE: operators_to_attributes_solver_classes.get(check.operator, lambda *args: None)(
                check.resource_types, check.attribute, check.attribute_value
            ),
            SolverType.CONNECTION: operator_to_connection_solver_classes.get(check.operator, lambda *args: None)(
                check.resource_types, check.connected_resources_types
            ),
            SolverType.FILTER: operator_to_filter_solver_classes.get(check.operator, lambda *args: None)(
                check.resource_types, check.attribute, check.attribute_value
            ),
        }

        solver = type_to_solver.get(check.type)
        if not solver:
            raise NotImplementedError(f"solver type {check.type} with operator {check.operator} is not supported")
        return solver


def get_complex_operator(raw_check: Dict[str, Any]) -> Optional[str]:
    for operator in operators_to_complex_solver_classes.keys():
        if raw_check.get(operator):
            return operator
    return None

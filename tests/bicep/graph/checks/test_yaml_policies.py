import os
import warnings
from pathlib import Path
from typing import List

from checkov.bicep.graph_manager import BicepGraphManager
from checkov.common.graph.db_connectors.networkx.networkx_db_connector import NetworkxConnector
from checkov.common.graph.graph_builder import CustomAttributes
from checkov.common.models.enums import CheckResult
from checkov.common.output.record import Record
from checkov.common.output.report import Report, CheckType
from tests.common.graph.checks.test_yaml_policies_base import TestYamlPoliciesBase


class TestYamlPolicies(TestYamlPoliciesBase):
    def __init__(self, args):
        graph_manager = BicepGraphManager(db_connector=NetworkxConnector())
        super().__init__(
            graph_manager=graph_manager,
            real_graph_checks_path=str(
                Path(__file__).parent.parent.parent.parent.parent / "checkov/bicep/checks/graph_checks"
            ),
            test_checks_path="",
            check_type="bicep",
            test_file_path=__file__,
            args=args,
        )

    def setUp(self) -> None:
        os.environ["UNIQUE_TAG"] = ""
        warnings.filterwarnings("ignore", category=ResourceWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)

    def test_SQLServerAuditingEnabled(self):
        self.go("SQLServerAuditingEnabled")

    def test_registry_load(self):
        registry = self.get_checks_registry()
        self.assertGreater(len(registry.checks), 0)

    def assert_evaluated_keys(self, expected_evaluated_keys: List[str], results: List[Record]):
        evaluated_keys_results = results[0].check_result["evaluated_keys"]
        self.assertCountEqual(expected_evaluated_keys, evaluated_keys_results)

    def create_report_from_graph_checks_results(self, checks_results, check):
        report = Report(CheckType.BICEP)
        first_results_key = list(checks_results.keys())[0]
        for check_result in checks_results[first_results_key]:
            entity = check_result["entity"]
            record = Record(
                check_id=check["id"],
                check_name=check["name"],
                check_result=check_result,
                code_block=[(0, "")],
                file_path=entity.get(CustomAttributes.FILE_PATH),
                file_line_range=[entity.get("__startline__"), entity.get("__endline__")],
                resource=f"{entity.get(CustomAttributes.RESOURCE_TYPE)}.{entity.get(CustomAttributes.BLOCK_NAME)}",
                entity_tags=entity.get("tags", {}),
                evaluations=None,
                check_class="",
                file_abs_path=entity.get(CustomAttributes.FILE_PATH),
            )
            if check_result["result"] == CheckResult.PASSED:
                report.passed_checks.append(record)
            if check_result["result"] == CheckResult.FAILED:
                report.failed_checks.append(record)
        return report

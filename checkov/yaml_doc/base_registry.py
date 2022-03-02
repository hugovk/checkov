from checkov.common.checks.base_check_registry import BaseCheckRegistry
from checkov.common.models.enums import CheckResult
from checkov.yaml_doc.enums import BlockType


class Registry(BaseCheckRegistry):
    def __init__(self):
        super().__init__()
        self._scanner = {
            BlockType.ARRAY: self._scan_yaml_array,
            BlockType.OBJECT: self._scan_yaml_object,
        }

    def _scan_yaml_array(
            self, scanned_file, check, skip_info, entity, entity_name, entity_type, results
    ):
        if isinstance(entity, dict):
            analayzed_dict = entity.get(entity_type, {})
            for item, item_conf in analayzed_dict.items():
                if '__startline__' != item and '__endline__' != item:
                    result = self.update_result(
                        check,
                        item_conf,
                        item,
                        entity_type,
                        results,
                        scanned_file,
                        skip_info,
                    )
        if isinstance(entity, list):
            for item in entity:
                if entity_name in item:
                    result = self.update_result(
                        check,
                        item[entity_name],
                        entity_name,
                        entity_type,
                        results,
                        scanned_file,
                        skip_info,
                    )
                    if result == CheckResult.FAILED:
                        break

    def _scan_yaml_object(
            self, scanned_file, check, skip_info, entity, entity_name, entity_type, results
    ):
        if entity_name in entity:
            self.update_result(
                check,
                entity[entity_name],
                entity_name,
                entity_type,
                results,
                scanned_file,
                skip_info,
            )

    def _scan_yaml_document(
            self, scanned_file, check, skip_info, entity, entity_name, entity_type, results
    ):
        self.update_result(
            check, entity, entity_name, entity_type, results, scanned_file, skip_info
        )

    def _scan_yaml(
            self,
            scanned_file,
            checks,
            skipped_checks,
            runner_filter,
            entity,
            entity_name,
            entity_type,
            results,
    ):
        for check in checks:
            skip_info = ([x for x in skipped_checks if x["id"] == check.id] or [{}])[0]

            if runner_filter.should_run_check(check=check):
                scanner = self._scanner.get(check.block_type, self._scan_yaml_document)
                if check.path:
                    target = entity
                    for p in check.path.split("."):
                        if p.endswith("]"):
                            ip = p.split("[")
                            i = int(ip[1][:-1])
                            target = target[ip[0]][i]
                        else:
                            target = target[p]
                else:
                    target = entity

                scanner(
                    scanned_file,
                    check,
                    skip_info,
                    target,
                    entity_name,
                    entity_type,
                    results,
                )

    def scan(self, scanned_file, entity, skipped_checks, runner_filter):
        results = {}

        if not entity:
            return results

        for instruction, checks in self.checks.items():
            self._scan_yaml(
                scanned_file=scanned_file,
                checks=checks,
                skipped_checks=skipped_checks,
                runner_filter=runner_filter,
                entity=entity,
                entity_name=instruction,
                entity_type=instruction,
                results=results,
            )

        if self.wildcard_checks["*"]:
            self._scan_yaml(
                scanned_file=scanned_file,
                checks=self.wildcard_checks["*"],
                skipped_checks=skipped_checks,
                runner_filter=runner_filter,
                entity=entity,
                entity_name=scanned_file,
                entity_type="*",
                results=results,
            )

        return results

    def update_result(
            self,
            check,
            entity_configuration,
            entity_name,
            entity_type,
            results,
            scanned_file,
            skip_info,
    ):
        check_result = self.run_check(
            check,
            entity_configuration,
            entity_name,
            entity_type,
            scanned_file,
            skip_info,
        )
        result_key = f'{entity_type}.{entity_name}.{check.id}'

        result = check_result["result"]

        if result == CheckResult.SKIPPED:
            results[result_key] = {
                "check": check,
                "result": result,
                "suppress_comment": check_result["suppress_comment"],
                "results_configuration": None,
            }
            return result

        if isinstance(result, tuple):
            results[result_key] = {
                "check": check,
                "result": result[0],
                "results_configuration": result[1],
            }
            return result[0]
        results[result_key] = {
            "check": check,
            "result": result,
            "results_configuration": entity_configuration,
        }
        return result
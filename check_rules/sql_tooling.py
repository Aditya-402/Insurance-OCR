"""
SQL tooling - Consolidated imports for backward compatibility.
This module re-exports all functions from the split modules to maintain compatibility.

New modules:
- sql_rule_queries.py: Query functions for procedures, check rules, L1/L2 rules
- sql_document_checker.py: Document submission checking logic
"""

# Re-export all functions from split modules for backward compatibility
from .sql_rule_queries import (
    fetch_all_procedure_names_from_db,
    fetch_rules_for_procedure_from_db,
    fetch_rule_descriptions_for_ids_from_db,
    fetch_procedure_rules_expression_from_db,
    fetch_parent_check_rule_id,
    fetch_all_l2_rules_from_db,
    fetch_l1_rule_descriptions,
    fetch_l1_rule_descriptions_with_values,
    _fetch_data_for_l1_rule,
)

from .sql_document_checker import (
    check_document_submission_status,
    get_table_column_names,
)

# All functionality is now in the specialized modules above
# This file exists only for backward compatibility

__all__ = [
    'fetch_all_procedure_names_from_db',
    'fetch_rules_for_procedure_from_db',
    'fetch_rule_descriptions_for_ids_from_db',
    'fetch_procedure_rules_expression_from_db',
    'fetch_parent_check_rule_id',
    'fetch_all_l2_rules_from_db',
    'fetch_l1_rule_descriptions',
    'fetch_l1_rule_descriptions_with_values',
    '_fetch_data_for_l1_rule',
    'check_document_submission_status',
    'get_table_column_names',
]

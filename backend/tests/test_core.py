from app.mcp_tools import safe_calculate,search_sources
from app.evaluation_suite import CASES
def test_safe_calculator():
 assert safe_calculate('9 / 10 * 100')==90
 assert safe_calculate('(2+3)*4')==20
def test_calculator_rejects_python_code():
 try:safe_calculate("__import__('os').system('echo nope')");assert False
 except (ValueError,SyntaxError):assert True
def test_corpus_search():
 r=search_sources('orchestrator agents MCP',5);assert r and all('document_id' in x for x in r)
def test_30_cases():assert len(CASES)>=30
def test_cost_formula_example():
 input_tokens,output_tokens,input_price,output_price=4000,1000,1.0,5.0
 cost=input_tokens/1_000_000*input_price+output_tokens/1_000_000*output_price
 assert abs(cost-.009)<1e-9


def test_calculator_rejects_non_finite_and_extreme_values():
    for expression in ("1e309", "2**1000", "1/0"):
        try:
            safe_calculate(expression)
            assert False, f"Unsafe expression accepted: {expression}"
        except ValueError:
            pass


def test_calculator_rejects_boolean_and_string_literals():
    for expression in ("True", "'hello'", "None"):
        try:
            safe_calculate(expression)
            assert False, f"Non-numeric expression accepted: {expression}"
        except ValueError:
            pass


def test_run_id_path_validation():
    from app.mcp_tools import _validated_run_path
    import pytest
    with pytest.raises(ValueError):
        _validated_run_path("../../outside", ".json")

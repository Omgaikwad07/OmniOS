"""
actions/calculator.py
=====================
Safe local arithmetic evaluator for OmniOS.

Uses Python's ``ast`` module to parse and walk the expression tree.
``eval()``, ``exec()``, and all non-arithmetic AST nodes are explicitly
rejected before any computation takes place.

Supported operations
--------------------
  +   addition
  -   subtraction  /  unary minus
  *   multiplication
  /   true division
  %   modulo
  **  exponentiation
  ()  parentheses for grouping
  .   decimal literals (e.g. 3.14)
"""

from __future__ import annotations

import ast
import math

from core.schemas import ExecutionResult, ResultStatus

# Maximum expression length accepted (characters).
_MAX_EXPR_LEN = 200

# Exponentiation operand limits (integers only).
# float ** float is bounded by IEEE 754 and is always safe.
# Python integers are unbounded, so 9**9**9 would allocate gigabytes.
_MAX_INT_BASE = 1_000_000
_MAX_INT_EXP  = 1_000

# Allowed binary operator AST types mapped to callables.
_BINOPS: dict[type, object] = {
    ast.Add:  lambda a, b: a + b,
    ast.Sub:  lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div:  lambda a, b: a / b,
    ast.Mod:  lambda a, b: a % b,
    ast.Pow:  lambda a, b: a ** b,
}

# Allowed unary operator AST types mapped to callables.
_UNARYOPS: dict[type, object] = {
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: +a,
}


def _eval_node(node: ast.AST) -> float | int:
    """Recursively evaluate an AST node.

    Only whitelisted node types are processed.  Any other node type
    raises ``ValueError`` immediately — no code is ever executed.
    """
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"Non-numeric constant: {node.value!r}")
        return node.value

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BINOPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if op_type is ast.Div and right == 0:
            raise ZeroDivisionError("Division by zero.")
        if op_type is ast.Mod and right == 0:
            raise ZeroDivisionError("Modulo by zero.")
        if op_type is ast.Pow and isinstance(left, int) and isinstance(right, int):
            if abs(left) > _MAX_INT_BASE or abs(right) > _MAX_INT_EXP:
                raise ValueError(
                    f"Exponentiation operands too large (base limit {_MAX_INT_BASE}, "
                    f"exponent limit {_MAX_INT_EXP}). Use smaller values."
                )
        return _BINOPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARYOPS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        return _UNARYOPS[op_type](_eval_node(node.operand))

    # Everything else — Call, Attribute, Name, Import, Subscript, etc. — is rejected.
    raise ValueError(
        f"Unsupported expression node '{type(node).__name__}'. "
        "Only arithmetic expressions are allowed."
    )


def calculate(expression: str) -> ExecutionResult:
    """Evaluate a safe arithmetic expression.

    Parameters
    ----------
    expression : str
        A string containing only numbers, arithmetic operators
        (+, -, *, /, %, **), parentheses, and decimal points.

    Returns
    -------
    ExecutionResult
        SUCCESS with the numeric result in ``output``; REFUSED for
        disallowed expressions; ERROR for division by zero or overflow.
    """
    if not expression or not isinstance(expression, str):
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error="expression must be a non-empty string.",
        )

    expression = expression.strip()

    if len(expression) > _MAX_EXPR_LEN:
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            error=f"Expression exceeds maximum length of {_MAX_EXPR_LEN} characters.",
        )

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            error=f"Invalid expression syntax: {exc.msg}",
        )

    try:
        result = _eval_node(tree)
    except ZeroDivisionError as exc:
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error=str(exc),
        )
    except ValueError as exc:
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            error=str(exc),
        )

    # Guard against non-finite results (e.g. overflow via huge exponentiation).
    if isinstance(result, float) and not math.isfinite(result):
        return ExecutionResult(
            status=ResultStatus.ERROR,
            error=f"Result is not a finite number: {result}",
        )

    # Return a clean numeric string: drop unnecessary trailing zeros.
    formatted = int(result) if isinstance(result, float) and result == int(result) else result
    return ExecutionResult(
        status=ResultStatus.SUCCESS,
        output=formatted,
    )

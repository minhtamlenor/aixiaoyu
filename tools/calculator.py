# ============================================================
# TIỂU VŨ - CALCULATOR TOOL
# ============================================================

import ast
import operator


OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def calculate(expression):
    """
    Tính biểu thức toán học an toàn.
    Ví dụ:
    12 + 5
    100 / 4
    25 * 8
    """

    try:
        tree = ast.parse(
            expression,
            mode="eval"
        )

        result = _evaluate(tree.body)

        if isinstance(result, float) and result.is_integer():
            result = int(result)

        return str(result)

    except Exception:
        return "Không tính được biểu thức này."


def _evaluate(node):

    if isinstance(node, ast.Constant):

        if isinstance(node.value, (int, float)):

            return node.value

        raise ValueError()


    if isinstance(node, ast.BinOp):

        operator_function = OPERATORS.get(
            type(node.op)
        )

        if operator_function is None:
            raise ValueError()

        left = _evaluate(node.left)
        right = _evaluate(node.right)

        return operator_function(left, right)


    if isinstance(node, ast.UnaryOp):

        operator_function = OPERATORS.get(
            type(node.op)
        )

        if operator_function is None:
            raise ValueError()

        return operator_function(
            _evaluate(node.operand)
        )


    raise ValueError()
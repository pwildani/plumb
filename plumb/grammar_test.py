from .grammar import parse_commands
from . import ast
from lark import Token


def word(s: str) -> Token:
    return Token("WORD", s)


def bareword(s: str) -> Token:
    return Token("BAREWORD", s)


def test_simplest_rule():
    r = parse_commands(
        """
    rule test
    stop
    """
    )
    assert len(r) == 2
    assert isinstance(r[0], ast.RuleCommand)
    assert r[0].label == "test"
    assert (
        ast.RuleCommand(label=word("test")),
        ast.StopAction(),
    ) == r


def test_basic_commands_with_var():
    r = parse_commands(
        """
    rule test
    a=b
    stop
    """
    )
    assert len(r) == 3
    assert isinstance(r[0], ast.RuleCommand)
    assert r[0].label == "test"
    assert (
        ast.RuleCommand(label=Token("WORD", "test")),
        ast.SetVariable(
            var=Token("WORD", "a"), rhs=ast.ExprLiteral(val=Token("WORD", "b"))
        ),
        ast.StopAction(),
    ) == r


def test_set_var_to_str():
    r = parse_commands(
        """
    a="str"
    """
    )
    assert len(r) == 1
    assert (
        ast.SetVariable(var=Token("WORD", "a"), rhs=ast.ExprLiteral(val="str")),
    ) == r


def test_set_var_to_var():
    r = parse_commands(
        """
    a=$b
    """
    )
    assert len(r) == 1
    assert (
        ast.SetVariable(var=Token("WORD", "a"), rhs=ast.VariableReference("b")),
    ) == r


def test_simple_glob():
    r = parse_commands(
        """
    glob "*.py"
    """
    )
    assert len(r) == 1
    assert (ast.ConditionCommand(condition=(ast.GlobCondition(pattern="*.py"))),) == r


def test_bareword_glob():
    r = parse_commands(
        """
    glob py
    """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(condition=(ast.GlobCondition(pattern=bareword("py")))),
    ) == r


def test_multi_glob_quoted():
    r = parse_commands(
        """
    glob "*.py" "*.pyc"
    """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.OrCondition(
                (
                    ast.GlobCondition("*.py"),
                    ast.GlobCondition("*.pyc"),
                )
            )
        ),
    ) == r


def test_multi_glob_bare():
    r = parse_commands(
        """
    glob *.py *.pyc
    """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.OrCondition(
                (
                    ast.GlobCondition(bareword("*.py")),
                    ast.GlobCondition(bareword("*.pyc")),
                )
            )
        ),
    ) == r


def test_is_dir():
    r = parse_commands(
        """
    is dir
    """
    )
    assert len(r) == 1
    assert (ast.ConditionCommand(ast.StatFileTypeCondition("dir")),) == r


def test_stop():
    r = parse_commands(
        """
    stop
    """
    )
    assert len(r) == 1
    assert (ast.StopAction(),) == r


def test_copyto():
    r = parse_commands(
        """
    copyto "dest"
    """
    )
    assert len(r) == 1
    assert (ast.CopyToAction("dest"),) == r


def test_conjunction():
    r = parse_commands(
        """
    is file and is dir
    """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.StatFileTypeCondition("file"),
                    ast.StatFileTypeCondition("dir"),
                )
            )
        ),
    ) == r


def test_disjunction():
    r = parse_commands(
        """
    is file or is dir
    """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.OrCondition(
                (
                    ast.StatFileTypeCondition("file"),
                    ast.StatFileTypeCondition("dir"),
                )
            )
        ),
    ) == r


def test_parens():
    r = parse_commands(
        """
    (is file)
    """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.StatFileTypeCondition("file"),
        ),
    ) == r


def test_parens_2():
    r = parse_commands(
        """
    (is file
    or is dir)
    """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.OrCondition(
                (
                    ast.StatFileTypeCondition("file"),
                    ast.StatFileTypeCondition("dir"),
                )
            )
        ),
    ) == r


def test_and_glob_long():
    r = parse_commands(
        """
    (
     glob x
     and glob y
    )
    """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.GlobCondition(bareword("x")),
                    ast.GlobCondition(bareword("y")),
                )
            )
        ),
    ) == r


def test_and_glob_flat():
    r = parse_commands(
        """
    glob x and glob y
    """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.GlobCondition(bareword("x")),
                    ast.GlobCondition(bareword("y")),
                )
            )
        ),
    ) == r


def test_multi_and_glob_flat():
    r = parse_commands(
        """
    glob x z and glob y q
    """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.OrCondition(
                        (
                            ast.GlobCondition(bareword("x")),
                            ast.GlobCondition(bareword("z")),
                        )
                    ),
                    ast.OrCondition(
                        (
                            ast.GlobCondition(bareword("y")),
                            ast.GlobCondition(bareword("q")),
                        )
                    ),
                )
            )
        ),
    ) == r


def test_multi_or_glob_flat():
    r = parse_commands(
        """
    glob x z or glob y q
    """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.OrCondition(
                (
                    ast.GlobCondition(bareword("x")),
                    ast.GlobCondition(bareword("z")),
                    ast.GlobCondition(bareword("y")),
                    ast.GlobCondition(bareword("q")),
                )
            )
        ),
    ) == r

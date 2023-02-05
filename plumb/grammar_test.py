from .grammar import parse_commands
from . import ast
from lark import Token


def bareword(s: str) -> Token:
    return Token("BAREWORD", s)


word = bareword


def litword(s: str) -> ast.ExprLiteral:
    return ast.ExprLiteral(bareword(s))


def litstr(s: str) -> ast.ExprLiteral:
    return ast.ExprLiteral(s)


def varref(s: str) -> ast.VariableReference:
    return ast.VariableReference(word(s))


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
        stop"""
    )
    assert len(r) == 3
    assert isinstance(r[0], ast.RuleCommand)
    assert r[0].label == "test"
    assert (
        ast.RuleCommand(label=bareword("test")),
        ast.SetVariable(var=bareword("a"), rhs=litword("b")),
        ast.StopAction(),
    ) == r


def test_set_var_to_word():
    r = parse_commands(
        """a=str""",
    )
    assert len(r) == 1
    assert (ast.SetVariable(var=bareword("a"), rhs=litword("str")),) == r


def test_set_var_to_var():
    r = parse_commands("""a=$b """)
    assert len(r) == 1
    assert (ast.SetVariable(word("a"), varref("b")),) == r


def test_simple_glob():
    r = parse_commands("""glob "*.py\"""")
    assert len(r) == 1
    assert (ast.ConditionCommand(condition=(ast.GlobCondition(litstr("*.py")))),) == r


def test_bareword_glob():
    r = parse_commands("""glob py""")
    assert len(r) == 1
    assert (ast.ConditionCommand(condition=(ast.GlobCondition(litword("py")))),) == r


def test_multi_glob_quoted():
    r = parse_commands(
        """\n
    glob "*.py" "*.pyc"\n
    """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.OrCondition(
                (
                    ast.GlobCondition(litstr("*.py")),
                    ast.GlobCondition(litstr("*.pyc")),
                )
            )
        ),
    ) == r


def test_multi_glob_bare():
    r = parse_commands("""glob *.py *.pyc""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.OrCondition(
                (
                    ast.GlobCondition(litword("*.py")),
                    ast.GlobCondition(litword("*.pyc")),
                )
            )
        ),
    ) == r


def test_simple_not():
    r = parse_commands("""not is file""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.NotCondition(ast.StatFileTypeCondition(Token("FILEMODETYPES", "file")))
        ),
    ) == r


def test_parens_not():
    r = parse_commands("""not(is file)""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.NotCondition(ast.StatFileTypeCondition(Token("FILEMODETYPES", "file")))
        ),
    ) == r


def test_and_not():
    r = parse_commands("""is file and not is file""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.StatFileTypeCondition(Token("FILEMODETYPES", "file")),
                    ast.NotCondition(
                        ast.StatFileTypeCondition(Token("FILEMODETYPES", "file"))
                    ),
                )
            )
        ),
    ) == r


def test_and_not_parens2nd():
    r = parse_commands("""is file and (not is file)""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.StatFileTypeCondition(Token("FILEMODETYPES", "file")),
                    ast.NotCondition(
                        ast.StatFileTypeCondition(Token("FILEMODETYPES", "file"))
                    ),
                )
            )
        ),
    ) == r


def test_and_not_parens3rd():
    r = parse_commands("""is file and not (is file)""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.StatFileTypeCondition(Token("FILEMODETYPES", "file")),
                    ast.NotCondition(
                        ast.StatFileTypeCondition(Token("FILEMODETYPES", "file"))
                    ),
                )
            )
        ),
    ) == r


def test_and_not_parens1st():
    r = parse_commands("""(is file) and not is file""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.StatFileTypeCondition(Token("FILEMODETYPES", "file")),
                    ast.NotCondition(
                        ast.StatFileTypeCondition(Token("FILEMODETYPES", "file"))
                    ),
                )
            )
        ),
    ) == r


def test_and_not_parens_outer():
    r = parse_commands("""(is file and not is file)""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.StatFileTypeCondition(Token("FILEMODETYPES", "file")),
                    ast.NotCondition(
                        ast.StatFileTypeCondition(Token("FILEMODETYPES", "file"))
                    ),
                )
            )
        ),
    ) == r


def test_and_not_parens_inner_1():
    r = parse_commands("""(is file)and(not is file)""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.StatFileTypeCondition(Token("FILEMODETYPES", "file")),
                    ast.NotCondition(
                        ast.StatFileTypeCondition(Token("FILEMODETYPES", "file"))
                    ),
                )
            )
        ),
    ) == r


def test_and_not_parens_full():
    r = parse_commands("""(is file)and(not(is file))""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.StatFileTypeCondition(Token("FILEMODETYPES", "file")),
                    ast.NotCondition(
                        ast.StatFileTypeCondition(Token("FILEMODETYPES", "file"))
                    ),
                )
            )
        ),
    ) == r


def test_multi_glob_not():
    r = parse_commands("""glob *.py and not glob *.pyc""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.GlobCondition(litword("*.py")),
                    ast.NotCondition(ast.GlobCondition(litword("*.pyc"))),
                )
            )
        ),
    ) == r


def test_multi_glob_not_parens_1():
    r = parse_commands("""(glob *.py)and not glob *.pyc""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.GlobCondition(litword("*.py")),
                    ast.NotCondition(ast.GlobCondition(litword("*.pyc"))),
                )
            )
        ),
    ) == r


def test_multi_glob_not_parens_2():
    r = parse_commands("""glob *.py and(not glob *.pyc)""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.GlobCondition(litword("*.py")),
                    ast.NotCondition(ast.GlobCondition(litword("*.pyc"))),
                )
            )
        ),
    ) == r


def test_match():
    r = parse_commands("""match "x" """)
    assert len(r) == 1
    assert (ast.ConditionCommand(ast.RegexCondition(litstr("x"))),) == r


def test_grep():
    r = parse_commands("""grep "x" """)
    assert len(r) == 1
    assert (ast.ConditionCommand(ast.GrepCondition(litstr("x"))),) == r


def test_is_dir():
    r = parse_commands("""is dir""")
    assert len(r) == 1
    assert (ast.ConditionCommand(ast.StatFileTypeCondition("dir")),) == r


def test_stop():
    r = parse_commands("""stop""")
    assert len(r) == 1
    assert (ast.StopAction(),) == r


def test_copyto():
    r = parse_commands(""" copyto "dest" """)
    assert len(r) == 1
    assert (ast.CopyToAction(litstr("dest")),) == r


def test_conjunction():
    r = parse_commands("""is file and is dir""")
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
    r = parse_commands("""is file or is dir""")
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
    r = parse_commands("""(is file)""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.StatFileTypeCondition("file"),
        ),
    ) == r


def test_parens_2():
    r = parse_commands(
        """
        ((is file or is dir))
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
        (glob x and glob y)
        """
    )
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.GlobCondition(litword("x")),
                    ast.GlobCondition(litword("y")),
                )
            )
        ),
    ) == r


def test_and_glob_flat():
    r = parse_commands("""glob x and glob y""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.GlobCondition(litword("x")),
                    ast.GlobCondition(litword("y")),
                )
            )
        ),
    ) == r


def test_multi_and_glob_flat():
    r = parse_commands("""glob x z and glob y q""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.AndCondition(
                (
                    ast.OrCondition(
                        (
                            ast.GlobCondition(litword("x")),
                            ast.GlobCondition(litword("z")),
                        )
                    ),
                    ast.OrCondition(
                        (
                            ast.GlobCondition(litword("y")),
                            ast.GlobCondition(litword("q")),
                        )
                    ),
                )
            )
        ),
    ) == r


def test_multi_or_glob_flat():
    r = parse_commands("""glob x z or glob y q""")
    assert len(r) == 1
    assert (
        ast.ConditionCommand(
            ast.OrCondition(
                (
                    ast.GlobCondition(litword("x")),
                    ast.GlobCondition(litword("z")),
                    ast.GlobCondition(litword("y")),
                    ast.GlobCondition(litword("q")),
                )
            )
        ),
    ) == r


def test_glob_of_var():
    r = parse_commands("""$foo glob x""")
    assert len(r) == 1
    assert (ast.ConditionCommand(ast.GlobCondition(litword("x"))),) == r
    assert r[0].condition.datasource == varref("foo")


def test_inspect_all():
    r = parse_commands("""inspect all""")
    assert len(r) == 1
    assert (ast.InspectAction(Token("ALL", "all")),) == r


def test_inspect_var():
    r = parse_commands("""inspect $foo""")
    assert len(r) == 1
    assert (ast.InspectAction(varref("foo")),) == r


def test_fstring_empty():
    r = parse_commands(
        """
    x = ""
    """
    )
    assert r[0].rhs == ast.ExprLiteral("")


def test_fstring_simple():
    r = parse_commands(
        """
    x = "data"
    """
    )
    assert r[0].rhs == ast.ExprLiteral("data")


def test_fstring_bareword():
    r = parse_commands(
        """
    x = "{HOME}"
    """
    )
    assert r[0].rhs == litword("HOME")


def test_fstring_varref():
    r = parse_commands(
        """
    x = "{$HOME}"
    """
    )
    assert r[0].rhs == ast.VariableReference("HOME")


def test_fstring_strcat_prefix_bareword():
    r = parse_commands(
        """
    x = "a{word}"
    """
    )
    assert r[0].rhs == ast.ExprLiteral("aword")


def test_fstring_strcat_suffix_bareword():
    r = parse_commands(
        """
    x = "{word}a"
    """
    )
    assert r[0].rhs == ast.ExprLiteral("worda")


def test_fstring_strcat_infix_bareword():
    r = parse_commands(
        """
    x = "the{word}a"
    """
    )
    assert r[0].rhs == ast.ExprLiteral("theworda")


def test_fstring_strcat_bareword2():
    r = parse_commands(
        """
    x = "{a}{word}"
    """
    )
    assert r[0].rhs == ast.ExprLiteral("aword")


def test_fstring_strcat_substring():
    r = parse_commands(
        """
    x = "{"foo"}"
    """
    )
    assert r[0].rhs == ast.ExprLiteral("foo")


def test_fstring_strcat_substring_prefix():
    r = parse_commands(
        """
    x = "{"foo"}bar"
    """
    )
    assert r[0].rhs == ast.ExprLiteral("foobar")


def test_fstring_strcat_substring_prefix():
    r = parse_commands(
        """
    x = "foo{"bar"}"
    """
    )
    assert r[0].rhs == ast.ExprLiteral("foobar")


def test_fstring_strcat_substring2():
    r = parse_commands(
        """
    x = "{"foo"}{"bar"}"
    """
    )
    assert r[0].rhs == ast.ExprLiteral("foobar")


def test_fstring_strcat_varref_suffix():
    r = parse_commands(
        """
    x = "a{$foo}"
    """
    )
    assert r[0].rhs == ast.StringConcatExpr([ast.ExprLiteral("a"), varref("foo")])


def test_fstring_strcat_varref_2():
    r = parse_commands(
        """
    x = "{$foo}{$bar}"
    """
    )
    assert r[0].rhs == ast.StringConcatExpr([varref("foo"), varref("bar")])


def test_fstring_strcat_varref_prefix():
    r = parse_commands(
        """
    x = "{$foo}a"
    """
    )
    assert r[0].rhs == ast.StringConcatExpr(
        [
            varref("foo"),
            ast.ExprLiteral("a"),
        ]
    )


def test_fstring_strcat_varref_infix():
    r = parse_commands(
        """
    x = "b{$foo}a"
    """
    )
    assert r[0].rhs == ast.StringConcatExpr(
        [
            ast.ExprLiteral("b"),
            varref("foo"),
            ast.ExprLiteral("a"),
        ]
    )

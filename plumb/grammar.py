import logging
import lark
from . import ast
from typing import Type

lark.logger.setLevel(logging.DEBUG)

__all__ = ["command_parser"]

FILE_MODE_TYPES = sorted(ast.StatFileTypeCondition.MODE_TYPES.keys())
FILE_MODE_GRAMMAR = f"""
%override FILEMODETYPES: {'|'.join(f'"{t}"' for t in FILE_MODE_TYPES)}
"""


command_parser = lark.Lark(
    grammar := r"""\
start: _NL* _command ( _NL+ _command)* _NL*

_command: rulecommand | _actioncommand | _varcommand | conditioncommand

rulecommand: "rule"i BAREWORD
conditioncommand: _conditionexpr
_varcommand: _varexpr
_actioncommand: stop | copyto | inspect | moveto

_conditionexpr: notcondition | _atomiccondition | junctioncondition
junctioncondition: _conditionexpr BOOLEANOPERATION _conditionexpr

BOOLEANOPERATION: "and"|"or"

notcondition: _NOT _atomiccondition
_NOT.1: "not"i

_atomiccondition: ( "(" _conditionexpr ")") | condition

condition: [expr] (glob | is_filemodetype | match | grep)

glob: "glob"i _glob_pat+
match: "match"i fstr
grep: "grep"i fstr
is_filemodetype: "is"i FILEMODETYPES

 // regex: "/" _regex_contents+ "/"

_varexpr: setvar

setvar: _varname "=" expr
expr: _exprscalar | envlookup
_exprscalar: fstr | varref | exprliteral
exprliteral: BAREWORD
varref: "$" _varname

envlookup: "env"i expr

_varname: BAREWORD

inspect: "inspect"i [ALL|expr]
ALL: "all"i
copyto: "copyto"i expr
moveto: "moveto"i expr
stop: "stop"i


fstr: "\"" _fstr_contents* "\""
_fstr_expr: "{" expr "}"
_LBRACE.99: "{"
_RBRACE.99: "}"
_fstr_contents: (_fstr_expr | FEXPR_STRING_CHAR | escaped_char)
FEXPR_STRING_CHAR.0: /[^\\"{}\n]+/

// _regex_contents: (_fstr_expr | REGEX_STRING_CHAR| escaped_char)
// REGEX_STRING_CHAR.0: /[^\\\/{}\n]+/

escaped_char: ESCAPED_CHAR
ESCAPED_CHAR: /\\./

_glob_pat: expr

// BAREWORD: non-whitespace text that isn't also keyword-like or things that might
// be failed attempts at quoting.
BAREWORD: /(?!\b(and|or|not|glob|is|rule)\b)[^\s#$"'\\\s()={}]+/i

// WS_STRING: /[^\s\n]+/
// EMPTY_LINE: /^\s*\n/

_separated{x, sep}: x (sep x)*

FILEMODETYPES: "dir" | "file"

%import common.NEWLINE -> _NL
%import common (WS_INLINE, ESCAPED_STRING, SH_COMMENT)
%ignore WS_INLINE
%ignore SH_COMMENT

"""
    + FILE_MODE_GRAMMAR,
    debug=True,
    parser="lalr",
)


@lark.v_args(inline=True)
class CommandTree(lark.Transformer):
    def __init__(self):
        super().__init__()
        self.referenced_variables = set()

    def _as_tuple(self, *a) -> tuple:
        return a

    actions = _as_tuple

    def escaped_string(self, value: str) -> str:
        return value[1:-1].replace(r"\"", '"')

    def rulecommand(self, label):
        return ast.RuleCommand(label)

    def junctioncondition(
        self, lhs: ast.Condition, op: lark.Token, rhs: ast.Condition | None = None
    ):
        """
        boolean logic operations
        """
        node: Type[ast.AndCondition] | Type[ast.OrCondition] = ast.AndCondition
        match op.lower():
            case "and":
                node = ast.AndCondition
            case "or":
                node = ast.OrCondition

        # Peephole optimization: collapse operator chains to one operator tree
        # node.
        match lhs, rhs:
            case node(lhschildren), node(rhschildren):
                # (a and b) and (c and d)
                assert isinstance(lhs, node)
                lhs.children = lhschildren + rhschildren
                return lhs
            case node(lhschildren), _:
                # (a and b) and c
                assert isinstance(lhs, node)
                lhs.children = lhschildren + (rhs,)
                return lhs
            case _, node(rhschildren):
                # c and (a and b)
                # and also the second most common case of chaining: a and b and c
                # because the grammar is right recursive.
                assert isinstance(rhs, node)
                rhs.children = (lhs,) + rhschildren
                return rhs
            case None, None:
                # dunno how we got here
                return node(tuple())
            case _, None:
                # dunno how we got here
                return node((lhs,))
            case None, _:
                # dunno how we got here
                return node((rhs,))
            case _:
                # The most common case: a and b
                return node((lhs, rhs))

    junctionconditionnl = junctioncondition

    def notcondition(self, child):
        return ast.NotCondition(child)

    def copyto(self, dest):
        return ast.CopyToAction(dest)

    def glob(self, *pats):
        if len(pats) == 1:
            return ast.GlobCondition(pats[0])

        globs: list[ast.Condition] = []
        globs.extend(ast.GlobCondition(p) for p in pats)
        return ast.OrCondition(tuple(globs))

    def stop(self):
        return ast.StopAction()

    def inspect(self, arg=None):
        return ast.InspectAction(arg)

    def is_filemodetype(self, filetype):
        assert str(filetype) in ast.StatFileTypeCondition.MODE_TYPES, filetype
        return ast.StatFileTypeCondition(filetype)

    def setvar(self, var, rhs):
        return ast.SetVariable(var, rhs)

    def exprliteral(self, value):
        return ast.ExprLiteral(value)

    def varref(self, var: lark.Token):
        self.referenced_variables.add(var)
        return ast.VariableReference(var)

    def conditioncommand(self, condition: ast.Condition):
        return ast.ConditionCommand(condition)

    def condition(
        self, datasource: ast.Expr | None, condition: ast.Condition
    ) -> ast.Condition:
        condition.datasource = datasource
        return condition

    def match(self, regex: ast.Expr) -> ast.Condition:
        return ast.RegexCondition(regex)

    def grep(self, regex: ast.Expr) -> ast.Condition:
        return ast.GrepCondition(regex)

    def moveto(self, dest: ast.Expr) -> ast.Action:
        return ast.MoveToAction(dest)

    def expr(self, expr):
        return expr

    def start(self, *commands):
        return commands

    def envlookup(self, nameexpr):
        return ast.EnvironmentLookupExpr(nameexpr)

    def escaped_char(self, char):
        assert char[0] == "\\"
        return char[1]

    def fstr(self, *parts):
        fused: list[ast.Expr] = []
        print("FSTR", parts)
        for part in parts:
            match part:
                # Flatten the string bits
                case ast.ExprLiteral(v) | lark.Token("FEXPR_STRING_CHAR", v):
                    if fused:
                        if isinstance(fused[-1], ast.ExprLiteral):
                            print("FSTR EXPRFUSION", fused[-1], "+", v)
                            fused[-1].val += v
                            continue
                        if isinstance(fused[-1], lark.Token):
                            print("FSTR TOKENFUSION", fused[-1], "+", v)
                            last: lark.Token = fused[-1]
                            fused[-1] = ast.ExprLiteral(last + v)
                        else:
                            print("FSTR APPEND NEW", v)
                            fused.append(ast.ExprLiteral(v))
                    else:
                        print("FSTR APPEND FIRST", v)
                        fused.append(ast.ExprLiteral(v))
                case ast.Expr():
                    print("FSTR APPEND UNFUSABLE", part)
                    fused.append(part)
                case _:
                    assert (
                        False
                    ), f"Unexpected element in string or regex literal: {part!r}"

        match len(fused):
            case 1:
                # Nothing to concat. Skip that step
                return fused[0]
            case 0:
                # empty string
                return ast.ExprLiteral("")
            case _:
                return ast.StringConcatExpr(fused)

    regex = fstr


def parse_commands(text, grammarentrypoint="start") -> list[ast.Command]:
    p = command_parser.parse(text, start=grammarentrypoint)
    commands: list[ast.Command] = CommandTree().transform(p)
    return commands

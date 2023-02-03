import logging
import lark
from . import ast

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

_unused: _varcommand | conditioncommand| _actioncommand

rulecommand: "rule"i WORD
conditioncommand: _conditionexpr
_varcommand: _varexpr
_actioncommand: stop | copyto | inspect

_conditionexpr: _atomiccondition | junctioncondition | notcondition
junctioncondition: _atomiccondition BOOLEANOPERATION _conditionexpr

// junctionconditionnl, conditionexprnl: Accept NL inside parens, but otherwise identical to junctioncondition
_conditionexprnl: (_atomiccondition | junctionconditionnl | notcondition)
junctionconditionnl: _atomiccondition _NL? BOOLEANOPERATION _NL? _conditionexpr

BOOLEANOPERATION: "and"|"or"

notcondition: "not"i (_atomiccondition)

_atomiccondition: condition | "(" _NL? _conditionexprnl _NL? ")"

condition: [expr] (glob | is_filemodetype | match)

glob: "glob"i _glob_pat+
match: "match"i _regex
is_filemodetype: "is"i FILEMODETYPES

regex: "/" regexcontents "/"
//!regexcontents: ( /[\w]/ | /\\\W/ | "(" regexcontents ")" | "[" ( "-" | "^" | "\\]") /[^\]]|\\\]/ "]" )* 
regexcontents:  /x/

_varexpr: setvar

setvar: _varname "=" expr
expr: _exprscalar
_exprscalar: exprliteral | varref
exprliteral: escaped_string | WORD
varref: "$" _varname

_varname: WORD

inspect: "inspect"i [ALL|expr]
ALL: "all"i
copyto: "copyto"i escaped_string
stop: "stop"i

escaped_string: ESCAPED_STRING

_glob_pat: escaped_string | BAREWORD

// BAREWORD: non-whitespace text that isn't also keyword-like or things that might
// be failed attempts at quoting.
BAREWORD: /(?!\b(and|or|not|glob|is|rule)\b)[^"'\\\s()]+/i

_regex: escaped_string | WORD

WS_STRING: /[^\s\n]+/
EMPTY_LINE: /^\s*\n/

_separated{x, sep}: x (sep x)*

FILEMODETYPES: "dir" | "file"

%import common.NEWLINE -> _NL
%import common (WORD, INT, WS, WS_INLINE, ESCAPED_STRING, SH_COMMENT)
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
        self, lhs: ast.Condition, op: lark.Token, rhs: ast.Condition = None
    ):
        """
        boolean logic operations
        """
        node = ast.AndCondition
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

    def condition(self, datasource: ast.Expr | None, condition: ast.Condition):
        condition.datasource = datasource
        return condition

    def match(self, regex):
        return ast.RegexCondition(regex)

    def expr(self, expr):
        return expr

    def regexcontents(self, *parts):
        # TODO: dynamic regex with ${varref} parts
        return "".join(parts)

    def regex(self, pattern):
        import re

        return re.compile(pattern)

    def start(self, *commands):
        return commands


def parse_commands(text, grammarentrypoint="start") -> list[ast.Command]:
    p = command_parser.parse(text, start=grammarentrypoint)
    commands: list[ast.Command] = CommandTree().transform(p)
    return commands

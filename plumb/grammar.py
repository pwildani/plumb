import logging
import lark
from . import ast

# lark.logger.setLevel(logging.DEBUG)

__all__ = ["parser", "Plumbing"]

FILE_MODE_TYPES = sorted(ast.StatFileTypeCondition.MODE_TYPES.keys())
FILE_MODE_GRAMMAR = f"""
%override FILEMODETYPES: {'|'.join(f'"{t}"' for t in FILE_MODE_TYPES)}
"""

parser = lark.Lark(
    grammar := r"""\
start: _NL? rule+

rule: _label _NL conditions _NL actions _NL+
_label: "rule"i WORD

FILEMODETYPES: "dir" | "file"

conditions: _separated{_conditionexpr, _NL}
_conditionexpr: _atomiccondition | conjunctioncondition | notcondition
conjunctioncondition: _atomiccondition _NL? "and"i _conditionexpr
disjunctioncondition: _atomiccondition _NL? "or"i _conditionexpr
notcondition: "not"i _atomiccondition
_atomiccondition: _subcondition | glob | is_filemodetype
_subcondition: "(" _conditionexpr ")"

glob: "glob"i _glob_pat+ 
is_filemodetype: "is"i FILEMODETYPES

actions: _separated{_action, _NL}
_action: stop | copyto

copyto: "copyto"i escaped_string
stop: "stop"i

escaped_string: ESCAPED_STRING

_glob_pat: escaped_string | WORD
_regex: escaped_string | WORD

WS_STRING: /[^\s\n]+/
EMPTY_LINE: /^\s*\n/

_separated{x, sep}: x (sep x)*

%import common.NEWLINE -> _NL
%import common (WORD, INT, WS, WS_INLINE, ESCAPED_STRING, SH_COMMENT)
%ignore WS_INLINE
%ignore SH_COMMENT

"""
    + FILE_MODE_GRAMMAR,
    # debug=True,
)


@lark.v_args(inline=True)
class Plumbing(lark.Transformer):
    def __init__(self):
        self.rules: list[ast.Rule] = []

    def _as_tuple(self, *a) -> tuple:
        return a

    actions = _as_tuple

    def escaped_string(self, value: str) -> str:
        return value[1:-1].replace(r"\"", '"')

    def rule(self, label, condition: ast.Condition, actions: list[ast.Action]):
        rule = ast.Rule(label, condition, actions)
        self.rules.append(rule)
        return rule

    def conjunctioncondition(self, *children: ast.Condition):
        return ast.AndCondition(children)

    conditions = conjunctioncondition

    def disjunctioncondition(self, *children: ast.Condition):
        return ast.OrCondition(children)

    def notcondition(self, child):
        return ast.NotCondition(child)

    def copyto(self, dest):
        return ast.CopyToAction(dest)

    def glob(self, *pats):
        globs: list[ast.Condition] = []
        globs.extend(ast.GlobCondition(p) for p in pats)
        return ast.OrCondition(tuple(globs))

    def stop(self):
        return ast.StopAction()

    def is_filemodetype(self, filetype):
        assert str(filetype) in ast.StatFileTypeCondition.MODE_TYPES, filetype
        return ast.StatFileTypeCondition(filetype)

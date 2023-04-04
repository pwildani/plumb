Loosely inspired by plan9's plumb.

Each input message is run through the rules to discover what actions to take. Then the selected actions are run.

Setting message fields other than the core `data` is a work in progress.


Example: 

Goal: "When I download an html file that's a Twine game, move it to my games/twine folder."

Which can expressed in `plumb_rules` as :
```
rule move-twine-to-games-webserver
glob */Downloads/*.html
grep "(?i)sugarcane" or grep "(?i)twine"
moveto "{env HOME}/games/twine"
```

Which will cause `plumb Downloads/my-fresh-twine-discovery.html` to move that file
out of downloads into $HOME/games/twine


## Flow Control

Execution of plumbing steps starts at the top of the file, then runs until a
(Condition)[#Condition] step fails, after which execution resumes at the next
(`rule`)[#rule] block.

Technically, each line is a separate command including "rule". But since the
default flow control on condition failures is "jump to the next rule", it works
best to think of each rule as an independent block.


### rule

```
rule <name>
```

A block of commands. The rule has a required name, but it is not used by plumb yet.

Example:
```
rule catchall
inspect "{$data} was not routable!"
stop
```

### stop
```
stop
```

Technically an action command, `stop` command halts rule evaluation, and thus starts execution of the collected actions.
Use this when a rule is decisive and no other rule should handle this message.
(Note that rules are evaluated in their order of definition)

Example:
```
rule catchall
inspect "{$data} was not routable!"
stop
```

## Conditions
Conditions check the state of the message's data payload (by default) or an
expression (before the condition if specified). They can succeed or fail. On
failure, the current `rule` is aborted and plumb jumps to evaluating the next
`rule`.

```
[expr] <condition>
```

### is X

where X is the bare word "file" or "dir" or other types of objects that dwell in the depths of file systems.

Checks if the path names a file or directory or any other thing a file path can name.
(see stat(2)'s `st_mode` docs for other types of things that live in file systems.)

```
is file
is dir
... and other types
```


### glob
```
glob <glob-pattern>
```
Check if the data matches the glob pattern. (see glob(3) for syntax)

Example:
```
glob "*.txt"
```

### match
```
match "regex-pattern"
```
Check if the data matches the given regular expression.
See `pydoc3 re` for syntax.

Capture groups in the pattern are put in variables `$1`, `$2`, `$3`, .... The whole match is put in `$0`.
Named groups are in `$match_<name>`.


### grep
```
grep "regex-pattern"
grep(< bytecount scale) "regex-pattern"
```
Check if the *contents* of the path named by data match the given regular expression.
See `pydoc3 re` for syntax.

If (< bytecount scale) is specified, and bytecount is a decimal integer and
scale is not specified or one of b, kb,kib,mb,mib,gb,gib, limit the portion of
the file specified to those bytes.


## Actions

### X = Y
```
<variable name> = <expression>
```
Sets the contents of a variable to the result of an expression


### copyto
```
copyto <expr>
```

`rsync`s the path named by data (TODO should be file) to the named destination.

### moveto

```
moveto <expr>
```

`mv`s the path named by data (TODO should be file) to the named destination.

### inspect

```
inspect all|<expression>
```

Debug helper.
Print out the argument expression, or when given `all`, all message properties and variables.

```
rule catchall
inspect "{$data} was not routable!"
stop
```


## Expressions

### and, or, not, ()'s
Conditions can be joined in disjunctions with `or`, conjunctions with `and`,
and inverted with `not`. Order of evaluation is specified with parentheses.

```
(glob "*.pt" and not glob "*.vae.pt") or glob "*.yaml"
```


### "strings" and "string{concatenation}"

String literals and string interpolation. Backslash escapes special characters,
but C-like replacements are not supported. So no `\t` or `\n`, but you can have
`\"` or `\{`.

### $variable_reference

Look up the value of a variable by prefixing its name with `$`

### env
Environment variable lookup.
```
env <expr>
```

Example
```
HOME=env HOME
inspect $HOME
```



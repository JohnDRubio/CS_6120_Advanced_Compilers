import lark
import z3
import sys

# A language based on a Lark example from:
# https://github.com/lark-parser/lark/wiki/Examples
GRAMMAR = """
?start: sum
  | sum "?" sum ":" sum -> if

?sum: term
  | sum "+" term        -> add
  | sum "-" term        -> sub

?term: item
  | term "*"   item      -> mul
  | term "/"   item      -> div
  | term ">>"  item      -> shr
  | term "<<"  item      -> shl
  | term "<"   item      -> lt
  | term ">"   item      -> gt
  | term "=="  item      -> eq
  | term "!="  item      -> neq
  | term "&"   item      -> and
  | term "|"   item      -> or
  | term "^"   item      -> xor

?item: NUMBER           -> num
  | "-" item            -> neg
  | "~" item            -> not
  | CNAME               -> var
  | "(" start ")"

%import common.NUMBER
%import common.WS
%import common.CNAME
%ignore WS
""".strip()


def interp(tree, lookup):
    """Evaluate the arithmetic expression.

    Pass a tree as a Lark `Tree` object for the parsed expression. For
    `lookup`, provide a function for mapping variable names to values.
    """

    op = tree.data
    if op in ('add', 'sub', 'mul', 'div', 'shl', 'shr', 'lt', 'gt', 'eq', 'neq', 'and', 'or', 'xor'):  # Binary operators.
        lhs = interp(tree.children[0], lookup)
        rhs = interp(tree.children[1], lookup)
        if op == 'add':
            return lhs + rhs
        elif op == 'sub':
            return lhs - rhs
        elif op == 'mul':
            return lhs * rhs
        elif op == 'div':
            return lhs / rhs
        elif op == 'shl':
            return lhs << rhs
        elif op == 'shr':
            return lhs >> rhs
        elif op == 'lt':
            cond = lhs < rhs
            return z3.If(cond, 1, 0)
        elif op == 'gt':
            cond = lhs > rhs
            return z3.If(cond, 1, 0)
        elif op == 'eq':
            cond = lhs == rhs
            return z3.If(cond, 1, 0)
        elif op == 'neq':
            cond = lhs != rhs
            return z3.If(cond, 1, 0)
        elif op == 'and':
            return lhs & rhs
        elif op == 'or':
            return lhs | rhs
        elif op == 'xor':
            return lhs ^ rhs
    elif op == 'neg':  # Negation.
        sub = interp(tree.children[0], lookup)
        return -sub
    elif op == 'not':
        not_ = interp(tree.children[0], lookup)
        return ~not_
    elif op == 'num':  # Literal number.
        return int(tree.children[0])
    elif op == 'var':  # Variable lookup.
        return lookup(tree.children[0])
    elif op == 'if':  # Conditional.
        cond = interp(tree.children[0], lookup)
        true = interp(tree.children[1], lookup)
        false = interp(tree.children[2], lookup)
        return (cond != 0) * true + (cond == 0) * false

def model_values(model):
    """Get the values out of a Z3 model.
    """
    return {
        d.name(): model[d]
        for d in model.decls()
    }


def expand(var, plain_vars):
    """ Expands a single hole to switches among {v1, ..., vn, h}
    where v1,...,vn are all the bound variables.
    """
    name = var.decl().name()
    if name.startswith("hh"):
        expr = z3.BitVec(name + "#$num", 1)
        for v in plain_vars:
            cond = z3.BitVec(name + "#" + v, 1)
            expr = z3.If(z3.Distinct(cond, z3.BitVecVal(0, 1)),
                         expr, z3.BitVec(v, 1))
        return expr
    else:
        return var

def pretty(tree, subst={}, paren=False):
    """Pretty-print a tree, with optional substitutions applied.

    If `paren` is true, then loose-binding expressions are
    parenthesized. We simplify boolean expressions "on the fly."
    """

    # Add parentheses?
    if paren:
        def par(s):
            return '({})'.format(s)
    else:
        def par(s):
            return s

    op = tree.data
    if op in ('add', 'sub', 'mul', 'div', 'shl', 'shr'):
        lhs = pretty(tree.children[0], subst, True)
        rhs = pretty(tree.children[1], subst, True)
        c = {
            'add': '+',
            'sub': '-',
            'mul': '*',
            'div': '/',
            'shl': '<<',
            'shr': '>>',
        }[op]
        return par('{} {} {}'.format(lhs, c, rhs))
    elif op == 'neg':
        sub = pretty(tree.children[0], subst)
        return '-{}'.format(sub, True)
    elif op == 'num':
        return tree.children[0]
    elif op == 'var':
        name = tree.children[0]
        return str(subst.get(name, name))
    elif op == 'if':
        cond = pretty(tree.children[0], subst)
        true = pretty(tree.children[1], subst)
        false = pretty(tree.children[2], subst)
        return par('{} ? {} : {}'.format(cond, true, false))
    
def dig_holes(tree, plain_vars):
    """ Replaces each hole in tree with conditional switches
    between bound variables and constants"""
    if tree.decl().kind() == z3.Z3_OP_UNINTERPRETED:
        return expand(tree, plain_vars)
    else:
        substs = [(c, dig_holes(c, plain_vars)) for c in tree.children()]
        return z3.substitute(tree, substs)

    
def fill_holes(tree, model):
    """ Fills digged holes back in and returns new model_values """
    model_vals = model_values(model)

    # recursive constant folding from root of hole tree
    def fold_cond(t):
        decl = t.decl()
        if (decl.kind() == z3.Z3_OP_UNINTERPRETED
            and decl.name().endswith("$num")):
            return model_vals[decl.name()]
        elif decl.kind() == z3.Z3_OP_ITE:
            cond = t.children()[0]
            if cond.decl().kind() == z3.Z3_OP_DISTINCT:
                lhs = cond.children()[0]
                if (lhs.decl().kind() == z3.Z3_OP_UNINTERPRETED
                    and lhs.decl().name().startswith("hh")):
                    if model_vals[lhs.decl().name()].as_long() != 0:
                        return fold_cond(t.children()[1])
                    else:
                        return t.children()[2]
                else:
                    return t
            else:
                return t
        else:
            return t
        
    new_model_vals = { }

    for key in model_vals:
        if key.startswith("h") and not key.startswith("hh"):
            new_model_vals[key] = model_vals[key]

    def helper(t):
        if t.decl().kind() == z3.Z3_OP_ITE:
            print(t)
            cond = t.children()[0]
            false = t.children()[2]
            if (false.decl().kind() == z3.Z3_OP_UNINTERPRETED
                and cond.children()[0].decl().name().startswith("hh")):
                # t is now Root of the manufactured hole tree
                # Start constant folding
                hole = cond.children()[0]
                key = hole.decl().name()[:hole.decl().name().index("#")]
                new_val = fold_cond(t)
                new_model_vals[key] = new_val
            else:
                for child in t.children():
                    helper(child)
        else:
            for child in t.children():
                helper(child)

    helper(tree)
    return new_model_vals


def run(tree, env):
    """Ordinary expression evaluation.

    `env` is a mapping from variable names to values.
    """

    return interp(tree, lambda n: env[n])


def z3_expr(tree, vars=None):
    """Create a Z3 expression from a tree.

    Return the Z3 expression and a dict mapping variable names to all
    free variables occurring in the expression. All variables are
    represented as BitVecs of width 8. Optionally, `vars` can be an
    initial set of variables.
    """

    vars = dict(vars) if vars else {}

    # Lazily construct a mapping from names to variables.
    def get_var(name):
        if name in vars:
            return vars[name]
        else:
            v = z3.BitVec(name, 1)
            vars[name] = v
            return v

    return interp(tree, get_var), vars


def solve(phi):
    """Solve a Z3 expression, returning the model.
    """

    s = z3.Solver()
    s.add(phi)
    s.check()
    return s.model()


def model_values(model):
    """Get the values out of a Z3 model.
    """
    return {
        d.name(): model[d]
        for d in model.decls()
    }


def synthesize(tree1, tree2):
    """Given two programs, synthesize the values for holes that make
    them equal.

    `tree1` has no holes. In `tree2`, every variable beginning with the
    letter "h" is considered a hole.
    """

    expr1, vars1 = z3_expr(tree1)
    expr2, vars2 = z3_expr(tree2, vars1)

    # Filter out the variables starting with "h" to get the non-hole
    # variables.
    plain_vars = {k: v for k, v in vars1.items()
                  if not k.startswith('h')}
    
    expr2 = dig_holes(expr2, plain_vars)

    # Formulate the constraint for Z3.
    goal = z3.ForAll(
        list(plain_vars.values()),  # For every valuation of variables...
        expr1 == expr2,  # ...the two expressions produce equal results.
    )

    # Solve the constraint.
    model = solve(goal)
    model_vals = fill_holes(expr2, model)
    return model_vals


def ex2(source):
    src1, src2 = source.strip().split('\n')

    parser = lark.Lark(GRAMMAR)
    tree1 = parser.parse(src1)
    tree2 = parser.parse(src2)

    model = synthesize(tree1, tree2)
    print(pretty(tree1))
    print(pretty(tree2, model))
    print(model)


if __name__ == '__main__':
    # parser = lark.Lark(GRAMMAR)
    ex2(sys.stdin.read())
    # ex2('~x | ~y\n~h|~hh')
    # ex2('x * y\nx == h1 ? y : x * y')
    # ex2('x * x + y * y + z * z + 2 * x * y + 2 * y * z + 2 * x * z\n(hh1 + hh2 + hh3) * (hh3 + hh1 + hh2)')
    # ex2('~x | ~y | (h&hh)\n1')
    # ex2('~x | h\n1')
    # ex2('A|1\nh')
    # env = { 'x': 1, 'y': 1}
    # tree = parser.parse("x & y")
    # print(interp(tree, lambda v: env[v]))


# input:  ~A & ~B
# output: ~(hh | h)
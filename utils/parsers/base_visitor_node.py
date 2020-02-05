__author__ = 'bogdan'

import ast


class BaseVisitorNode(ast.NodeVisitor):
    """
    Only enforces that name of variables in expressions are in a list of <<accepted_context>> in
    case this is passed in. Can subclass for more specific enforcements.
    """
    def __init__(self, accepted_context):
        self.ok = True
        self.start_up = True
        self.error_message = ""
        self.accepted_context = accepted_context or []

    # Check that node is in defined set of variables
    def visit_Name(self, node):
        if self.accepted_context and node.id not in self.accepted_context:
            self.ok = False
            self.error_message = "Node %s is not accepted in expression. Only variables accepted are %s" % (
                node.id, self.accepted_context
            )
            return

    # No specific checks on operators.
    def visit_Call(self, node):
        pass

    def visit_Str(self, node):
        pass

    def visit_Index(self, node):
        pass

    def visit_Num(self, node):
		pass

    def visit_Subscript(self, node):
        pass

    def visit_LtE(self, node):
        pass

    def visit_Lt(self, node):
        pass

    def visit_GtE(self, node):
        pass

    def visit_Not(self, node):
        pass

    def visit_Gt(self, node):
        pass

    def visit_Compare(self, node):
        pass

    def visit_BoolOp(self, node):
        pass

    def visit_And(self, node):
        pass

    def visit_Or(self, node):
        pass

    def visit_Add(self, node):
        pass

    def visit_Load(self, node):
        pass

    def visit_Attribute(self, node):
        pass

    def visit_Sub(self, node):
        pass

    def visit_Mult(self, node):
        pass

    def visit_Div(self, node):
        pass

    def visit_Mod(self, node):
        pass

    def visit_Pow(self, node):
        pass

    def visit_UAdd(self, node):
        pass

    def visit_USub(self, node):
        pass

    # Catch all unary operations
    def visit_UnaryOp(self, node):
        self.visit(node.op)
        if not self.ok:
            if not self.error_message:
                self.error_message = "visit_UnaryOp: Failed to validate node %s" % node
            return
        self.visit(node.operand)

    # Catch all binary operations
    def visit_BinOp(self, node):
        self.visit(node.op)
        if not self.ok:
            if not self.error_message:
                self.error_message = "visit_BinOp: Failed to validate node %s" % node
            return
        self.visit(node.left)
        self.visit(node.right)

    # Every binary/unary op is prefixed by an expression
    def visit_Expr(self, node):
        for i in ast.iter_child_nodes(node):
            self.visit(i)

    def generic_visit(self, node):
        if self.start_up:
            # The first node in a parse tree is a module node, which we need to skip
            self.start_up = False
        else:
            self.error_message = "generic_visit: Failed to validate node %s" % node
            # This node is not caught by any of the above methods and therefore not allowed.
            self.ok = False
        super(BaseVisitorNode, self).generic_visit(node)


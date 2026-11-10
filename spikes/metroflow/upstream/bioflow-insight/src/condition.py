
from .outils import replace_call_parentheses, replace_single_dollar_signs, replace_single_ampersand, replace_single_bar_by_or, replace_equal_wave

import warnings
from parsimonious.nodes import NodeVisitor
from parsimonious.grammar import Grammar
from sympy.logic.boolalg import to_cnf, to_dnf
import time
import re

def apply_negation_and_uniform(leaf):
    def write(dico):
        for ele in dico:
            left, right = dico[ele]["left"], dico[ele]["right"]
            return f"{left} {ele} {right}"
    
    if(type(leaf)==str):
        return leaf
    if(len(leaf)>1):
        raise Exception("This shoudn't happen -> the condition tree is not well formed")
    for ele in leaf:
        if(ele == "neg"):
            to_negate = leaf[ele]
            if(type(to_negate)==str):
                return f"~({to_negate})"
            if(len(to_negate)>1):
                raise Exception("This shoudn't happen -> the condition tree is not well formed")
            for n in to_negate:
                if(n == "=="):
                    return apply_negation_and_uniform({"!=": {"left":to_negate[n]["left"], "right":to_negate[n]["right"]}})
                elif(n == "!="):
                    return apply_negation_and_uniform({"==": {"left":to_negate[n]["left"], "right":to_negate[n]["right"]}})
                elif(n == ">"):
                    return apply_negation_and_uniform({"<=": {"left":to_negate[n]["left"], "right":to_negate[n]["right"]}})
                elif(n == ">="):
                    return apply_negation_and_uniform({"<": {"left":to_negate[n]["left"], "right":to_negate[n]["right"]}})
                elif(n == "<"):
                    return apply_negation_and_uniform({">=": {"left":to_negate[n]["left"], "right":to_negate[n]["right"]}})
                elif(n == "<="):
                    return apply_negation_and_uniform({">": {"left":to_negate[n]["left"], "right":to_negate[n]["right"]}})
                elif(n == "or"):
                    values, new_values = to_negate[n], []
                    for v in values:
                        new_values.append(apply_negation_and_uniform({'neg': v}))
                    return apply_negation_and_uniform({"and": new_values})
                elif(n == "and"):
                    values, new_values = to_negate[n], []
                    for v in values:
                        new_values.append(apply_negation_and_uniform({'neg': v}))
                    return apply_negation_and_uniform({"or": new_values})
                elif(n == "neg"):
                    return apply_negation_and_uniform(to_negate[n])
            #return to_negate
        elif(ele in ["==", "!="]):
            left, right = leaf[ele]["left"], leaf[ele]["right"]
            switched = False
            if(left>right):
                switched = True
            if(switched):
                return write({ele: {"left":right, "right":left}})
            else:
                return write({ele: {"left":left, "right":right}})
        
        elif(ele in [">"]):
            left, right = leaf[ele]["left"], leaf[ele]["right"]
            switched = False
            if(left>right):
                switched = True
            if(switched):
                return write({"<": {"left":right, "right":left}})
            else:
                return write({ele: {"left":left, "right":right}})
        elif(ele in [">="]):
            left, right = leaf[ele]["left"], leaf[ele]["right"]
            switched = False
            if(left>right):
                switched = True
            if(switched):
                return write({"<=": {"left":right, "right":left}})
            else:
                return write({ele: {"left":left, "right":right}})
        
        elif(ele == "<"):
            left, right = leaf[ele]["left"], leaf[ele]["right"]
            switched = False
            if(left>right):
                switched = True
            if(switched):
                return write({">": {"left":right, "right":left}})
            else:
                return write({ele: {"left":left, "right":right}})
        elif(ele == "<="):
            left, right = leaf[ele]["left"], leaf[ele]["right"]
            switched = False
            if(left>right):
                switched = True
            if(switched):
                return write({">=": {"left":right, "right":left}})
            else:
                return write({ele: {"left":left, "right":right}})
        elif(ele == "or"):
            tab = []
            for e in leaf[ele]:
                tab.append(apply_negation_and_uniform(e))
            return "("+" | ".join(tab)+")"
        elif(ele == "and"):
            tab = []
            for e in leaf[ele]:
                tab.append(apply_negation_and_uniform(e))
            return "("+" & ".join(tab)+")"
        else:
            raise Exception("This shouldn't happen")

grammar = Grammar(
    r"""
    expression = sum
    #https://en.wikipedia.org/wiki/Parsing_expression_grammar#Indirect_left_recursion

    sum  = product (orOP product)*
    product = factor (andOP factor)*

    factor  = expPara / negExpression / primary
    expPara   = ws "(" ws expression ws ")" ws

    primary    = comparison / unit  
    negExpression = ws "!" ws factor ws

    comparison = unit ws compOP ws unit
    compOP    = ws ("==" / "!=" / "<=" / "<" / ">=" / ">" ) ws

    andOP     = ws "&&" ws
    orOP      = ws "$OR$" ws

    unit       = ~"[^\(\)$&=<>!]+"
    ws         = ~"\s*"
    """
)



test = [
"bool ", "!(bool)", "! bool", "!( a == 1)", "params.fasta ",
"(A $OR$ B) $OR$ C && (E)",
"params.readsTest",
"!(params.readsTest) && params.single",
"!(params.readsTest) && !(params.single)",
"params.clusterNuclIDlist == \"\"",
"!(params.clusterNuclIDlist == \"\")",
"params.clusterAAIDlist == \"\"",
"!(params.clusterAAIDlist == \"\")",
"!(!params.skipAdapterRemoval )",
"params.DataCheck $OR$ params.Analyze",
"!(!params.skipPrimerRemoval)",
"!(!params.skipMerging && !params.single) && !(params.single)",
"!(params.filter)",
"params.DataCheck",
"!(params.DataCheck) && params.Analyze",
"!(!params.skipPhylogeny $OR$ params.asvTClust)",
"!(params.asvTClust && !params.skipPhylogeny)",
"!(params.asvMED)",
"!(!params.skipPhylogeny $OR$ params.aminoTClust)",
"!(params.aminoTClust && !params.skipPhylogeny)",
"!(params.aminoMED)",
"!params.skipReport",
"params.ncASV",
"!(params.ncASV)",
"!(params.pcASV)",
"!params.skipAminoTyping",
"!(!params.skipAminoTyping)",
"!params.skipTaxonomy && params.Analyze",
"!params.skipFastQC",
"!params.skipAdapterRemoval ",
"!params.skipPrimerRemoval",
"!params.single",
"!params.skipFastQC && !params.skipPrimerRemoval",
"!(!params.single) && params.single",
"!params.skipMerging && !params.single",
"!(!params.skipMerging && !params.single) && params.single",
"params.filter",
"!params.skipReadProcessing $OR$ !params.skipMerging ",
"!(!params.skipReadProcessing $OR$ !params.skipMerging )",
"!params.skipPhylogeny $OR$ params.asvMED $OR$ params.asvTClust",
"!params.skipPhylogeny $OR$ params.asvTClust",
"params.asvTClust && !params.skipPhylogeny",
"params.asvMED",
"!params.skipPhylogeny $OR$ params.aminoMED $OR$ params.aminoTClust",
"!params.skipPhylogeny $OR$ params.aminoTClust",
"params.aminoTClust && !params.skipPhylogeny",
"params.aminoMED",
"params.pcASV",
"!params.skipEMBOSS",
"params.dbtype == \"NCBI\"",
"!params.skipTaxonomy",
"!(params.dbtype == \"NCBI\") && params.dbtype== \"RVDB\"",
"!(!params.skipTaxonomy)",
"!params.skipPhylogeny",
"!(!params.skipPhylogeny)",
"!params.skipAdapterRemoval $OR$ !params.skipReadProcessing $OR$ !params.skipMerging",
"!(!params.skipAdapterRemoval $OR$ !params.skipReadProcessing $OR$ !params.skipMerging)"
]


class ConditionVisitor(NodeVisitor):
    def generic_visit(self, node, visited_children):
        if len(visited_children) == 1:
            return visited_children[0]
        elif len(visited_children) == 0:
            return node.text
        return visited_children


    def visit_sum(self, node, visited_children):
        left, rest = visited_children
        if(not rest): #This means there is a single item
            return left
        
        rest_tab = []
        if(type(rest[1])==list):#This means there are multiple ORs
            for r in rest:
                rest_tab.append(r[1])
        else:
            rest_tab.append(rest[1])
                
        return {"or": [left]+rest_tab}
    #
    def visit_product(self, node, visited_children):
        left, rest = visited_children
        if(not rest): #This means there is a single item
            return left
        rest_tab = []
        if(type(rest[1])==list):#This means there are multiple ANDs
            for r in rest:
                rest_tab.append(r[1])
        else:
            rest_tab.append(rest[1])
                
        return {"and": [left]+rest_tab}
    
    #
    def visit_factor(self, node, visited_children):
        #print("factor", visited_children)
        return visited_children[0]
    #
    def visit_expPara(self, node, visited_children):
        _, _, _, val, _, _, _ = visited_children
        #print("expPara", visited_children)
        return val
    #
    def visit_primary(self, node, visited_children):
        #print("primary", visited_children)
        return visited_children[0]
        
    #
    def visit_negExpression(self, node, visited_children):
        #print("negExpression", visited_children)
        return {"neg": visited_children[3]}
    #
    def visit_comparison(self, node, visited_children):
        left, _, op, _, right = visited_children
        #print("comparison", visited_children)
        return {op: {"left":left, "right":right}}
    
    def visit_compOP(self, node, visited_children):
        _, op, _ = visited_children
        return op

    def visit_unit(self, node, visited_children):
        #print("unit", visited_children)
        return node.text.strip()



class Condition:
    def __init__(self, origin, condition, artificial = False):
        self.origin = origin
        self.value = str(condition)
        self.artificial = artificial
        #self.initialise()
        self.minimal_product_of_sums = None
        self.minimal_sum_of_products = None
        
        #self.get_minimal_sum_of_products()
        #self.get_minimal_product_of_sums()

    def get_workflow(self):
        return self.origin.get_workflow()

    def get_value(self):
        return self.value
    
    def get_artificial(self):
        return self.artificial

    def same_condition(self, condition):
        return self.value == condition.value
    
    def get_tree(self):
        text = self.get_value()
        #print(text)
        s = replace_equal_wave(
                replace_single_bar_by_or(
                    replace_single_ampersand(
                        replace_single_dollar_signs(
                            replace_call_parentheses(text)))))
        #print(s)
        #print()
        tree =  grammar.parse(s)
        return tree

    def get_simple_dico(self):
        try:
            tree = self.get_tree()
            #print(tree)
            transformer = ConditionVisitor()
            return transformer.visit(tree)
        except:
            w = f'The condition "{self.get_value()}" was not sucessfully analysed'
            warnings.warn(w)
            return self.get_value()
        
    def get_leafs(self, leafs):
        dico = self.get_simple_dico()
        def get_leafs_rec(dico):
            if(type(dico)==str):#This means it's a single value
                leafs[dico] = ""
            else:
                if(len(dico)>1):
                    raise Exception("This shoudn't happen -> the condition tree is not well formed")
                for ele in dico:
                    if(ele in ["or", "and"]):
                        for e in dico[ele]:
                            get_leafs_rec(e)
                    elif(ele == "neg"):
                        to_negate = dico[ele]
                        if(type(to_negate)==str):
                            leafs[to_negate] = ""
                            #return f"~({to_negate})"
                            return f"{to_negate}"
                        if(len(to_negate)>1):
                            raise Exception("This shoudn't happen -> the condition tree is not well formed")
                        for n in to_negate:
                            if(n == "=="):
                                get_leafs_rec({"!=": {"left":to_negate[n]["left"], "right":to_negate[n]["right"]}})
                            elif(n == "!="):
                                get_leafs_rec({"==": {"left":to_negate[n]["left"], "right":to_negate[n]["right"]}})
                            elif(n == ">"):
                                get_leafs_rec({"<=": {"left":to_negate[n]["left"], "right":to_negate[n]["right"]}})
                            elif(n == ">="):
                                get_leafs_rec({"<": {"left":to_negate[n]["left"], "right":to_negate[n]["right"]}})
                            elif(n == "<"):
                                get_leafs_rec({">=": {"left":to_negate[n]["left"], "right":to_negate[n]["right"]}})
                            elif(n == "<="):
                                get_leafs_rec({">": {"left":to_negate[n]["left"], "right":to_negate[n]["right"]}})
                            elif(n == "or"):
                                values, new_values = to_negate[n], []
                                for v in values:
                                    d ={'neg': v}
                                    get_leafs_rec(d)
                                    new_values.append(d)
                                return get_leafs_rec({"and": new_values})
                            elif(n == "and"):
                                values, new_values = to_negate[n], []
                                for v in values:
                                    d ={'neg': v}
                                    get_leafs_rec(d)
                                    new_values.append(d)
                                return get_leafs_rec({"or": new_values})
                            elif(n == "neg"):
                                return get_leafs_rec(to_negate[n])
                    
                        #get_leafs_rec(dico[ele])
                    else:
                        left, right = dico[ele]['left'], dico[ele]['right']

                        switched = False
                        if(left>right):
                            switched = True

                        if(ele in ["==", "!="]):
                            if(switched):
                                name = f"{right} {ele} {left}"
                            else:
                                name = f"{left} {ele} {right}"
      
                        elif(ele in [">"]):
                            if(switched):
                                name = f"{right} < {left}"
                            else:
                                name = f"{left} {ele} {right}"
                        elif(ele in [">="]):
                            if(switched):
                                name = f"{right} <= {left}"
                            else:
                                name = f"{left} {ele} {right}"
                        elif(ele in ["<"]):
                            if(switched):
                                name = f"{right} > {left}"
                            else:
                                name = f"{left} {ele} {right}"
                        elif(ele in ["<="]):
                            if(switched):
                                name = f"{right} >= {left}"
                            else:
                                name = f"{left} {ele} {right}"
                        else:
                            name = f"{left} {ele} {right}"

                        leafs[name] = ""
        get_leafs_rec(dico)
        return list(leafs.keys())
    
    def get_leafs_reel_objetcs(self):
        dico = self.get_simple_dico()
        def get_leafs_reel_objetcs_rec(dico, tab):
            if(type(dico)==str):#This means it's a single value
                tab.append(dico)
            else:
                if(len(dico)>1):
                    raise Exception("This shoudn't happen -> the condition tree is not well formed")
                for ele in dico:
                    if(ele in ["or", "and"]):
                        for e in dico[ele]:
                            tab = get_leafs_reel_objetcs_rec(e, tab)
                    elif(ele == "neg"):
                        tab = get_leafs_reel_objetcs_rec(dico[ele], tab)
                    else:
                        tab.append(dico)
            return tab
        return get_leafs_reel_objetcs_rec(dico, [])
    

    def get_bool_value(self, dico_of_values):
        dico = self.get_simple_dico()
        def get_bool_value_rec(dico):
            if(type(dico)==str):#This means it's a single value
                return dico_of_values[dico]
            else:
                if(len(dico)>1):
                    raise Exception("This shoudn't happen -> the condition tree is not well formed")
                for ele in dico:
                    if(ele == "and"):
                        val = 1
                        for e in dico[ele]:
                            val = val and get_bool_value_rec(e)
                        return val
                    elif(ele == "or"):
                        val = 0
                        for e in dico[ele]:
                            val = val or get_bool_value_rec(e)
                        return val
                    elif(ele == "neg"):
                        return not get_bool_value_rec(dico[ele])
                    else:
                        left, right = dico[ele]['left'], dico[ele]['right']
                        name = f"{left} {ele} {right}"
                        return dico_of_values[name]
        return bool(get_bool_value_rec(dico))
    


    
    def get_uniform_expression(self):
        return apply_negation_and_uniform(self.get_simple_dico())
    
    def get_minimal_sum_of_products(self):
        if(self.minimal_sum_of_products == None):
            leafs = self.get_leafs({})
            leafs.sort(reverse=True, key = len)
            dico_replace = {}
            expression = self.get_uniform_expression()

            for leaf in leafs:
                cle = f"a{str(time.time()).replace('.', '')}"
                dico_replace[cle] = leaf
                if(leaf not in expression):
                    raise Exception("The leaf was not found")
                expression = expression.replace(leaf, cle)       
    
            dnf = str(to_dnf(expression, simplify = True, force=True))
            products = dnf.split('|')
            for i in range(len(products)):
                products[i] = products[i].strip()
                products[i] = products[i].replace('(', '').replace(')', '')
                p = products[i].split('&')
                for y in range(len(p)):
                    value = p[y].strip()
                    if("~" == value[0]):
                        p[y] = "~"+dico_replace[value[1:]]
                    else:
                        p[y] = dico_replace[value]
                products[i] = p
                products[i].sort()
            self.minimal_sum_of_products = products
            return products
        else:
            return self.minimal_sum_of_products
    
    def get_minimal_product_of_sums(self):
        if(self.minimal_product_of_sums == None):
            leafs = self.get_leafs({})
            leafs.sort(reverse=True, key = len)
            dico_replace = {}
            expression = self.get_uniform_expression()
            for leaf in leafs:
                cle = f"a{str(time.time()).replace('.', '')}"
                dico_replace[cle] = leaf
                expression = expression.replace(leaf, cle) 

            

            #try:
            #    def georges_cnf(expression):
            #        from pyeda.inter import expr as pyeda_expr
            #        from pyeda.boolalg.expr import AndOp, OrOp, Complement, Variable
            #
            #
            #        def expr_to_str(e) -> str:
            #            if isinstance(e, AndOp):
            #                return '(' + ' & '.join(expr_to_str(x) for x in e.xs) + ')'
            #            elif isinstance(e, OrOp):
            #                return '(' + ' | '.join(expr_to_str(x) for x in e.xs) + ')'
            #            elif isinstance(e, Complement):
            #                return '~' + expr_to_str(e.inputs[0])
            #            elif isinstance(e, Variable):
            #                return e.name
            #            else:
            #                return str(e)
            #
            #            def to_cnf(expression):
            #                normalized = re.sub(r'~\((\w+)\)', r'~\1', expression)
            #                e = pyeda_expr(normalized)
            #                exp_str = expr_to_str(e.to_cnf())
            #                if(exp_str[0]=="(" and exp_str[1]==")"):
            #                    return exp_str[1:-1]
            #                return exp_str
            #        
            #        return to_cnf(expression)
            #
            #    cnf = georges_cnf(expression)
            #except:
            cnf = str(to_cnf(expression, simplify = True, force=True))
            products = cnf.split('&')
            for i in range(len(products)):
                products[i] = products[i].strip()
                products[i] = products[i].replace('(', '').replace(')', '')
                p = products[i].split('|')
                for y in range(len(p)):
                    value = p[y].strip()
                    if("~" == value[0]):
                        p[y] = "~"+dico_replace[value[1:]]
                    else:
                        if(value=="False"):
                            p[y] = value
                        else:
                            p[y] = dico_replace[value]
                products[i] = p
                products[i].sort()
            self.minimal_product_of_sums = products
            return products
        else:
            return self.minimal_product_of_sums
        


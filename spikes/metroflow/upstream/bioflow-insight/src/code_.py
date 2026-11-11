from .outils import remove_comments, get_code_until_parenthese_count, extract_curly, get_next_element_caracter, get_code_until_character, get_end_call
from .bioflowinsighterror import BioFlowInsightError
import re
from . import constant
import numpy as np

class Code:
    def __init__(self, code, origin, initialise):
        self.code = code
        self.code_wo_comments = code
        self.origin = origin
        if(initialise):
            self.initialise()
        #self.check_its_nextflow()


    
    def initialise(self):
        #I do this just to avoid out of file problems later on
        self.code = '\n'+self.code+'\n'
        self.code_wo_comments = self.code_wo_comments.replace("\\\\'", "$double_bar$'")
        self.code_wo_comments = self.code_wo_comments.replace('\\\\"', '$double_bar$"')
        self.code_wo_comments = self.code_wo_comments.replace("\\'", "$anti_slash_single$")
        self.code_wo_comments = self.code_wo_comments.replace('\\"', "$anti_slash_double$")
        self.code_wo_comments = self.code_wo_comments.replace('\"\'\"', "$double_single_double$")
        self.code_wo_comments = self.code_wo_comments.replace('\'"\'', "$single_double_single$")
        self.code_wo_comments = self.code_wo_comments.replace('[\'\"]', "$list_of_quotes1$")
        self.code_wo_comments = self.code_wo_comments.replace('[\"\']', "$list_of_quotes2$")
        self.code_wo_comments = self.code_wo_comments.replace('https://', "https_link_")
        self.code_wo_comments = remove_comments(self.code_wo_comments)
        self.code_wo_comments = re.sub(constant.DOUBLE_BACKSLAPSH_JUMP, ' ', self.code_wo_comments)
        self.code_wo_comments = re.sub(constant.BACKSLAPSH_JUMP, ' ', self.code_wo_comments)
        self.code_wo_comments = re.sub(r"(\n( |\t)*)+\.", '.', self.code_wo_comments)
        self.code_wo_comments = self.code_wo_comments.replace("||", "$OR$")
        self.code_wo_comments = self.turn_single_multiline_conditions_into_single(self.code_wo_comments)
        self.code_wo_comments = self.turn_single_condition_into_multiline(self.code_wo_comments)
        self.code_wo_comments = self.remove_things_inside_map(self.code_wo_comments )
        #self.code_wo_comments = self.rewrite_ternary_operation_to_normal_condition(self.code_wo_comments)
        self.code_wo_comments = self.rewrite_jump_dot(self.code_wo_comments)
        self.code_wo_comments = self.replace_single_slash_by_quote(self.code_wo_comments)
        self.code_wo_comments = self.replace_quote_dollar_curly(self.code_wo_comments)
        
        
    
    def replace_single_slash_by_quote(self, code):
        to_replace = []
        code = code.replace('\\/', "€splash_splash€")
        for match in re.finditer(r'\/([^\n\/]+(\$|\+))\/', code):
            old = match.group(0)
            new = match.group(1).replace('"', '\\"')
            new = f'"{new}"'
            to_replace.append((old, new))

    
        for r in to_replace:
            old, new = r
            code =code.replace(old, new, 1)
        code = code.replace("€splash_splash€", '\\/')
        return code
    
    def replace_quote_dollar_curly(self, code):
        to_replace = []
        for match in re.finditer(r'"\${([^}]+)}"', code):
            old = match.group(0)
            new = match.group(1).replace('"', '\\"')
            new = f'"${{{new}}}"'
            to_replace.append((old, new))

    
        for r in to_replace:
            old, new = r
            code =code.replace(old, new, 1)
        return code


    def check_its_nextflow(self):
        for illegal in constant.ILLEGAL_IMPORTS:
            for match in re.finditer(constant.START_IMPORT+illegal, self.get_code()):
                bit_of_code = match.group(0)
                raise BioFlowInsightError("ieic", self, bit_of_code, self.get_string_line(bit_of_code))

   
    #This methods turns a single line condition into a muli line conditions 
    def turn_single_condition_into_multiline(self, code):
        
        to_replace = []

        start = 0

        curly_count, parenthese_count = 0, 0
        quote_single, quote_double = False, False
        triple_single, triple_double = False, False

        timeout = 0
        while(start<len(code) and timeout<constant.WHILE_UPPER_BOUND):         
            checked_triple = False
            if(start+3<=len(code)):
                if(code[start:start+3]=="'''" and not quote_single and not quote_double and not triple_single and not triple_double):
                    triple_single = True
                    start+=3
                    checked_triple = True
                elif(code[start:start+3]=="'''" and not quote_single and not quote_double and triple_single and not triple_double):
                    triple_single = False
                    start+=3
                    checked_triple = True
        
                if(code[start:start+3]=='"""' and not quote_single and not quote_double and not triple_single and not triple_double):
                    triple_double = True
                    start+=3
                    checked_triple = True
                elif(code[start:start+3]=='"""' and not quote_single and not quote_double and not triple_single and triple_double):
                    triple_double = False
                    start+=3
                    checked_triple = True
            
            if(not checked_triple):
                if(code[start]=="{" and not quote_single and not quote_double and not triple_single and not triple_double):
                    curly_count+=1
                elif(code[start]=="}" and not quote_single and not quote_double and not triple_single and not triple_double):
                    curly_count-=1
                
                if(code[start]=="(" and not quote_single and not quote_double and not triple_single and not triple_double):
                    parenthese_count+=1
                elif(code[start]==")" and not quote_single and not quote_double and not triple_single and not triple_double):
                    parenthese_count-=1
        
                if(code[start]=="'" and not quote_single and not quote_double and not triple_single and not triple_double):
                    if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                        quote_single=True
                elif(code[start]=="'" and quote_single and not quote_double and not triple_single and not triple_double):
                    if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                        quote_single=False
        
                if(code[start]=='"' and not quote_single and not quote_double and not triple_single and not triple_double):
                    if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                        quote_double=True
                elif(code[start]=='"' and not quote_single and quote_double and not triple_single and not triple_double):
                    if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                        quote_double=False

       
                if(code[start:start+2]=="if" and [quote_single, quote_double, triple_single, triple_double]==[False, False, False, False]):

                    pattern = r"(if *\()(.+)\n"
        
                    temp_code = code[start:]
                    for match in re.finditer(pattern, temp_code):
                        if(match.span(0)[0]==0):
                            _, end_line = match.span(0)
                            found_if_bloc = True
                            all = match.group(0)
                            extarcted = match.group(2).strip()
                            
                            if(extarcted!="" and extarcted[-1] not in ["{", "}"]):
                                _, end_condition = match.span(1)
                                extracted_condition = get_code_until_parenthese_count(code=temp_code[end_condition:], val=-1)
                                condition = extracted_condition[:-1]
                                #body = extarcted.replace(extracted_condition.strip(), "", 1).strip()
                                body = re.sub(r"if *\( *"+re.escape(extracted_condition.strip()), "", all).strip()
                                if(body!="" and body[0]!="{"):
                                    new = f"if ({condition}) {{\n{body}\n}}\n"
                                    to_replace.append((all, new))
                                elif(body==""):
                                    char, pos = get_next_element_caracter(temp_code, end_line)
                                    #if(char!="{" and temp_code[pos:pos+3] not in ['"""', "'''"]):
                                    #    raise BioFlowInsightError(f"The condition '({extracted_condition}' was not extracted correctly. Make sure the condition follows the correct syntaxe.", type="Unable to extract condition")
                                    
                if(code[start:start+4]=="else" and [quote_single, quote_double, triple_single, triple_double]==[False, False, False, False]):
                    if(code[start-1] in [' ', '\n']):
                        pattern = r"(else *)(.+)\n"
                        temp_code = code[start:]
                        for match in re.finditer(pattern, temp_code):
                            if(match.span(0)[0]==0):
                                _, end_line = match.span(0)
                                all = match.group(0)
                                extarcted = match.group(2).strip()
                                if(extarcted!="" and extarcted[0] not in ["{"] and extarcted[-1] not in ["{", "}"] and not bool(re.fullmatch(r"if *\(.+", extarcted))):
                                    new = f"else {{\n{extarcted}\n}}\n"
                                    to_replace.append((all, new))
                                    
                                
                                    
                            
                start+=1
            timeout+=1
        if(timeout>=constant.WHILE_UPPER_BOUND):
            raise BioFlowInsightError("ube", self, "BioFlow-Insight was unable to turn a single line condition into a multi line condition. Make sure the workflow uses correct Nextflow syntaxe (https://www.nextflow.io/docs/latest/index.html).")

        
        for r in to_replace:
            old, new = r
            code = code.replace(old, new)
        return code
    
    #This function takes the code and adds '''...''' inside the map operator
    def remove_things_inside_map(self, code):
        index = 0
        searching = True
        timeout = 0
        while(searching and timeout<constant.WHILE_UPPER_BOUND):
            searching = False
            for word in ["map", "flatMap", "view", "ifEmpty"]:
                for end_char in ['{', '\(']:
                    pattern = fr"(\.|\|)\s*"+word+r"\s*"+end_char
                    for match in re.finditer(pattern, code):
                        connector = match.group(1)
                        start_map, end = match.span(0)
                        new = f"¤{id(self)}_{index}¤" 
                        if(end_char=="{"):
                            end_map = extract_curly(code, end)
                            old = code[end:end_map-1]
                            new_code = f"{connector}{word}_modified {{ {new} }}"
                        else:
                            new_code = f"{connector}{word}_modified ({new})"
                            old = get_code_until_parenthese_count(code[end:], -1)
                            end_map = end+len(old)
                            old = old.strip()[:-1]
                        
                        if(old[:-1].strip()!=''):
                            #self.add_map_element(old, new)

                            old_code = code[start_map:end_map]
                            self.add_map_element(old_code, new_code)
                            temp =code
                            code = code.replace(old_code, new_code)
                            if(old_code!=new_code and code==temp):
                                raise Exception("The code was no updated")

                            searching = True
                            index+=1
                            break
            #For reduce
            for match in re.finditer(r"(\.|\|)\s*reduce\s+\{", code):
                connector = match.group(1)
                start_map, end = match.span(0)
                end_map = extract_curly(code, end)
                old = code[end:end_map-1]        
                new = f"¤{id(self)}_{index}¤" 
                #self.add_map_element(old, new)
                old_code = code[start_map:end_map]
                new_code = f"{connector}reduce_modified {{ {new} }}"
                self.add_map_element(old_code, new_code)
                temp =code
                code = code.replace(old_code, new_code)
                if(old_code!=new_code and code==temp):
                    raise Exception("The code was no updated")
                searching = True
                index+=1
                break
            timeout+=1
        if(timeout>=constant.WHILE_UPPER_BOUND):
            raise BioFlowInsightError("ube", self, "BioFlow-Insight was unable to extract the inside of a 'map' operator. Make sure the workflow uses correct Nextflow syntaxe (https://www.nextflow.io/docs/latest/index.html).")

        return code

    def add_to_ternary_operation_dico(self, old, new):
        self.origin.add_to_ternary_operation_dico(old, new)

    def add_map_element(self, old, new):
        self.origin.add_map_element(old, new)

    ##This methods rewrite ternary operation into "normal" conditions
    ##variable = (condition) ? Expression2 : Expression3;
    #def rewrite_ternary_operation_to_normal_condition(self, code):
    #    pattern = r"(def)? *(\w+) *\= *([^?\n]+) *\? *([^:\n]+) *\: *([^\n]+)\n"
    #    to_replace = []
    #    checked = []
    #    for match in re.finditer(pattern, code):
    #        def_variable = ""
    #        if(match.group(1)!=None):
    #            def_variable = match.group(1)
    #        
    #            
    #        variable = match.group(2)
    #        condition = match.group(3).strip()
    #        exp1, exp2 = match.group(4).strip(), match.group(5).strip()
    #        old = match.group(0)
    #        #print(exp1)
    #        #print(exp2)
    #        #print()
    #        new = f"if ({condition}) {{\n{def_variable} {variable} = {exp1}\n}}\n" 
    #        new += f"if (!({condition})) {{\n{def_variable} {variable} = {exp2}\n}}\n\n" 
    #        print(new)
    #        #else {{\n{variable} = {exp2}\n}}\n"
    #        #Here we check that it's worked correctly -> that we have done a good parsing
    #        if(get_parenthese_count(condition)==0 and get_parenthese_count(exp1)==0 and get_parenthese_count(exp2)==0 and get_curly_count(condition)==0 and get_curly_count(exp1)==0 and get_curly_count(exp2)==0):
    #            to_replace.append((old, new))
    #        else:
    #            checked.append(match.group(0))
    #    for r in to_replace:
    #        old, new = r
    #        self.add_to_ternary_operation_dico(old, new)
    #        tmp = code
    #        code = code.replace(old, new, 1)
    #        if(old!=new and tmp==code):
    #            raise Exception("This shouldn't happen -> the code wasn't replaced")
    #    #Check if there is still a ternary operation in this case we cannot analyse it
    #    #Cause it is a complexe/multiple ternanry operation
    #    for match in re.finditer(pattern, code):
    #        #print(match.group(0))
    #        if(match.group(0) not in checked):
    #            raise BioFlowInsightError(f"Detected a multi ternary operation (a ternary operation in a ternary operation) in the file '{self.origin.get_file_address()}'. BioFlow-Insight does not support this, try defining it in a different way.", type="Multi ternary operation")
    #    return code
    
    #This methods rewrite ternary operation into "normal" conditions
    #variable = (condition) ? Expression2 : Expression3;
    def rewrite_ternary_operation_to_normal_condition(self, code):
        #Turning multi line ternry operations into single ternary operations
        code = re.sub(r"(\n( |\t)*)+:", ' :', code)
        pattern = r"\n *(def)? *(\w+) *\= *(([^?\n]+) *\? *([^:\n]+) *\: *([^\n]+))\n"
        to_replace = []
        already_searched = []

        searching = True

        while(searching):
            searching = False
            for match in re.finditer(pattern, code):
                def_variable = ""
                if(match.group(1)!=None):
                    def_variable = match.group(1)
                
                    
                variable = match.group(2)
                exp = match.group(3).strip()
                old = match.group(0)
                old = old[1:]
                dico_conditions = {}

                def rewrite_ternary(exp, dico_conditions):
                    exp = exp.strip()
                    if(exp==""):
                        return "null"
                    if(exp[0]=="(" and exp[-1]==")"):
                        exp = exp[1:-1].strip()
                    
                    try:
                        expression, end_condition = get_code_until_character(exp, "?")
                    except:
                        return exp

                    condition = exp[:end_condition].strip()
                    try:
                        _, end_potential_condition = get_code_until_character(expression, "?")
                        
                    except:
                        end_potential_condition = np.inf
                    exp2, end_exp1 = get_code_until_character(expression, ":")
                    dico_true, dico_false = {}, {}
                    #if(expression[:end_exp1]==""):
                    #    raise BioFlowInsightError(f"The 'True' case in the ternary condition '{exp}' has no value.", type="Incomplete ternary operation")
                    #if(exp2==""):
                    #    raise BioFlowInsightError(f"The 'False' case in the ternary condition '{exp}' has no value.", type="Incomplete ternary operation")
                    
                    #We do this so that a ternary in a list is not rewritten
                    if(condition.strip()[0]!='['):
                        #Case there is a condition right after the first condition
                        if(end_potential_condition<end_exp1):
                            expression_false, end_exp1 = get_code_until_character(expression, ":", left_to_right=False)
                            dico_conditions[condition] = {"True": rewrite_ternary(expression[:end_exp1], dico_true), "False": rewrite_ternary(expression_false, dico_false)}
                        else:        
                            dico_conditions[condition] = {"True": rewrite_ternary(expression[:end_exp1], dico_true), "False": rewrite_ternary(exp2, dico_false)}
                    return dico_conditions

                if(old not in already_searched):
                    
                    try:
                        rewrite_ternary(exp, dico_conditions)
                    except:
                        already_searched.append(old)
                        searching = True
                        break

                
                    def rewrite_dico_2_condition(var, dico_condition, num = 0):
                        code = ''
                        if(type(dico_condition)==str):
                            return f"{var} = {dico_condition}\n"
                        for condition in dico_condition:
                            code = f"if({condition}) {{\n\t{rewrite_dico_2_condition(var, dico_condition[condition]['True'], num = num+1)}}} else {{\n\t{rewrite_dico_2_condition(var, dico_condition[condition]['False'], num = num+1)}}}\n"
                        return code
                
                    new = rewrite_dico_2_condition(f"{def_variable} {variable}", dico_conditions)+'\n'

                    to_replace.append((old, new))
                    tmp = code
                    code = code.replace(old, new, 1)
                    if(old!=new and tmp==code):
                        raise Exception("This shouldn't happen -> the code wasn't replaced")
                    searching = True
                    break
        
        for r in to_replace:
            old, new = r
            #Check that we have corretly extracted a ternary operator (this is a way to filter false positives)
            if(new.strip()!=''):
                self.add_to_ternary_operation_dico(old, new)


        #Check if there is still a ternary operation in this case we cannot analyse it
        for match in re.finditer(pattern, code):
            old = match.group(0)
            old = old[1:]
            if(old not in already_searched):
                raise BioFlowInsightError('toito', self, self.get_string_line(old))
        return code
    
    def turn_single_multiline_conditions_into_single(self, code):
        start = 0

        curly_count, parenthese_count = 0, 0
        quote_single, quote_double = False, False
        triple_single, triple_double = False, False

        to_replace = []
        timeout = 0
        while(start<len(code) and timeout < constant.WHILE_UPPER_BOUND):    
            checked_triple = False
            if(start+3<=len(code)):
                if(code[start:start+3]=="'''" and not quote_single and not quote_double and not triple_single and not triple_double):
                    triple_single = True
                    start+=3
                    checked_triple = True
                elif(code[start:start+3]=="'''" and not quote_single and not quote_double and triple_single and not triple_double):
                    triple_single = False
                    start+=3
                    checked_triple = True
        
                if(code[start:start+3]=='"""' and not quote_single and not quote_double and not triple_single and not triple_double):
                    triple_double = True
                    start+=3
                    checked_triple = True
                elif(code[start:start+3]=='"""' and not quote_single and not quote_double and not triple_single and triple_double):
                    triple_double = False
                    start+=3
                    checked_triple = True
            
            if(not checked_triple):
                if(code[start]=="{" and not quote_single and not quote_double and not triple_single and not triple_double):
                    curly_count+=1
                elif(code[start]=="}" and not quote_single and not quote_double and not triple_single and not triple_double):
                    curly_count-=1
                
                if(code[start]=="(" and not quote_single and not quote_double and not triple_single and not triple_double):
                    parenthese_count+=1
                elif(code[start]==")" and not quote_single and not quote_double and not triple_single and not triple_double):
                    parenthese_count-=1
        
                if(code[start]=="'" and not quote_single and not quote_double and not triple_single and not triple_double):
                    if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                        quote_single=True
                elif(code[start]=="'" and quote_single and not quote_double and not triple_single and not triple_double):
                    if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                        quote_single=False
        
                if(code[start]=='"' and not quote_single and not quote_double and not triple_single and not triple_double):
                    if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                        quote_double=True
                elif(code[start]=='"' and not quote_single and quote_double and not triple_single and not triple_double):
                    if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                        quote_double=False

      
                if(code[start:start+2]=="if" and [quote_single, quote_double, triple_single, triple_double]==[False, False, False, False]):
                    found_if_bloc = False
                    for match in re.finditer(r"if *\(", code[start:]):
                        if(match.span(0)[0]==0):
                            start_if, end_if = match.span(0)
                            try:
                                txt = get_end_call(code[start:], start_if, end_if)
                                if('\n' in txt):
                                    to_replace.append(txt)
                                end = start+len(txt)
                                found_if_bloc = True
                            except:
                                import warnings
                                w = f'Unable to transform a condition'
                                warnings.warn(w)
                            break
                        else:
                            break 
                    if(found_if_bloc):
                        #Case we need to jump to the end of the if
                        start = end-1
        
                start+=1
            timeout+=1
        if(timeout>=constant.WHILE_UPPER_BOUND):
            raise BioFlowInsightError("ube", self, "BioFlow-Insight was unable to extract the conditions. Make sure the workflow uses correct Nextflow syntaxe (https://www.nextflow.io/docs/latest/index.html).")
        to_replace = list(set(to_replace))
        for r in to_replace:
            temp = code
            code = code.replace(r, r.replace('\n', " "))
            if(code==temp):
                raise Exception("Not updated!")
        return code

    def rewrite_jump_dot(self, code):
        pattern = r"(\n *)+\."
        code = re.sub(pattern, '.', code)
        return code

    def get_line(self, bit_of_code):
        code = remove_comments(self.code)
        index = code.find(bit_of_code)
        if(index!=-1):
            line = code[:index].count('\n')
            if(line==0):
                return 1
            return line
        return -1
    
    def get_string_line(self, bit_of_code):
        line = self.get_line(bit_of_code)
        line_error = ''
        if(line!=-1):
            line_error = f", possibly at line {line}"
        return line_error


    #Returns the code witout comments
    def get_code(self, get_OG =False):
        if(get_OG):
            return self.code.strip()
        else:
            return self.code_wo_comments.strip()
    
    def get_file_address(self, short = False):
        return self.origin.get_file_address(short = short)
    
    def get_nextflow_file(self):
        return self.origin.get_nextflow_file()
    
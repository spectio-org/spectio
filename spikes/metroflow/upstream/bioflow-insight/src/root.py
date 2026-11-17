
from .nextflow_building_blocks import Nextflow_Building_Blocks
from .bioflowinsighterror import BioFlowInsightError

from .outils import *
from . import constant

import re

class Root(Nextflow_Building_Blocks):
    def __init__(self, code, origin, modules_defined,
                 subworkflow_inputs = []):#These channels are the inputs of the subworkflow
        Nextflow_Building_Blocks.__init__(self, code, initialise_code=False)
        self.origin = origin
        self.executors = []
        self.blocks = []
        self.modules_defined = modules_defined
        self.elements_being_called = []
        self.channels = subworkflow_inputs
        self.defined_processes = []
    

    #############
    #  GENERAL
    #############
    def get_type(self):
        return "Root"
    
    def get_cycle_status(self):
        return self.origin.get_cycle_status()
    
    def get_position_in_main(self, executor):
        return self.origin.get_position_in_main(executor)
    
    def get_subworkflow_calls_to_get_here(self, executor):
        if(self.origin.get_type()=="Main"):
            return []
        elif(self.origin.get_type() in ["Block", "Root"]):
            return self.origin.get_subworkflow_calls_to_get_here(executor)
        #Case subworkflow
        else:
            call = self.origin.get_call()
            return [call]+call.get_subworkflow_calls_to_get_here(executor)

    def get_blocks(self):
        return self.blocks
    
    def get_conditions_2_ignore(self):
        return self.origin.get_conditions_2_ignore()

    def add_element_to_elements_being_called(self, element):
        self.elements_being_called.append(element)

    #Does this on the same level
    def get_blocks_with_same_conditions(self, searching_block):
        tab = []
        for block in self.blocks:
            if(block != searching_block):
                if(block.same_condition(searching_block)):
                    tab.append(block)
        return tab
    
    #This method returns returns all the conditions above the block
    #Basically everything which needs to be true for the block to exist
    def get_all_conditions(self, conditions):
        if(self.get_origin().get_type()=="Subworkflow"):
            self.get_origin().get_call().get_all_conditions(conditions = conditions)
        return conditions


    #############
    # CHANNELS
    #############

    def get_channels_same_level(self):
        return self.channels

    def get_channels_from_name_same_level(self, name):
        tab = []
        for c in self.channels:
            if(c.get_name()==name):
                tab.append(c)
        return tab
    
    def get_channels_above_level(self):
        return []
    
    def get_channels_above_level_rec(self, dico ):
        for c in self.channels:
            dico[c] = ''

    def get_channels_from_name_above_level(self, name):
        tab = []
        for c in self.get_channels_above_level():
            if(c.get_name()==name):
                tab.append(c)
        return tab
        
    def get_channels_inside_level_rec(self, dico ):
        for c in self.channels:
            dico[c] = ''
        for b in self.blocks:
            b.get_channels_inside_level_rec(dico)
    
    def get_channels_inside_level(self):
        dico = {}
        for b in self.blocks:
            b.get_channels_inside_level_rec(dico)
        return list(dico.keys())
    
    def get_channels_from_name_inside_level(self, name):
        tab = []
        for c in self.get_channels_inside_level():
            if(c.get_name()==name):
                tab.append(c)
        return tab

    def get_channels_from_other_blocks_on_same_level(self):
        return []
    
    def get_channels_from_name_other_blocks_on_same_level(self, name):
        tab = []
        for c in self.get_channels_from_other_blocks_on_same_level():
            if(c.get_name()==name):
                tab.append(c)
        return tab
    
    def get_channels_from_name_all_channels(self, name):
        channels = self.get_channels_same_level()+self.get_channels_inside_level()
        tab = []
        for c in channels:
            if(c.get_name()==name):
                tab.append(c)
        return tab




    #def check_in_channels(self, channel):
    #    for c in self.get_channels():
    #        if(c.equal(channel)):
    #            return True
    #    for b in self.blocks:
    #        if(b.check_in_channels(channel)):
    #            return True
    #    return False
    

    def add_channel(self, channel):        
        self.channels.append(channel)

        
    #def get_channel_from_name(self, name):
    #    for c in self.get_channels():
    #        if(name == c.get_name()):
    #            return c
    #    return None
    #    #tab = []
    #    #for b in self.blocks:
    #    #    channels = b.get_channel_from_name(name)
    #    #    tab+=channels
    #    #raise Exception(f"{name} is not in the list of channels")
        
    

    #############
    # EXECUTORS
    #############
    def get_executors_same_level(self):
        return self.executors
    
    def get_above_executors(self):
        return []

    def get_above_executors_rec(self, dico ):
        for e in self.executors:
            dico[e] = ''
    
    #This method returns all the executors inside a block
    def get_inside_executors_rec(self, dico):
        for e in self.executors:
            dico[e] = ''
        for b in self.blocks:
            b.get_inside_executors_rec(dico)
    
    def get_inside_executors(self):
        dico = {}
        for b in self.blocks:
            b.get_inside_executors_rec(dico)
        return list(dico.keys())
    
    #def get_all_executors_from_workflow(self):
    #    return self.get_executors_same_level()+self.get_inside_executors()

    #def get_calls(self):
    #    tab = []
    #    for c in self.get_executors():
    #        if(c.get_type()=="Call"):
    #            tab.append(c)
    #        elif(c.get_type()=="Operation"):
    #            for o in c.get_origins():
    #                if(o.get_type()=="Call"):
    #                    tab.append(o)
    #    return tab
    
    #############
    #   CALLS
    #############

    def get_calls_same_level(self):
        tab = []
        for c in self.executors:
            if(c.get_type()=="Call"):
                tab.append(c)
            elif(c.get_type()=="Operation"):
                for o in c.get_origins():
                    if(o.get_type()=="Call"):
                        tab.append(o)
        return tab
    
    def get_calls_above_level(self):
        return []
    
    #This method returns all the calls inside a block
    def get_calls_inside_level(self):
        tab = []
        executors = self.get_inside_executors()
        for e in executors:
            if(e.get_type()=="Call"):
                tab.append(e)
            elif(e.get_type()=="Operation"):
                for o in e.get_origins():
                    if(o.get_type()=="Call"):
                        tab.append(o)
        return tab
    

    def get_calls_from_other_blocks_on_same_level(self):
        return []

    def get_all_calls_in_subworkflow(self, calls ):
        all_calls = self.get_calls_same_level()+self.get_calls_inside_level()
        for call in all_calls:
            for c in call.get_all_calls():
                calls[c] = ''
                #if(c.get_first_element_called().get_type()=="Subworkflow"):
                #    c.get_first_element_called().root.get_all_calls(calls = calls)
    

    def get_all_executors_in_subworkflow(self, calls ):
        all_executors = self.get_executors_same_level()+self.get_inside_executors()
        for e in all_executors:
            calls[e] = ''

    def get_all_calls_from_root(self):
        dico = {}
        self.get_all_calls_in_subworkflow(calls=dico)
        return list(dico.keys())
    

    #############
    # PROCESSES
    #############
    def extract_defined_processes(self):
        code = self.get_code()
        #For each block -> remove its code
        for b in self.blocks:
            code = code.replace(b.get_code(), "", 1)

        for match in re.finditer(r"\<src\.process\.Process object at \w+\>", code):
            for process in self.modules_defined:
                if(str(process)==match.group(0)):
                    process.set_origin(self)
                    self.defined_processes.append(process)
    
    
    def initialise(self):
        #Define the blocks
        code = self.get_code()
        conditions = extract_conditions(code)

        #For each condition -> create a block
        for c in conditions:
            from .block import Block
            body = code[conditions[c][0]:conditions[c][1]].strip()
            c = c.split("$$__$$")[0]
            import copy
            block = Block(code=body, origin=self, condition=c, modules_defined=self.modules_defined, existing_channels = copy.copy(self.channels))
            self.blocks.append(block)


        self.extract_executors()
        
        #Case DSL1 -> need to extract the processes which have been defined but rplaced in the code
        self.extract_defined_processes()

       
        #This is to get the order of execution
        code = self.get_code()
        position_2_thing_2_analyse = {}
        for block in self.blocks:
            block_code = block.get_code().strip()
            if(block_code!=""):
                found = False
                while(not found):
                    if(len(block_code)<=0):
                        break
                    pos = code.find(block_code)
                    if(pos!=-1):
                        position_2_thing_2_analyse[pos] = block
                        code = code.replace(block_code, "a"*len(block_code), 1)
                        found = True
                    else:
                        block_code = block_code[:-1]
                if(not found):
                    raise Exception("This shouldn't happen")
        
        for process in self.defined_processes:
            found = False
            pos = code.find(str(process))
            if(pos!=-1):
                position_2_thing_2_analyse[pos] = process
                found = True
            if(not found):
                raise Exception("This shouldn't happen")            
        
        for e in self.executors:
            e_code = e.get_code()
            found = False
            while(not found):
                if(len(e_code)<=0):
                    break
                pos = code.find(e_code)
                if(pos!=-1):
                    position_2_thing_2_analyse[pos] = e
                    code = code.replace(e_code, "a"*len(e_code), 1)
                    found = True
                else:
                    e_code = e_code[:-1]
            if(not found):
                raise Exception("This shouldn't happen") 
       
        sorted_position_2_thing_2_analyse = dict(sorted(position_2_thing_2_analyse.items()))

        for key in sorted_position_2_thing_2_analyse:
            element = sorted_position_2_thing_2_analyse[key]
            element.initialise()

    #Example with 132
    def check_that_a_channel_is_not_defined_used_and_redefined_used_in_another_block(self):
        channels_defined_at_root_level = []
        for exe in self.get_executors_same_level():
            if(exe.get_type()=="Operation"):
                channels_defined_at_root_level+=exe.get_gives()
        channels_defined_used_in_calls_at_root = []
        for call in self.get_calls_same_level():
            params = call.get_parameters()
            for p in params:
                if(p.get_type()=="Operation"):
                    channels_defined_used_in_calls_at_root += p.origins

        if(channels_defined_used_in_calls_at_root!=[]):
            for block in self.blocks:
                temp_return = block.check_that_a_channel_is_not_defined_used_and_redefined_used_in_another_block()
                if(temp_return!=None):
                    return temp_return
                channels_defined_inside_block = []
                for exe in block.get_executors_same_level()+block.get_inside_executors():
                    if(exe.get_type()=="Operation"):
                        channels_defined_inside_block+=exe.get_gives()
                calls_inside_block = block.get_calls_same_level()+block.get_calls_inside_level()
                for call in calls_inside_block:
                    params = call.get_parameters()
                    for p in params:
                        if(p.get_type()=="Operation"):
                            for o in p.origins:
                                if(o in channels_defined_inside_block):
                                    for ch in channels_defined_used_in_calls_at_root:
                                        if(o.get_code()==ch.get_code()):
                                            return o.get_code()
        return None


    def get_process_from_name(self, name):
        for m in self.modules_defined:
            if(m.get_type()=="Process" and m.get_alias()==name):
                return m
            
    def get_subworkflow_from_name(self, name):
        for m in self.modules_defined:
            if(m.get_type()=="Subworkflow" and m.get_alias()==name):
                return m
            
    def get_function_from_name(self, name):
        for m in self.modules_defined:
            if(m.get_type()=="Function" and m.get_alias()==name):
                return m

    def extract_executors(self):
        from .operation import Operation
        from .call import Call


        code = self.get_code()
        code_og = self.get_code()

        #For each block -> remove its code
        for b in self.blocks:
            code = code.replace(b.get_code(), "", 1)

        things_to_remove = []
        #things_to_remove+= self.processes+self.includes+self.subworkflows+self.functions
        #if(self.main!=None):
        #    things_to_remove+=[self.main]
        #
        #for to_remove in things_to_remove:
        #    code = code.replace(to_remove.get_code(get_OG = True), "", 1)

        #We add this to simplify the search of the executors 
        code = "start\n"+code+"\nend"

        #This function takes an executor (already found and expandes it to the pipe operators)
        def expand_to_pipe_operators(text, executor):
            #If the executor ends with the pipe operator -> we remove it so that it can be detected by the pattern
            if(executor[-1]=="|"):
                executor = executor[:-1].strip()
            start = text.find(executor)+len(executor)
            for match in re.finditer(constant.END_PIPE_OPERATOR, text[start:]):
                begining, end = match.span(0)
                if(begining==0):
                    return expand_pipe_operator(text, executor+match.group(0))
                break
            return executor

        

        #---------------------------------------------------------------
        #STEP1 - Extract equal operations eg. 
        # *Case "channel = something"
        # *Case "(channel1, channel2) = something"
        #--------------------------------------------------------------- 
        pattern_equal = constant.LIST_EQUALS
    
        searching = True
        timeout = 0
        while(searching and timeout<constant.WHILE_UPPER_BOUND):
            timeout+=1
            searching= False
            text = code
            text = text.replace("/\\033\[[0-9;]*m/", "")
            for e in self.executors:
                text = text.replace(e.get_code(), "", 1)
            
            for pattern in pattern_equal:
                for match in re.finditer(pattern, text):
                    
                    start, end = match.span(2)
                    try:
                        ope = extract_end_operation(text, start, end)
                    except:
                        raise BioFlowInsightError("uteeo", self, code_og)
                        
                    ope = expand_to_pipe_operators(text, ope)
                 
                    #If the thing which is extracted is not in the conditon of an if 
                    if(not checks_in_condition_if(text, ope) and not checks_in_string(text, ope)):
                        operation = Operation(ope, self)
                        self.executors.append(operation)
                        searching= True
                        break
        if(timeout>=constant.WHILE_UPPER_BOUND):
            raise Exception("Time out")

        #I switched step 2 and step 3 -> cause there were cases where there was operations in the paramters of a call -> they were extracted and removed
        #-----------------------------------
        #STEP3 - Extract the remaining calls
        #-----------------------------------
        #These are the processes and subworkflows we need to check are called
        if(self.get_DSL()=="DSL2"):
            to_call = []
            for m in self.modules_defined:
                to_call.append(m.get_alias())
            pattern_call = constant.BEGINNING_CALL
            searching = True
            while(searching):
                searching= False
                text = " "+code
                for e in self.executors:
                    text = text.replace(e.get_code(), "", 1)
        
                for match in re.finditer(pattern_call, text):
                    if(match.group(1) in to_call):
                        
                        start, end = match.span(0)
                        #We do this cause the first caracter is a " "
                        start+=1
                        txt_call = get_end_call(text, start, end)
                        txt_call = expand_to_pipe_operators(text, txt_call)
                        #If the thing which is extracted is not in the conditon of an if 
                        if(not checks_in_condition_if(text, txt_call) and not checks_in_string(text, txt_call)):
                            if(txt_call.find("|")!=-1 and txt_call[txt_call.find("|")-1]!="|" and txt_call[txt_call.find("|")+1]!="|"):
                                first_thing_called = txt_call.split('|')[-1].strip()
                                if(first_thing_called in to_call):
                                    call = Call(code =txt_call, origin =self)
                                    self.executors.append(call)
                                else:
                                    added = True
                                    if(first_thing_called in constant.LIST_OPERATORS):
                                        added = True
                                    if(not added):
                                        for operator in constant.LIST_OPERATORS:
                                            for match in re.finditer(operator+constant.END_OPERATOR, txt_call.split('|')[-1].strip()):
                                                start, end = match.span(0)
                                                if(start==0):
                                                    added = True
                                    if(not added):
                                        raise BioFlowInsightError("nieie", self, first_thing_called, txt_call, self.get_string_line(txt_call))
                                    else:
                                        ope = Operation(code =txt_call, origin =self)
                                        self.executors.append(ope)
                            else:
                                #We need to see if we can expand the call to a operation perhaps process().set{ch}
                                expanded = expand_call_to_operation(text, txt_call)
                                if(txt_call==expanded):
                                    call = Call(code =txt_call, origin =self)
                                    self.executors.append(call)
                                else:
                                    ope = Operation(code =expanded, origin =self)
                                    self.executors.append(ope)
                            
                            searching = True
                            break


        #-------------------------------------------------
        #STEP2 - Extract the terms which use the operators
        #-------------------------------------------------
        pattern_dot = constant.DOT_OPERATOR
        searching = True
        searched = []


        while(searching):
            searching= False
            text = code
            for e in self.executors:
                text = text.replace(e.get_code(), "", 1)
            
            for match in re.finditer(pattern_dot, text):
                start, end = match.span(1)
                if(match.group(1) not in constant.ERROR_WORDS):
                    if(match.group(1) in constant.LIST_OPERATORS):

                        
                        #Use if there is an operator called right before opening the curlies/parenthse
                        #curly_left, curly_right = get_curly_count(text[:start]), get_curly_count(text[end:])
                        parenthese_left, parenthese_right = get_parenthese_count(text[:start]), get_parenthese_count(text[end:])
                        
                        #if(curly_left==0 and curly_right==0 and parenthese_left==0 and parenthese_right==0 and (start, end) not in searched):
                        #if(parenthese_left==0 and parenthese_right==0 and (start, end, temp) not in searched):
                        if(parenthese_left==0 and parenthese_right==0):
                            
                        
                            try:
                                pot = extract_executor_from_middle(text, start, end) 
                            except:
                                try:
                                    temp = text[start-10:end+10]
                                except:
                                    temp = text[start:end]
                                raise BioFlowInsightError("ftec", self, self.get_string_line(temp))                            
                            pot = expand_to_pipe_operators(text, pot)
                            #IF the exact potential hasn't already been searched, then we don't do it
                            if((start, end, pot) not in searched):
                                searched.append((start, end, pot))
                                #If the thing which is extracted is not in the conditon of an if 
                                if(not checks_in_condition_if(text, pot) and not checks_in_string(text, pot)):
                                    if(self.get_DSL()=="DSL2"):
                                        to_call = []
                                        for m in self.modules_defined:
                                            to_call.append(m.get_alias())
                                        if(pot.find("|")!=-1):
                                            if(not checks_in_condition_if(pot, '|') and not checks_in_string(pot, '|') and not check_if_pipe_operator_is_mixed_with_regular_operators(pot)):
                                                first_thing_called = pot.split('|')[-1].strip()
                                                if(first_thing_called in to_call):
                                                    call = Call(code =pot, origin =self)
                                                    self.executors.append(call)
                                                elif(first_thing_called in constant.LIST_OPERATORS):
                                                    ope = Operation(code =pot, origin =self)
                                                    self.executors.append(ope)
                                                else:
                                                    raise BioFlowInsightError('nieie', self, first_thing_called, pot, self.get_string_line(pot))                                            
                                            else:
                                                from .executor import Executor
                                                executor = Executor(pot, self)
                                                self.executors.append(executor.return_type())
                                        
                                        else:
                                            from .executor import Executor
                                            executor = Executor(pot, self)
                                            self.executors.append(executor.return_type())
                                    else:
                                        ope = Operation(pot, self)
                                        self.executors.append(ope)
                                    searching = True
                                    break
                        

        #---------------------------------------------------------------
        #STEP4 - Extract the Executors which only use the pipe operators (which start with a channel)
        #---------------------------------------------------------------
        to_call = []
        for m in self.modules_defined:
            to_call.append(m.get_alias())

        searching = True
        while(searching):
            searching= False
            text = code
            for e in self.executors:
                text = text.replace(e.get_code(get_OG=True), "", 1)
            pattern = constant.BEGINNING_PIPE_OPERATOR
            
            for match in re.finditer(pattern, text):
                try:
                    txt_call = expand_pipe_operator(text, match.group(0))
                except:
                    raise BioFlowInsightError("utepo", self, match.group(0), self.get_string_line(match.group(0)))
                full_executor =  txt_call
                
                #start, end = match.span(0)
                ## Check to see if a parameter is given such as in the example 'splitLetters | flatten | convertToUpper | view { it.trim() }'
                #params, full_executor = check_if_parameter_is_given_pipe(text, start, end)
                #if(params!=''):
                #    tab_to_call = txt_call.split('|')
                #    start = f"{tab_to_call[0]}({params})"
                #    txt_call = start + '|' + '|'.join(tab_to_call[1:])

                
                #If the thing which is extracted is not in the conditon of an if 
                if(not checks_in_condition_if(text, full_executor) and not checks_in_string(text, full_executor)):
                    tab_to_call = txt_call.split('|')
                    if(tab_to_call[0].strip() in to_call):
                        start = f"{tab_to_call[0]}()"
                        txt_call = start + '|' + '|'.join(tab_to_call[1:])
                    first_thing_called = txt_call.split('|')[-1].strip()

                    if(first_thing_called in to_call):
                        call = Call(code =txt_call, origin =self, OG_code= full_executor)
                        self.executors.append(call)
                        searching = True
                        break
                    elif(first_thing_called in constant.LIST_OPERATORS):
                        ope = Operation(code =txt_call, origin =self, OG_code= full_executor)
                        self.executors.append(ope)
                        searching = True
                        break
                    else:
                        added = False
                        #This is in the case "channel | map {dfvfdvd}"
                        for ope in constant.LIST_OPERATORS:
                            if(first_thing_called[:len(ope)]==ope and not added):
                                ope = Operation(code =txt_call, origin =self, OG_code= full_executor)
                                self.executors.append(ope)
                                added = True
                                searching = True
                        if(added):
                            break
                        elif(not added):
                            raise BioFlowInsightError("nieie", self, first_thing_called, txt_call, self.get_string_line(txt_call))
        
        #---------------------------------------------------------------------
        #STEP5 - We remove the things which were falsy extracted as executors
        #---------------------------------------------------------------------
        to_remove = []
        starting_by_to_remove = ["System.out"]
        for e in self.executors:
            for r in starting_by_to_remove:
                if(e.get_code()[:len(r)]==r):
                    to_remove.append(e)
        for e in to_remove:
            self.executors.remove(e)

    def get_structure(self, dico):
        #This only for DSL1 workflows
        if(self.origin.get_DSL()=="DSL1"):
            for process in self.defined_processes:
                process.get_structure(dico)
            for channel in self.channels:
                for sink in channel.get_sink():
                    #If the sink an operation then the edge has already been added in the get_structure method for the operation
                    if(sink.get_type()=="Process"):
                        channel.get_structure(dico, sink)

        
        for block in self.blocks:
            block.get_structure(dico)
        for e in self.executors:
            if(e.get_type()=="Operation"):
                e.get_structure(dico)
            elif(e.get_type()=="Call"):
                e.get_structure(dico)
            else:
                raise Exception(f"Executor of type '{e.get_type()}' was extracted in a DSL2 workflow! I don't know what this is! The code is '{e.get_code()}'")

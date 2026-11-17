import re

from . import constant

from .code_ import Code
from .outils import update_parameters, get_curly_count, get_parenthese_count, checks_in_string
from .nextflow_building_blocks import Nextflow_Building_Blocks
from .bioflowinsighterror import BioFlowInsightError




class Executor(Nextflow_Building_Blocks):
    def __init__(self, code, origin):
        self.origin = origin
        self.code = Code(code = code, origin = self, initialise=False)

        
        

    #---------------------------------
    #AUXILIARY METHODS FOR ALL CLASSES
    #---------------------------------
    def get_cycle_status(self):
        return self.origin.get_cycle_status()

    def get_list_name_processes(self):
        return self.origin.get_list_name_processes()
    
    def get_all_conditions(self):
        block = self.get_block()
        if(block.get_type()=="Root"):
            conditions = {}
            return block.get_all_conditions(conditions)
        #Type block
        else:
            conditions = {}
            return block.get_all_conditions(conditions)

        if(self.origin.get_type()=="Root"):
            return []
        elif(self.origin.get_type()=="Block"):
            conditions = {}
            return self.origin.get_all_conditions(conditions)
        else:
            return self.origin.get_all_conditions()
    
    
    def get_subworkflow_from_name(self, name):
        return self.origin.get_subworkflow_from_name(name)
    
    def get_function_from_name(self, name):
        return self.origin.get_function_from_name(name) 
    
    def get_list_name_subworkflows(self):
        return self.origin.get_list_name_subworkflows()
   
    def get_list_name_includes(self):
        return self.origin.get_list_name_includes()
      
    def add_channel(self, channel):
        self.origin.add_channel(channel)  
     

    def get_channels_same_level(self):
        return self.origin.get_channels_same_level() 
    
    def get_channels_above_level(self):
        return self.origin.get_channels_above_level() 
    
    def get_channels_inside_level(self):
        return self.origin.get_channels_inside_level() 
    
    def get_channels_from_other_blocks_on_same_level(self):
        return self.origin.get_channels_from_other_blocks_on_same_level()
    
    def get_channels_from_name_same_level(self, name):
        return self.origin.get_channels_from_name_same_level(name)

    def get_channels_from_name_inside_level(self, name):
        return self.origin.get_channels_from_name_inside_level(name)
    
    def get_channels_from_name_above_level(self, name):
        return self.origin.get_channels_from_name_above_level(name)
    
    def get_channels_from_name_all_channels(self, name):
        return self.origin.get_channels_from_name_all_channels(name)
    
    def get_position_in_main(self, executor):
        return self.origin.get_position_in_main(executor)
    
    def get_subworkflow_calls_to_get_here(self, executor):
        return self.origin.get_subworkflow_calls_to_get_here(executor)

    
    
    def get_channels_from_name_other_blocks_on_same_level(self, name):
        return self.origin.get_channels_from_name_other_blocks_on_same_level(name)
    
    
    def get_block(self):
        if(self.origin.get_type() in ['Root', "Block"]):
            return self.origin
        else:
            return self.origin.get_block()
    
    
    #def get_channels(self):
    #    return self.origin.get_channels() 

    def check_in_channels(self, channel):
        return self.origin.check_in_channels(channel)    
    
    def get_channel_from_name(self, channel):
        return self.origin.get_channel_from_name(channel)
    
    def get_executors(self):
        return self.origin.get_executors()


    def add_element_to_elements_being_called(self, element):
        self.origin.add_element_to_elements_being_called(element)


    
    def clean_pipe_operator(self, pipe):
    
        #Replace the || temporairly cause we don't wanna analyse them
        to_replace_double_pipe = []
        found_or = True
        while(found_or):
            found_or = False
            if(pipe.find("||")!=-1):
                new_tag = f'{str(self)}_OR_{len(to_replace_double_pipe)}'
                pipe = pipe.replace('||', new_tag, 1)
                to_replace_double_pipe.append(new_tag)
                found_or = True
            

        head = ''
        if(pipe.find("=")!=-1):
            if(bool(re.fullmatch(constant.WORD, pipe.split("=")[0].strip()))):
                head = f'{pipe.split("=")[0].strip()} = '
                pipe = "=".join(pipe.split("=")[1:])
        
        
        to_call = []
        for m in self.get_modules_defined():
            to_call.append(m.get_alias())
        searching = True
        to_replace = []
        OG_pipe = pipe.strip()
        first_loop = True
        while(searching):
            if(pipe.find('|')==-1):
                searching=False
            else:
                #If the pipe operator is in a string we replace by something temporary
                if(checks_in_string(pipe, '|')):#It selects the first one
                    new_tag = f'{str(self)}_{len(to_replace)}'
                    pipe = pipe.replace('|', new_tag, 1)
                    to_replace.append(new_tag)
                #If it is not in a string
                else:
                    
                    pipe_split = pipe.split('|')
                    first_executor = pipe_split[0].strip()
                    #Here we check if we need to add () if the first thing is called
                    if(first_loop and re.fullmatch(constant.WORD, first_executor)):
                        for module in self.get_modules_defined():
                            if(module.get_alias()==first_executor):
                                if(module.get_type()=='Process'):
                                    if(module.get_nb_inputs()==0):
                                        first_executor = first_executor+'()'
                                if(module.get_type()=='Subworkflow'):
                                    if(module.get_nb_takes()==0):
                                        first_executor = first_executor+'()'
                                
                    first_pipe = pipe_split[1]
                    left_side = first_executor
                    right_side = "|".join(pipe_split[1:])
                    thing = first_pipe.strip()
                    #This to test if it's actually a pipe operator and not just an ||
                    if(get_parenthese_count(left_side)==0 and get_parenthese_count(right_side)==0 and get_curly_count(left_side)==0 and get_curly_count(right_side)==0):
                        #thing needs to follow the pattern for the pipe operator
                        
                        if(thing in to_call):
                            if(len(pipe_split[2:])==0):
                                pipe = f"{thing}({first_executor})"
                                searching = False
                            else:
                                pipe = f"{thing}({first_executor})" + '|'+ '|'.join(pipe_split[2:])
                        elif(thing in constant.LIST_OPERATORS):
                            if(len(pipe_split[2:])==0):
                                pipe = f"{first_executor}.{thing}()"
                                searching = False
                            else:
                                pipe = f"{first_executor}.{thing}()" + '|'+'|'.join(pipe_split[2:])
                        else:
                            added = False
                            for operator in constant.LIST_OPERATORS:
                                if(thing[:len(operator)]==operator and not added):
                                    added = True
                                    #This is in the case "channel | map {dfvfdvd}"
                                    pipe = f"{first_executor}.{thing}" 
                                    #If there is still operations remaining we add them
                                    if('|'.join(pipe_split[2:])!=""):
                                        pipe = pipe + '|'+'|'.join(pipe_split[2:])
                            if not added:
                                raise BioFlowInsightError("ueipo", self, thing, self.get_string_line(thing))

                    else:
                        pipe = str(self).join([left_side, right_side])
            first_loop = False

        for tag in to_replace:
            pipe = pipe.replace(tag, '|')
        for tag in to_replace_double_pipe:
            pipe = pipe.replace(tag, '||')
        new_pipe = (pipe).replace(str(self), '|', 1).strip()
        return (head+pipe).replace(str(self), '|', 1), {new_pipe: OG_pipe}
    
    
    #This method analyses if the executor if an operation or a call, and returns
    #the correct object corresponding to it
    #TO do this we search if an operator is in parenthes or not
    #If it's an operation the executor should be outside the parentheses
    #If it's a call the operator should be inside the parentheses
    def return_type(self):
        list_things_to_call = self.get_modules_defined()
        is_operation =False
        code = self.get_code()
        code = code.replace(' ', '')
        #Case for sure operation (it doesn't start with a call)
        if(code.split('(')[0] not in list_things_to_call):
            is_operation = True

        if(not is_operation):        
            curly_count, parenthese_count = 0, 0
            quote_single, quote_double = False, False
            end=0
            while(end<len(code)): 
                curly_count, parenthese_count, quote_single, quote_double = update_parameters(code, end, curly_count, parenthese_count, quote_single, quote_double) 
                
                if(curly_count==0 and parenthese_count==0 and quote_single==False and quote_double==False):
                    if(code[end]=="."):
                        #I've updated this -> in anycase if it's an emit it's still an operation
                        is_operation=True
                        #for operator in constant.LIST_OPERATORS:
                        #    try:
                        #        if(code[end:end+len(operator)+1]=="."+operator):
                        #            is_operation=True
                        #    except:
                        #        None
                end+=1
        
        #If it is type operation -> the funtion returns the operation 
        if(is_operation):
            from .operation import Operation
            return Operation(self.get_code(), self.origin)
        #Else it is an operation
        else:
            from .call import Call
            return Call(self.get_code(), self.origin)
    

    #Method which returns the calls which call the element called 
    def get_calls_by_name(self, name):
        tab = []
        if(self.origin.get_type() in ['Root', 'Block']):
            for call in self.origin.get_calls_same_level():
                #call.initialise()
                for c in call.get_all_calls():
                    if(c.first_element_called.get_alias()==name):
                        tab.append(c)
                #if(c.first_element_called.get_alias()==name):
                #    tab.append(c)
            #Here it is important that BioFlow-Insight is not a Nextflow verificator
            #Here i'm checking the call inside the block
            if(len(tab)==0):
                for call in self.origin.get_calls_inside_level():
                    #call.initialise()
                    for c in call.get_all_calls():
                        if(c.first_element_called.get_alias()==name):
                            tab.append(c)
            if(len(tab)==0):
                for call in self.origin.get_calls_above_level():
                    #call.initialise()
                    for c in call.get_all_calls():
                        if(c.first_element_called.get_alias()==name):
                            tab.append(c)
            #Looking inside the other blocks
            if(len(tab)==0):
                for call in self.origin.get_calls_from_other_blocks_on_same_level():
                    #call.initialise()
                    for c in call.get_all_calls():
                        if(c.first_element_called.get_alias()==name):
                            tab.append(c)
            #If there is no calls found then we search in all root
            if(len(tab)==0):
                for call in self.origin.get_all_calls_from_root():
                    #call.initialise()
                    for c in call.get_all_calls():
                        if(c.first_element_called.get_alias()==name):
                            tab.append(c)
            return tab

        else:
            return self.origin.get_calls_by_name(name)




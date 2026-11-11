import re
import json


from .code_ import Code
from .outils import get_next_param, replace_group1
from .executor import Executor
from .bioflowinsighterror import BioFlowInsightError
from . import constant


class Call(Executor):
    def __init__(self, code, origin, OG_code = ''):
        self.code = Code(code = code, origin = self, initialise=False)
        self.origin = origin
        self.called = []
        self.first_element_called = None
        self.parameters = []#These are in the order
        self.OG_code = OG_code
        self.initialised = False
        self.emits = []
        self.analyse_first_element_called(self.get_code(clean_pipe = True))
        #It's important this is last
        #self.condition = Condition(self)
        if(self.get_DSL()=="DSL1"):
            raise BioFlowInsightError("cidw", self, code)

     
    #This method returns all the calls inside a call eg p1(p2(), p3()) returns [p1(p2(), p3()), p2(), p3()]
    def get_all_calls(self):
        tab = []
        tab.append(self)
        for param in self.parameters:
            if(param.get_type()=="Operation"):
                for o in param.get_origins():
                    if(o.get_type()=="Call"):
                        tab+=o.get_all_calls()
        return tab


    def add_to_emits(self, emitted):
        self.emits.append(emitted)

    def get_later_emits(self):
        return self.emits
        
    def __str__(self):
     return f"Call_{id(self)}"
    
    def get_parameters(self):
        return self.parameters

    def get_code(self, clean_pipe = False, get_OG=False, remove_emit_and_take = False, replace_calls = False):
        if(get_OG):
            if(self.OG_code==''):
                return self.code.get_code()
            return self.OG_code
        if(clean_pipe):
            code, _ = self.clean_pipe_operator(self.code.get_code())
            return code
        else:
            return self.code.get_code()
    
    
    def get_type(self):
        return "Call"

    
    def get_first_element_called(self):
        return self.first_element_called
    
    def get_elements_called(self, tab_input = [], first_call = True):
        tab = tab_input.copy()
        #if(first_call):
        #    if(tab!=[]):
        #        raise Exception("herer")
        #    tab = []
      
        tab += [self.first_element_called]
        for para in self.parameters:
            if(para.get_type()=="Call"):
                tab = para.get_elements_called(tab_input = tab.copy(), first_call = False)
            elif(para.get_type()=="Operation"):
                tab = para.get_elements_called(tab = tab.copy())

        temp = list(set(tab))
        #del tab
        return temp

        
    def get_code_split_space(self, code):
        to_add_spaces = ['(', ')', '}', '{']
        for character in to_add_spaces:
            temp = code
            if(character in code):
                code = code.replace(f'{character}', f' {character} ')
                if(temp==code):
                    raise Exception("This shouldn't happen")
        return code.split()

    def get_artificial_status(self):
        return False

    def analye_parameters(self, param):

        #Step 1 -> get parameters
        tab_params, start, next_param = [], 0, None
        temp_param = param
        timeout = 0
        while(start!=-1 and timeout<constant.WHILE_UPPER_BOUND):
            temp_param = temp_param[start:]
            next_param, start = get_next_param(temp_param)
            tab_params.append(next_param.strip())
            timeout+=1
        if(timeout>=constant.WHILE_UPPER_BOUND):
            reason = f"BioFlow-Insight was unable to extract the parameters for the call '{self.get_code(get_OG=True)}'. Make sure the workflow uses correct Nextflow syntaxe (https://www.nextflow.io/docs/latest/index.html)"
            raise BioFlowInsightError("ube", None, reason)

        #Step 2 -> analyse paramters
        for param in tab_params:
            if(re.fullmatch(constant.CHANNEL_EQUALS, param)):
                raise BioFlowInsightError('aic', self, param, self.get_code())
            analysed_param = False
            if param!='':
                #Case it's a channel
                if(re.fullmatch(constant.WORD, param) and not analysed_param):
                    channels = self.origin.get_channels_from_name_same_level(param)
                    if(channels==[]):
                        channels = self.origin.get_channels_from_name_all_channels(param)
                    if(channels==[]):
                        from .channel import Channel
                        channel = Channel(name=param, origin=self.origin)
                        self.origin.add_channel(channel)
                        channels = [channel]
                    from .operation import Operation
                    ope = Operation(f"{param}", self)
                    ope.set_as_artificial()
                    for channel in channels:
                        channel.add_sink(self)
                        ope.add_element_origins(channel)
                        ope.set_as_artificial()
                    self.parameters.append(ope)
                    analysed_param = True
                    
                    
                else:
                    from .executor import Executor
                    executor = Executor(param, self)
                    executor = executor.return_type()
                    if(executor.get_type()=="Call"):
                        temp_call = executor
                        temp_call.initialise()
                        self.parameters.append(temp_call)
                    elif(executor.get_type()=="Operation"):
                        ope = executor
                        ope.initialise_from_call()
                        #Case is an Emitted -> there's only one value given and it's an emitted
                        if(ope.check_if_operation_is_an_full_emitted() and len(ope.get_gives())==1 and ope.get_gives()[0].get_type()=="Emitted"):
                            emit = ope.get_gives()[0]
                            self.parameters.append(emit)
                        else:
                            self.parameters.append(ope)
                    else: 
                        raise Exception(f"I don't know what type '{param}' is!")
    
    
    def get_nb_outputs(self):
        first=self.get_first_element_called()
        if(first.get_type()=="Process"):
            return first.get_nb_outputs()
        elif(first.get_type()=="Subworkflow"):
            return first.get_nb_emit()
        raise Exception("This soudn't happen!")
    

    def get_structure(self, dico):
        if(self.get_first_element_called().get_type()=="Process"):
            process = self.get_first_element_called()
            #Add process here
            process.get_structure(dico)
            
            def add_parameter(p):
                #Case parameter is a channel
                if(p.get_type()=="Channel"):
                    channel = p
                    channel.get_structure(dico, B=process)

                #Case parameter is a Emitted 
                elif(p.get_type()=="Emitted"):
                    emitted = p
                    emitted.get_structure(dico, B=process)

                #Case parameter is a Operation 
                elif(p.get_type()=="Operation"):
                    operation = p
                    if(operation.show_in_structure):
                        operation.get_structure(dico)
                        dico["edges"].append({'A':str(operation), 'B':str(process), "label":""})
                
                #Case parameter is a Call
                elif(p.get_type()=="Call"):
                    call = p
                    call.get_structure(dico)
                    #Case the first call is a process
                    if(call.get_first_element_called().get_type()=="Process"):
                        for output in call.get_first_element_called().get_outputs():
                            dico["edges"].append({'A':str(call.get_first_element_called()), 'B':str(process), "label":""})
                    #Case the first call is a subworkflow
                    elif(call.get_first_element_called().get_type()=="Subworkflow"):
                        for emit in call.get_first_element_called().get_emit():
                            dico["edges"].append({'A':str(emit), 'B':str(process), "label":""})
        
                else:
                    raise Exception(f"Type '{p.get_type()}' was given as a parameter -> I don't know how to handle this!")
            
            #If the name number of parameters are given
            if(len(self.parameters)==process.get_nb_inputs()):
                for p in self.parameters:
                    add_parameter(p)
            #If they are not -> we check that the right number isn't implied
            else:
                num_inputs = 0
                for p in self.parameters:
                    if(p.get_type()=="Call"):
                        num_inputs+= p.get_nb_outputs()
                    elif(p.get_type()=="Emitted"):
                        emitted = p
                        
                        if(emitted.get_emitted_by().get_type()=="Subworkflow"):
                            if(emitted.get_emits()==None):
                                num_inputs+= emitted.get_emitted_by().get_nb_emit()
                            else:
                                num_inputs+=1
                        elif(emitted.get_emitted_by().get_type()=="Process"):
                            if(emitted.get_emits()==None):
                                num_inputs+= emitted.get_emitted_by().get_nb_outputs()
                            else:
                                num_inputs+=1
                        elif(emitted.get_emitted_by().get_type()=="Call"):
                            call = emitted.get_emitted_by()
                            first_thing_called = call.get_first_element_called()
                            if(first_thing_called.get_type()=="Process"):
                                if(emitted.get_emits()==None):
                                    num_inputs+= first_thing_called.get_nb_emit()
                                else:
                                    num_inputs+=1

                            elif(first_thing_called.get_type()=="Subworkflow"):
                                if(emitted.get_emits()==None):
                                    num_inputs+= first_thing_called.get_nb_outputs()
                                else:
                                    num_inputs+=1
                            else:
                                raise Exception("This shoudn't happen")

                        else:
                            print(emitted.get_emitted_by().get_type())
                            raise Exception("This shoudn't happen")
                    else:
                        #Cause in case channel, operation or emit, it is only one channel given
                        num_inputs+=1
                if(num_inputs==process.get_nb_inputs()):
                    for p in self.parameters:
                        add_parameter(p)
                    
                else:
                    name = f"{process.get_type().lower()} '{process.get_alias()}'"
                    line = self.get_string_line(self.get_code(get_OG=True))
                    raise BioFlowInsightError("ntsnop", self, name, line)

        elif(self.get_first_element_called().get_type()=="Subworkflow"):
            sub = self.get_first_element_called()
            
            temp_dico = {}
            temp_dico['nodes'] = []
            temp_dico['edges'] = []
            temp_dico['subworkflows'] = {}
            sub.get_structure(temp_dico)
            #dico['subworkflows'][f"{sub.get_alias()}_$$_{str(id(sub))}"] = temp_dico
            id_sub = self.get_workflow().get_element_2_index(sub.get_alias())
            #dico['subworkflows'][f"{sub.get_alias()}_$$_{str(id(sub))}"] = temp_dico
            dico['subworkflows'][f"{sub.get_alias()}_$$_{id_sub}"] = temp_dico

            param_index = 0

            def add_parameter(p, param_index):
                sub_input = sub.get_takes()[param_index]
                #Case parameter is a channel
                if(p.get_type()=="Channel"):
                    channel = p
                    channel.get_structure(dico, B=sub_input)

                #Case parameter is a Emitted 
                elif(p.get_type()=="Emitted"):
                    emitted = p
                    emitted.get_structure(dico, B=sub_input)

                #Case parameter is a Operation 
                elif(p.get_type()=="Operation"):
                    operation = p
                    if(operation.show_in_structure):
                        operation.get_structure(dico)
                        dico["edges"].append({'A':str(operation), 'B':str(sub_input), "label":""})
                
                #Case parameter is a Call
                elif(p.get_type()=="Call"):
                    call = p
                    call.get_structure(dico)
                    #Case the first call is a process
                    if(call.get_first_element_called().get_type()=="Process"):
                        for output in call.get_first_element_called().get_outputs():
                            dico["edges"].append({'A':str(call.get_first_element_called()), 'B':str(sub_input), "label":""})
                    #Case the first call is a subworkflow
                    elif(call.get_first_element_called().get_type()=="Subworkflow"):
                        for emit in call.get_first_element_called().get_emit():
                            dico["edges"].append({'A':str(emit), 'B':str(sub_input), "label":""})
        
                else:
                    raise Exception(f"Type '{p.get_type()}' was given as a parameter -> I don't know how to handle this!")
                param_index+=1
                return param_index 
            
            #If the name number of parameters are given
            if(len(self.parameters)==sub.get_nb_takes()):
                for p in self.parameters:
                    param_index  = add_parameter(p, param_index)
            ##If they are not -> we check that the right number isn't implied
            else:
                name = f"{sub.get_type().lower()} '{sub.get_alias()}'"
                line = self.get_string_line(self.get_code(get_OG=True))
                raise BioFlowInsightError("ntsnop", self, name, line)

            #    num_inputs = 0
            #    for p in self.parameters:
            #        if(p.get_type()=="Call"):
            #            num_inputs+= p.get_nb_outputs()
            #        else:
            #            #Cause in case channel, operation or emit, it is only one channel given
            #            num_inputs+=1
            #    if(num_inputs==sub.get_nb_takes()):
            #        for p in self.parameters:
            #            param_index  = add_parameter(p, param_index )
            #        
            #    else:
            #        raise BioFlowInsightError(f"Not the same number of parameters given as input for the subworklfow '{sub.get_alias()}' in the call{self.get_string_line(self.get_code())}.", num = 2, origin=self)


        elif(self.get_first_element_called().get_type()=="Function"):
            None

        else:
            raise Exception(f"This shoudn't happen! is type")



    def analyse_call(self, call):
        tab_call = self.get_code_split_space(call)
        if(re.fullmatch(constant.WORD, tab_call[0]) and tab_call[1]=='('):
            #params1 = ' '.join(tab_call[2:-1])
            start = re.findall(tab_call[0]+constant.END_CALL, call)[0]
            params = call.replace(start, "")
            if(params[-1]==')'):
                params = params[:-1]
            else:
                raise Exception("This shouldn't happens")
            
            self.analye_parameters(params)
        #    process = self.get_process_from_name(tab_call[0])
        #    subworkflow = self.get_subworkflow_from_name(tab_call[0])
        #    fun = self.get_function_from_name(tab_call[0])
        #    if(process!=None and subworkflow==None and fun==None):
        #        #If the elements need to duplicated -> then we need to duplicate it
        #        if(self.get_duplicate_status()):
        #            process = process.copy()
        #        process.initialise()
        #        self.first_element_called = process
        #        self.origin.add_element_to_elements_being_called(process)
        #        #temp.incremente_number_times_called()
        #    if(process==None and subworkflow!=None and fun==None):
        #        if(self.get_duplicate_status()):
        #            subworkflow = subworkflow.copy()
        #        subworkflow.initialise()
        #        self.first_element_called = subworkflow
        #        self.origin.add_element_to_elements_being_called(subworkflow)
        #    if(process==None and subworkflow==None and fun!=None):
        #        self.first_element_called = fun
        #    if(process==None and subworkflow==None and fun==None):
        #        raise Exception("No first call found!!")
        #    self.called.append(self.first_element_called)
        #else:
        #    raise BioFlowInsightError(f"Failed to extract the call{self.get_string_line(self.get_code())}. Try rewriting it in a simplified version.", num = 15, origin=self)
    
    def analyse_first_element_called(self, call):
        tab_call = self.get_code_split_space(call)
        if(re.fullmatch(constant.WORD, tab_call[0]) and tab_call[1]=='('):
            #params1 = ' '.join(tab_call[2:-1])
            start = re.findall(tab_call[0]+constant.END_CALL, call)[0]
            params = call.replace(start, "")
            if(params[-1]==')'):
                params = params[:-1]
            else:
                raise Exception("This shouldn't happens")
            
            #self.analye_parameters(params)
            process = self.get_process_from_name(tab_call[0])
            subworkflow = self.get_subworkflow_from_name(tab_call[0])
            fun = self.get_function_from_name(tab_call[0])
            if(process!=None and subworkflow!=None or
                process!=None and fun!=None or 
                fun!=None and subworkflow!=None ):
                if(process==None):
                    name = subworkflow.get_name()
                else:
                    name = process.get_name()
                raise BioFlowInsightError("tsnwgtmt", self, name)
            if(process!=None and subworkflow==None and fun==None):
                #If the process is already initialised, then we need to create a copy
                if(process.is_initialised()):
                    temp = process
                    process, num  = process.copy()
                    process.set_alias(temp.get_alias())
                process.initialise()
                self.first_element_called = process
                process.add_to_calls(self)
                self.origin.add_element_to_elements_being_called(process)
                #temp.incremente_number_times_called()
            if(process==None and subworkflow!=None and fun==None):
                #If the subworkflow is already initialised, then we need to create a copy of it
                if(subworkflow.is_initialised()):
                    temp = subworkflow
                    subworkflow, num = subworkflow.copy()
                    subworkflow.set_alias(temp.get_alias())
                sub_origin = self.get_subworkflow_or_main()
                if(sub_origin.get_type() == "Subworkflow"):
                    if(sub_origin.get_name() == subworkflow.get_alias()):
                        raise BioFlowInsightError("rcos", self, sub_origin.get_name(), self.get_string_line(self.get_code(get_OG = True)))
   
                subworkflow.initialise()
                self.first_element_called = subworkflow
                subworkflow.add_to_calls(self)
                self.origin.add_element_to_elements_being_called(subworkflow)
            if(process==None and subworkflow==None and fun!=None):
                self.first_element_called = fun
            if(process==None and subworkflow==None and fun==None):
                raise Exception("No first call found!!")
            self.called.append(self.first_element_called)
        else:
            raise BioFlowInsightError('ftec', self, self.get_string_line(self.get_code()))

    def get_all_conditions(self, conditions):
        self.get_block().get_all_conditions(conditions = conditions)
        return list(conditions.keys())

    
    def get_called(self):
        tab = self.called
        for params in self.parameters:
            if(isinstance(params, Call)):
                tab += params.get_called()
        tab = list(set(tab))
        return tab


    def write_summary(self, tab=0):
        file = open(f"{self.get_output_dir()}/debug/calls.nf", "a")
        file.write("  "*tab+f"{self}"+"\n")
        file.write("  "*(tab+1)+"* Called "+str(self.get_called())+"\n")
        file.write("  "*(tab+1)+"* Code : "+ str(self.get_code())+"\n")
        file.write("  "*(tab+1)+"* Parameters"+"\n")
        for p in self.parameters:
            file.write("  "*(tab+3)+p.get_code(replace_calls = False)+f" '{p.get_type()}'"+"\n")
        file.write("\n")

    def add_call_count(self):
        if(self.get_first_element_called().get_type()=="Process"):
            process = self.get_first_element_called()
            with open(f"{self.get_output_dir()}/debug/processes_used.json") as json_file:
                dict = json.load(json_file)
            try:
                a = dict[process.get_file_address()]
            except:
                dict[process.get_file_address()] = []
            dict[process.get_file_address()].append(process.get_code())
            with open(f"{self.get_output_dir()}/debug/processes_used.json", "w") as outfile:
                    json.dump(dict, outfile, indent=4)
        elif(self.get_first_element_called().get_type()=="Subworkflow"):
            None
        elif(self.get_first_element_called().get_type()=="Function"):
            None
        else:
            raise Exception(f"I don't know what to do with '{self.get_first_element_called().get_type()}' in the call '{self.get_code()}' (in file ''{self.get_file_address()}'')")
        
    def initialise(self):
        if(not self.initialised):
            self.initialised = True
            self.analyse_call(self.get_code(clean_pipe = True))
            self.write_summary()
            

        




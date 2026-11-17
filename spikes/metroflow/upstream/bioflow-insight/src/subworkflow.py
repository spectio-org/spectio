import re 
from . import constant
from .code_ import Code
import copy
from .root import Root
from .main import Main
from .bioflowinsighterror import BioFlowInsightError
from .outils import remove_jumps_inbetween_parentheses, replace_group1, get_dico_from_tab_from_id, check_if_element_in_tab_rocrate




class Subworkflow(Main):
    def __init__(self, code, nextflow_file, name):
        Main.__init__(self, code, nextflow_file)
        self.name = name.replace("'", "").replace('"', '')
        self.alias = self.name
        self.printed_name = self.name
        #These are the different parts of of a subworkflow -> work corresponds to the main 
        self.take = []
        self.take_code = ""
        self.takes_channels = []
        self.work = None
        self.main_code = ""
        self.emit = []
        self.emit_code = ""
        self.call = []

        #These are probably to remove
        self.initialised = False
        self.later_emits = []
        self.number_times_called = 0

        self.called_by = []#List of calls
        self.number_times_copied = 0

        self.elements_in_order = True

        #This for when i analyse trough the language server
        self.elements_in_workflow = []

    def copy(self):
        sub = copy.copy(self)
        sub.alias = self.name
        sub.printed_name = self.printed_name 
        sub.take = []
        sub.takes_channels = []
        sub.work = None
        sub.emit = []
        sub.call = []
        sub.initialised = False
        sub.later_emits = []
        sub.number_times_called = 0
        sub.called_by = []
        num = self.number_times_copied
        self.number_times_copied+=1
        return sub, num
    
    def add_elements_to_workflow(self, ele):
        self.elements_in_workflow.append(ele)

    def get_elements_to_workflow(self):
        return self.elements_in_workflow

    def add_to_calls(self, call):
        self.called_by.append(call)

    def get_call(self):
        if(len(self.called_by)!=1):
            raise Exception("This shouldn't happen")
        return self.called_by[0]

    def get_calls(self):
        return self.called_by
    

    def get_calls_by_name(self, name):            
        tab = []
        for call in self.root.get_calls_same_level():
            #call.initialise()
            for c in call.get_all_calls():
                if(c.first_element_called.get_alias()==name):
                    tab.append(c)
        #Here it is important that BioFlow-Insight is not a Nextflow verificator
        #Here i'm checking the call inside the block
        if(len(tab)==0):
            for call in self.root.get_calls_inside_level():
                #call.initialise()
                for c in call.get_all_calls():
                    if(c.first_element_called.get_alias()==name):
                        tab.append(c)
        return tab
        

    def add_to_emits(self, emit):
        self.later_emits.append(emit)
    
    def get_later_emits(self):
        return self.later_emits

    def get_code_with_alias(self):
        code = self.get_code()
        def replacer(match):
            return match.group(0).replace(match.group(1), self.get_alias())
        return re.sub(r"workflow\s*(\w+)\s*\{", replacer, code)
    
    def get_code_with_alias_and_id(self):
        code = self.get_code()
        def replacer(match):
            return match.group(0).replace(match.group(1), self.get_alias_and_id())
        from .constant import SUBWORKFLOW_HEADER
        return re.sub(SUBWORKFLOW_HEADER, replacer, code)

    def get_code_to_simplify(self):
        return self.get_code_with_alias_and_id()
    

    def set_alias(self, alias):
        self.alias = alias

    def get_alias(self):
        return self.alias

    def get_alias_and_id(self):
        return f"{self.alias}_GG_{id(self)}"

    def get_type(self):
        return "Subworkflow"

    def get_name(self):
        return self.name
    
    def get_work(self):
        return self.work.get_code()
    

    #Method which initiliases the different parts of a workflow (take/main/emit)
    def initialise_parts(self):
        code = self.get_code()
        take_multiple, take_pos= False, (0, 0)
        for match in re.finditer(constant.TAKE, code):
            if(take_multiple):
                raise BioFlowInsightError("meis", self, "take", self.get_name())
            take_pos = match.span(0)
            take_multiple = True

        main_multiple, main_pos= False, (0, 0)
        for match in re.finditer(constant.MAIN, code):
            if(main_multiple):
                raise BioFlowInsightError("meis", self, "main", self.get_name())
            main_pos = match.span(0)
            main_multiple = True

        emit_multiple, emit_pos= False, (0, 0)
        for match in re.finditer(constant.EMIT_SUBWORKFLOW, code):
            if(emit_multiple):
                raise BioFlowInsightError("meis", self, "emit", self.get_name())
            emit_pos = match.span(0)
            emit_multiple = True

        #Case everything is there
        if(take_pos!=(0, 0) and main_pos!=(0, 0) and emit_pos!=(0, 0)):
            if(take_pos[0]<main_pos[0] and main_pos[0]<emit_pos[0]):
                self.take = Code(code[take_pos[1]:main_pos[0]].strip(), origin = self, initialise=False)
                self.work = Code(code[main_pos[1]:emit_pos[0]].strip(), origin = self, initialise=False)
                self.emit = Code(code[emit_pos[1]:code.rfind('}')].strip(), origin = self, initialise=False)
            elif(take_pos[0]<emit_pos[0] and emit_pos[0]<main_pos[0]):
                self.take = Code(code[take_pos[1]:emit_pos[0]].strip(), origin = self, initialise=False)
                self.emit = Code(code[emit_pos[1]:main_pos[0]].strip(), origin = self, initialise=False)
                self.work = Code(code[main_pos[1]:code.rfind('}')].strip(), origin = self, initialise=False)
                self.elements_in_order = False
            elif(emit_pos[0]<take_pos[0] and take_pos[0]<main_pos[0]):
                self.emit = Code(code[emit_pos[1]:take_pos[0]].strip(), origin = self, initialise=False)
                self.take = Code(code[take_pos[1]:main_pos[0]].strip(), origin = self, initialise=False)
                self.work = Code(code[main_pos[1]:code.rfind('}')].strip(), origin = self, initialise=False)
                self.elements_in_order = False
            elif(emit_pos[0]<main_pos[0] and main_pos[0]<take_pos[0]):
                self.emit = Code(code[emit_pos[1]:main_pos[0]].strip(), origin = self, initialise=False)
                self.work = Code(code[main_pos[1]:take_pos[0]].strip(), origin = self, initialise=False)
                self.take = Code(code[take_pos[1]:code.rfind('}')].strip(), origin = self, initialise=False)
                self.elements_in_order = False
            elif(main_pos[0]<take_pos[0] and take_pos[0]<emit_pos[0]):
                self.work = Code(code[main_pos[1]:take_pos[0]].strip(), origin = self, initialise=False)
                self.take = Code(code[take_pos[1]:emit_pos[0]].strip(), origin = self, initialise=False)
                self.emit = Code(code[emit_pos[1]:code.rfind('}')].strip(), origin = self, initialise=False)
                self.elements_in_order = False
            elif(main_pos[0]<emit_pos[0] and emit_pos[0]<take_pos[0]):
                self.work = Code(code[main_pos[1]:emit_pos[0]].strip(), origin = self, initialise=False)
                self.emit = Code(code[emit_pos[1]:take_pos[0]].strip(), origin = self, initialise=False)
                self.take = Code(code[take_pos[1]:code.rfind('}')].strip(), origin = self, initialise=False)
                self.elements_in_order = False
            else:
                raise Exception("This shoudn't happen")
        #Case nothing is there
        if(take_pos==(0, 0) and main_pos==(0, 0) and emit_pos==(0, 0)):
            #raise Exception(f"Subworkflow {code} doesn't have anything defined")
            firt_curly  = code.find("{")
            last_curly = code.rfind('}')
            self.work = Code(code[firt_curly+1:last_curly], origin = self, initialise=False)
        #Case there is an input but no output
        if(take_pos!=(0, 0) and main_pos!=(0, 0) and emit_pos==(0, 0)):
            if(take_pos[0]<main_pos[0]):
                self.take = Code(code[take_pos[1]:main_pos[0]].strip(), origin = self, initialise=False)
                self.work = Code(code[main_pos[1]:code.rfind('}')].strip(), origin = self, initialise=False)
            else:
                main = code[main_pos[1]:take_pos[0]].strip()
                take = code[take_pos[1]:code.rfind('}')].strip()
                self.work = Code(main, origin = self, initialise=False)
                self.take = Code(take, origin = self, initialise=False)
                self.elements_in_order = False
        #Case there is no input but an output
        if(take_pos==(0, 0) and main_pos!=(0, 0) and emit_pos!=(0, 0)):
            if(main_pos[0]<emit_pos[0]):
                self.work = Code(code[main_pos[1]:emit_pos[0]].strip(), origin = self, initialise=False)
                self.emit = Code(code[emit_pos[1]:code.rfind('}')].strip(), origin = self, initialise=False)
            else:
                emit = code[emit_pos[1]:main_pos[0]].strip()
                main = code[main_pos[1]:code.rfind('}')].strip()
                self.work = Code(main, origin = self, initialise=False)
                self.emit = Code(emit, origin = self, initialise=False)
                self.elements_in_order = False
        #Case there is a main but no input and no output
        if(take_pos==(0, 0) and main_pos!=(0, 0) and emit_pos==(0, 0)):
            self.work = Code(code[main_pos[1]:code.rfind('}')].strip(), origin = self, initialise=False)
        if( main_pos==(0, 0) and (take_pos!=(0, 0) or emit_pos!=(0, 0))):
            if(take_pos!=(0, 0) and emit_pos!=(0, 0)):
                raise Exception("TODO")
            elif(take_pos!=(0, 0) and emit_pos==(0, 0)):
                raise Exception("TODO")
            elif(take_pos==(0, 0) and emit_pos!=(0, 0)):
                self.emit = Code(code[emit_pos[1]:code.rfind('}')].strip(), origin = self, initialise=False)
                firt_curly  = code.find("{")
                self.work = Code(code[firt_curly+1:emit_pos[0]].strip(), origin = self, initialise=False)
                self.elements_in_order
            else:
                raise Exception("Not possible!")
        if(self.take!=[]):
            self.take_code = self.take.get_code()
        if(self.work!=None):
            self.main_code = self.work.get_code()
        if(self.emit!=[]):
            self.emit_code = self.emit.get_code()
    
    def get_channel_from_name_takes(self, name):
        for c in self.takes_channels:
            if(name == c.get_name()):
                return c
        return None

    def initialise_takes(self):
        if(self.take!=[]):
            code = remove_jumps_inbetween_parentheses(self.take.get_code()).split('\n')
            tab = []
            for i in range(len(code)):
                code[i] = code[i].strip()
                if(code[i]!=''):
                    channel = self.get_channel_from_name_takes(code[i])
                    #channel = self.root.get_channel_from_name(code[i])
                    #In the case the channel doesn't exist
                    if(channel==None):
                        from .operation import Operation
                        ope = Operation(f"t: {code[i]}", self)
                        ope.set_as_artificial()
                        from .channel import Channel
                        channel = Channel(code[i], self)
                        ope.add_element_gives(channel)
                        channel.add_source(ope)
                        #ope.initialise_from_subworkflow_take()
                    else:
                        raise BioFlowInsightError("caease", self, code[i], "")
                    tab.append(ope)
                    for channel in ope.get_gives():
                        self.takes_channels.append(channel)
            self.take = tab




    def initialise_emit(self):
        from .operation import Operation
        if(self.emit!=[]):
            code = remove_jumps_inbetween_parentheses(self.emit.get_code()).split('\n')
            tab = []
            for i in range(len(code)):
                code[i] = code[i].strip()
                if(code[i]!=""):
                    element = code[i]
                    left, right = "", ""
                    for match in re.finditer(r"(\w+) *= *(.+)", element):
                        if(match.group(1)==match.group(2).strip()):
                            element = match.group(1)
                            break
                        else:
                            left, right = match.group(1), match.group(2).strip()
                    
                    if(right!=""):
                        element = right

        
                    #V1
                    channels = self.root.get_channels_from_name_same_level(element)
                    if(channels==[]):
                        channels = self.root.get_channels_from_name_inside_level(element)
                    if(channels==[]):
                        channels = self.root.get_channels_from_name_other_blocks_on_same_level(element)

                    #V2
                    #channels = self.root.get_channels_from_name_same_level(code[i])+self.root.get_channels_from_name_inside_level(code[i])+self.root.get_channels_from_name_other_blocks_on_same_level(code[i])
                    
                    from .channel import Channel
                    if(channels!=[]):
                        ope = Operation(code=f"e: {code[i]}", origin=self)
                        ope.set_as_artificial()
                        for channel in channels:
                            ope.add_element_origins(channel)
                            channel.add_sink(ope)
                        if(left!=""):
                            ope.add_element_gives(Channel(left, self))
                        tab.append(ope)
                        
                    else:
                        #raise Exception(f"I don't know how to handle '{code[i]}'")
                        #Case it's an operation 
                        operation = Operation(code[i], self)
                        operation.initialise()
                        operation.change_code(f"e: {code[i]}")
                        operation.set_as_artificial()
                        if(left!=""):
                            operation.add_element_gives(Channel(left, self))
                        tab.append(operation)
                        #operation.add_gives(channel)
                        #for gives in operation.get_gives():
                        #    gives.add_sink(operation)
                        #tab.append(operation)
                        ##self.add_operation(operation)
                        ##self.executors.append(operation)
            self.emit = tab
            
            

    

    def get_emit(self):
        return self.emit
    
    def get_nb_emit(self):
        return len(self.emit)

    def get_takes(self):
        return self.take
    
    def get_nb_takes(self):
        return len(self.take)
    
    def get_nb_inputs(self):
        return self.get_nb_takes()
            
    def is_initialised(self):
        return self.initialised

    def initialise(self):
        if(not self.initialised):
            self.initialised = True
            self.initialise_parts()
            self.initialise_takes()
            self.modules_defined = self.nextflow_file.get_modules_defined()
            #Check that includes are not defined in the main or subworkflows
            self.check_includes()
            self.root = Root(code=self.get_work(), origin=self, modules_defined=self.modules_defined, subworkflow_inputs = self.takes_channels)
            self.root.initialise()
            self.initialise_emit()
            

    def get_all_executors_in_subworkflow(self):
        dico = {}
        self.root.get_all_executors_in_subworkflow(calls = dico)
        for operation in self.emit:
            dico[operation] = ""
        return list(dico.keys())

    def get_structure(self, dico):
        super().get_structure(dico)

        for ope in self.get_takes():
            #ope.set_operation_type("Branch")
            ope.get_structure(dico)
        
        for ope in self.get_emit():
            #ope.set_operation_type("Branch")
            ope.get_structure(dico)

  
    def add_2_rocrate(self, dico, parent_key, prov_ro_crate):
        sub_key = self.get_rocrate_key(dico)
        dico_sub = get_dico_from_tab_from_id(dico, sub_key)
        if(dico_sub==None):
            dico_sub = {}
            dico_sub["@id"] = sub_key
            dico_sub["name"] = f"Subworkflow#{self.get_alias()}"
            dico_sub["@type"] = ["s:SoftwareSourceCode", "bioschemas:ComputationalWorkflow"]
            #dico_main["conformsTo"] = {"@id": "https://bioschemas.org/profiles/ComputationalWorkflow/0.5-DRAFT-2020_07_21"}
            #dico_main["dct:conformsTo"]= "https://bioschemas.org/profiles/ComputationalWorkflow/1.0-RELEASE/"
            
            
            #ADD INPUTS
            dico_sub["bioschemas:input"] = []
            for input in self.get_takes():
                if(type(input)==str):
                    name_input = input
                else:
                    name_input = input.get_code(get_OG = True)
                dico_input = get_dico_from_tab_from_id(dico, name_input)
                if(dico_input==None):
                    dico_input = {"@id":f"#{name_input}", "name": name_input, "@type": "FormalParameter"}
                    dico["@graph"].append(dico_input)
                dico_sub["bioschemas:input"].append({"@id":dico_input["@id"]})
            #ADD OUTPUTS
            dico_sub["bioschemas:output"] = []
            for output in self.get_emit():
                if(type(output)==str):
                    name_output = output
                else:
                    name_output = output.get_code(get_OG = True)
                dico_output = get_dico_from_tab_from_id(dico, name_output)
                if(dico_output==None):
                    dico_output = {"@id":f"#{name_output}", "name": name_output, "@type": "FormalParameter"}
                    dico["@graph"].append(dico_output)
                dico_sub["bioschemas:output"].append({"@id":dico_output["@id"]})


            dico_sub["s:isPartOf"] = [{"@id": parent_key}]
            dico_sub["s:hasPart"] = []
            if(prov_ro_crate):
                dico_sub["s:step"] = []


            called = []
            for call in self.root.get_all_calls_from_root():
                called.append(call.get_first_element_called())

            for c in called:
                if(c==self):
                    raise Exception("This shoudn't happen!")
                c.add_2_rocrate(dico, sub_key, prov_ro_crate)
                if(call.get_type()=="Subworkflow" or not prov_ro_crate):
                    dico_sub["s:hasPart"].append({"@id":c.get_rocrate_key(dico)})
                else:
                    #Case process and we want prov
                    dico_sub["s:step"].append({"@id":c.get_rocrate_key(dico)})

            dico["@graph"].append(dico_sub)
        else:
            if(not check_if_element_in_tab_rocrate(dico_sub["s:isPartOf"], parent_key)):
                dico_sub["s:isPartOf"].append({"@id":parent_key})

        self.get_nextflow_file().add_to_has_part(dico, sub_key)
    
    def get_DBfile_description(self, workflow_name):
        text = ""
        text+= f"# {self.get_alias()} Subworkflow"
        text+=f"""\nbioschemas:subworkflow{self.get_alias()} rdf:type bioschemas:Subworkflow ;
\tp-plan:isSubPlanOf bioschemas:{workflow_name}"""
        
        processes_called, subworkflows_called = [], []
        all_calls = self.get_all_calls_in_subworkflow()
        for c in all_calls:
            if(c.get_first_element_called().get_type()=="Process"):
                processes_called.append(c.get_first_element_called())
            if(c.get_first_element_called().get_type()=="Subworkflow"):
                subworkflows_called.append(c.get_first_element_called())
        
        for i in range(len(processes_called)):
            processes_called[i] = f'bioschemas:step{processes_called[i].get_alias()}'
        if(len(processes_called)!=0):
            text+= f" ;\n\tschema:step {', '.join(processes_called)}"
        
        input_params = []
        for input in self.get_takes():
            input_params.append(f"bioschemas:{input.get_code(get_OG = True)}")
        if(len(input_params)!=0):
            text+= f" ;\n\tbioschemas:inputVariable {', '.join(input_params)}"

        output_params = []
        for output in self.get_emit():
            val = output.get_code(get_OG = True)
            val = val.replace(",", "\\,")
            val = val.replace("'", "\\'")
            val = val.replace('"', '\\"')
            output_params.append(f"bioschemas:{val}")
        if(len(output_params)!=0):
            text+= f" ;\n\tbioschemas:outputVariable {', '.join(output_params)}"
        text+=" ."

        for input in input_params:
            text+=f"\n\n{input} rdf:type bioschemas:Variable ."

        for output in output_params:
            text+=f"\n\n{output} rdf:type bioschemas:Variable ."

        for sub in subworkflows_called:
            text+=f'\n\n{sub.get_DBfile_description(f"subworkflow{self.get_alias()}")}'
            
        return text

        
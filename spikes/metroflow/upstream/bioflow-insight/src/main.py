from .nextflow_building_blocks import Nextflow_Building_Blocks
from .bioflowinsighterror import BioFlowInsightError
from .root import Root
import re
from .outils import *

from . import constant



class Main(Nextflow_Building_Blocks):
    def __init__(self, code, nextflow_file):
        Nextflow_Building_Blocks.__init__(self, code, initialise_code=False)
        self.nextflow_file = nextflow_file
        self.initialised = False
        self.root = None 


    def get_cycle_status(self):
        return self.nextflow_file.get_cycle_status()
    
    def get_origin(self):
        return self.nextflow_file
    
    def get_order_execution_executors(self, dico, seen):
        executors = self.get_all_executors_in_subworkflow()
        pos = {}
        for e in executors:
            if(not e.get_artificial_status()):
                code = e.get_code(get_OG = True)
                #We don't have to check the calls -> since there are renamed with their ids when we rewrite the code -> so it solve the issue
                if(code in seen and e.get_type()=="Operation"):
                    raise BioFlowInsightError('oatitew', self, code)
                seen[code] = e
                pos[e] = e.get_position_in_main(e)
        pos =  {k: v for k, v in sorted(pos.items(), key=lambda item: item[1])}
        for e in pos:
            if(e.get_type()=="Call"):
                if(e.get_first_element_called().get_type()=="Subworkflow"):
                    dico[e] = {}
                    e.get_first_element_called().get_order_execution_executors(dico[e], seen)
                else:
                    dico[e.get_first_element_called()] = pos[e]
            else:
                dico[e] = pos[e]
        return dico

    #We do thus to defitiate the subworkflwow and main case
    def get_code_to_simplify(self):
        return self.get_code()

    
    
    def get_position_in_main(self, executor):
        code = self.get_code()
        return code.find(executor.get_code(get_OG = True))

    def get_string_line(self, bit_of_code):
        return self.nextflow_file.get_string_line(bit_of_code)
    
    #def check_in_channels(self, channel):
    #    return self.root.check_in_channels(channel)

    def get_conditions_2_ignore(self):
        return self.nextflow_file.get_conditions_2_ignore()

    def get_modules_defined(self):
        return self.nextflow_file.get_modules_defined()

    
    def get_DSL(self):
        return self.nextflow_file.get_DSL()
    
    def get_file_address(self, short = False):
        return self.nextflow_file.get_file_address(short = short)
    
    def get_nextflow_file(self):
        return self.nextflow_file


    def get_output_dir(self):
        return self.nextflow_file.get_output_dir()


    def get_type(self):
        return "Main"

    def get_all_calls_in_subworkflow(self):
        dico = {}
        self.root.get_all_calls_in_subworkflow(calls = dico)
        return list(dico.keys())
    
    def get_all_executors_in_subworkflow(self):
        dico = {}
        self.root.get_all_executors_in_subworkflow(calls = dico)
        return list(dico.keys())


    def get_all_calls_in_workflow(self):
        all_calls = self.get_all_calls_in_subworkflow()
        dico = {}
        for c in all_calls:
            sub = c.get_first_element_called()
            if(sub.get_type()=="Subworkflow"):
                if(c not in dico):
                    sub_calls = sub.get_all_calls_in_workflow()
                    for sub_c in sub_calls:
                        dico[sub_c] = ""
        for c in all_calls:
            dico[c] = ""

        return list(dico.keys())
    
 
    def get_all_executors_in_workflow(self):
        all_executors = self.get_all_executors_in_subworkflow()
        dico = {}
        for e in all_executors:
            dico[e] = ""

        calls = self.get_all_calls_in_workflow()
        for call in calls:
            
            sub = call.get_first_element_called()
            if(sub.get_type()=="Subworkflow"):
                sub_calls = sub.get_all_executors_in_workflow()
                for sub_c in sub_calls:
                    dico[sub_c] = ""

    
        return list(dico.keys())

    
    def check_includes(self):
        code = self.get_code()

        pattern = constant.FULL_INCLUDE
        for match in re.finditer(pattern, code):
            if(self.get_type()=="Main"):
                raise BioFlowInsightError("ific", self, match.group(0), "main")
            elif(self.get_type()=="Subworkflow"):
                raise BioFlowInsightError("ific", self, match.group(0), f"subworkflow '{self.get_name()}'")
            else:
                raise Exception("This shouldn't happen!")
            
        
    def initialise(self):
        if(not self.initialised):

            self.initialised=True

            #Get the modules (Processes defined for the main/subworkflow)
            self.modules_defined = self.nextflow_file.get_modules_defined()

            #Check that includes are not defined in the main or subworkflows
            self.check_includes()
            self.root = Root(code=self.get_code(), origin=self, modules_defined=self.modules_defined, subworkflow_inputs = [])
            #The weird DSL1 bug is here
            #self.root = Root(code=self.get_code(), origin=self, modules_defined=self.modules_defined)
            self.root.initialise()




    def get_structure(self, dico):
        self.root.get_structure(dico)
        dico["id"] = str(self)
        return dico
    
    def get_most_influential_conditions(self, get_on_process_dependency):
        most_influential_conditions = {}
        if(self.nextflow_file.get_DSL()=="DSL2"):
            if(get_on_process_dependency):
                all_executors = self.get_all_calls_in_subworkflow()
            else:
                all_executors = self.get_all_executors_in_workflow()
            for exe in all_executors:
                if(exe.get_type()=="Call"):
                    c = exe
                    if(c.get_first_element_called().get_type()=="Process"):
                        for condition in c.get_all_conditions(conditions = {}):
                            try:
                                temp = most_influential_conditions[condition]
                            except:
                                most_influential_conditions[condition] = []
                            most_influential_conditions[condition]+=[c]
                    
                    if(c.get_first_element_called().get_type()=="Subworkflow"):
                        most_influential_conditions_sub = c.get_first_element_called().get_most_influential_conditions(get_on_process_dependency = get_on_process_dependency)
                        for cond in most_influential_conditions_sub:
                            try:
                                temp = most_influential_conditions[cond]
                            except:
                                most_influential_conditions[cond] = []
                            most_influential_conditions[cond]+= most_influential_conditions_sub[cond]
   
                elif(exe.get_type()=="Operation" and not get_on_process_dependency):
                    if(not exe.get_artificial_status()):
                        for condition in exe.get_block().get_all_conditions(conditions = {}):
                            try:
                                temp = most_influential_conditions[condition]
                            except:
                                most_influential_conditions[condition] = []
                            most_influential_conditions[condition]+=[exe]
                            
                else:
                    raise Exception("This shoudn't happen")
            return most_influential_conditions
        
        elif(self.nextflow_file.get_DSL()=="DSL1"):
            if(not get_on_process_dependency):
                #Oerations first
                for exe in self.get_all_executors_in_workflow():
                    if(not exe.get_artificial_status()):
                        for condition in exe.get_block().get_all_conditions(conditions = {}):
                            try:
                                temp = most_influential_conditions[condition]
                            except:
                                most_influential_conditions[condition] = []
                            most_influential_conditions[condition]+=[exe]
            
            
            modules = self.get_modules_defined()
            for p in modules:
                if(p.get_type()=="Process"):
                    if(p.is_initialised()):
                        for condition in p.origin_DSL1.get_all_conditions(conditions = {}):
                            try:
                                temp = most_influential_conditions[condition]
                            except:
                                most_influential_conditions[condition] = []
                            most_influential_conditions[condition]+=[p]
            return most_influential_conditions
        else:
            raise Exception("This shouldn't happen")
    
    def check_that_a_channel_is_not_defined_used_and_redefined_used_in_another_block(self):
        return self.root.check_that_a_channel_is_not_defined_used_and_redefined_used_in_another_block()
    
    

    #=========================================================
    #-----------------------RO-CRATE--------------------------
    #=========================================================


    def add_2_rocrate(self, dico, prov_ro_crate):
        #By definition we add this info
        dico["@graph"].append({ "@id": "#nextflow", "@type": "ComputerLanguage", "name": "Nextflow", "identifier": {   "@id": "https://www.nextflow.io/" }, "url": {   "@id": "https://www.nextflow.io/" }})
        parent_key = self.nextflow_file.get_file_rocrate_key(dico)
        self.nextflow_file.add_computational_workflow_to_types(dico)
        main_key = f"{parent_key}#MAIN"
        dico_main = get_dico_from_tab_from_id(dico, main_key)
        if(dico_main==None):
            dico_main = {}
            dico_main["@id"] = main_key
            dico_main["name"] = "Main Workflow"
            dico_main["@type"] = ["s:SoftwareSourceCode", "bioschemas:ComputationalWorkflow"]

            #dico_main["conformsTo"] = {"@id": "https://bioschemas.org/profiles/ComputationalWorkflow/0.5-DRAFT-2020_07_21"}
            #dico_main["dct:conformsTo"]= "https://bioschemas.org/profiles/ComputationalWorkflow/1.0-RELEASE/"
            dico_main["bioschemas:input"] = []
            dico_main["bioschemas:output"] = []
            dico_main["s:isPartOf"] = [{"@id": parent_key}]
            dico_main["s:hasPart"] = []
            called = []
            for call in self.root.get_all_calls_from_root():
                called.append(call.get_first_element_called())
            for c in called:
                c.add_2_rocrate(dico, main_key, prov_ro_crate)
                dico_main["s:hasPart"].append({"@id":c.get_rocrate_key(dico)})
                
            dico["@graph"].append(dico_main)
        self.nextflow_file.add_to_has_part(dico, main_key)

        #Remove duplicates from dico["@graph"]
        duplicates = []
        seen = []
        for ele in dico["@graph"]:
            if(ele in seen):
                duplicates.append(ele)
            else:
                seen.append(ele)
        for ele in duplicates:
            dico["@graph"].remove(ele)

        
    
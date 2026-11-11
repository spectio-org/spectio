
import re 
import os
import ctypes
from pathlib import Path

from . import constant
from .nextflow_building_blocks import Nextflow_Building_Blocks
from .process import Process
from .subworkflow import Subworkflow
from .operation import Operation
from .outils import *
from .bioflowinsighterror import BioFlowInsightError


def get_object(address):
    address = int(re.findall(r"\dx\w+", address)[0], base=16)
    return ctypes.cast(address, ctypes.py_object).value



class Nextflow_File(Nextflow_Building_Blocks):
    def __init__(self, address, workflow, first_file  = False):
        self.address = address 
        self.workflow = workflow
        self.first_file = first_file
        self.main = None
        self.workflow.add_nextflow_file_2_workflow(self)
        self.includes = []
        self.processes = []
        self.subworkflows = []
        self.functions = []

        #These 2 attributes are for if we want to analyse using the language server
        self.dico_conditions = {}
        self.structure = {}
        self.local_id_2_global_id = {}
        self.subworkflows_2_takes_emits = {}
        self.temp_structure = {}

        self.initialised = False
        self.added_2_rocrate = False
        contents = check_file_exists(self.get_file_address(), self)
        Nextflow_Building_Blocks.__init__(self, contents, initialise_code=True)
        self.check_file_correctness()

    #----------------------
    #GENERAL
    #----------------------

    def get_link_dico_processes(self):
        return self.workflow.get_link_dico_processes()

    def get_cycle_status(self):
        return self.workflow.get_cycle_status()

    def add_to_ternary_operation_dico(self, old, new):
        self.workflow.add_to_ternary_operation_dico(old, new)
    
    def add_map_element(self, old, new):
        self.workflow.add_map_element(old, new)

    def get_map_element(self):
        return self.workflow.get_map_element()

    def get_root_directory(self):
        return self.workflow.get_root_directory()

    def get_string_line(self, bit_of_code):
        return self.code.get_string_line(bit_of_code)

    def get_conditions_2_ignore(self):
        return self.workflow.get_conditions_2_ignore()

    #Method that returns the address of the file
    def get_file_address(self, short = False):
        if(not short):
            return Path(os.path.normpath(self.address))
        else:
            address = str(self.get_file_address())
            #dir = self.workflow.get_workflow_directory()
            #new_address = address.replace(dir, "")
            #if(new_address[0]=="/"):
            #    new_address = new_address[1:]
            #return new_address
            return str(self.get_file_address())[address.find(self.workflow.get_workflow_directory())+len((self.workflow.get_workflow_directory())):]
    

    def get_nextflow_file(self):
        return self
    
    def get_DSL(self):
        return self.workflow.get_DSL()
    


    #def get_origin(self):
    #    return self.workflow
    
    def check_file_correctness(self):
        code = self.get_code()
        #if(code.count("{")!=code.count("}")):
        #    curly_count = get_curly_count(code)
        #    if(curly_count!=0):
        #        raise BioFlowInsightError("ntsnocif", self)
        #if(code.count("(")!=code.count(")")):
        #    parenthese_count = get_parenthese_count(code)
        #    if(parenthese_count!=0):
        #        raise BioFlowInsightError("ntsnopif", self)

        if(code.count('"""')%2!=0):
            raise BioFlowInsightError("onotqif", self)

        


    #Method which returns the DSL of the workflow -> by default it's DSL2
    #I use the presence of include, subworkflows and into/from in processes as a proxy
    def find_DSL(self):
        DSL = "DSL2"
        #If there are include
        pattern = constant.FULL_INLCUDE_2
        for match in re.finditer(pattern, self.get_code()):
            return DSL
        #If there are subworkflows
        for match in re.finditer(constant.SUBWORKFLOW_HEADER, self.get_code()):
            return DSL
        #If there is the main
        for match in re.finditer(constant.WORKFLOW_HEADER_2, '\n'+self.get_code()+'\n'):
            return DSL
        #Analyse the processes
        self.extract_processes()
        for p in self.processes:
            DSL = p.which_DSL()
            if(DSL=="DSL1"):
                self.processes = []
                return DSL
        self.processes = []
        return DSL
    
    def get_workflow(self):
        return self.workflow

    
    #Returns either a subworkflow or process from the name
    def get_element_from_name(self, name):
        for process in self.processes:
            if(name==process.get_alias()):
                return process
        for subworkflow in self.subworkflows:
            if(name==subworkflow.get_alias()):
                return subworkflow
        for fun in self.functions:
            if(name==fun.get_alias()):
                return fun
        return None
        #raise BioFlowInsightError("estbdic", self, name)

    def get_modules_defined(self):
        return self.get_processes()+self.get_subworkflows()+self.get_functions()+self.get_modules_included()

    def get_output_dir(self):
        return self.workflow.get_output_dir()

    #----------------------
    #PROCESSES
    #----------------------
    def extract_processes(self):
        from .process import Process
        code = self.get_code()
        #Find pattern
        for match in re.finditer(constant.PROCESS_HEADER, code):
            start = match.span(0)[0]
            name = match.group(1)
            try:
                end = extract_curly(code, match.span(0)[1])#This function is defined in the functions file
            except:
                raise BioFlowInsightError('uteeoe', self, "process", name)
            p = Process(code=code[start:end], nextflow_file=self)
            self.processes.append(p)

    def get_processes(self):
        return self.processes


    #----------------------
    #SUBWORKFLOW (ones found in the file)
    #----------------------
    def extract_subworkflows(self):
        from .subworkflow import Subworkflow
        #Get code without comments
        code = self.get_code()
        #Find pattern
        for match in re.finditer(constant.SUBWORKFLOW_HEADER, code):
            start = match.span(0)[0]
            name = match.group(1)
            try:
                end = extract_curly(code, match.span(0)[1])#This function is defined in the functions file
            except:
                raise BioFlowInsightError('uteeoe', self, "subworkflow", name)
            sub = Subworkflow(code=code[start:end], nextflow_file=self, name = name)
            self.subworkflows.append(sub)

    def get_subworkflows(self):
        return self.subworkflows

    #----------------------
    #MAIN WORKFLOW
    #----------------------
    #This method extracts the "main" workflow from the file 
    def extract_main(self):
        if(self.first_file):
            from .main import Main
            #This returns the code without the comments
            code = "\n"+self.get_code()+"\n"
            #Find pattern
            twice = False
            for match in re.finditer(constant.WORKFLOW_HEADER_2, code):
                
                start = match.span(1)[0]
                try:
                    end = extract_curly(code, match.span(1)[1])#This function is defined in the functions file
                except:
                    code = self.get_code()
                    if(code.count("{")!=code.count("}")):
                        curly_count = get_curly_count(code)
                        if(curly_count!=0):
                            raise BioFlowInsightError("ntsnocif", self)
                    if(code.count("(")!=code.count(")")):
                        parenthese_count = get_parenthese_count(code)
                        if(parenthese_count!=0):
                            raise BioFlowInsightError("ntsnopif", self)
                    raise BioFlowInsightError('uteeoe', self, "main", start)

                self.main = Main(code= code[start:end], nextflow_file=self)
                if(twice):
                    raise BioFlowInsightError('mmic', self)
                twice = True
            if(self.main==None):
                self.main = Main(code= "", nextflow_file=self)
                #raise BioFlowInsightError("nomic", self)


    #----------------------
    #FUNCTIONS
    #----------------------

    #Method that extracts the functions from a file -> we don't analyse them
    #since they don't structurally change the workflow
    def extract_functions(self):
        from .function import Function
        #pattern_function = r"(def|String|void|Void|byte|short|int|long|float|double|char|Boolean) *(\w+) *\([^,)]*(,[^,)]+)*\)\s*{"
        pattern_function = constant.HEADER_FUNCTION
        code = self.get_code()
        #Find pattern
        for match in re.finditer(pattern_function, code):
            start = match.span(0)[0]
            if(match.group(2) not in ['if']):
                try:
                    end = extract_curly(code, match.span(0)[1])#This function is defined in the functions file
                    f = Function(code = code[start:end], name = match.group(2), origin =self)
                except:
                        #Since in reality we don't do anything with the groups -> so need to analyse them
                        f = Function(code = match.group(0), name = match.group(2), origin =self)
                        #f = Function(code = code[start:end], name = match.group(2), origin =self)
                self.functions.append(f)
            #    print(code)
            #    1/0
            #f = Code(code=code[start:end], origin=self)
            #Fobiden names of functions
            

    def get_functions(self):
        return self.functions


    #----------------------
    #INCLUDES
    #----------------------
    def extract_includes(self):
        from .include import Include

        code = self.get_code()
        pattern = constant.FULL_INLCUDE_2
        
        for match in re.finditer(pattern, code):
            
            includes = match.group(1).replace('{', '').replace('}', '').strip()

            #We do this if there are multiple includes
            #To take into account
            #include {
            #PAIRTOOLS_SELECT
            #    as PAIRTOOLS_SELECT_VP;
            #PAIRTOOLS_SELECT
            #    as PAIRTOOLS_SELECT_LONG
            found_semi, found_n = bool(includes.find(";")+1), bool(includes.find("\n")+1)
            if(found_semi and found_n):
                temp = includes.split(";")
                tab = []
                for temp_include in temp:
                    temp_include = temp_include.replace("\n", ' ').strip()
                    if(temp_include[:3] in constant.LIST_AS):
                        tab[-1] = tab[-1]+" "+temp_include
                    else:
                        tab.append(temp_include)
                includes = tab
            elif(found_semi):
                includes = includes.split(";")
            elif(found_n):
                temp = includes.split("\n")
                tab = []
                for temp_include in temp:
                    temp_include = temp_include.strip()
                    if(temp_include[:3]in constant.LIST_AS):
                        tab[-1] = tab[-1]+" "+temp_include
                    else:
                        tab.append(temp_include)
                includes = tab
            else:
                includes = [includes]
            
            
            
            #https://www.nextflow.io/docs/latest/plugins.html#plugins
            #https://github.com/nextflow-io/nf-validation
            #address = match.group(0).split('from')[1].strip()
            address = match.group(6).strip()
            if(address[1:].split('/')[0] not in ['plugin']):
                include = Include(code =match.group(0), file = address, importing = includes, nextflow_file=self)
                self.includes.append(include)

    def get_includes(self):
        return self.includes
    
    def get_modules_included(self):
        modules = []
        for include in self.includes:
            modules+=list(include.defines.values())
        return modules

    def get_calls_made_outside_of_main(self):
        #Code without processes
        code = self.get_code()
        for proecess in self.processes:
            temp = code
            code = code.replace(proecess.get_code(), "")
            if(temp==code):
                raise Exception("This souldn't happen")
        for sub in self.subworkflows:
            temp = code
            code = code.replace(sub.get_code(), "")
            if(temp==code):
                raise Exception("This souldn't happen")
        for fun in self.functions:
            temp = code
            code = code.replace(fun.get_code(), "")
            if(temp==code):
                raise Exception("This souldn't happen")
        if(self.first_file and self.main!=None):
            temp = code
            code = code.replace(self.main.get_code(), "")
            if(temp==code):
                raise Exception("This souldn't happen")
        for include in self.includes:
            temp = code
            code = code.replace(include.get_code(), "")
            if(temp==code):
                raise Exception("This souldn't happen")

        from .root import Root
        self.root = Root(code=code, origin= self, modules_defined=self.get_modules_defined(), subworkflow_inputs = [])
        self.root.initialise()
        calls = {}
        self.root.get_all_calls_in_subworkflow(calls=calls)
        return list(calls.keys())

    #----------------------
    #INITIALISE
    #----------------------

    #Method that initialises the nextflow file
    def initialise(self, language_server = None, name_subworkflow = ""):
        
            
        #If there is no langauge Server then we run the bioFlow-Insight Analysis
        if(language_server == None):
            #If the file is not alreday initialised then we initialise it
            if(not self.initialised):
                self.initialised = True
                if(self.workflow.get_display_info_bool()):
                    print(f"Analysing -> '{self.get_file_address()}'")
            
                if(self.get_DSL()=="DSL2"):
                
                    #Extarct Processes
                    self.extract_processes()
                    #Analysing Processes
                    for process in self.processes:
                        process.initialise()

                    #Code without processes
                    code = self.get_code()
                    for proecess in self.processes:
                        temp = code
                        code = code.replace(proecess.get_code(), "", 1)
                        if(temp==code):
                            print(f"'{code}'")
                            print(proecess.get_code())
                            raise Exception("This souldn't happen")
                        
                    
                    #Extract includes
                    self.extract_includes()

                    #Extract subworkflows
                    self.extract_subworkflows()

                    #Analyse Inludes
                    for include in self.includes:
                        include.initialise()

                    #Extract main
                    self.extract_main()
                    
                    #Extract functions
                    self.extract_functions()

                    #Analyse Main
                    if(self.first_file and self.main!=None):
                        self.main.initialise()
                    #
                    ##Analyse subworkflows
                    #indice=1
                    #for sub in self.subworkflows:
                    #    sub.initialise()
                    #    indice+=1
                elif(self.get_DSL()=="DSL1"):
                    from .main import Main
                    #Extarct Processes
                    self.extract_processes()
                    code = self.get_code()
                    #Extract functions
                    self.extract_functions()

                    
                    #Replacing the processes and functions defined with their identifiers -> this is to simplifly the analysis with the conditions
                    for process in self.processes:
                        temp = code
                        code = code.replace(process.get_code(get_OG = True), f"process: {str(process)}")
                        if(temp==code):
                            print(process.get_code())
                            raise Exception("Something went wrong the code hasn't changed")
                
                    for function in self.functions:
                        temp = code
                        code = code.replace(function.get_code(get_OG = True), f"function: {str(function)}")
                        #if(temp==code):
                        #    #print(code)
                        #    #print("-", function.get_code(get_OG = True))
                        #    #print(self.functions)
                        #    raise Exception("Something went wrong the code hasn't changed")
                    self.main = Main(code= code, nextflow_file=self)
                    self.main.initialise()
                    
                else:
                    raise Exception("This shouldn't happen")
        #Then we run the langauge Server Analysis

        else:
            structure, conditions, processes, workflows = language_server.parse_file(self.get_file_address(), name_subworkflow = name_subworkflow)
            self.temp_structure = structure
            #This is not pretty but hey it gets the job done
            structure = str(structure).replace("George%27s%20Hard%20Drive", "George's Hard Drive")
            if(str(structure)=="{error=DAG preview cannot be shown because the script has errors.}"):
                raise BioFlowInsightError("ewlsif", origin=self)
            if(not self.initialised):
                self.initialised = True
                #Fill the processes
                for p in processes:
                    process = Process(code=p['code'], nextflow_file=self)
                    process.set_alias(p["name"])
                    self.processes.append(process)
                #Fill the subworkflows
                for sub in workflows:
                    subworkflow = Subworkflow(sub['code'], nextflow_file=self, name=sub['name'])
                    self.subworkflows.append(subworkflow)

            dico_structure, condition_edges = parse_mermaid_graph(str(structure))
            self.subworkflows_2_takes_emits[name_subworkflow] = {"takes":get_takes_emit_from_mermaid(str(structure), "take"), "emits":get_takes_emit_from_mermaid(str(structure), "emit")}

            def get_all_subgraphs(tab, dico):
                for sub_id in dico['subgraphs']:
                    sub = dico['subgraphs'][sub_id]
                    tab.append({"id":sub["id"], "nodes":sub["nodes"]})
                    tab = get_all_subgraphs(tab, dico['subgraphs'][sub_id])
                return tab
            
            all_subgraphs = get_all_subgraphs([], dico_structure)

            conditions_2_nodes = {}
            if(not conditions):
                conditions = {}
            conditions = dict(conditions)
            for id_cond in conditions:
                condition = conditions[id_cond]
                succ_positive, succ_negative = None, None
                for e in condition_edges:
                    if(e["A"]==f'v{id_cond}'):
                        succ_positive = e['B']
                    if(e["A"]==f'!v{id_cond}'):
                        succ_negative = e['B']
                    for sub in all_subgraphs:
                        if(sub["id"] == succ_positive):
                             #cond = Condition(origin = self, condition = condition)
                            conditions_2_nodes[condition] = sub['nodes']
                        if(sub["id"] == succ_negative):
                            #cond = Condition(origin = self, condition = f"!({condition})")
                            conditions_2_nodes[f"!({condition})"] = sub['nodes']
  
            #print(conditions_2_nodes)
            self.structure[name_subworkflow] = {}

            self.structure[name_subworkflow]['structure'] = dico_structure
            self.structure[name_subworkflow]['conditions'] = conditions_2_nodes


            #This is the recursive part
            elements_to_add_2_structure = []
            for n in dico_structure["nodes"]:
                id, name, ref = n['id'], n['name'], n['href']
                if(ref):
                    elements_to_add_2_structure.append(n)
            for ele in elements_to_add_2_structure:
                id, name, ref = ele['id'], ele['name'], ele['href']
                nf = self.workflow.get_nextflow_file(ref)
                if(not nf):
                    nf = Nextflow_File(ref, self.get_workflow())
                    self.workflow.add_nextflow_file_2_workflow(nf)
                nf.initialise(language_server=language_server, name_subworkflow = name)



        
    def add_to_has_part(self, dico, to_add_key):
        file_name = str(self.get_file_address())[len(dico["temp_directory"]):]
        file_dico = get_dico_from_tab_from_id(dico, file_name)
        file_dico["s:hasPart"].append({"@id":to_add_key})

    
    def add_computational_workflow_to_types(self, dico):
        file_name = str(self.get_file_address())[len(dico["temp_directory"]):]
        file_dico = get_dico_from_tab_from_id(dico, file_name)
        file_dico["@type"].append("bioschemas:ComputationalWorkflow")

    def get_file_rocrate_key(self, dico):
        file_name = str(self.get_file_address())[len(dico["temp_directory"]):]
        return file_name


    def object_from_name(self, name, code):
        for p in self.processes:
            if(p.get_alias()==name):
                new_p, _ = p.copy()
                new_p.set_alias(name)
                self.processes.append(new_p)
                return new_p
                #return p
        for sub in self.subworkflows:
            if(sub.get_name()==name):
                return sub
        #If we cannot find it it may because it has been renarmed, in that case we search the pattern 
        pattern = fr'(\w+)\s+(as|As|AS|aS)\s+{re.escape(name)}'
        new_name = ""
        for match in re.finditer(pattern, code):
            new_name = match.group(1)
            for p in self.processes:
                if(p.get_alias()==new_name):
                    new_p, _ = p.copy()
                    new_p.set_alias(name)
                    self.processes.append(new_p)
                    return new_p
            for sub in self.subworkflows:
                if(sub.get_name()==new_name):
                    new_sub, _ = sub.copy()
                    new_sub.set_alias(name)
                    self.subworkflows.append(new_sub)
                    return new_sub
        return None

    def get_source_sink_subworkflow(self, subworkflow):
        source, sink = [], []
        for n in self.subworkflows_2_takes_emits[subworkflow]['takes']:
            source.append((n[1], self.local_id_2_global_id[subworkflow][n[0]]))
        sink = []
        for n in self.subworkflows_2_takes_emits[subworkflow]['emits']:
            sink.append((n[1], self.local_id_2_global_id[subworkflow][n[0]]))
        return source, sink
        
    def get_structure(self, dico, element):

        self.local_id_2_global_id[element] = {}
        local_structure = self.structure[element]["structure"]
        subworkflow_to_internal_source_sink = {}
        for node in local_structure['nodes']:
            #This means it is not a 
            if(node["href"]!=None):
                nextflow_file_ref = self.workflow.get_nextflow_file(node["href"])
                name_node, name_id = str(node["name"]), f'{str(node["name"])}_$$_{str(node["id"])}'
                ele = nextflow_file_ref.object_from_name(name_node, self.get_code())
                if(ele.get_type()=="Subworkflow"):
                    self.local_id_2_global_id[element][node['id']] = ele
                    dico_temp = {}
                    dico_temp["nodes"] = []
                    dico_temp["edges"] = []
                    dico_temp["subworkflows"] = {}
                    dico_temp["id"] = str(ele)
                    dico["subworkflows"][name_id] = dico_temp
                    nextflow_file_ref.get_structure(dico["subworkflows"][name_id], name_node)
                    #Add elements which are defined in the subworkflow in the list which stores that
                    def get_all_nodes_rec(dico, nodes):
                        for n in dico["nodes"]:
                            nodes[n["id"]] = ""
                        for sub in dico["subworkflows"]:
                            get_all_nodes_rec(dico["subworkflows"][sub], nodes)
                        return nodes
                    for id in get_all_nodes_rec(dico["subworkflows"][name_id], {}):
                        object = get_object(id)
                        ele.add_elements_to_workflow(object)

                    subworkflow_to_internal_source_sink[node['id']] = {}
                    source, sink = nextflow_file_ref.get_source_sink_subworkflow(name_node)
                    subworkflow_to_internal_source_sink[node['id']]["source"] = source
                    subworkflow_to_internal_source_sink[node['id']]["sink"] = sink
                if(ele.get_type()=="Process"):
                    dico_node = {"artificial":False, "id":str(ele), "name":str(ele.get_alias()), 'shape':"ellipse", "xlabel":''}
                    self.local_id_2_global_id[element][node['id']] = ele
                    dico['nodes'].append(dico_node)
            #This means it's an operation
            else:
                #The difference between the 2 is that i add an artificial attribute
                if("take:" in node['name'] or "emit:" in node['name']):
                    ele = Operation(code=node['name'], origin=self)
                    ele.set_as_artificial()
                    self.local_id_2_global_id[element][node['id']] = ele
                    dico_node = {"artificial":True, "id":str(ele), "name":'', 'shape':"point", "xlabel":node['name']}
                    dico['nodes'].append(dico_node)
                #This means it is just a regular operation
                else:
                    ele = Operation(code=node['name'], origin=self)
                    self.local_id_2_global_id[element][node['id']] = ele
                    dico_node = {"artificial":False, "id":str(ele), "name":'', 'shape':"point", "xlabel":node['name']}
                    dico['nodes'].append(dico_node)

        for edge in local_structure['edges']:
            A_id, B_id = edge['A'], edge['B'] 
            #Regular
            if(A_id not in subworkflow_to_internal_source_sink and B_id not in subworkflow_to_internal_source_sink):
                
                try:
                    dico['edges'].append({"A":str(self.local_id_2_global_id[element][A_id]), "B":str(self.local_id_2_global_id[element][B_id]), "label":""})
                except Exception as e:
                    print(str(e))
                    import pprint
                    print(self.temp_structure)
                    1/0
            #Connecting the emits
            if(A_id in subworkflow_to_internal_source_sink and B_id not in subworkflow_to_internal_source_sink):
                emits = subworkflow_to_internal_source_sink[A_id]['sink']
                #print("-->", emits, self.local_id_2_global_id[element][B_id], self.local_id_2_global_id[element][B_id].get_code())
                found_matching = False
                for emit in emits:
                    name_emit, id_emit = emit
                    if(name_emit==self.local_id_2_global_id[element][B_id].get_code().replace("emit:", "")):
                        found_matching = True
                        dico['edges'].append({"A":str(id_emit), "B":str(self.local_id_2_global_id[element][B_id]), "label":""})
                #This is the backup
                if(not found_matching):
                    for emit in emits:
                        name_emit, id_emit = emit
                        dico['edges'].append({"A":str(id_emit), "B":str(self.local_id_2_global_id[element][B_id]), "label":""})
            #Connecting the takes
            if(A_id not in subworkflow_to_internal_source_sink and B_id in subworkflow_to_internal_source_sink):
                takes = subworkflow_to_internal_source_sink[B_id]['source']
                for take in takes:
                    name_take, id_take = take
                    if(name_take==self.local_id_2_global_id[element][A_id].get_code().replace("take:", "")):
                        found_matching = True
                        dico['edges'].append({"A":str(self.local_id_2_global_id[element][A_id]), "B":str(id_take), "label":""})

            #if(B_id in subworkflow_to_internal_source_sink):
            #    print("takes")
            #
            #if(A_id in subworkflow_to_internal_source_sink and B_id in subworkflow_to_internal_source_sink):
            #    #Need to connect everything with everything
            #else:
            #    #Regular case
            #    None
                
        #print(self.subworkflows_2_takes_emits)
        #print(subworkflow_to_internal_source_sink)

                #print(object_from_name(node["name"]))
        return dico
    
    def get_conditions(self, dico, element):
        local_structure = self.structure[element]["structure"]
        local_conditions = self.structure[element]["conditions"]

        for condition in local_conditions:
            try:
                temp = dico[condition]
            except:
                dico[condition] = []
            for id in local_conditions[condition]:
                ele = self.local_id_2_global_id[element][id]
                
                if(ele.get_type()=="Subworkflow"):
                    for e in ele.get_elements_to_workflow():
                        dico[condition]+=ele.get_elements_to_workflow()
                else:
                    dico[condition].append(ele)
            dico[condition] = list(set(dico[condition]))

        for node in local_structure['nodes']:
            #This means it is not a 
            if(node["href"]!=None):
                nextflow_file_ref = self.workflow.get_nextflow_file(node["href"])
                name_node = str(node["name"])
                nextflow_file_ref.get_conditions(dico, name_node)

        #self.local_id_2_global_id[element][B_id]
        #print(self.dico_conditions)
        return dico
from .code_ import Code


class Nextflow_Building_Blocks:
    def __init__(self, code, initialise_code):
        self.code = Code(code = code, origin = self, initialise=initialise_code)
    
    #---------------------------------
    #AUXILIARY METHODS FOR ALL CLASSES
    #---------------------------------

    def add_to_ternary_operation_dico(self, old, new):
        self.origin.add_to_ternary_operation_dico(old, new)
    
    def add_map_element(self, old, new):
        self.origin.add_map_element(old, new)

    def get_map_element(self):
        try:
            return self.origin.get_map_element()
        except:
            return self.nextflow_file.get_map_element()

    def get_code(self, get_OG = False):
        return self.code.get_code(get_OG = get_OG)
    
    def get_modules_defined(self):
        return self.origin.get_modules_defined()
    
    def get_process_from_name(self, name):
        return self.origin.get_process_from_name(name)
    
    def get_origin(self):
        return self.origin
    
    def get_workflow(self):
        return self.get_origin().get_workflow()
    
    def get_output_dir(self):
        return self.origin.get_output_dir()
    
    def get_DSL(self):
        return self.origin.get_DSL()
    
    def get_processes_annotation(self):
        return self.origin.get_processes_annotation()
    
    
    def get_nextflow_file(self):
        try:
            return self.origin.get_file_address()
        except:
            return self.nextflow_file
        
    def get_link_dico_processes(self):
        try:
            return self.origin.get_link_dico_processes()
        except:
            return self.nextflow_file.get_link_dico_processes()
        
        
    
    def get_display_info(self):
        return self.origin.get_display_info()
    
    def get_name_processes_subworkflows(self):
        return self.origin.get_list_name_subworkflows()+self.origin.get_list_name_includes()+ self.origin.get_list_name_processes()
    

    def get_line(self, bit_of_code):
        return self.origin.get_line(bit_of_code)
    
    def get_string_line(self, bit_of_code):
        return self.origin.get_string_line(bit_of_code)
    
    def get_name_file(self):
        return self.origin.get_name_file()
    
    def get_subworkflow_or_main(self):
        origin = self.get_origin()
        if(origin.get_type() in ["Main", "Subworkflow"]):
            return origin
        else:
            return origin.get_subworkflow_or_main()

    def get_rocrate_key(self, dico):
        return f"{str(self.get_file_address())[len(dico['temp_directory']):]}#{self.get_name()}"

    def get_file_address(self, short = False):
        try:
            return self.origin.get_file_address(short = short)
        except:
            return self.nextflow_file.get_file_address(short = short)
    
    def get_workflow_address(self):
        return self.origin.get_workflow_address()

    
    
    def get_workflow_code(self):
        return self.origin.get_workflow_code()
    
    def get_file_conditions(self):
        return self.origin.get_file_conditions()


    #----------------------
    #EXECUTORS
    #----------------------
    


    def get_executors(self):
        return self.executors
    
    
        

    #----------------------
    #OPERATIONS
    #----------------------

    #Method that adds operation into the lists of operations
    def add_operation(self, operation):
        self.operations.append(operation)

    #----------------------
    #INCLUDES
    #----------------------
    def get_all_includes(self):
        return self.origin.get_all_includes()

    def add_include_to_all_includes(self, include):
        self.origin.add_include_to_all_includes(include)


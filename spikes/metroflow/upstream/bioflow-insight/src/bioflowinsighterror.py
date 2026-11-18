# creating a custom exception
class BioFlowInsightError(Exception):
    """
    This is the custom BioFlow-Insight error class, from this class, errors can be made.

    Attributes:
        error: A string indicating the error message to the user
        num: An integers indicating the type of error (see below)
        origin: A "Nextflow Building Bloc" derived type object, from this the file address can be given to the user
        
    """
    def __init__(self, type, origin, *args):
        self.origin = origin
        errors = {
            "fdne": self.file_does_not_exist,
            "ube": self.upper_bound_exceeded,
            "meg": self.multiple_emits_given,
            "ueipo": self.unknown_element_in_pipe_operator,
            "tco": self.ternary_conditional_operator,
            "caease": self.channel_already_exists_as_something_else,
            "ntsnop": self.not_the_same_number_of_parameters,
            "nieie": self.none_indentified_element_in_executor,
            "ntsnopif" : self.not_the_same_number_of_parantheses_in_file,
            "ntsnocif" : self.not_the_same_number_of_curlies_in_file,
            "onotqif": self.odd_number_of_triple_quotes_in_file,
            "mmic": self.multiple_mains_in_code,
            "nomic": self.no_main_in_code,
            "estbdic": self.element_supposed_to_be_defined_in_code,
            "ftec": self.failed_to_extract_call,
            "ieic": self.illegal_element_in_code,
            "toito": self.ternary_operation_in_ternary_operation,
            "oatitew": self.operation_appears_twice_in_the_exact_way,
            "ific": self.include_found_in_code,
            "ccnbf": self.call_could_not_be_found,
            "taws": self.tuple_associated_with_something,
            "sen": self.subworkflow_emits_nothing,
            "tmctu": self.to_many_channels_to_unpack,
            "cwne": self.condition_was_not_extracted,
            "onsbdc": self.operator_not_supported_by_DSL1_conversion,
            "ep": self.empty_process,
            "meip": self.multiple_elements_in_process,
            "uiip": self.unrecognised_input_in_process,
            "cciop": self.cannot_convert_input_of_process,
            "meis": self.multiple_elements_in_subworkflow,
            "nnfid": self.no_nextflow_file_in_directory,
            "nem": self.no_emitted_matched,
            "pnip": self.processes_name_is_process,
            "uteeoe": self.unable_to_extract_end_of_element,
            "rcos": self.recursive_call_of_subworkflow,
            "creio": self.cannot_recognise_element_in_operation,
            "dinoens": self.dash_in_name_of_element_not_supported,
            "utii": self.unable_to_import_include,
            "tsnwgtmt": self.the_same_name_was_given_to_multiple_things,
            "utepo": self.unable_to_extract_pipe_operator,
            "ewlsif":self.error_with_language_server_in_file,
            "wwwd":self.workflow_written_with_DSL1,
            "udncol":self.user_defined_nb_cluster_over_limit,
            "uteeo": self.unable_to_extract_end_operation,
            "cie": self.call_in_emits,
            "cidw": self.call_in_DSL1_workflow,
            "aic":self.assignment_in_call
        }
        error = errors[type](*args)

        if(origin==None):
            super().__init__(f"{error} ~[{type}]")
        else:
            self.workflow = origin.get_workflow()
            if(self.workflow.initialise_with_both_engines):
                if(self.workflow.get_DSL()=="DSL2"):
                    error = errors['ewlsif'](*args)
                else:
                    error = errors['wwwd'](*args)
                super().__init__(f"Error in the file '{self.origin.get_file_address(short = True)}': "+error+f"")
            else:           
                super().__init__(f"Error in the file '{self.origin.get_file_address(short = True)}': "+error+f" ~[{type}]")

    def assignment_in_call(self, *args):
        assignment = args[0]
        call = args[1]
        return f"An assignment '{assignment}' has been indentified in a parameter of a call '{call}'."

    def call_in_DSL1_workflow(self, *args):
        call = args[0]
        return f"The call '{call}' has been identified in a DSL1 workflow."
    
    def call_in_emits(self, *args):
        call = args[0]
        return f"BioFlow-Insight does not support calls in the emits of subworkflow. It is due to this '{call}'."

    def unable_to_extract_end_operation(self, *args):
        operation = args[0]
        return f"Unable to extract the end of the operation: '{operation}', this often due to defining a string using backslashes '\\'."

    def user_defined_nb_cluster_over_limit(self, *args):
        return f"Something went wrong in the generation of the user-defined abstarction, there was a loop detected."

    def workflow_written_with_DSL1(self, *args):
        return f"The workflow is written Nextflow's DSL1. The Nextflow Language Server does not support this."

    def error_with_language_server_in_file(self, *args):
        return f"The Nextflow Language Server has detected an error in the file. Trying opening it with VSCode with the Nextflow plugin to fix it."
    
    def unable_to_extract_pipe_operator(self, *args):
        name = args[0]
        line = args[1]
        return f"Unable to extract the end of the pipe operator which starts with '{name}'{line}. Try writing it in a different way."


    def the_same_name_was_given_to_multiple_things(self, *args):
        name = args[0]
        return f"'{name}' was given to multiple processes, subworkflows or functions. This is not supported, please rename an element."


    def unable_to_import_include(self, *args):
        include = args[0]
        return f"Unable to import '{include}'. Make sure the includes are written correctly and that the element is defined in the imported file."

    def dash_in_name_of_element_not_supported(self, *args):
        name = args[0]
        return f"Using a dash ('-'), in the name of a Process, Subworkflow or Function is not supported:'{name}'."

    def cannot_recognise_element_in_operation(self, *args):
        element = args[0]
        operation = args[1]
        line = args[2]
        return f"Cannot recognize '{element}' in the operation '{operation}'{line}."


    def unable_to_extract_end_of_element(self, *args):
        element = args[0]
        name = args[1]
        return f"Unable to extract the end of the {element} '{name}'. Make sure each parenthese and curly which are opened are correctly closed."

    def no_nextflow_file_in_directory(self, *args):
        return "No Nextflow files ('.nf') are in the directory."


    def processes_name_is_process(self, *args):
        return "Process's name is 'process'."

    def recursive_call_of_subworkflow(self, *args):
        name = args[0]
        line = args[1]
        return f"Ths subworkflow '{name}' is called recursively{line}. This is not supported by BioFlow-Insight."


    def no_emitted_matched(self, *args):
        name = args[0]
        element = args[1]
        file = args[2]
        return f"No emitted matched with '{name}'. Should match with an emittes from '{element}'."


    def cannot_convert_input_of_process(self, *args):
        input = args[0]
        process = args[1]
        return f"Cannot convert '{input}' in the process '{process}'. Try rewritting it in a different way."

    def unrecognised_input_in_process(self, *args):
        input = args[0]
        process = args[1]
        return f"Do not recognise the input '{input}' in the process '{process}'. Try rewritting it in a different way."


    def multiple_elements_in_subworkflow(self, *args):
        element = args[0]
        subworkflow = args[1]
        return f"Multiple '{element}' were found in the subworkflow '{subworkflow}'."


    def multiple_elements_in_process(self, *args):
        element = args[0]
        process = args[1]
        return f"Multiple '{element}' were found in the process '{process}'."


    def empty_process(self, *args):
        process = args[0]
        return f"The process '{process}' is an empty process."


    def operator_not_supported_by_DSL1_conversion(self, *args):
        operator = args[0]
        return f'The operator "{operator}" is not supported by the DSL1 Conversion.'
            
    def condition_was_not_extracted(self, *args):
        condition = args[0]
        line = args[1]
        return f"The condition '({condition}' was not extracted correctly{line}. It's perhaps due to the jump line in the condition. Make sure the condition follows the correct syntaxe."

    def to_many_channels_to_unpack(self, *args):
        sub = args[0]
        line = args[1]
        return f"To much to unpack : The subworkflow '{sub}' emits over one channel in a operation{line}."

    def subworkflow_emits_nothing(self, *args):
        sub = args[0]
        line = args[1]
        return f"The subworkflow '{sub}' doesn't emit anything. It is given to an operation{line}."


    def tuple_associated_with_something(self, *args):
        type_of_element = args[0]
        line = args[1]
        return f"A tuple is associated with a {type_of_element}{line}. BioFlow-Insight doesn't support this (see specification list), try defining the operation in a different way."

    def call_could_not_be_found(self, *args):
        name_called = args[0]
        operation = args[1]
        line = args[2]
        return f"The call for '{name_called}' coudn't be found, before its use in the operation '{operation}'{line}. Either because the call wasn't made before the operation or that the element it is calling doesn't exist."

    def include_found_in_code(self, *args):
        include = args[0]
        part = args[1]
        return f"An include ('{include}') was found in the {part}. Try putting the include at the start of the file."

    def operation_appears_twice_in_the_exact_way(self, *args):
        code = args[0]
        return f'Operation "{code}" appears twice in the workflow in the exact same way. BioFlow-Insight cannot rewrite the workflow then, try slighly changing how one of the executors is defined.'

    def ternary_operation_in_ternary_operation(self, *args):
        line = args[0]
        return f"Detected a multi ternary operation (a ternary operation in a ternary operation){line}. BioFlow-Insight does not support this, try defining it in a different way."
        

    def illegal_element_in_code(self, *args):
        bit_of_code = args[0]
        line = args[1]
        return f"The presence of '{bit_of_code}' is detected{line}."
        

    def failed_to_extract_call(self, *args):
        line = args[0]
        return f"Failed to extract the call or operation{line}. Try rewriting it in a simplified version."

    def element_supposed_to_be_defined_in_code(self, *args):
        name = args[0]
        address = args[1]
        return f"'{name}' is expected to be defined in the '{address}', but it could not be found."

    def no_main_in_code(self, *args):
        return f"A 'main' workflow was not found in the code."

    def multiple_mains_in_code(self, *args):
        return f"Found multiple 'main' in code."

    def not_the_same_number_of_parantheses_in_file(self, *args):
        return f"Not the same number of opening and closing parentheses '()' in the file."
    
    def not_the_same_number_of_curlies_in_file(self, *args):
        return f"Not the same number of opening and closing curlies '{'{}'}' in the file."
    
    def odd_number_of_triple_quotes_in_file(self, *args):
        return f"An odd number of '\"\"\"' was found in the code."



    def none_indentified_element_in_executor(self, *args):
        first_thing_called = args[0]
        pot = args[1]
        line = args[2]
        return f"'{first_thing_called}' is neither a process, subworkflow or an operator. In the executor '{pot}'{line}."


    def not_the_same_number_of_parameters(self, *args):
        name = args[0]
        line = args[1]
        return f"Not the same number of parameters given as input for the {name}{line}."

    def channel_already_exists_as_something_else(self, *args):
        name = args[0]
        line = args[1]
        return f"'{name}' is trying to be created as a channel{line}. This identifier already exists as a process, a function or a subworkflow in the nextflow file."


    def ternary_conditional_operator(self, *args):
        line = args[0]
        return f"A ternary conditional operator was used with a tuple{line}."

    def file_does_not_exist(self, *args):
        line = args[0]
        address = args[1]
        return f"Something went wrong in an include{line}. No such file: '{address}'."
    
    def upper_bound_exceeded(self, *args):
        reason = args[0]
        return f"The WHILE_UPPER_BOUND was exceeded. {reason}."
    
    def multiple_emits_given(self, *args):
        emit = args[0]
        element = args[1]
        return f"One channel was expected in the emit '{emit}'. Even though multiple emits are defined for the {element}."

    def unknown_element_in_pipe_operator(self, *args):
        thing = args[0]
        element = args[1]
        return f"Don't know how to handle '{thing}' in a pipe operator{element}. Try using the recommended operator composition."







            
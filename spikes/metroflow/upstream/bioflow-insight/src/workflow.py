# Import dependencies
# Local
from .nextflow_file import Nextflow_File
from .ro_crate import RO_Crate
from .condition import Condition
from .DBfile import DBfile
from .outils import hsl_to_rgb, jaccard, get_basic_blocks, read_config_with_includes, extract_profiles_config, profile_enables_scope, uses_pipe_operator as code_uses_pipe_operator
from . import constant
from .outils_graph import enrich_json_with_positions
from .bioflowinsighterror import BioFlowInsightError
from .graph import Graph
from .language_server import Language_Server
from .abstraction import Abstraction
from .history import History

# Outside packages
import os
import re
import json
from pathlib import Path
import glob
import ctypes
import subprocess
from datetime import datetime


def get_object(address):
    address = int(re.findall(r"\dx\w+", address)[0], base=16)
    return ctypes.cast(address, ctypes.py_object).value




class Workflow:
    """
    This is the main workflow class, from this class, workflow analysis can be done.
    After analysis, workflow structure reconstruction can be done.

    Attributes:
        file: A string indicating the address to the workflow main or the directory containing the workflow
        display_info: A boolean indicating if the analysis information should be printed
        output_dir: A string indicating where the results will be saved
        name: A string indicating the name of the workflow
    """

    def __init__(
        self, file, display_info=True, output_dir='./results', name=None, engines=['nls', 'bioflow'], is_workflow=True, commit_2_set = ""
    ):
        self.commit_2_set = commit_2_set
        if(commit_2_set!=""):
            if(".nf" in file):
                workflow_directory = '/'.join(file.split('/')[:-1])
            else:
                workflow_directory = file
            current_path= os.getcwd()
            os.chdir(Path(os.path.normpath(workflow_directory)))
            os.system(f"git checkout -f {commit_2_set} >/dev/null 2>&1")
            os.chdir(current_path)

        # Getting the main nextflow file
        if not os.path.isfile(file):
            nextflow_files = glob.glob(f'{file}/*.nf')
            if len(nextflow_files) == 0:
                raise BioFlowInsightError("nnfid", None)
            txt = ""
            # Try to read the main.nf file -> if this cannot be found then the first nextflow file is used
            try:
                file = file + "/main.nf"
                with open(file, 'r') as f:
                    txt = f.read()
            except:
                None
                # raise BioFlowInsightError("No 'main.nf' file found at the root of the prohject")
            if txt == "":
                if len(nextflow_files) == 1:
                    file = nextflow_files[0]
                    with open(file, 'r') as f:
                        txt = f.read()
                else:
                    # If there are multiple files and no main -> we just choose one at random
                    #nextflow_files.sort()
                    file = nextflow_files[0]
                    with open(file, 'r') as f:
                        txt = f.read()
                    # raise BioFlowInsightError("Multiple Nextflow files found at the root with no 'main.nf' file: I don't know which one to select")

        self.is_workflow = is_workflow
        self.file = file
        self.display_info = display_info
        self.output_dir = Path(output_dir)
        self.nextflow_files = []
        self.workflow_directory = '/'.join(file.split('/')[:-1])
        self.name = name
        self.graph = None
        self.conditions_2_ignore = []
        self.ternary_operation_dico = {}
        self.map_element_dico = {}
        self.language_server = None
        self.all_conditions_language_server = {}
        self.engines = ['nls', 'bioflow']
        self.initialise_with_both_engines = False
        if is_workflow:
            OG_file = Nextflow_File(self.file, workflow=self, first_file=True)
            self.DSL = OG_file.find_DSL()

            if self.display_info:
                print(f"Workflow is written in {self.DSL}")
        self.create_empty_results()
        self.cycle_in_workflow = False
        self.alias_2_tools = {}
        self.scripts_2_tools = {}
        self.condition_abstraction = None
        self.dominator_abstraction = None
        self.user_defined_abstraction = None
        self.parallel_abstraction = None
        self.is_sp_graph = None
        self.element_2_index = {}
        self.history = None

    def generate_metro_map_from_json(self):
        if not self.is_workflow:
            import shutil

            shutil.copyfile(self.file, self.output_dir / 'graphs/process_dependency_graph.json')
            self.graph = Graph(self)
            self.graph.generate_dot_from_json(self.file)
            self.enrich_json_files_with_positions()
            shutil.copyfile(self.output_dir / 'graphs/process_dependency_graph.json', self.output_dir / 'graphs/metro_map.json')
        else:
            raise Exception('It is a workflow and not a json file')

    def purge(self):
        self.language_server = None
        self.nextflow_files = []
        OG_file = Nextflow_File(self.file, workflow=self, first_file=True)

    def get_element_2_index(self, ele):
        try:
            temp = self.element_2_index[ele]
        except:
            self.element_2_index[ele] = 0
        self.element_2_index[ele] += 1
        return self.element_2_index[ele]

    def get_name(self):
        if self.name != None:
            return self.name
        else:
            return self.get_root_directory().split('/')[-2]

    def get_workflow_directory(self):
        return self.workflow_directory

    def create_empty_results(self):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.output_dir / 'debug', exist_ok=True)
        os.makedirs(self.output_dir / 'graphs', exist_ok=True)

        with open(self.output_dir / "debug" / "operations.nf", 'w') as file:
            pass
        with open(self.output_dir / "debug" / "calls.nf", 'w') as file:
            pass
        with open(self.output_dir / "debug" / "operations_in_call.nf", 'w') as file:
            pass

    def get_history(self):
        if not self.history:
            hist = History(self)
            hist.initialise()
            self.history = hist
            return self.history.get_values()
        else:
            return self.history.get_values()

    def get_date_dev_who_created(self, name_ele, type_ele):
        hist = History(self)
        val = hist.get_date_dev_who_created(name_ele, type_ele)
        if(self.commit_2_set!=""):
            current_path= os.getcwd()
            os.chdir(Path(os.path.normpath(self.workflow_directory)))
            os.system(f"git checkout -f {self.commit_2_set} >/dev/null 2>&1")
            os.chdir(current_path)
        return val

    #Returns the date (datetime) of the last commit of the workflow (None if not a git repository)
    def get_last_commit(self):
        try:
            date = subprocess.check_output(["git", "-C", os.path.normpath(self.workflow_directory), "log", "-1", "--format=%cI"], stderr=subprocess.DEVNULL, text=True).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
        if(date==""):
            return None
        return datetime.fromisoformat(date)

    #Returns the address of the nextflow.config at the root of the project
    def get_nextflow_config_address(self):
        return os.path.join(self.get_root_directory(), "nextflow.config")

    #Checks if there is a nextflow.config file at the root of the project
    def has_nextflow_config(self):
        return os.path.isfile(self.get_nextflow_config_address())

    def get_citation_cff_address(self):
            return os.path.join(self.get_root_directory(), "CITATION.cff")
    
    def has_citation_cff(self):
        return os.path.isfile(self.get_citation_cff_address())

    #Returns the profiles defined in the nextflow.config (and the configs it includes) -> {name_profile: code_profile}
    def get_config_profiles(self):
        if(not self.has_nextflow_config()):
            return {}
        code = read_config_with_includes(self.get_nextflow_config_address(), self.get_root_directory())
        return extract_profiles_config(code)

    #Checks if a profile is named after one of the keywords or if it enables one of the scopes
    def has_profile(self, keywords, scopes, extra_patterns = []):
        for name, code in self.get_config_profiles().items():
            if(any(keyword in name.lower() for keyword in keywords)):
                return True
            if(profile_enables_scope(code, scopes)):
                return True
            if(any(re.search(pattern, code) for pattern in extra_patterns)):
                return True
        return False

    #Checks if a docker profile is defined in the nextflow.config
    def has_docker_profile(self):
        return self.has_profile(["docker"], ["docker"])

    #Checks if a conda profile is defined in the nextflow.config
    def has_conda_profile(self):
        #'process.conda = ...' or 'process { conda = ... }' (older way of using conda)
        return self.has_profile(["conda", "mamba"], ["conda"], [r"\bprocess\s*\.\s*conda\s*=", r"\bprocess\s*\{[^}]*\bconda\s*="])

    #Checks if a singularity or apptainer profile is defined in the nextflow.config
    def has_singularity_profile(self):
        return self.has_profile(["singularity", "apptainer"], ["singularity", "apptainer"])

    #Returns all the executors (calls and operations) of the workflow (only for DSL2)
    def get_all_executors_DSL2(self):
        if(self.get_DSL()!="DSL2"):
            return []
        if(not self.is_initialised_with_bioflow()):
            self.initialise_with_bioflow()
        return self.get_workflow_main().get_all_executors_in_workflow()

    #Checks if the workflow uses the pipe operator '|' in one of its calls/operations (only for DSL2)
    def uses_pipe_operator(self):
        for executor in self.get_all_executors_DSL2():
            if(code_uses_pipe_operator(executor.get_code(get_OG=True))):
                return True
        return False

    #Checks if the workflow follows the standard nf-core file structure template (only for DSL2)
    def follows_nf_core_structure(self):
        if(self.get_DSL()!="DSL2"):
            return False
        root = self.get_root_directory()
        return all(os.path.isdir(os.path.join(root, folder)) for folder in ["workflows", "subworkflows", "modules"])

    #Returns the codes of all the emits used in the workflow (e.g. 'PROCESS.out[0]', 'PROCESS.out.channel')
    def get_all_emits_DSL2(self):
        emits, seen = [], set()
        def explore(ele):
            if(ele in seen):
                return
            seen.add(ele)
            if(ele.get_type()=="Emitted"):
                emits.append(ele.get_code())
            elif(ele.get_type()=="Operation"):
                for o in ele.get_origins()+ele.get_gives():
                    explore(o)
            elif(ele.get_type()=="Call"):
                for p in ele.get_parameters():
                    explore(p)
        for executor in self.get_all_executors_DSL2():
            explore(executor)
        return emits

    #Checks if the workflow uses numbered outputs, e.g. '.out[0]' (only for DSL2)
    def uses_numbered_outputs(self):
        return any(re.search(constant.EMIT_TAB, emit) for emit in self.get_all_emits_DSL2())

    #Checks if the workflow uses named outputs, e.g. '.out.my_channel' (only for DSL2)
    def uses_named_outputs(self):
        for emit in self.get_all_emits_DSL2():
            for match in re.finditer(constant.EMIT_NAME, emit):
                #'.out.map{...}' is an operator applied on the outputs, not a named output
                if(match.group(3) not in constant.LIST_OPERATORS):
                    return True
        return False

    #Returns the Nextflow files constituting the workflow (included files are only discovered during the analysis)
    def get_all_nextflow_files(self):
        if(not self.is_initialised_with_bioflow()):
            self.initialise_with_bioflow()
        return self.nextflow_files

    #Returns the number of Nextflow files constituting the workflow
    def get_number_of_files(self):
        return len(set(file.get_file_address() for file in self.get_all_nextflow_files()))

    #Returns the total number of lines (raw count) of the Nextflow files constituting the workflow
    def get_number_of_lines_of_code(self):
        total = 0
        for address in set(file.get_file_address() for file in self.get_all_nextflow_files()):
            with open(address, 'r') as f:
                total += sum(1 for _ in f)
        return total

    def get_cycle_status(self):
        return self.cycle_in_workflow

    def get_root_directory(self):
        first_file = self.get_first_file()
        return '/'.join(str(first_file.get_file_address()).split('/')[:-1]) + "/"

    def get_conditions_2_ignore(self):
        return self.conditions_2_ignore

    def get_output_dir(self):
        return Path(self.output_dir)

    def get_DSL(self):
        return self.DSL

    def get_display_info_bool(self):
        return self.display_info

    def set_DSL(self, DSL):
        self.DSL = DSL

    def add_2_rocrate(self, dico, prov_ro_crate):
        self.get_workflow_main().add_2_rocrate(dico, prov_ro_crate)

    def get_first_file(self):
        for file in self.nextflow_files:
            if file.first_file:
                return file

    def get_workflow_main(self):
        return self.get_first_file().main

    def add_nextflow_file_2_workflow(self, nextflow_file):
        self.nextflow_files.append(nextflow_file)
        self.nextflow_files = list(set(self.nextflow_files))

    def get_nextflow_file(self, address):
        for file in self.nextflow_files:
            if file.get_file_address() == Path(os.path.normpath(address)):
                return file
        return None

    def print_citation(self):
        if self.display_info:
            citation = """\nTo cite BioFlow-Insight, please use the following publication:
George Marchment, Bryan Brancotte, Marie Schmit, Frédéric Lemoine, Sarah Cohen-Boulakia, BioFlow-Insight: facilitating reuse of Nextflow workflows with structure reconstruction and visualization, NAR Genomics and Bioinformatics, Volume 6, Issue 3, September 2024, lqae092, https://doi.org/10.1093/nargab/lqae092"""
            print(citation)

    def is_initialised_with_bioflow(self):
        return self.get_workflow_main() != None

    def initialise_with_bioflow(self):
        """Method that initialises the analysis of the worflow

        Keyword arguments:

        """
        # At this point there should only be one nextflow file
        if len(self.nextflow_files) == 1:
            self.nextflow_files[0].initialise(language_server=None)
        else:
            raise Exception(
                "This souldn't happen. There are multiple Nextflow files composing the workflow before the analysis has even started."
            )

        self.print_citation()

        if self.graph == None:
            self.graph = Graph(self)

        with open(self.get_output_dir() / "engine.txt", "w") as outfile:
            outfile.write("bioflow")

    def initialise_with_language_server(self):
        self.print_citation()
        if self.get_DSL() == "DSL2":
            self.language_server = Language_Server()
            if len(self.nextflow_files) == 1:
                try:
                    self.nextflow_files[0].initialise(language_server=self.language_server)
                except BioFlowInsightError as b:
                    raise b
                except:
                    raise BioFlowInsightError("ewlsif", None)
            else:
                raise Exception(
                    "This souldn't happen. There are multiple Nextflow files composing the workflow before the analysis has even started."
                )
            self.graph = Graph(self)
            with open(self.get_output_dir() / "engine.txt", "w") as outfile:
                outfile.write("NLS")
        else:
            raise BioFlowInsightError("wwwd", None)

    def get_link_dico_processes(self, bool_get_object):
        self.graph.initialise()
        return self.graph.get_link_dico_process(bool_get_object=bool_get_object)

    def get_structure(self):
        dico = {}
        dico['nodes'] = []
        dico['edges'] = []
        dico['subworkflows'] = {}

        if self.language_server == None:
            if self.get_DSL() == "DSL1":
                main = self.get_workflow_main()
                if main != None:
                    return main.get_structure(dico)
            elif self.get_DSL() == "DSL2":
                main = self.get_workflow_main()
                if main != None:
                    return main.get_structure(dico)
                else:
                    return dico
                # return self.get_structure_DSL2(dico=dico, start = True)
            else:
                raise Exception(f"The workflow's DSL is '{self.DSL}' -> I don't know what this is!")
        else:
            structure = self.get_first_file().get_structure(dico, element="")
            structure["id"] = str(self.get_first_file())
            return structure

    #################
    #    GRAPHS
    #################
    def get_metadata_specification_graph(self):
        metadata = self.graph.get_stats_graph_by_hand(dico_2_analyse="specification")
        with open(f"{self.get_output_dir()}/graphs/metadata_specification.json", 'w') as output_file:
            json.dump(metadata, output_file, indent=4)
        return metadata

    def get_metadata_process_dependency_graph(self):
        metadata = self.graph.get_stats_graph_by_hand(dico_2_analyse="process_dependency")
        with open(f"{self.get_output_dir()}/graphs/metadata_process_dependency.json", 'w') as output_file:
            json.dump(metadata, output_file, indent=4)
        return metadata

    def generate_specification_graph(self, render_graphs=True):
        self.graph.initialise()
        self.graph.get_specification_graph(render_graphs=render_graphs)
        self.enrich_json_files_with_positions()

    def generate_process_dependency_graph(self, render_graphs=True, with_conditions = False):
        self.graph.initialise()
        self.graph.render_process_dependency_graph(render_graphs=render_graphs, with_conditions = with_conditions)
        self.enrich_json_files_with_positions()

    def get_process_dependency_graph_dico(self):
        self.graph.initialise()
        self.graph.render_process_dependency_graph(render_graphs=False)
        return self.graph.get_process_dependency_graph()

    def generate_all_graphs(self, render_graphs=True):
        self.generate_specification_graph(render_graphs=render_graphs)
        self.generate_process_dependency_graph(render_graphs=render_graphs)
        self.enrich_json_files_with_positions()

    # This function takes the json files and searches for the corrresponding dot pos files
    # And adds the information regarding the position of the nodes
    def enrich_json_files_with_positions(self):
        jsons = glob.glob(f'{self.get_output_dir()/"graphs"}/process_dependency_graph*.json', recursive=False)
        for file in jsons:
            enrich_json_with_positions(file)

    # Method that checks if a given graph sepcification is an isomorphism with the workflows
    def check_if_json_equal_to_full_structure(self, file):
        return self.graph.check_if_json_equal_to_full_structure(file)

    def initialise_conditions(self, get_on_process_dependency):
        conditions = self.get_most_influential_conditions(get_on_process_dependency)
        for c in conditions:
            c.get_minimal_product_of_sums()

    def get_condition_abstraction(self, get_on_process_dependency):
        self.condition_abstraction = Abstraction(workflow=self, get_on_process_dependency=get_on_process_dependency)
        condition_abtsraction = self.condition_abstraction.get_condition_abtsraction()
        return condition_abtsraction

    def get_dominator_abstraction(self, get_on_process_dependency):
        self.dominator_abstraction = Abstraction(workflow=self, get_on_process_dependency=get_on_process_dependency)
        dominator_abstraction = self.dominator_abstraction.get_dominator_abstraction()
        return dominator_abstraction

    def get_parallel_abstraction(self, get_on_process_dependency):
        self.parallel_abstraction = Abstraction(workflow=self, get_on_process_dependency=get_on_process_dependency)
        parallel_abstraction = self.parallel_abstraction.get_parallel_abstraction()
        return parallel_abstraction

    def get_user_defined_abstraction(self, get_on_process_dependency):
        self.user_defined_abstraction = Abstraction(workflow=self, get_on_process_dependency=get_on_process_dependency)
        user_defined_abstraction = self.user_defined_abstraction.get_user_defined_abstraction()
        if get_on_process_dependency:
            stats = self.graph.get_stats_graph_by_hand(dico_2_analyse="process_dependency")
        else:
            stats = self.graph.get_stats_graph_by_hand(dico_2_analyse="specification_graph")
        tree = user_defined_abstraction
        if stats["subworkflows"] < len(tree.get_groups(dico={})):
            raise BioFlowInsightError('udncol', self.get_workflow_main())
        return user_defined_abstraction

    def get_relevant_abstraction(self, relevant_processes, get_on_process_dependency):
        self.relevant_abstraction = Abstraction(workflow=self, get_on_process_dependency=get_on_process_dependency)
        relevant_abstraction = self.relevant_abstraction.get_relevant_abstraction(relevant_processes)
        return relevant_abstraction

    def get_number_of_nodes_without_clouds(self):
        return self.condition_abstraction.get_number_of_nodes_without_clouds()

    def get_number_split_subworkflows(self, tree):
        number_split_subworkflows = 0
        subworkflows = self.get_operations_and_processes_per_subworkflows()
        nb_subworkflows = len(subworkflows)
        created_groups = tree.get_groups({})
        dico_split = {}

        def get_smallest_set(a, b):
            if len(a) < len(b):
                return a
            return b

        for sub in subworkflows:
            group_subworkflow = set(subworkflows[sub])
            split_subworkflow = False
            nb_nodes = len(group_subworkflow)
            nb_processes = 0
            for ele in group_subworkflow:
                if ele.get_type() == "Process":
                    nb_processes += 1
            dico_split[str(sub)] = {}
            dico_split[str(sub)]['split'] = False
            dico_split[str(sub)]['processes'] = nb_processes
            dico_split[str(sub)]['nodes'] = nb_nodes
            for c in created_groups:
                cluster = set(created_groups[c])
                # If the intersection of the two groups aren't equal
                if group_subworkflow.intersection(cluster) != set():
                    # Verify that one group isn't including in the other
                    if group_subworkflow.intersection(cluster) != get_smallest_set(group_subworkflow, cluster):
                        split_subworkflow = True
                        break
            if split_subworkflow:
                number_split_subworkflows += 1
                dico_split[str(sub)]['split'] = True

        return number_split_subworkflows, nb_subworkflows, dico_split

    def get_similarity_subworkflows_clusters(self, tree, get_on_process_dependency=True):
        subworkflows = self.get_operations_and_processes_per_subworkflows()
        if tree.get_on_process_dependency:
            subworkflows_filtered = {}
            for sub in subworkflows:
                processes = []
                for ele in subworkflows[sub]:
                    if ele.get_type() == "Process":
                        processes.append(ele)
                subworkflows_filtered[sub] = processes
            subworkflows = subworkflows_filtered
        nb_subworkflows = len(subworkflows)
        created_groups = tree.get_groups({})

        dico_similarity_subworkflows = {}
        for sub in subworkflows:
            group_subworkflow = set(subworkflows[sub])
            nb_processes = 0
            sub_id = str(sub)
            for ele in group_subworkflow:
                if ele.get_type() == "Process":
                    nb_processes += 1
            cond = True
            if get_on_process_dependency:
                cond = nb_processes != 0
            if cond:
                dico_similarity_subworkflows[sub_id] = {}
                dico_similarity_subworkflows[sub_id]['processes'] = nb_processes
                dico_similarity_subworkflows[sub_id]['nodes'] = len(group_subworkflow)
                dico_similarity_subworkflows[sub_id]['sub_in_module'] = False
                dico_similarity_subworkflows[sub_id]['module_in_sub'] = False

                tab_similarity = []
                largest_module_in_sub, smallest_module_that_sub_is_in = {}, -1
                cluster_with_max_similarity, max_similarity = None, -1
                for c in created_groups:
                    cluster = set(created_groups[c])
                    tab_similarity.append(jaccard(group_subworkflow, cluster))
                    if(jaccard(group_subworkflow, cluster)>max_similarity):
                        max_similarity = jaccard(group_subworkflow, cluster)
                        cluster_with_max_similarity = cluster
                    #Get largest module_in_sub
                    if( set(cluster) <= set(group_subworkflow) and len(cluster)>len(largest_module_in_sub)):
                        largest_module_in_sub = cluster
                        dico_similarity_subworkflows[sub_id]['module_in_sub'] = True
                    if( set(group_subworkflow) <= set(cluster) and (smallest_module_that_sub_is_in==-1 or len(cluster)<len(smallest_module_that_sub_is_in))):
                        smallest_module_that_sub_is_in = cluster
                        dico_similarity_subworkflows[sub_id]['sub_in_module'] = True

                dico_similarity_subworkflows[sub_id]["similarity"] = (
                    max(tab_similarity) if len(tab_similarity) > 0 else 0
                )
                
                dico_similarity_subworkflows[sub_id]['nb_processes_which_break_module_property'] = None
                dico_similarity_subworkflows[sub_id]['percentage_of_subworklows_processes_which_break_module_property'] = None
                if(largest_module_in_sub!={}):
                    dico_similarity_subworkflows[sub_id]['nb_processes_which_break_module_property'] = len(set(group_subworkflow)) - len(largest_module_in_sub.intersection(set(group_subworkflow)))
                    dico_similarity_subworkflows[sub_id]['percentage_of_subworklows_processes_which_break_module_property'] = (len(set(group_subworkflow)) - len(largest_module_in_sub.intersection(set(group_subworkflow))))/nb_processes*100
                
                dico_similarity_subworkflows[sub_id]['nb_processes_to_add_to_form_full_property'] = None
                dico_similarity_subworkflows[sub_id]['percentage_of_subworklows_processes_to_add_to_form_full_property'] = None
                if(smallest_module_that_sub_is_in!=-1):
                    dico_similarity_subworkflows[sub_id]['nb_processes_to_add_to_form_full_property'] = len(set(smallest_module_that_sub_is_in)) - len(smallest_module_that_sub_is_in.intersection(set(group_subworkflow)))
                    dico_similarity_subworkflows[sub_id]['percentage_of_subworklows_processes_to_add_to_form_full_property'] = (len(set(smallest_module_that_sub_is_in)) - len(smallest_module_that_sub_is_in.intersection(set(group_subworkflow))))/nb_processes*100

                def get_edit_distance(cluster, sub):
                    inter = set(cluster).intersection(set(sub))
                    nb_to_remove = len(sub) - len(inter)
                    nb_to_add = len(set(cluster).difference(inter))
                    return nb_to_add+nb_to_remove

                if(max_similarity>-1):
                    dico_similarity_subworkflows[sub_id]['closest_edit_distance'] = get_edit_distance(cluster_with_max_similarity, group_subworkflow)
                else:
                    dico_similarity_subworkflows[sub_id]['closest_edit_distance'] = -1

        dico_similarity_clusters = {}
        for c in created_groups:
            cluster = set(created_groups[c])
            cluster_id = str(c)
            nb_processes = 0
            for ele in cluster:
                if ele.get_type() == "Process":
                    nb_processes += 1
            dico_similarity_clusters[cluster_id] = {}
            dico_similarity_clusters[cluster_id]['processes'] = nb_processes
            dico_similarity_clusters[cluster_id]['nodes'] = len(cluster)
            tab_similarity = []
            for sub in subworkflows:
                group_subworkflow = set(subworkflows[sub])
                tab_similarity.append(jaccard(group_subworkflow, cluster))
            dico_similarity_clusters[cluster_id]["similarity"] = max(tab_similarity) if len(tab_similarity) > 0 else 0

        return dico_similarity_subworkflows, dico_similarity_clusters

    def get_metro_map_json(self, render_dot=True, type_metro="regular"):

        self.generate_process_dependency_graph(render_graphs=render_dot, with_conditions = True)
        self.enrich_json_files_with_positions()
        json_file = glob.glob(f'{self.get_output_dir()/"graphs"}/process_dependency_graph.json', recursive=False)[0]
        with open(json_file, 'r') as JSON:
            full_workflow = json.load(JSON)
        metro_map_dico = {"nodes": [], "edges": [], "subworkflows": {}}

        def fill_metro_map(dico_wf, metro_map, ids_2_homogene_ids, current_sub=[], depth_sub_max=0):

            ids_added = []
            for node in dico_wf["nodes"]:
                process = get_object(node['id'])
                node['id'] = ids_2_homogene_ids[str(node['id'])]
                # node["position"]['x'] = str(1.6*float(node["position"]['x']))
                # node["position"]['y'] = str(1.6*float(node["position"]['y']))
                node["position"]['x'] = node["position"]['x']
                node["position"]['y'] = node["position"]['y']
                node['code'] = process.get_code()
                short_adress = process.get_file_address(short=True)
                if short_adress[0] == "/":
                    short_adress = short_adress[1:]
                node['file_ref'] = f"({short_adress})"
                for ele in ["artificial", "shape", "xlabel", "fillcolor"]:
                    try:
                        node.pop(ele)
                    except: 
                        None
                if node["id"] not in ids_added:
                    ids_added.append(node["id"])
                    metro_map["nodes"].append(node)
            for edge in dico_wf["edges"]:
                edge['A'] = ids_2_homogene_ids[str(edge['A'])]
                edge['B'] = ids_2_homogene_ids[str(edge['B'])]
                edge['id'] = edge['A'] + ' -> ' + edge['B']
                for ele in ["label"]:
                    edge.pop(ele)
                metro_map["edges"].append(edge)
            for sub in dico_wf["subworkflows"]:

                def get_all_nodes_in_sub(dico, nodes):
                    for node in dico["nodes"]:
                        nodes.append(ids_2_homogene_ids[str(node['id'])])
                    for sub in dico["subworkflows"]:
                        nodes = get_all_nodes_in_sub(dico["subworkflows"][sub], nodes)
                    return nodes

                all_nodes = get_all_nodes_in_sub(dico_wf['subworkflows'][sub], [])
                # name = "_".join(sub.split("_")[:-1])
                name = sub


                h = [
                    58,  # yellow
                    100,  # green
                    241,  # dark blue
                    0,  # red
                    177,  # light blue
                    37,  # oragne
                    281,  # purple
                ]
                s = 90
                l_min, l_max = 85, 99
                if all_nodes != []:
                    norm = l_max - l_min
                    if depth_sub_max == 0:
                        l = l_min
                    else:
                        l = l_max - (len(current_sub) / depth_sub_max) ** 3 * norm
                        l = max(l, 99 - len(current_sub) * 4)
                    if(len(all_nodes)>1 or type_metro == "regular"):


                        sub_dico = dico_wf['subworkflows'][sub]
                        file_ref = ""
                        if 'id' in sub_dico:
                            short_adress = get_object(sub_dico['id']).get_file_address(short=True)
                            if short_adress[0] == "/":
                                short_adress = short_adress[1:]
                            file_ref = f"({short_adress})"

                        metro_map["subworkflows"]['.'.join(current_sub + [sub])] = {
                            "nodes": all_nodes,
                            "label": name.split("_$$_")[0],
                            "code": sub_dico.get('code', ""),
                            "condition": sub_dico.get('condition'),
                            "file_ref": file_ref,
                        }


                fill_metro_map(
                    dico_wf['subworkflows'][sub], metro_map, ids_2_homogene_ids, current_sub + [sub], depth_sub_max
                )



        def get_sub_max(dico_wf, depth_sub_max):
            temp = depth_sub_max
            for sub in dico_wf["subworkflows"]:
                depth = get_sub_max(dico_wf["subworkflows"][sub], depth_sub_max + 1)
                if depth > temp and len(dico_wf["subworkflows"][sub]['nodes'])>1:
                    temp = depth
            return temp

        def get_ids_2_homogene_ids(dico_wf, ids_2_homogene_ids, current_sub):
            for node in dico_wf["nodes"]:
                process = get_object(node['id'])
                new_name = ".".join(current_sub) + "." + str(process.get_alias())
                #Make the name unique if another process already has it
                while new_name in ids_2_homogene_ids.values():
                    new_name+="1"
                ids_2_homogene_ids[str(process)] = new_name
            for sub in dico_wf["subworkflows"]:
                get_ids_2_homogene_ids(dico_wf["subworkflows"][sub], ids_2_homogene_ids, current_sub + [str(sub)])
            return ids_2_homogene_ids

        ids_2_homogene_ids = get_ids_2_homogene_ids(full_workflow, {}, [])
        file_name = "metro_map"
        if type_metro == "regular":
            None
        elif type_metro == "condition":
            if(not self.condition_abstraction):
                self.get_condition_abstraction(get_on_process_dependency = True)
            full_workflow = self.condition_abstraction.get_workflow_with_subworkflows(full_workflow)
            file_name +="_condition"
        elif type_metro == "dominator":
            if(not self.dominator_abstraction):
                self.get_dominator_abstraction(get_on_process_dependency = True)
            full_workflow = self.dominator_abstraction.get_workflow_with_subworkflows(full_workflow)
            file_name +="_dominator"
        elif type_metro == "parallel":
            if(not self.parallel_abstraction):
                self.get_parallel_abstraction(get_on_process_dependency = True)
            full_workflow = self.parallel_abstraction.get_workflow_with_subworkflows(full_workflow)
            file_name +="_parallel"
        # elif(type_metro == "relevant"):
        #    full_workflow = self.relevant_abstraction.get_workflow_with_subworkflows(full_workflow)

        depth_sub_max = get_sub_max(full_workflow, -1)

        fill_metro_map(full_workflow, metro_map_dico, ids_2_homogene_ids, [], depth_sub_max)

        # Sorting the list of the metro dictionnary such that
        metro_map_dico["nodes"] = sorted(metro_map_dico["nodes"], key=lambda d: d['id'])
        metro_map_dico["edges"] = sorted(metro_map_dico["edges"], key=lambda d: d['id'])

        with open(f"{self.get_output_dir()}/graphs/{file_name}.json", 'w') as output_file:
            json.dump(metro_map_dico, output_file, indent=4)
        return metro_map_dico

    # The generation of the Ro-Crate has been valid from
    # - https://ro-crate.ldaca.edu.au/explorer, and
    # - https://github.com/crs4/rocrate-validator (with the workflow-ro-crate-1.0 profile)
    def get_rocrate(
        self,
        display_info=False,
        personnal_acces_token=None,
        datePublished=None,
        description=None,
        license=None,
        authors=None,
        publisher=None,
        keywords=None,
        producer=None,
    ):
        self.rocrate = RO_Crate(
            self,
            prov_ro_crate=False,
            display_info=display_info,
            personnal_acces_token=personnal_acces_token,
            datePublished=datePublished,
            description=description,
            license=license,
            authors=authors,
            publisher=publisher,
            keywords=keywords,
            producer=producer,
        )
        self.rocrate.initialise()

    def get_prov_rocrate(
        self,
        display_info=False,
        personnal_acces_token=None,
        datePublished=None,
        description=None,
        license=None,
        authors=None,
        publisher=None,
        keywords=None,
        producer=None,
    ):
        self.rocrate = RO_Crate(
            self,
            prov_ro_crate=True,
            display_info=display_info,
            personnal_acces_token=personnal_acces_token,
            datePublished=datePublished,
            description=description,
            license=license,
            authors=authors,
            publisher=publisher,
            keywords=keywords,
            producer=producer,
        )
        self.rocrate.initialise()

    def get_DBfile(self):
        file = DBfile(self)
        file.initialise()

    # Returns a dico of number of executors per each condition
    # For example : {condition1: [exe1, exe2, exe3], condition2: [exe3], condition:[exe1]}
    def get_most_influential_conditions(self, get_on_process_dependency):
        def uniform_conditions(dico):
            condition_in_commun = {}
            for cond in dico:
                try:
                    temp = condition_in_commun[cond.get_value()]
                except:
                    condition_in_commun[cond.get_value()] = []
                condition_in_commun[cond.get_value()].append(cond)
            new_dico = {}
            for cond in condition_in_commun:
                if len(condition_in_commun[cond]) > 1:
                    new_cond = Condition(self, cond)
                    new_tab = []
                    for id in condition_in_commun[cond]:
                        new_tab += dico[id]
                    new_dico[new_cond] = new_tab
                else:
                    new_dico[condition_in_commun[cond][0]] = dico[condition_in_commun[cond][0]]
            return new_dico

        if self.get_workflow_main():
            most_influential_conditions = self.get_workflow_main().get_most_influential_conditions(
                get_on_process_dependency=get_on_process_dependency
            )
            return uniform_conditions(most_influential_conditions)
        else:
            if self.all_conditions_language_server == {}:
                # Case language server
                conditions = self.get_first_file().get_conditions({}, "")
                new_conditions = {}
                for cond in conditions:
                    c = Condition(self, str(cond))
                    new_conditions[c] = []
                    for ele in conditions[cond]:
                        if ele.get_type() == "Operation" and ele.get_artificial_status():
                            if get_on_process_dependency:
                                None
                            else:
                                new_conditions[c].append(ele)
                        else:
                            new_conditions[c].append(ele)
                self.all_conditions_language_server = uniform_conditions(new_conditions)
                return self.all_conditions_language_server
            else:
                return self.all_conditions_language_server

    # Method that returns the order of execution for each executor
    def get_order_execution_executors(self):
        dico = {}
        seen = {}
        dico = self.get_workflow_main().get_order_execution_executors(dico, seen)
        tab = []

        def explore_dico(dico):
            if type(dico) != dict:
                None
            else:
                for val in dico:
                    tab.append(val)
                    explore_dico(dico[val])

        explore_dico(dico)

        return tab

    def add_to_ternary_operation_dico(self, old, new):
        self.ternary_operation_dico[new] = old

    def add_map_element(self, old, new):
        self.map_element_dico[new] = old

    def get_map_element(self):
        return self.map_element_dico

    def get_subworkflows_called(self):
        subs = []
        for c in self.get_workflow_main().get_all_calls_in_workflow():
            ele = c.get_first_element_called()
            if ele.get_type() == "Subworkflow":
                subs.append(ele)
        return subs

    def get_processes_called(self):
        processes_called = []
        if self.get_DSL() == "DSL2":
            for c in self.get_workflow_main().get_all_calls_in_workflow():
                p = c.get_first_element_called()
                if p.get_type() == "Process":
                    processes_called.append(p)
        else:
            processes_called = self.get_first_file().get_processes()
        return processes_called

    def get_operations_and_processes_per_subworkflows(self):
        subs = self.get_subworkflows_called()
        dico = {}
        for s in subs:
            executors = s.get_all_executors_in_workflow()
            tab = []
            for e in executors:
                if not e.get_artificial_status():
                    tab += get_basic_blocks(e, {})
            dico[s] = list(set(tab))
        return dico

    def generate_user_view(self, relevant_processes=[], render_graphs=True, use_process_dependency_graph=False):
        alias_2_tools = self.alias_2_tools
        self.graph.initialise()
        self.graph.generate_user_view(
            relevant_processes=relevant_processes,
            render_graphs=render_graphs,
            use_process_dependency_graph=use_process_dependency_graph,
            alias_2_tools=alias_2_tools,
        )

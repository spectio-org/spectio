import os
import time
import re
import pandas as pd

from .constant import month_mapping
from .outils import encode_string

def get_commits(file):
    commits = {}
    pattern = r"commit (.+)\nAuthor: ([^\<]+)<([^\>]+)\>\nDate: +\w+ (\w+) (\d+) \d+:\d+:\d+ +(\d+)"
    for match in re.finditer(pattern, file):
        commit = match.group(1)
        name = match.group(2).strip()
        email = match.group(3).strip()
        date = f"{match.group(5)}/{month_mapping[match.group(4)]}/{match.group(6)}"
        commits[commit] = {}
        commits[commit]["name"] = name
        commits[commit]['email'] = email
        commits[commit]['date'] = date
    return commits

class History:
    def __init__(self, origin):
        self.origin = origin
        self.tab_versions_workflow = None
        self.updates_elements = None

    def get_workflow(self):
        return self.origin.get_workflow()

    def initialise(self):
        current_path= os.getcwd()
        os.chdir(self.origin.get_root_directory())
        name_temp_file = f"georges_temps_{str(time.time()).replace('.', '')}.txt"
        os.system(f"git log > {name_temp_file}")
        with open(name_temp_file) as f:
            log_file = f.read().strip()
        os.system(f"rm {name_temp_file}")
        os.chdir(current_path)

        
        
        commits = get_commits(log_file)

        from .workflow import Workflow
        tab_versions_workflow, tab_updates_elements = [], []
        last_version_of_structure = None

        def compare_old_version_new_version(tab_updates_elements, old_version, new_version, commit, commits):
            #Comapre Processes
            def get_node(node, searching):
                for n in searching['nodes']:
                    if(n['id']==node["id"]):
                        return n
                    if(n['code']==node["code"]):
                        return n
                return None
            def update_node(n, update):
                temp = {}
                temp["ele_name"] = n["name"]
                temp["ele_type"] = "process"
                temp["update"] = update
                temp["commit"] = commit
                temp["dev_name"] = commits[commit]['name']
                temp["dev_email"] = commits[commit]['email']
                temp["date"] = commits[commit]['date']
                tab_updates_elements.append(temp)

            if(old_version==None):
                for n in new_version['nodes']:
                    update_node(n, "Addition")
            else:
                #Compare old to New
                for n in old_version['nodes']:
                    equivalent_new_node = get_node(n, new_version)
                    if(equivalent_new_node):
                        if(equivalent_new_node['code']==n['code']):
                            None
                        else:
                            update_node(n, "Modification")
                    else:
                        update_node(n, "Deletion")
                #Compare New to old
                for n in new_version["nodes"]:
                    equivalent_old_node = get_node(n, old_version)
                    if(equivalent_old_node):
                        None
                    else:
                        update_node(n, "Addition")

            #Comapre PSubworkflow
            def get_subworkflow(sub_id, searching):
                for n in searching['subworkflows']:
                    if(n==sub_id):
                        return n
                return None
            def update_subworkflow(sub, update):
                temp = {}
                temp["ele_name"] = sub
                temp["ele_type"] = "subworkflow"
                temp["update"] = update
                temp["commit"] = commit
                temp["dev_name"] = commits[commit]['name']
                temp["dev_email"] = commits[commit]['email']
                temp["date"] = commits[commit]['date']
                tab_updates_elements.append(temp)

            if(old_version==None):
                for n in new_version['subworkflows']:
                    update_subworkflow(n, "Addition")
            else:
                #Compare old to New
                for n in old_version['subworkflows']:
                    equivalent_new_subworkflow = get_subworkflow(n, new_version)
                    if(equivalent_new_subworkflow):
                        if(set(old_version['subworkflows'][n]['nodes'])==set(new_version['subworkflows'][equivalent_new_subworkflow]['nodes'])):
                            None
                        else:
                            update_subworkflow(n, "Modification")
                    else:
                        update_subworkflow(n, "Deletion")
                #Compare New to old
                for n in new_version["subworkflows"]:
                    equivalent_old_subworkflow = get_subworkflow(n, old_version)
                    if(equivalent_old_subworkflow):
                        None
                    else:
                        update_subworkflow(n, "Addition")

            return tab_updates_elements

        for commit in reversed(commits.keys()):
            os.chdir(self.origin.get_root_directory())
            os.system(f"git checkout -f {commit} >/dev/null 2>&1")
            os.chdir(current_path)
            try:
                w = Workflow(f"{self.origin.get_root_directory()}", display_info = False)
                w.initialise_with_bioflow()
                w.generate_process_dependency_graph(render_graphs=False)
                stats = w.graph.get_stats_graph_by_hand(dico_2_analyse = "process_dependency")
                graph = w.get_metro_map_json()
                stats['analysis_succesfull'] = True
                tab_updates_elements = compare_old_version_new_version(tab_updates_elements, last_version_of_structure, graph, commit, commits)
                last_version_of_structure = graph
            except Exception as e:
                stats = {}
                stats['analysis_succesfull'] = False
            stats["commit"] = commit
            stats["dev_name"] = commits[commit]['name']
            stats["dev_email"] = commits[commit]['email']
            stats["date"] = commits[commit]['date']
            tab_versions_workflow.append(stats)
        os.system(f"git checkout -f main >/dev/null 2>&1")
            
        self.tab_versions_workflow = pd.DataFrame(tab_versions_workflow)
        self.updates_elements = pd.DataFrame(tab_updates_elements)

    def get_values(self):
        return self.tab_versions_workflow, self.updates_elements


    def get_date_dev_who_created(self, name_ele, type_ele):
        current_path = os.getcwd()
        root_directory = self.origin.get_root_directory()

        os.chdir(root_directory)

        name_temp_file = f"georges_temps_{str(time.time()).replace('.', '')}.txt"
        os.system(f"git log --reverse --topo-order > {name_temp_file}")

        with open(name_temp_file) as f:
            log_file = f.read().strip()

        os.system(f"rm {name_temp_file}")
        os.chdir(current_path)

        commits = get_commits(log_file)
        commit_list = list(commits.keys())

        if type_ele == "Subworkflow":
            keyword = "workflow"
        elif type_ele == "Process":
            keyword = "process"
        else:
            keyword = None

        # e.g. "process  my_process   {" or "workflow\nmy_wf{" — flexible whitespace,
        # exact name match (word boundary so "my_proc" doesn't match "my_process2")
        definition_pattern = re.compile(
            rf"{keyword}\s+{re.escape(name_ele)}\s*\{{"
        ) if keyword else None

        def element_exists(commit):
            """
            Check whether "process <name_ele> {" (or "workflow <name_ele> {" for
            subworkflows) is defined in any .nf file at this commit.
            """
            if definition_pattern is None:
                return False

            os.chdir(root_directory)
            os.system(f"git checkout -f {commit} >/dev/null 2>&1")
            os.chdir(current_path)

            for dirpath, _, filenames in os.walk(root_directory):
                for filename in filenames:
                    if not filename.endswith(".nf"):
                        continue
                    filepath = os.path.join(dirpath, filename)
                    try:
                        with open(filepath, encoding="utf-8", errors="ignore") as nf_file:
                            content = nf_file.read()
                    except Exception:
                        continue
                    if definition_pattern.search(content):
                        return True
            return False

        # Binary search for the FIRST commit where the element exists
        left = 0
        right = len(commit_list) - 1
        first_found = None
        while left <= right:
            middle = (left + right) // 2
            commit = commit_list[middle]
            if element_exists(commit):
                # Element exists here.
                # Therefore, the creation commit is either this one
                # or somewhere before it.
                first_found = middle
                right = middle - 1
            else:
                # Element doesn't exist here.
                # Therefore, we need to search later commits.
                left = middle + 1

        # Restore main branch
        os.chdir(root_directory)
        os.system("git checkout -f main >/dev/null 2>&1")
        os.chdir(current_path)

        if first_found is None:
            return None

        commit = commit_list[first_found]

        return {
            "commit":commit,
            "name":commits[commit]["name"],
            "encoded_email":encode_string(commits[commit]["email"]),
            "date":commits[commit]["date"]
        }

    def get_date_dev_who_created_old(self, name_ele, type_ele):

        current_path= os.getcwd()
        os.chdir(self.origin.get_root_directory())
        name_temp_file = f"georges_temps_{str(time.time()).replace('.', '')}.txt"
        os.system(f"git log > {name_temp_file}")
        with open(name_temp_file) as f:
            log_file = f.read().strip()
        os.system(f"rm {name_temp_file}")
        os.chdir(current_path)

        def get_commits(file):
            commits = {}
            pattern = r"commit (.+)\nAuthor: ([^\<]+)<([^\>]+)\>\nDate: +\w+ (\w+) (\d+) \d+:\d+:\d+ +(\d+)"
            for match in re.finditer(pattern, file):
                commit = match.group(1)
                name = match.group(2).strip()
                email = match.group(3).strip()
                date = f"{match.group(5)}/{month_mapping[match.group(4)]}/{match.group(6)}"
                commits[commit] = {}
                commits[commit]["name"] = name
                commits[commit]['email'] = email
                commits[commit]['date'] = date
            return commits

        
        commits = get_commits(log_file)

        from .workflow import Workflow
        found = False
        value = None

        for commit in reversed(commits.keys()):
            if(not found):
                os.chdir(self.origin.get_root_directory())
                os.system(f"git checkout -f {commit} >/dev/null 2>&1")
                os.chdir(current_path)
                try:
                    w = Workflow(f"{self.origin.get_root_directory()}", display_info = False)
                    w.initialise_with_bioflow()

                    if(type_ele=="Subworkflow"):
                        sub = w.get_subworkflows_called()
                        for s in sub:
                            if(s.get_alias()==name_ele):
                                value = commit, commits[commit]['name'], commits[commit]['email'], commits[commit]['date']
                                found = True
                    if(type_ele=="Process"):
                        processes = w.get_processes_called()
                        for p in processes:
                            if(p.get_alias()==name_ele):
                                value = commit, commits[commit]['name'], commits[commit]['email'], commits[commit]['date']
                                found = True
                except Exception as e:
                    None
        os.system(f"git checkout -f main >/dev/null 2>&1")
        os.chdir(current_path)
        return value





        val = self.initialise(name_ele=name_ele, type_ele=type_ele)
        print(val)
        if(type(val)==dict):
            return val
        else:
            return -1

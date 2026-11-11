import re
import ctypes
from collections import OrderedDict

from .ro_crate import RO_Crate

def get_object(address):
    address = int(re.findall(r"\dx\w+", address)[0], base=16)
    return ctypes.cast(address, ctypes.py_object).value

class DBfile(RO_Crate):
    def __init__(self, workflow, 
                 personnal_acces_token = None,
                 display_info=False):
        RO_Crate.__init__(self, workflow, personnal_acces_token = personnal_acces_token, display_info=display_info)

        self.file_contents="""@prefix sf: <http://sharefair.org/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <https://schema.org/> .
@prefix edam: <http://edamontology.org/> .
@prefix p-plan: <http://purl.org/net/p-plan#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix efo: <https://www.ebi.ac.uk/gwas/efotraits/> ."""
        


    def initialise(self):
        workflow_name = self.workflow.get_name()
        workflow_long_name = self.info_dico_workflow["full_name"]
        description = self.get_description()
        creator =self.info_dico_workflow["owner"]["html_url"]
        authors_tab, authors_temp= [], self.get_authors()
        for author in authors_temp:
            #These are filters to keep in "real" authors
            if("@users.noreply.github.com" not in author['email'] and "@machine" not in author['email']):
                if(" " not in author["@id"]):
                    authors_tab.append(author)
        maintainer = f"https://github.com/{authors_tab[0]['@id']}"
        date_created = self.get_datePublished()
        keywords = self.get_keywords()
        steps_string = []
        for p in self.workflow.get_processes_called():
            steps_string.append(f"sf:step{p.get_alias()}")
        steps_string = ", ".join(steps_string)

        link_dico_processes = self.workflow.get_link_dico_processes()
        first_processes, last_processes = list(link_dico_processes.keys()), []
        for p in link_dico_processes:
            if(link_dico_processes[p]==[]):
                last_processes.append(get_object(p))
            else:
                for p2 in link_dico_processes[p]:
                    try:
                        first_processes.remove(p2)
                    except:
                        None
        temp = []
        for p in first_processes:
            temp.append(get_object(p))
        first_processes = temp

        inputs = []
        for p in first_processes:
            _, generic_ids = p.get_inputs_DBfile()
            inputs+= generic_ids
        outputs = []
        for p in last_processes:
            _, generic_ids = p.get_outputs_DBfile()
            outputs+= generic_ids


        header = f"""### Main workflow
sf:{workflow_name}Workflow rdf:type sf:Workflow ;
\tschema:name "{workflow_long_name}" ;
\tschema:description "{description}" ;
\tschema:creator <{creator}> ;
\tschema:maintainer <{maintainer}> ;
\tschema:dateCreated "{date_created}"^^xsd:date ;
\tschema:programmingLanguage <https://w3id.org/workflowhub/workflow-ro-crate#nextflow> ;
\tschema:step {steps_string} ;"""
        if(inputs!=[]):
            header+=f"\n\tsf:inputVariable {', '.join(inputs)} ;"
        if(outputs!=[]):
            header+=f"\n\tsf:outputVariable {', '.join(outputs)} ;"
        header+=f'\n\tschema:keywords "{keywords}" .'

        
        self.file_contents+=f"\n\n{header}"

        for author in authors_tab:
            self.file_contents+=f"\n\n<https://github.com/{author['@id']}> rdf:type schema:Person ."
        
        self.file_contents+="""\n\n<https://w3id.org/workflowhub/workflow-ro-crate#nextflow> rdf:type schema:ComputerLanguage ;
                                                            rdfs:label "Nextflow" ."""
        
        for p in self.workflow.get_processes_called():
            self.file_contents+="\n\n"+p.get_DBfile_description()
        
        all_calls = self.workflow.get_workflow_main().get_all_calls_in_subworkflow()
        for c in all_calls:
            if(c.get_first_element_called().get_type()=="Subworkflow"):
                sub = c.get_first_element_called()
                self.file_contents+="\n\n"+sub.get_DBfile_description(workflow_name)
        
        #This is to remove multiple lines
        self.file_contents = "\n\n".join(list(OrderedDict.fromkeys(self.file_contents.split("\n\n"))))


        with open(f"{self.workflow.get_output_dir()}/DBfile.ttl", 'w') as output_file :
             output_file.write(self.file_contents)

        

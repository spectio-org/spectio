import json
import glob
import os
import re

from . import constant


class RO_Crate:
    def __init__(self, workflow, prov_ro_crate, personnal_acces_token = None,
                 display_info=False,
                 datePublished=None, description=None,
                  license=None, authors = None,
                   publisher = None, keywords = None,
                   producer = None):
        self.workflow = workflow
        self.directory = workflow.get_root_directory()
        self.personnal_acces_token = personnal_acces_token
        self.display_info = display_info
        self.files = []
        self.dico = {}
        self.info_dico_workflow = {}
        self.log = ""
        self.dico["temp_directory"] = self.directory
        self.datePublished = datePublished
        self.description = description
        self.license = license
        self.authors = authors
        self.publisher = publisher
        self.keywords = keywords
        self.producer = producer
        self.prov_ro_crate = prov_ro_crate

        self.fill_log()
        self.workflow_git_name = self.set_address()
        self.fill_info_dico_workflow()

    def set_address(self):
        address = ""
        current_directory = os.getcwd()
        os.chdir(self.directory)
        try:
            os.system(f"git ls-remote --get-url origin > temp_address_{id(self)}.txt")
            with open(f'temp_address_{id(self)}.txt') as f:
                address = f.read()
            os.system(f"rm temp_address_{id(self)}.txt")
        except:
            None
        os.chdir(current_directory)
        for match in re.finditer(r"https:\/\/github\.com\/([^\.]+)\.git", address):
            address = match.group(1)
            return address
        return ""

    def fill_info_dico_workflow(self):
        current_directory = os.getcwd()
        os.chdir(self.directory)
        try:
            if(self.personnal_acces_token!=None):
                command = f'curl --silent --request GET --url "https://api.github.com/repos/{self.workflow_git_name}" --header "Authorization: Bearer {self.personnal_acces_token}" --header "X-GitHub-Api-Version: 2022-11-28" > temp_dico_{id(self)}.json'
            else:
                command = f'curl --silent --request GET --url "https://api.github.com/repos/{self.workflow_git_name}" > temp_dico_{id(self)}.json'
            _ = os.system(command)
            with open(f'temp_dico_{id(self)}.json') as json_file:
                self.info_dico_workflow = json.load(json_file)
            os.system(f"rm temp_dico_{id(self)}.json")
            
        except:
            _ = os.system(f"rm temp_dico_{id(self)}.json")
        if(self.display_info):
            if(self.info_dico_workflow=={}):
                print("Unable to retrieve information regarding the commits")
            else:
                print("Successfully retrieved information regarding the commits")
        os.chdir(current_directory)


    def fill_log(self):
        """Method that reads the git log and saves it

        Keyword arguments:
        
        """
        current_directory = os.getcwd()
        os.chdir(self.directory)
        try:

            os.system(f"git log --reverse > temp_{id(self)}.txt")
            with open(f'temp_{id(self)}.txt') as f:
                self.log = f.read()
            os.system(f"rm temp_{id(self)}.txt")
        except:
            None
        if(self.display_info):
            if(self.log==""):
                print("Unable to retrieve the git log")
            else:
                print("Successfully retrieved the git log")
        os.chdir(current_directory)

    def get_files(self):
        self.files = glob.glob(f'{self.directory}/**/*.*', recursive=True)
        tab_files = []
        for file in self.files:
            tab_files.append({"@id":file[len(self.directory):]})
        return tab_files
    
    #Format yyyy-mm-dd
    #Here i return the first commit date
    def get_datePublished(self):
        """Method that returns the date of publication

        Keyword arguments:
        
        """
        if(self.datePublished==None):
            for match in re.finditer(r"Date: +\w+ +(\w+) +(\d+) +\d+:\d+:\d+ +(\d+)",self.log):
                month = constant.month_mapping[match.group(1)]
                day = match.group(2)
                year = match.group(3)
                if(int(month)<10 and len(month)==1):
                    month = f"0{month}"
                if(int(day)<10):
                    day = f"0{day}"
                return f"{year}-{month}-{day}"
        else:
            return self.datePublished
    
    def get_description(self):
        """Method that returns the description

        Keyword arguments:
        
        """
        if(self.description==None):
            try:
                res = self.info_dico_workflow["description"]
            except:
                res = None
            return res
        else:
            return self.description
        
    def get_license(self):
        """Method that returns the license

        Keyword arguments:
        
        """
        if(self.license==None):
            return None
            raise Exception("License is not given -> give it from list list https://spdx.org/licenses/")
            #try:
            #    res = self.info_dico_workflow["license"]["key"]
            #except:
            #    res = None
            #return res
        else:
            return self.license
        
    def get_authors(self):
        """Method that returns a list of the authors

        Keyword arguments:
        
        """
        if(self.authors==None):
            authors = {}
            for match in re.finditer(r"Author: ([^>]+)<([^>]+)>",self.log):
                authors[match.group(2)] = match.group(1).strip()
            tab = []
            for author in authors:
                #tab.append({"@id":author, "name":authors[author]})
                tab.append({"@id":authors[author], "email":author})
            return tab
        else:
            authors = self.authors.split(',')
            tab = []
            for a in authors:
                tab.append({"@id":a.strip()})
            return tab
        
    def get_publisher(self):
        """Method that returns the publisher

        Keyword arguments:
        
        """
        if(self.publisher==None):
            if(self.info_dico_workflow!={}):
                return "https://github.com/"
            else:
                return None
        else:
            self.publisher


    def get_creativeWorkStatus(self):
        return "TODO"

    def get_version(self):
        return "TODO"

    #Need to follow this format : "rna-seq, nextflow, bioinformatics, reproducibility, workflow, reproducible-research, bioinformatics-pipeline"
    def get_keywords(self):
        """Method that returns the keywords

        Keyword arguments:
        
        """
        if(self.keywords==None):
            try:
                res = ", ".join(self.info_dico_workflow["topics"])
            except:
                res = None
            return res
        else:
            return self.keywords
        
    def get_producer(self):
        """Method that returns the producer

        Keyword arguments:
        
        """
        if(self.producer==None):
            try:
                res = {"@id": str(self.dico["owner"]["login"])}
            except:
                res = None
            return res
        else:
            return self.producer

    def initialise_dico(self):
        self.dico["@context"] = [
            "https://w3id.org/ro/crate/1.1/context",
            "https://w3id.org/ro/terms/workflow-run/context/context",
            {
                "@base": f"https://github.com/{self.workflow_git_name}",
                "EFO": "http://www.ebi.ac.uk/efo/",
                "OBO": "http://purl.obolibrary.org/obo/",
                "SIO": "http://semanticscience.org/resource/",
                "SWO": "http://www.ebi.ac.uk/swo/",
                "bioschemas": "https://bioschemas.org/",
                "biotools": "https://bio.tools/",
                "edam": "http://edamontology.org/",
                "s": "http://schema.org/"
        }

    ]
        self.dico["@graph"] = []
        #GENERAL
        general = {}
        #general["@id"] = f"ro-crate-metadata-{self.workflow.get_name()}.json"
        general["@id"] = f"ro-crate-metadata.json"
        general["@type"] = "CreativeWork"
        general["about"] = {"@id":"./"}
        general["conformsTo"] = [{"@id":"https://w3id.org/ro/crate/1.1"}
                                 #, {"@id":"https://w3id.org/workflowhub/workflow-ro-crate/1.0"}#This description does not conform 
                                 ]
        self.dico["@graph"].append(general)
        #ROOT
        root = {}
        root["@id"] = "./"
        root["@type"] = "Dataset"
        root["name"] = self.workflow.get_name()
        root["datePublished"] = self.get_datePublished()
        root["description"] = str(self.get_description())
        root["s:mainEntity"] = {"@id": str(self.workflow.get_first_file().get_file_address()).split("/")[-1]}
                              #, "@type":["File", "SoftwareSourceCode"]} #We do not consider a File as a "ComputationalWorkflow" since multiple (sub)workflows can be defined in a same file
        license = str(self.get_license())
        root["license"] = license
        #self.dico["@graph"].append({"@id":license, "@type":['License'], "name":"MIT"})
        authors = self.get_authors()
        tab_authors, tab_authors_ids= [], []
        for author in authors:
            id_author = f'#{"_".join(author["@id"].split())}'
            tab_authors_ids.append({"@id":id_author})
            try:
                #tab_authors.append({"@id":author["@id"], "email":author["email"]})
                tab_authors.append({"@id":id_author, "@type": ["Person"], "name":author["@id"],"email":author["email"]})
            except:
                #tab_authors.append({"@id":author["@id"]})
                tab_authors.append({"@id":id_author, "@type": ["Person"], "name":author["@id"]})
        self.dico["@graph"]+=tab_authors
        root["author"] = tab_authors_ids
        root["maintainer"] = tab_authors_ids #Right now i'm assuming that all the authors are maintainers
        files = self.get_files()
        tab_files = []
        for file in files:
            tab_files.append({"@id":file["@id"]})
        root["s:hasPart"] = tab_files
        publisher = str(self.get_publisher())
        root["publisher"] = {"@id":publisher}
        self.dico["@graph"].append({"@id":publisher, "@type":["Organization"]})
        #subjectOf TODO
        root["subjectOf"] = None
        root["creativeWorkStatus"] = self.get_creativeWorkStatus()
        root["version"] = self.get_version()
        root["keywords"] = self.get_keywords()
        root["producer"] = self.get_producer()
        self.dico["@graph"].append(root)

    def get_programming_language(self, file):
        if(file[-3:]==".nf"):
            #return "https://w3id.org/workflowhub/workflow-ro-crate#nextflow"
            return "#nextflow"
        return None
    
    def get_contentSize(self, file):
        file_stats = os.stat(file)
        return file_stats.st_size/1e3
    


    def get_dateCreated(self, file):
        info = self.log
        for match in re.finditer(r"Date: +\w+ +(\w+) +(\d+) +\d+:\d+:\d+ +(\d+)", info):
            month = constant.month_mapping[match.group(1)]
            day = match.group(2)
            year = match.group(3)
            if(int(month)<10 and len(month)==1):
                month = f"0{month}"
            if(int(day)<10):
                day = f"0{day}"
            return f"{year}-{month}-{day}"
        return None
    
 
    def get_dateModified(self, file):
        info = self.log
        for match in re.finditer(r"Date: +\w+ +(\w+) +(\d+) +\d+:\d+:\d+ +(\d+)", info):
            month = constant.month_mapping[match.group(1)]
            day = match.group(2)
            year = match.group(3)
            if(int(month)<10 and len(month)==1):
                month = f"0{month}"
            if(int(day)<10):
                day = f"0{day}"
            return f"{year}-{month}-{day}"
        return ""
        
    
    def get_url(self, file):
        if(self.workflow_git_name!=""):
            return f"https://github.com/{self.workflow_git_name}/blob/main/{file}"
        return None
    

    def get_creators(self, file):
        info = self.log
        for match in re.finditer(r"Author: ([^>]+)<([^>]+)>",info):
            return [{"@id": match.group(1).strip()}]
        return []


    def get_types(self, file):
        types = ["s:File"]
        if(file[-3:]==".nf"):
            types.append("s:SoftwareSourceCode")
        return types
        

    def initialise_file(self, file):
        key = file[len(self.directory):]
        dico = {}
        dico["@id"] = key
        dico["name"] = key
        dico["@type"] = self.get_types(file)
        dico["programmingLanguage"] = {"@id":str(self.get_programming_language(file))}
        dico["contentSize"] = self.get_contentSize(file)
        dico["dateCreated"] = self.get_dateCreated(key)
        dico["dateModified"] = self.get_dateModified(key)
        dico["url"] = self.get_url(key)
        creators = self.get_creators(key)
        dico["creator"] = []
        for creator in creators:
            dico["creator"].append({"@id": f'#{creator["@id"]}'})
        dico["s:isPartOf"] = []
        dico["s:hasPart"] = []
        self.dico["@graph"].append(dico)    

    def fill_from_workflow(self, prov_ro_crate):
        self.workflow.add_2_rocrate(self.dico, prov_ro_crate)

    def initialise(self):
        self.initialise_dico()
        for file in self.files:
            self.initialise_file(file)
        self.fill_from_workflow(self.prov_ro_crate)
        self.dico.pop("temp_directory")


        if(not self.prov_ro_crate):
            with open(f"{self.workflow.get_output_dir()}/ro-crate-metadata.json", 'w') as output_file :
                json.dump(self.dico, output_file, indent=2)
        else:
            with open(f"{self.workflow.get_output_dir()}/prov-ro-crate-metadata.json", 'w') as output_file :
                json.dump(self.dico, output_file, indent=2)
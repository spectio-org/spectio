import jpype
import os
from pathlib import Path
import importlib.resources


def extract_process_source(p, src):
    start_line = p.getLineNumber()
    start_col  = p.getColumnNumber()
    end_line   = p.getLastLineNumber()
    end_col    = p.getLastColumnNumber()

    lines = src.splitlines(keepends=True)

    def offset(line, col):
        return sum(len(lines[i]) for i in range(line - 1)) + (col - 1)

    start = offset(start_line, start_col)
    end   = offset(end_line, end_col)

    return src[start:end]

class Language_Server:
    def __init__(self):
        file_path = os.path.realpath(__file__)
        
        with importlib.resources.path(
            "src.language_server_source_code",
            "language-server-all.jar"
        ) as jar_path:
            nextflow_jar_path = str(jar_path)

        if not jpype.isJVMStarted():
            jpype.startJVM(classpath=[nextflow_jar_path])

        self.ScriptCodeLensProvider = jpype.JClass("nextflow.lsp.services.script.ScriptCodeLensProvider")
        self.ScriptAstCache = jpype.JClass("nextflow.lsp.services.script.ScriptAstCache")
        self.FileCache = jpype.JClass("nextflow.lsp.file.FileCache")
        self.LanguageServerConfiguration = jpype.JClass("nextflow.lsp.services.LanguageServerConfiguration")
        self.PluginSpecCache = jpype.JClass("nextflow.lsp.spec.PluginSpecCache")

    def parse_file(self, file, name_subworkflow = None):
        if(name_subworkflow==""):
            name_subworkflow = None

        with open(file) as f:
            contents = f.read()

        workflow_folder = Path(file).resolve().parent.as_uri()
        cache = self.ScriptAstCache(workflow_folder)

        config = self.LanguageServerConfiguration.defaults()
        plugin_cache = self.PluginSpecCache(config.pluginRegistryUrl())

        cache.initialize(config, plugin_cache)

        file_cache = self.FileCache()

        file_uri = Path(file).resolve().as_uri()
        uri_obj = jpype.java.net.URI(file_uri)

        file_cache.setContents(uri_obj, contents)
        file_cache.markChanged(uri_obj)

        uris_java = jpype.java.util.HashSet()
        uris_java.add(uri_obj)

        cache.update(uris_java, file_cache)

      
        script_node = cache.getScriptNode(uri_obj)
        processes = script_node.getProcesses()
        workflows = script_node.getWorkflows()
        list_processes, list_subworkflow = [], []

        #Extract the process information 
        for p in processes:
            name, code = p.getName(), extract_process_source(p, contents)
            if(code!=""):
                list_processes.append({"name":name, 'code':code})
       

        for p in workflows:
            name = p.getName()
            if(p.getName()==None):
                name=""
            code = extract_process_source(p, contents)
            if(code!=""):
                list_subworkflow.append({"name":name, 'code':code})
        


        provider = self.ScriptCodeLensProvider(cache)

        structure = provider.previewDag(file_uri, name_subworkflow, "TB", True, True)
        conditions = provider.getControlConditions(file_uri)
        
        return structure, conditions, list_processes, list_subworkflow


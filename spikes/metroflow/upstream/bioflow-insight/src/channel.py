#Import dependencies
#Local
from .nextflow_building_blocks import Nextflow_Building_Blocks
from .bioflowinsighterror import BioFlowInsightError

class Channel(Nextflow_Building_Blocks):
    """
    This is the channel class, from this class, channels can be made and manipulated.

    Attributes:
        name: A string indicating the error message to the user
        origin: A "Nextflow Building Bloc" derived type object, indicating from what the channel originated from 
        
    """

    def __init__(self, name, origin):
        self.name = name.strip()
        self.origin = origin
        self.source = []
        self.sink = []
        to_call = []
        for m in self.get_modules_defined():
            to_call.append(m.get_alias())
        if(self.name in to_call):
            raise BioFlowInsightError('caease', self, self.name, self.get_string_line(self.origin.get_code()))


    def get_code(self, get_OG = True, replace_calls =False, clean_pipe=True, remove_emit_and_take=True):
        """Method that returns the channels code

        Keyword arguments:
        
        """
        return self.name.strip()

    def add_source(self, source):
        """Method that adds an element to the channel's source

        Keyword arguments:
            source: element which is gonna be added to the list of sources
        """
        self.source.append(source)

    def add_sink(self, sink):
        """Method that adds an element to the channel's sink

        Keyword arguments:
            sink: element which is gonna be added to the list of sinks
        """
        self.sink.append(sink)

    def set_sink_null(self):
        """Method that sets the channel's sink to an empty list
        """
        self.sink = []

    def get_type(self):
        """Method that returns the channel's type which is "Channel"
        """
        return "Channel"

    def equal(self, channel):
        """Method that checks if two channels are equal

        Keyword arguments:
            channel: element (preferably of channel type) which is gonna be tested against the channel
        """
        return (self.name==channel.name and self.origin==self.origin)
    
    def get_source(self):
        """Method that returns the channel's sources
        """
        return self.source

    def remove_element_from_sink(self, ele):
        """Method that removes an element from the channel's sink

        Keyword arguments:
            channel: element which is gonna be removed
        """
        self.sink.remove(ele)

    def get_sink(self):
        """Method that returns the channel's sink
        """
        return self.sink
    
    def get_name(self):
        """Method that returns the channel's name
        """
        return self.name
    
    def get_structure(self, dico, B):
        """Method that adds the channel to the structure 

        Keyword arguments:
            dico: dictionnary which is decribing the workflow strutcure
            B: element which should be connected to the channel, so that for every source element in the channels source, there is source->B
        """
        for source in self.get_source():
            dico["edges"].append({'A':str(source), 'B':str(B), "label":self.get_name()})



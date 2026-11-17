
from .root import Root
from .condition import Condition

class Block(Root):
    def __init__(self, code, origin, condition, modules_defined, existing_channels):
        Root.__init__(self = self, code = code, origin = origin, modules_defined = modules_defined, subworkflow_inputs = existing_channels)
        self.condition = Condition(origin=self, condition = condition)

    def initialise(self):
        if(self.condition.value not in self.origin.get_conditions_2_ignore()):
            return super().initialise()
        
    def get_conditions_2_ignore(self):
        return self.origin.get_conditions_2_ignore()
    
    def get_type(self):
        return "Block"
    
    #This method returns returns all the conditions above the block
    #Basically everything which needs to be true for the block to exist
    def get_all_conditions(self, conditions):
        conditions[self.condition] = ''
        self.origin.get_all_conditions(conditions = conditions)
        return conditions


    def same_condition(self, block):
        return self.condition.same_condition(block.condition)

    def get_blocks_with_same_conditions(self, condition):
        tab = self.origin.get_blocks_with_same_conditions(self)
        return tab

    #This method returns all the executors of a block and the block above it
    #As well as the executors with the same condition on the same level
    def get_executors(self):
        blocks_with_same_condition = self.get_blocks_with_same_conditions(self.condition)
        executors_in_other_blocks = []
        for b in blocks_with_same_condition:
            executors_in_other_blocks+=b.executors
        return self.executors+self.origin.get_executors()+executors_in_other_blocks
    
    def get_structure(self, dico):
        return super().get_structure(dico)
    

    #This method returns all the executors inside a block
    def get_above_executors_rec(self, dico):
        for e in self.executors:
            dico[e] = ''
        self.origin.get_above_executors_rec(dico)

    def get_above_executors(self):
        dico = {}
        self.origin.get_above_executors_rec(dico)
        return list(dico.keys())
        

    def get_calls_above_level(self):
        tab = []
        for e in self.get_above_executors():
            if(e.get_type()=="Call"):
                tab.append(e)
            elif(e.get_type()=="Operation"):
                for o in e.get_origins():
                    if(o.get_type()=="Call"):
                        tab.append(o)
        return tab
    
    #These are the calls from different blocks on the same level
    def get_calls_from_other_blocks_on_same_level(self):
        tab = []
        for block in self.origin.get_blocks():
            if(block!=self):
                tab+=block.get_calls_same_level()
                tab+=block.get_calls_inside_level()
        return tab
    
    def get_all_calls_from_root(self):
        return self.origin.get_all_calls_from_root()

    #############
    # CHANNELS
    #############
    def get_channels_above_level_rec(self, dico):
        for c in self.channels:
            dico[c] = ''
        self.origin.get_channels_above_level_rec(dico)
        
    def get_channels_above_level(self):
        dico = {}
        self.origin.get_channels_above_level_rec(dico)
        return list(dico.keys())
    
    #These are the channels from different blocks on the same level
    def get_channels_from_other_blocks_on_same_level(self):
        tab = []
        for block in self.origin.get_blocks():
            if(block!=self):
                tab+=block.get_channels_same_level()
                tab+=block.get_channels_inside_level()
        return tab
    
    def get_channels_from_name_all_channels(self, name):
        return self.origin.get_channels_from_name_all_channels(name)

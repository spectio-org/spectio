import re
from .channel import Channel
from .bioflowinsighterror import BioFlowInsightError
from . import constant


class Emitted(Channel):

    def __init__(self, name, origin, emitted_by):
        Channel.__init__(self, name=name, origin=origin)

        self.emitted_by = emitted_by
        emitted_by.add_to_emits(self)

        
        self.source.append(emitted_by)
        self.emits = None #->this is the channel it's emits -> in the case of a subworkflow

    def get_all_conditions(self):
        return self.origin.get_all_conditions()


    def get_emitted_by(self):
        return self.emitted_by
    
    def get_emits(self):
        return self.emits

    def get_type(self):
        return "Emitted"

    def set_emits_decimal(self, decimal):
        thing_which_emits = self.emitted_by.get_first_element_called()
        if(thing_which_emits.get_type()=="Subworkflow"):
            self.emits = thing_which_emits.get_emit()[decimal]
        elif(thing_which_emits.get_type()=="Process"):#Case it's a process
            self.emits =thing_which_emits
        else:
            raise Exception("This shoudn't happen!")

    def set_emits_name(self, name):
        thing_which_emits = self.emitted_by.get_first_element_called()
        
        if(thing_which_emits.get_type()=="Subworkflow"):
            emitted = thing_which_emits.get_emit()
            
            for o in emitted:
                code = o.get_code()
                if(code[:len("e:")]=="e:"):
                    code =code[len("e:"):].strip()
                if(name==code):
                    self.emits = o
                else:
                    for match in re.finditer(constant.WORD_EQUALS, code):
                        if(name==match.group(1)):
                            self.emits = o
        elif(thing_which_emits.get_type()=="Process"):
            outputs = thing_which_emits.get_outputs()
            for o in outputs:
                if(bool(re.search(fr"emit *\: *{re.escape(name)}", o))):
                    self.emits = thing_which_emits
        else:
            raise Exception("This shoudn't happen!")
        
        if(self.emits==None):
            raise BioFlowInsightError("nem", self, name, self.emitted_by.get_first_element_called().get_name(), self.emitted_by.get_file_address())

    def set_emits(self, input):
        thing_which_emits = self.emitted_by.get_first_element_called()
        if(input!=""):
            try:
                input = int(input)
                self.set_emits_decimal(decimal=input)
            except:
                self.set_emits_name(name=input)
        else:
            if(thing_which_emits.get_type()=='Subworkflow'):
                if(len(thing_which_emits.emit)!=1):
                    element = f"{self.emitted_by.get_first_element_called().get_type().lower()} '{self.emitted_by.get_first_element_called().get_name()}'"
                    raise BioFlowInsightError("meg", self, self.get_code(), element)
                self.emits = thing_which_emits.emit[0]
            elif(thing_which_emits.get_type()=="Process"):
                if(len(thing_which_emits.get_outputs())!=1):
                    element = f"{self.emitted_by.get_first_element_called().get_type().lower()} '{self.emitted_by.get_first_element_called().get_name()}'"
                    raise BioFlowInsightError("meg", self, self.get_code(), element)
                self.emits = thing_which_emits
            else:
                raise Exception("This shoudn't happen!")

    def get_structure(self, dico, B):
        emits = self.get_emitted_by()
        if(emits.get_type()=="Call"):
            first_element_called = emits.get_first_element_called()
            if(first_element_called.get_type()=="Process"):
                dico["edges"].append({'A':str(first_element_called), 'B':str(B), "label":self.get_code()})
            elif(first_element_called.get_type()=="Subworkflow"):
                if(self.emits==None):
                    raise Exception("Just a check")
                else:

                    dico["edges"].append({'A':str(self.emits), 'B':str(B), "label":self.get_name()})
        else:
            raise Exception("This shouldn't happen")
                    


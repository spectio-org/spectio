import re
import subprocess
import os
from . import constant
from .bioflowinsighterror import BioFlowInsightError


#=============================================================
# THESE A JUST UTILITY FUNCTIONS TO BE ABLE TO MANIPULATE CODE
#=============================================================

#Function that returns the next character (+ it's index)
def get_next_element_caracter(string, i):
    while(i+1<len(string)):
        i+=1
        if(string[i]!=' ' and string[i]!='\n'and string[i]!='\t'):
            return string[i], i
    return -1, -1

#Function that returns the character before (+ it's index)
def get_before_element_caracter(string, i):
    while(i>0):
        i-=1
        if(string[i]!=' ' and string[i]!='\n'and string[i]!='\t'):
            return string[i], i
    return -1, -1

def get_curly_count(code):
    curly_count = 0
    quote_single, quote_double = False, False
    triple_single, triple_double = False, False
    for end in range(len(code)):
        checked_triple = False
        if(end+3<=len(code)):
            if(code[end:end+3]=="'''" and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_single = True
                end+=3
                checked_triple = True
            elif(code[end:end+3]=="'''" and not quote_single and not quote_double and triple_single and not triple_double):
                triple_single = False
                end+=3
                checked_triple = True

            if(code[end:end+3]=='"""' and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_double = True
                end+=3
                checked_triple = True
            elif(code[end:end+3]=='"""' and not quote_single and not quote_double and not triple_single and triple_double):
                triple_double = False
                end+=3
                checked_triple = True
        
        if(not checked_triple):
            if(code[end]=="{" and not quote_single and not quote_double and not triple_double):
                curly_count+=1
            if(code[end]=="}" and not quote_single and not quote_double and not triple_double):
                curly_count-=1
            
            if(code[end]=="'" and not quote_single and not quote_double and not triple_double):
                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                    quote_single=True
            elif(code[end]=="'" and quote_single and not quote_double and not triple_double):
                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                    quote_single=False

            if(code[end]=='"' and not quote_single and not quote_double and not triple_double):
                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                    quote_double=True
            elif(code[end]=='"' and not quote_single and quote_double and not triple_double):
                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                    quote_double=False
    return curly_count

def get_single_count(code):
    single_count = 0
    quote_single, quote_double = False, False
    for end in range(len(code)):        
        if(code[end]=="'" and not quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=True
                single_count+=1
        elif(code[end]=="'" and quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=False
                single_count-=1

        if(code[end]=='"' and not quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=True
        elif(code[end]=='"' and not quote_single and quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=False
    return single_count

def get_double_count(code):
    double_count = 0
    quote_single, quote_double = False, False
    for end in range(len(code)):        
        if(code[end]=="'" and not quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=True
        elif(code[end]=="'" and quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=False
    
        if(code[end]=='"' and not quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=True
                double_count+=1
        elif(code[end]=='"' and not quote_single and quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=False
                double_count-=1
    return double_count


#Function that returns the parenthese count of a bit of code
def get_parenthese_count(code):
    parenthese_count = 0
    quote_single, quote_double = False, False
    triple_single, triple_double = False, False
    for end in range(len(code)):
        checked_triple = False
        if(end+3<=len(code)):
            if(code[end:end+3]=="'''" and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_single = True
                end+=3
                checked_triple = True
            elif(code[end:end+3]=="'''" and not quote_single and not quote_double and triple_single and not triple_double):
                triple_single = False
                end+=3
                checked_triple = True

            if(code[end:end+3]=='"""' and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_double = True
                end+=3
                checked_triple = True
            elif(code[end:end+3]=='"""' and not quote_single and not quote_double and not triple_single and triple_double):
                triple_double = False
                end+=3
                checked_triple = True
        
        if(not checked_triple):
            if(code[end]=="(" and not quote_single and not quote_double and not triple_single and not triple_double):
                parenthese_count+=1
            if(code[end]==")" and not quote_single and not quote_double and not triple_single and not triple_double):
                parenthese_count-=1

            if(code[end]=="'" and not quote_single and not quote_double and not triple_single and not triple_double):
                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                    quote_single=True
            elif(code[end]=="'" and quote_single and not quote_double and not triple_single and not triple_double):
                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                    quote_single=False

            if(code[end]=='"' and not quote_single and not quote_double and not triple_single and not triple_double):
                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                    quote_double=True
            elif(code[end]=='"' and not quote_single and quote_double and not triple_single and not triple_double):
                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                    quote_double=False
    return parenthese_count


#Function that returns a subpart of the code until the parenthse_count equals the given value
def get_code_until_parenthese_count(code, val, left_2_right = True):
    parenthese_count = 0
    quote_single, quote_double = False, False
    if(left_2_right):
        tab = list(range(len(code)))
    else:
        tab = list(range(len(code)-1, -1, -1))
    for end in tab:
        if(parenthese_count==val):
            if(left_2_right):
                return code[:end]    
            else:
                return code[end:]

        if(code[end]=="(" and not quote_single and not quote_double):
            parenthese_count+=1
        if(code[end]==")" and not quote_single and not quote_double):
            parenthese_count-=1
        
        if(code[end]=="'" and not quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=True
            
        elif(code[end]=="'" and quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=False

        if(code[end]=='"' and not quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=True
        elif(code[end]=='"' and not quote_single and quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=False
    
    if(parenthese_count==val):
        return code  
    return None


#This function takes some code, the begining of an operator and the end, then extracts
#the whole executor
def extract_executor_from_middle(code, start, end):
    save_start, save_end = start, end
    find_start, find_end = False, False

    


    #Basically the logic here is that at the end of operation curly or parenthese count can be negative but never positive
    #For example (.join is detected first):
    #trim_reads
    #.join(trim_log)
    #.map {
    #    meta, reads, trim_log ->
    #        if (!meta.single_end) {
    #            trim_log = trim_log[-1]
    #        }
    #        if (getTrimGaloreReadsAfterFiltering(trim_log) > 0) {
    #            [ meta, reads ]
    #        }
    #}
    #.set { trim_reads }
    
    curly_count_right, parenthese_count_right = 0, 0
    quote_single_right, quote_double_right = False, False


    while(not find_end):
        if(end>=len(code)):
            raise Exception(f"Couldn't find the end of the executor : {code[start:save_end]}")
        

        if(code[end]=="{" and not quote_single_right and not quote_double_right):
            curly_count_right+=1
        if(code[end]=="}" and not quote_single_right and not quote_double_right):
            curly_count_right-=1
        if(code[end]=="(" and not quote_single_right and not quote_double_right):
            parenthese_count_right+=1
        if(code[end]==")" and not quote_single_right and not quote_double_right):
            parenthese_count_right-=1
        if(code[end]=="'" and not quote_single_right and not quote_double_right):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single_right=True
        elif(code[end]=="'" and quote_single_right and not quote_double_right):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single_right=False
        if(code[end]=='"' and not quote_single_right and not quote_double_right):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double_right=True
        elif(code[end]=='"' and not quote_single_right and quote_double_right):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double_right=False



        next_character, next = get_next_element_caracter(code, end)
        next_next_character, next = get_next_element_caracter(code, next)
        character_before, _ = get_before_element_caracter(code, end)
        #my intuition tells me i need to add next_character in ['}', ')'])
        #But it creates a problem in this example
        #MERGED_LIBRARY_ATAQV_MKARV (
        #    MERGED_LIBRARY_ATAQV_ATAQV.out.json.collect{it[1]}
        #)
        #v0
        #if(code[end]=='\n' and (re.fullmatch("\w", next_character) or next_character in ['}', '/', '|']) and character_before in [')', '}'] and curly_count<=0 and parenthese_count<=0 and not quote_single and not quote_single):
        #v1
        #if(code[end]=='\n' and (re.fullmatch("\w", next_character) or next_character in ['}', '/', '|']) and curly_count<=0 and parenthese_count<=0 and not quote_single and not quote_single):
        #v2
        if(code[end]=='\n' and (re.fullmatch("\w", next_character) or next_character in ['}', '/', '|']) and character_before not in [','] and next_next_character not in ['.', '|'] and curly_count_right<=0 and parenthese_count_right<=0 and not quote_single_right and not quote_single_right):
            find_end = True
        else:
            end+=1


    #Basically the logic here is that at the start of operation curly or parenthese count can be positive but never negative (see example below)
    curly_count_left, parenthese_count_left = 0, 0
    quote_single_left, quote_double_left = False, False


    while(not find_start):
        if(start<0):
            raise Exception(f"Couldn't find the start of the executor : {code[save_start:save_end]}")
        
        if(code[start]=="{" and not quote_single_left and not quote_double_left):
            curly_count_left+=1
        if(code[start]=="}" and not quote_single_left and not quote_double_left):
            curly_count_left-=1
        if(code[start]=="(" and not quote_single_left and not quote_double_left):
            parenthese_count_left+=1
        if(code[start]==")" and not quote_single_left and not quote_double_left):
            parenthese_count_left-=1
        if(code[start]=="'" and not quote_single_left and not quote_double_left):
            if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                quote_single_left=True
        elif(code[start]=="'" and quote_single_left and not quote_double_left):
            if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                quote_single_left=False
        if(code[start]=='"' and not quote_single_left and not quote_double_left):
            if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                quote_double_left=True
        elif(code[start]=='"' and not quote_single_left and quote_double_left):
            if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                quote_double_left=False
        
        next_character, _ = get_next_element_caracter(code, start)
        character_before, _ = get_before_element_caracter(code, start)
        

        if(code[start]=='\n' and (re.fullmatch("\w", next_character) or next_character in ['(']) and character_before not in ['(', '[', ',', '.', '|'] and (curly_count_left+curly_count_right)==0 and (parenthese_count_left+parenthese_count_left)==0 and not quote_single_left and not quote_single_left):
        #if(code[start]=='\n' and character_before not in ['(', '[', ',', '.', '|'] and curly_count>=0 and parenthese_count>=0 and not quote_single and not quote_single):
            find_start = True
        else:
            start-=1

    return code[start:end].strip()


def extract_end_operation(code, start, end):
    curly_count, parenthese_count , bracket_count= 0, 0, 0
    quote_single, quote_double = False, False
    finish = False
    while(not finish):
        if(end>=len(code)):
            raise Exception('Unable to extract')
        elif(code[end]=="{" and not quote_single and not quote_double):
            curly_count+=1
        elif(code[end]=="}" and not quote_single and not quote_double):
            curly_count-=1
        elif(code[end]=="(" and not quote_single and not quote_double):
            parenthese_count+=1
        elif(code[end]==")" and not quote_single and not quote_double):
            parenthese_count-=1
        elif(code[end]=="[" and not quote_single and not quote_double):
            bracket_count+=1
        elif(code[end]=="]" and not quote_single and not quote_double):
            bracket_count-=1
        elif(code[end]=="'" and not quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=True
        elif(code[end]=='"' and not quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=True
        elif(code[end]=="'" and quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=False
        elif(code[end]=='"' and not quote_single and quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=False

        character_before, _ = get_before_element_caracter(code, end)
        next_character, _ = get_next_element_caracter(code, end)
        if(code[end]=='\n' and next_character not in ['.', "|"] and curly_count==0 and parenthese_count==0 and bracket_count==0 and not quote_single and not quote_double and character_before!="|"):
        #if(next_character!='.' and curly_count==0 and parenthese_count==0 and not quote_single and not quote_double):
            finish = True
        elif((curly_count<0 or parenthese_count<0 or bracket_count<0)  and character_before in [')', '}'] and not quote_single and not quote_double):
            finish = True
        else:
            end+=1
    return code[start:end].strip()

#Function that 'finds' the end of the process, when we give the start position
#So it follows the pattern 'process name {....}'
def extract_curly(text, start):

    end = start
    code= text
    curly_count, parenthese_count = 1, 0
    quote_single, quote_double = False, False
    triple_single, triple_double = False, False


    while(parenthese_count!=0 or curly_count!=0 or quote_single or quote_double or triple_single or triple_double): 

        
        checked_triple = False
        if(end+3<=len(code)):
            if(code[end:end+3]=="'''" and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_single = True
                end+=3
                checked_triple = True
            elif(code[end:end+3]=="'''" and not quote_single and not quote_double and triple_single and not triple_double):
                triple_single = False
                end+=3
                checked_triple = True

            if(code[end:end+3]=='"""' and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_double = True
                end+=3
                checked_triple = True
            elif(code[end:end+3]=='"""' and not quote_single and not quote_double and not triple_single and triple_double):
                triple_double = False
                end+=3
                checked_triple = True
        
        if(not checked_triple):
            if(code[end]=="{" and not quote_single and not quote_double and not triple_single and not triple_double):
                curly_count+=1
            elif(code[end]=="}" and not quote_single and not quote_double and not triple_single and not triple_double):
                curly_count-=1
            
            if(code[end]=="(" and not quote_single and not quote_double and not triple_single and not triple_double):
                parenthese_count+=1
            elif(code[end]==")" and not quote_single and not quote_double and not triple_single and not triple_double):
                parenthese_count-=1

            if(code[end]=="'" and not quote_single and not quote_double and not triple_single and not triple_double):
                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                    quote_single=True
            elif(code[end]=="'" and quote_single and not quote_double and not triple_single and not triple_double):
                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                    quote_single=False

            if(code[end]=='"' and not quote_single and not quote_double and not triple_single and not triple_double):
                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                    quote_double=True
            elif(code[end]=='"' and not quote_single and quote_double and not triple_single and not triple_double):
                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                    quote_double=False

            end+=1

        if(end>len(code)):
            raise Exception('Unable to extract')
    return end



def get_end_operator(code, start, end, beginning_character):
    curly_count, parenthese_count = 0, 0
    quote_single, quote_double = False, False
    
    start_param = end
    if(beginning_character=="("):
        parenthese_count+=1
    if(beginning_character=="{"):
        curly_count+=1

    while(parenthese_count!=0 or curly_count!=0 or quote_single or quote_double):     
        if(code[end]=="{" and not quote_single and not quote_double):
            curly_count+=1
        if(code[end]=="}" and not quote_single and not quote_double):
            curly_count-=1
        if(code[end]=="(" and not quote_single and not quote_double):
            parenthese_count+=1
        if(code[end]==")" and not quote_single and not quote_double):
            parenthese_count-=1
        if(code[end]=="'" and not quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=True
        elif(code[end]=="'" and quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=False
        if(code[end]=='"' and not quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=True
        elif(code[end]=='"' and not quote_single and quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=False
        end+=1
        if(end>len(code)):
            raise Exception('Unable to extract')
        
    return code[start:end].strip(), code[start_param:end-1].strip()



#=====================================================
#FUNCTIONS FOR THE CODE CLASS -> REMOVE COMMENTS ETC..
#=====================================================

def remove_comments(input_text):

    input_text= input_text+"\n\n\n"
    #Remove the \" and \' in the code
    #input_text = re.sub(r'([^\\])\\"', r'\g<1>', input_text)
    #input_text = re.sub(r"([^\\])\\'", r'\g<1>', input_text)
    ##Remove the /'/ and /"/ in the code
    #input_text = re.sub(r'\/"\/', "", input_text)
    #input_text = re.sub(r"\/'\/", "", input_text)
    
    
    
    

    #input_text = input_text.replace('/\/*', '"').replace('\/*$/', '"')
    #TO remove `/\/* ... \/*$/ and /[fasta|fa]$/
    input_text = re.sub(r'\/\\\/\*([^(\\\/\*\$\/)]+)\\\/\*\$\/', r'"\g<1>"', input_text)

    #input_text = re.sub(r'\/([^($\/)]+)\$\/', r'"\g<1>"', input_text)
    #if(temp!=input_text):

    
    to_remove = []
    quote_single, quote_double = False, False
    triple_single, triple_double = False, False
    in_bloc, in_single_line = False, False
    start, end = 0, 0
    i=0
    while(i<len(input_text)-3):
    #for i in range(len(input_text)-3):
        #Case single line comment "//"
        if(input_text[i:i+2]=="//" and not quote_single and not quote_double and not in_bloc and not in_single_line and not triple_single and not triple_double):
            is_comment_one_line = True
            if(i-1>=0):
                if(input_text[i-1]=='\\'):
                    is_comment_one_line=False
            if(is_comment_one_line):
                start = i
                in_single_line = True
                i+=2
            else:
                i+=1
        elif(input_text[i]=="\n" and not quote_single and not quote_double and not in_bloc and in_single_line and not triple_single and not triple_double):
            end = i
            in_single_line = False
            to_remove.append(input_text[start:end+1])
            i+=1
        #Case bloc comment "/*...*/"
        elif(input_text[i:i+2]=="/*" and not quote_single and not quote_double and not in_bloc and not in_single_line and not triple_single and not triple_double):
            start = i
            in_bloc = True
            i+=2
        elif(input_text[i:i+2]=="*/" and not quote_single and not quote_double and in_bloc and not in_single_line and not triple_single and not triple_double):
            end = i+2
            in_bloc = False
            to_remove.append(input_text[start:end])
            i+=2
        #ELSE
        #Triple single
        elif(input_text[i:i+3]=="'''" and not quote_single and not quote_double and not in_bloc and not in_single_line and not triple_single and not triple_double):
            triple_single = True
            i+=3
        elif(input_text[i:i+3]=="'''" and not quote_single and not quote_double and not in_bloc and not in_single_line and triple_single and not triple_double):
            triple_single = False
            i+=3
        #Triple double
        elif(input_text[i:i+3]=='"""' and not quote_single and not quote_double and not in_bloc and not in_single_line and not triple_single and not triple_double):
            triple_double = True
            i+=3
        elif(input_text[i:i+3]=='"""' and not quote_single and not quote_double and not in_bloc and not in_single_line and not triple_single and triple_double):
            triple_double = False
            i+=3
        #Case single
        elif(input_text[i]=="'" and not quote_single and not quote_double and not in_bloc and not in_single_line and not triple_single and not triple_double):
            if(input_text[i-1]!="\\"):
                quote_single = True
            i+=1
        elif(input_text[i]=="'" and quote_single and not quote_double and not in_bloc and not in_single_line and not triple_single and not triple_double):
            if(input_text[i-1]!="\\"):
                quote_single = False
            i+=1
        #Case double
        elif(input_text[i]=='"' and not quote_single and not quote_double and not in_bloc and not in_single_line and not triple_single and not triple_double):
            if(input_text[i-1]!="\\"):
                quote_double = True
            i+=1
        elif(input_text[i]=='"' and not quote_single and quote_double and not in_bloc and not in_single_line and not triple_single and not triple_double):
            if(input_text[i-1]!="\\"):
                quote_double = False
            i+=1
        else:
            i+=1

    for r in to_remove:
        if(r[:2]=="//"):
            input_text = input_text.replace(r, '\n', 1)
        else:
            nb_jumps = r.count('\n')
            input_text = input_text.replace(r, '\n'*nb_jumps, 1)
        
    return input_text



#----------------------
#Calls
#----------------------
def get_end_call(code, start, end):
    curly_count, parenthese_count = 0, 1
    quote_single, quote_double = False, False
    #Before it was this
    #while(parenthese_count!=0 or curly_count!=0 or quote_single or quote_double or code[end]!='\n'):
    while(parenthese_count!=0 or curly_count!=0 or quote_single or quote_double):
        if(end>=len(code)):
            raise Exception('Unable to extract')
        if(code[end]=="{" and not quote_single and not quote_double):
            curly_count+=1
        if(code[end]=="}" and not quote_single and not quote_double):
            curly_count-=1
        if(code[end]=="(" and not quote_single and not quote_double):
            parenthese_count+=1
        if(code[end]==")" and not quote_single and not quote_double):
            parenthese_count-=1
        if(code[end]=="'" and not quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=True
        elif(code[end]=="'" and quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=False
        if(code[end]=='"' and not quote_single and not quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=True
        elif(code[end]=='"' and not quote_single and quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=False
        end+=1
    return code[start:end].strip()


#This function takes a string "param" and returns the next parameter
def get_next_param(param):
    curly_count, parenthese_count, bracket_count= 0, 0, 0
    quote_single, quote_double = False, False
    end= 0
    while(True):
        if(end>=len(param)):
            return param, -1
        if(parenthese_count==0 and curly_count==0 and bracket_count==0 and not quote_single and not quote_double and param[end]==','):
            return param[0:end], end+1
        
        if(param[end]=="{" and not quote_single and not quote_double):
            curly_count+=1
        elif(param[end]=="}" and not quote_single and not quote_double):
            curly_count-=1
        elif(param[end]=="(" and not quote_single and not quote_double):
            parenthese_count+=1
        elif(param[end]==")" and not quote_single and not quote_double):
            parenthese_count-=1
        elif(param[end]=="[" and not quote_single and not quote_double):
            bracket_count+=1
        elif(param[end]=="]" and not quote_single and not quote_double):
            bracket_count-=1
        elif(param[end]=="'" and not quote_single and not quote_double):
            if(param[end-1]!="\\"):
                quote_single=True
        elif(param[end]=='"' and not quote_single and not quote_double):
            if(param[end-1]!="\\"):
                quote_double=True
        elif(param[end]=="'" and quote_single and not quote_double):
            if(param[end-1]!="\\"):
                quote_single=False
        elif(param[end]=='"' and not quote_single and quote_double):
            if(param[end-1]!="\\"):
                quote_double=False
        end+=1

def update_parameters(code, end, curly_count, parenthese_count, quote_single, quote_double) :
    if(code[end]=="{" and not quote_single and not quote_double):
        curly_count+=1
    elif(code[end]=="}" and not quote_single and not quote_double):
        curly_count-=1
    elif(code[end]=="(" and not quote_single and not quote_double):
        parenthese_count+=1
    elif(code[end]==")" and not quote_single and not quote_double):
        parenthese_count-=1
    elif(code[end]=="'" and not quote_single and not quote_double):
        if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
            quote_single=True
    elif(code[end]=='"' and not quote_single and not quote_double):
        if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
            quote_double=True
    elif(code[end]=="'" and quote_single and not quote_double):
        if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
            quote_single=False
    elif(code[end]=='"' and not quote_single and quote_double):
        if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
            quote_double=False
    return curly_count, parenthese_count, quote_single, quote_double


def remove_jumps_inbetween_parentheses(code):
    code = re.sub(',\s*\n\s*', ', ', code)
    code = re.sub(';\s*\n\s*', '; ', code)
    code = list(code)
    parentheses_count = 0
    for i in range(len(code)):
        if(code[i]=="("):
            parentheses_count+=1
        elif(code[i]==")"):
            parentheses_count-=1
        elif(code[i]=="\n" and parentheses_count!=0):
            code[i] = " "
    code = "".join(code)
    code = re.sub(r", *\n", ", ", code)
    return code

def remove_jumps_inbetween_curlies(code):
    code = re.sub(',\s*\n\s*', ', ', code)
    code = re.sub(';\s*\n\s*', '; ', code)
    code = list(code)
    curly_count = 0
    for i in range(len(code)):
        if(code[i]=="{"):
            curly_count+=1
        elif(code[i]=="}"):
            curly_count-=1
        elif(code[i]=="\n" and curly_count!=0):
            code[i] = " "
    code = "".join(code)
    code = re.sub(r", *\n", ", ", code)
    return code

#def check_if_parameter_is_given_pipe(code, OG_start, OG_end):
#    char, end = get_next_element_caracter(code, OG_end-1)
#    start = OG_end
#    if(char in ['(', '{']):
#        curly_count, parenthese_count = int(char=="{"), int(char=="(")
#        quote_single, quote_double = False, False
#        end+=1
#        #Before it was this
#        #while(parenthese_count!=0 or curly_count!=0 or quote_single or quote_double or code[end]!='\n'):
#        while(parenthese_count!=0 or curly_count!=0 or quote_single or quote_double):
#            if(end>=len(code)):
#                raise Exception('Unable to extract')
#            if(code[end]=="{" and not quote_single and not quote_double):
#                curly_count+=1
#            if(code[end]=="}" and not quote_single and not quote_double):
#                curly_count-=1
#            if(code[end]=="(" and not quote_single and not quote_double):
#                parenthese_count+=1
#            if(code[end]==")" and not quote_single and not quote_double):
#                parenthese_count-=1
#            if(code[end]=="'" and not quote_single and not quote_double):
#                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
#                    quote_single=True
#            elif(code[end]=="'" and quote_single and not quote_double):
#                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
#                    quote_single=False
#            if(code[end]=='"' and not quote_single and not quote_double):
#                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
#                    quote_double=True
#            elif(code[end]=='"' and not quote_single and quote_double):
#                if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
#                    quote_double=False
#            end+=1
#        return code[start:end].strip()[1:-1].strip(), code[OG_start:end]
#    return ''

def expand_call_to_operation(code, call):
    start = code.find(call)
    end = start+len(call)
    char, _ = get_next_element_caracter(code, end-1)
    #This means it's an operation
    if(char=="."):
        return extract_end_operation(code, start, end)
    return call

def expand_pipe_operator(code, operator):
    start = code.find(operator)
    end = start+len(operator)
    expanding = True
    while(expanding):
        expanding = False
        char, _ = get_next_element_caracter(code, end-1)
        if(char in ['{', '|', '(']):
            operator = extract_end_operation(code, start, end)
            start = code.find(operator)
            end = start+len(operator)
            expanding = True
    return operator

#Function that checks if a bit of code given is in the condition of an if
def checks_in_condition_if(code, bit_of_code):
    start = code.find(bit_of_code)
    end = start+len(bit_of_code)
    start_if, end_if = 0, 0
    for match in re.finditer(r"if\s*\(", code[:start]):
        start_if, end_if = match.span(0)
    parenthese_count_left_before_if = get_parenthese_count(code[start_if:start])
    if(parenthese_count_left_before_if>0 and get_parenthese_count(code[:start_if])==0):
        code_end_if = get_code_until_parenthese_count(code[end:], -1*parenthese_count_left_before_if)
        if(code_end_if!=None):
            code_right_after_if = code[code.find(code_end_if)+len(code_end_if):]
            if(get_parenthese_count(code_right_after_if)==0):
                return True
    return False


#the function sort_and_filter takes two lists, positions and variables, and removes 
#entries with positions equal to (0, 0). It then sorts the remaining entries based 
#on positions and returns the sorted positions and corresponding variables.
def sort_and_filter(positions, variables):
    combined_data = list(zip(positions, variables))
    combined_data = [(pos, var) for pos, var in combined_data if pos != (0, 0)]
    combined_data.sort(key=lambda x: x[0])
    sorted_positions, sorted_variables = zip(*combined_data)
    return list(sorted_positions), list(sorted_variables)

#Function that checks if a bit of code given is in  a string
def checks_in_string(code, bit_of_code):
    start = code.find(bit_of_code)
    end = start+len(bit_of_code)

    
    #Start by single quote
    first_quote_from_left, first_quote_from_right = -1, -1
    for i in range(start-1, -1, -1):
        if(code[i]=="'"):
            first_quote_from_left = i
            break
    for i in range(end, len(code)):
        if(code[i]=="'"):
            first_quote_from_right = i
            break
    if(first_quote_from_left!=-1 and first_quote_from_right!=-1):
        if(get_single_count(code[:first_quote_from_left])==0 and get_single_count(code[first_quote_from_right+1:])==0):
            return True

    #Do the same for double quote
    first_quote_from_left, first_quote_from_right = -1, -1
    for i in range(start-1, -1, -1):
        if(code[i]=='"'):
            first_quote_from_left = i
            break
    if(first_quote_from_left==-1):
        return False
    for i in range(end, len(code)):
        if(code[i]=='"'):
            first_quote_from_right = i
            break
    if(first_quote_from_right==-1):
        return False
    if(first_quote_from_left!=-1 and first_quote_from_right!=-1):
        if(get_double_count(code[:first_quote_from_left])==0 and get_double_count(code[first_quote_from_right+1:])==0):
            return True
    
    return False


#Function that checks if a pipe operator is mixed with regular operators cause in that case we ignore the pipe operator
def check_if_pipe_operator_is_mixed_with_regular_operators(code):
    there_is_regular_operations = False
    for operator in constant.LIST_OPERATORS:
        pattern = fr'\. *{re.escape(operator)}'
        for match in re.finditer(pattern, code):
            there_is_regular_operations = True
        if(there_is_regular_operations):
            break
    return there_is_regular_operations

#This function extracts the rest of the inside of a parentheses given a 
#bit of code (we assume that the bit of code is inside the code)
def extract_inside_parentheses(code, bit_of_code):
    start = code.find(bit_of_code)
    end = start+len(bit_of_code)
    left = get_code_until_parenthese_count(code[:start], 1, left_2_right = False)
    right = get_code_until_parenthese_count(code[end:], -1, left_2_right = True)
    return (left[1:]+bit_of_code+right[:-1]).strip()

#This is used to get a dico from from the graph tab in a RO-Crate file
def get_dico_from_tab_from_id(dico, id):
    for temp_dico in dico["@graph"]:
        if(temp_dico["@id"]==id):
            return temp_dico
    return None

def check_if_element_in_tab_rocrate(tab, id):
    for ele in tab:
        if(ele["@id"]==id):
            return True
    return False


#Function that parses python script and extracts the packages which are imported 
def get_python_packages(script):
    packages = []
    #Examples that i need to consider: 
    # from fibo import *
    # from sound.effects.echo import echofilter
    # import fibo
    # import fibo, sys
    # import sound.effects.echo
    # import numpy as np

    #STEP1
    patterns_from = [r"fr(om)\s+(\w+)\s+import.+",
                     r"from\s+((\w+)(\.\w+)+)\s+import.+",]
    #First step is to extract the packages which are imported from the from and then removing them from the string
    froms = []
    for pattern in patterns_from:
        for match in re.finditer(pattern, script):
            packages.append(match.group(2))
            froms.append(match.group(0))
    for f in froms:
        script = script.replace(f, "")

    #STEP2
    #Remove the rest of the 'simple' imports
    def remove_commas(text):
        tab = text.split(',')
        words = []
        for t in tab:
            words.append(t.strip())
        return words
    for match in re.finditer(r"import\s+(\w+(\s*\,\s*\w+)+|(\w+))", script):
        packages+= remove_commas(match.group(1))

    return packages


#Function that parses R script and extracts the libraries which are loaded 
def get_R_libraries(script):
    libraries = []
    for match in re.finditer(r"library\s*\(\s*(\w+)\s*\)", script):
        libraries.append(match.group(1))
    return libraries

#Function that parses perl script and extracts the modules which are imported
def get_perl_modules(script):
    libraries = []
    for match in re.finditer(r"(package|use)\s+([^\s;]+)\s*;", script):
        libraries.append(match.group(2))
    return libraries


def check_file_exists(address, origin):
    try:
        with open(address, 'r') as f:
            contents = f.read()
            return contents
    except Exception:
        raise BioFlowInsightError('fdne', origin, "", address)

    

def is_git_directory(path = '.'):
    return subprocess.call(['git', '-C', path, 'status'], stderr=subprocess.STDOUT, stdout = open(os.devnull, 'w')) == 0


#Function that extracts the conditions defined in some code
#Right now the function is not recursif -> since i call blocks recursively and that this function is only used by blocks -> it is indirectrly called recursiverly
def extract_conditions(code, only_get_inside = True):
    conditions_dico = {}
    index_condition = 0

    start = 0

    curly_count, parenthese_count = 0, 0
    quote_single, quote_double = False, False
    triple_single, triple_double = False, False


    timeout = 0
    while(start<len(code) and timeout < constant.WHILE_UPPER_BOUND):    
        checked_triple = False
        if(start+3<=len(code)):
            if(code[start:start+3]=="'''" and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_single = True
                start+=3
                checked_triple = True
            elif(code[start:start+3]=="'''" and not quote_single and not quote_double and triple_single and not triple_double):
                triple_single = False
                start+=3
                checked_triple = True
    
            if(code[start:start+3]=='"""' and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_double = True
                start+=3
                checked_triple = True
            elif(code[start:start+3]=='"""' and not quote_single and not quote_double and not triple_single and triple_double):
                triple_double = False
                start+=3
                checked_triple = True
        
        if(not checked_triple):
            if(code[start]=="{" and not quote_single and not quote_double and not triple_single and not triple_double):
                curly_count+=1
            elif(code[start]=="}" and not quote_single and not quote_double and not triple_single and not triple_double):
                curly_count-=1
            
            if(code[start]=="(" and not quote_single and not quote_double and not triple_single and not triple_double):
                parenthese_count+=1
            elif(code[start]==")" and not quote_single and not quote_double and not triple_single and not triple_double):
                parenthese_count-=1
    
            if(code[start]=="'" and not quote_single and not quote_double and not triple_single and not triple_double):
                if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                    quote_single=True
            elif(code[start]=="'" and quote_single and not quote_double and not triple_single and not triple_double):
                if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                    quote_single=False
    
            if(code[start]=='"' and not quote_single and not quote_double and not triple_single and not triple_double):
                if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                    quote_double=True
            elif(code[start]=='"' and not quote_single and quote_double and not triple_single and not triple_double):
                if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                    quote_double=False

            #TODO Right now -> support only for if/else written with curlies -> not on single line
            def adding_inside(conditions_dico, code, start_inside, end_inside):
                temp_dico = extract_conditions(code[start_inside:end_inside])
                for c in temp_dico:
                    temp = temp_dico[c]
                    temp_dico[c] = (temp[0] + start_inside, temp[1] + start_inside)
                #Merging the 2 dicos
                conditions_dico = conditions_dico | temp_dico
                return conditions_dico
            #Just because there is an 'if' doesn't necessarily mean there is an if bloc
            found_if_bloc = False
            searching_for_else = False
            conditions = []
            if(code[start:start+2]=="if" and [quote_single, quote_double, triple_single, triple_double]==[False, False, False, False]):
                for match in re.finditer(r"if *\([^{]+\n", code[start:]):
                    if(match.span(0)[0]==0):
                        raise BioFlowInsightError("cwne", None, match.group(0).strip(), "")

                for match in re.finditer(r"if *\((.+)\)\s*\{", code[start:]):
                    if(match.span(0)[0]==0):
                        found_if_bloc = True
                        condition = match.group(1)
                        conditions.append(condition)
                        end = extract_curly(code, match.span(0)[1]+start)#Here we nedd to add the start index since we're only working on a subpart of code 
                        start_inside, end_inside = match.span(0)[1]+start, end-1
                        if(only_get_inside):
                            conditions_dico[f"{condition}$$__$${index_condition}"] = (start_inside, end_inside)
                        else:
                            conditions_dico[f"{condition}$$__$${index_condition}"] = (start, end)
                        index_condition+=1
                        searching_for_else = True
                        #conditions_dico = adding_inside(conditions_dico, code, start_inside, end_inside)
                    break
                while(searching_for_else):
                    searching_for_else = False
                    #Try to find an else corresponding
                    if(found_if_bloc and code[end:].strip()[:4]=="else"):
                        found_else_if = False
                        #CASE of "else if"
                        rest_of_code = code[end:]
                        for match in re.finditer(r"\s*else *if *\((.+)\)\s*\{", rest_of_code):
                            start_else, end_else = match.span(0)
                            if(start_else==0):
                                found_else_if = True
                                searching_for_else = True
                                condition = match.group(1)
                                printed_condition = ' && '.join(["!({})".format(v) for v in conditions])
                                printed_condition += " && "+condition
                                conditions.append(condition)
                                start_else+=end
                                end_else = extract_curly(code, end_else+end)
                                start_inside, end_inside = match.span(0)[1]+end, end_else-1
                                if(only_get_inside):
                                    conditions_dico[f"{printed_condition}$$__$${index_condition}"] = (start_inside, end_inside)
                                else:
                                    conditions_dico[f"{printed_condition}$$__$${index_condition}"] = (start_else, end_else)
                                index_condition+=1
                                #conditions_dico = adding_inside(conditions_dico, code, start_inside, end_inside)
                                break
                        #CASE of "else"
                        if(not found_else_if):
                            for match in re.finditer(r"else\s*{", code[end:]):
                                start_else, end_else = match.span(0)
                                start_else+=end
                                end_else = extract_curly(code, end_else+end)
                                start_inside, end_inside = match.span(0)[1]+end, end_else-1
                                condition = ' && '.join(["!({})".format(v) for v in conditions])
                                if(only_get_inside):
                                    conditions_dico[f"{condition}$$__$${index_condition}"] = (start_inside, end_inside)
                                else:
                                    conditions_dico[f"{condition}$$__$${index_condition}"] = (start_else, end_else)
                                index_condition+=1
                                #conditions_dico = adding_inside(conditions_dico, code, start_inside, end_inside)

                                break
                        end = end_else        
                if(found_if_bloc):
                    #Case we need to jump to the end of the if
                    start = end-1
    
            start+=1
        timeout+=1
    if(timeout>=constant.WHILE_UPPER_BOUND):
        raise BioFlowInsightError("ube", None, "BioFlow-Insight was unable to extarct the conditions. Make sure the workflow uses correct Nextflow syntaxe (https://www.nextflow.io/docs/latest/index.html).")
    for c in conditions_dico:
        start, end = conditions_dico[c]
    return conditions_dico
    
def process_2_DSL2(code):
    def replace_file_by_path(match):
        if(match.group(1)==" "):
            return "path "
        else:
            return "path("
        
    def replace_set_by_tuple(match):
        if(match.group(1)==" "):
            return "tuple "
        else:
            return "tuple("

    code = re.sub(r'file( | *\()', replace_file_by_path, code)
    code = re.sub(r'set( | *\()', replace_set_by_tuple, code)
    return remove_parentheses_after_thing(add_vals_when_necessary(code))

#This function removes the parentheses after a path or a tuple
#For example tuple (val(sample_id),  path ('*_trimmed.fq.gz')), emit: (se_aln_ch) becomes tuple val(sample_id),  path ('*_trimmed.fq.gz'), emit: (se_aln_ch)
def remove_parentheses_after_thing(line):
    line_OG = line
    line = line.strip()
    for match in re.finditer(r"(tuple|path) *\(", line):
        start, end= match.span(0)
        if(start==0):
            temp = end+1
            parentheses_count = 1
            while(temp<len(line)):
                if(line[temp]=='('):
                    parentheses_count+=1
                if(line[temp]==')'):
                    parentheses_count-=1
                if(parentheses_count==0):
                    break
                temp+=1
            line_OG = line_OG.replace(line[start:temp+1], line[start:end-1]+" "+line[end:temp])
            break
    return line_OG

#Function that adds vals around variables in a tuple
def add_vals_when_necessary(line):
    starts_with_tuple = False
    code_to_replace = ""
    for match in re.finditer(r"tuple\s*\((.+)\)", line):
        starts_with_tuple = True
        code_to_replace = match.group(1)
    if(not starts_with_tuple):
        for match in re.finditer(r"tuple\s*(.+)", line):
            starts_with_tuple = True
            code_to_replace = match.group(1)
    
    if(starts_with_tuple):
        code_to_replace = re.split(r'\,\s*emit\s*\:', code_to_replace)[0]
        #Adding val to cases where it's just the variable
        line_split = code_to_replace.split(',')
        for y in range(len(line_split)) :
            param = line_split[y]
            if(bool(re.fullmatch('\w+', param.strip()))):
                line_split[y] = f"val({param.strip()})"
        temp = ", ".join(line_split)
        line = line.replace(code_to_replace, temp)
    return line



def operation_2_DSL2(code, origin):
    
    #If channel.close() -> just remove it
    if(re.fullmatch(r'\w+\s*\.\s*close\s*\(\s*\)', code)):
        return ""

    def replace_create_by_empty(match):
            return ".empty()"
    def replace_groupBy_by_groupTuple(match):
            return ".groupTuple("
    def replace_print_by_view(match):
            return ".view("
    def replace_spread_by_combine(match):
            return ".combine("
        
    #Create to empty 
    code = re.sub(r'\.\s*create\s*\(\s*\)', replace_create_by_empty, code)
    #groupBy to groupTuple
    code = re.sub(r'\.\s*groupBy\s*\(', replace_groupBy_by_groupTuple, code)
    #print and println to view
    code = re.sub(r'\.\s*(print|println)\s*\(', replace_print_by_view, code)
    #spread to combine
    code = re.sub(r'\.\s*spread\s*\(', replace_spread_by_combine, code)

    if(bool(re.findall(r"\.\s*spread\s*\(", code))):
        raise BioFlowInsightError('onsbdc', None, "spread")
    if(bool(re.findall(r"\.\s*choice", code))):
        raise BioFlowInsightError('onsbdc', None, "choice")
    if(bool(re.findall(r"\.\s*countBy", code))):
        raise BioFlowInsightError('onsbdc', None, "countBy")
    if(bool(re.findall(r"\.\s*fork", code))):
        raise BioFlowInsightError('onsbdc', None, "fork")
    if(bool(re.findall(r"\.\s*route", code))):
        raise BioFlowInsightError('onsbdc', None, "route")
    if(bool(re.findall(r"\.\s*separate", code))):
        raise BioFlowInsightError('onsbdc', None, "separate")

    

    #Imporant it's last 
    there_is_an_into = False
    tab = re.split(r'\.\s*into\s*\{', code)
    if(len(tab)>1):
        code = ""
        body = tab[0]
        for gives in origin.get_gives():
            #code+=f"\n{gives.get_code()} = {body}"
            code+=f"\n{body}.set{{{gives.get_code()}}}"

    return code

def format_with_tabs(code):

    def replace_jump(match):
            return "\n"
    #Removing the current "\t"s and extras " "
    code = re.sub(r"\n[\t ]*", replace_jump, code)

    start = 0

    curly_count, parenthese_count = 0, 0
    quote_single, quote_double = False, False
    triple_single, triple_double = False, False


    while(start<len(code)):         
        checked_triple = False
        if(start+3<=len(code)):
            if(code[start:start+3]=="'''" and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_single = True
                start+=3
                checked_triple = True
            elif(code[start:start+3]=="'''" and not quote_single and not quote_double and triple_single and not triple_double):
                triple_single = False
                start+=3
                checked_triple = True
    
            if(code[start:start+3]=='"""' and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_double = True
                start+=3
                checked_triple = True
            elif(code[start:start+3]=='"""' and not quote_single and not quote_double and not triple_single and triple_double):
                triple_double = False
                start+=3
                checked_triple = True
        
        if(not checked_triple):
            if(code[start]=="{" and not quote_single and not quote_double and not triple_single and not triple_double):
                curly_count+=1
            elif(code[start]=="}" and not quote_single and not quote_double and not triple_single and not triple_double):
                curly_count-=1
            
            if(code[start]=="(" and not quote_single and not quote_double and not triple_single and not triple_double):
                parenthese_count+=1
            elif(code[start]==")" and not quote_single and not quote_double and not triple_single and not triple_double):
                parenthese_count-=1
    
            if(code[start]=="'" and not quote_single and not quote_double and not triple_single and not triple_double):
                if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                    quote_single=True
            elif(code[start]=="'" and quote_single and not quote_double and not triple_single and not triple_double):
                if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                    quote_single=False
    
            if(code[start]=='"' and not quote_single and not quote_double and not triple_single and not triple_double):
                if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                    quote_double=True
            elif(code[start]=='"' and not quote_single and quote_double and not triple_single and not triple_double):
                if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                    quote_double=False
        if(parenthese_count==0 and [quote_single, quote_double, triple_single, triple_double]==[False, False, False, False]):
            if(curly_count>0 and code[start]=="\n"):
                code = code[:start+1]+"\t"*curly_count+code[start+1:]
                start+=1
        start+=1

    return code

#This function takes a list of processes/subworkflows and opeartions 
#Add replaces the processes an d subworkflows by their calls
def replace_thing_by_call(tab):
    to_remove = []
    to_add = []
    for ele in tab:
        if(ele.get_type() not in ["Operation", "Call"]):
            to_remove.append(ele)
            call = ele.get_call()
            #This verification is really important 
            if(len(call)!=1):
                raise Exception("This shoudn't happen since duplicate mode is activated")
            call = call[0]
            to_add.append(call)
        
    for r in to_remove:
        tab.remove(r)
    tab+=to_add
    return tab

def replace_group1(text, pattern, replacement):
    def replacer(match):
        return match.group(0).replace(match.group(1), replacement)
    return re.sub(pattern, replacer, text)


#This function take a code and groups together ifs where possible (this function is only to be used with the ifs I define -> cause there are no elses or if elses)
def group_together_ifs(code):
    pattern = r"if\s*\(([^{]+)\{"
    condition_1, condition_2 = "", ""
    big_start, big_end = 0, 0
    still_changing = True
    while(still_changing):
        still_changing = False
        
        for match in re.finditer(pattern, code):
            condition_1, condition_2, inside_1, inside_2 = "", "a", "", ""
            condition_1 = match.group(1)
            big_start, end_1 = match.span(0)
            end = extract_curly(code, end_1)
            inside_1 = code[end_1:end-1].strip()

            for motch in re.finditer(re.escape(code[big_start:end])+r'\s*'+pattern, code):
                condition_2 = motch.group(1)
                _, end_2 = motch.span(0)
                end = extract_curly(code, end_2)
                big_end = end
                inside_2 = code[end_2:end-1].strip()
                break
            #Case they are the same condition then we merge the 2
            if(condition_1.strip()==condition_2.strip()):
                still_changing = True
                code = code.replace(code[big_start:big_end], f"if({condition_1}{{\n{inside_1}\n{inside_2}\n}}\n")
                break
            
    return code

def remove_extra_jumps(code):
    changed = True
    while(changed):
        changed = False
        temp = code
        def replacer(match):
            return "\n\n"
        code = re.sub(r"\n\s*\n\s*\n", replacer, code)
        if(code!=temp):
            changed = True
              
    return code

#This functions analyses the body of the subworkflow and the emitted values
#If a channel is created in a certain condition (and not the negative) -> then we create it
def get_channels_to_add_in_false_conditions(body, emitted_channels):
    conditions = extract_conditions(body)
    channels_2_conditions = {}
    #Creating the dictionnary channels 2 conditions
    for channel in emitted_channels:
        channels_2_conditions[channel] = []
        for match in re.finditer(fr"{re.escape(channel)}\s*=", body):
            start, end = match.span(0)
            for c in conditions:
                start_condition, end_conditions = conditions[c]
                if(start_condition<=start and start<=end_conditions):
                    channels_2_conditions[channel].append(c)
    #Simplifying the list of conditions
    # here it's important that the input workflow doesn't have a too complexe condition systems (e.g. writting the same condition in multiple ways)
    #Cause the converter doesn't analyse the conditions -> and basically it would create things which shloudn't
    for channel in channels_2_conditions:
        tab = channels_2_conditions[channel]
        to_remove = []
        for condition in tab:
            #If the condition and it's neagtion are in the tab -> then we remove the condition and it's negation form the list
            condition = condition.split("$$__$$")[0]
            negation = f"!({condition})"
            if(negation in tab):
                to_remove.append(condition)
                to_remove.append(negation)
        for r in to_remove:
            tab.remove(r)
        channels_2_conditions[channel] = tab

        #For the remaining condition in the list -> need to create an empty channel in the case of the negation
        for condition in channels_2_conditions[channel]:
            condition = condition.split("$$__$$")[0]
            #Originally it is not commented
            #body += f"\nif(!({condition})) {{\n{channel} = Channel.empty()\n}}"
    
    return body

#This function removes the empty conditions 
def remove_empty_conditions(code):
    pattern = r"(else +if *\(.+\)|if *\(.+\)|else)\s*{(\s*)}"
    def replace(text, pattern):
        def replacer(match):
            return match.group(0).replace(match.group(0), match.group(2))
        return re.sub(pattern, replacer, text)
    temp = code
    code = replace(code, pattern)
    while(code!=temp):
        temp = code
        code = replace(code, pattern)
    return code

#This function removes the empty conditions -> while keeping the anker_clusters -> if it's orignally in a condtion
def remove_empty_conditions_place_anker(code, workflow):
    #We remove the processes and functions from the code so that the conditions in the processes are not extracted
    temp_code = code
    for m in workflow.get_first_file().get_modules_defined():
        if(m.get_type() in ["Process", "Function"]):
            tmp = temp_code
            temp_code = temp_code.replace(m.get_code(), "a"*len(m.get_code()))
            if(tmp==temp_code):
                raise Exception("Something went wrong -> the code was not updated")

    conditions = extract_conditions(temp_code)
    OG_anker= "//Anker_clusters"
    pos = code.find(OG_anker)
    conditions_containing_anker = []
    for condition in conditions:
        start, end = conditions[condition]
        if(start<=pos and pos<=end):
            conditions_containing_anker.append(condition.split('$$__$$')[0])
    new_anker = OG_anker
    for condition in conditions_containing_anker:
        new_anker = f"\n}}\n{new_anker}\nif({condition}) {{\n"
    code = code.replace(OG_anker, new_anker)
    code = remove_empty_conditions(code)
    return code


def extract_single_quote(text, start):
    end = start
    code= text
    quote_single = True

    while(quote_single): 
        if(code[end]=="'" and quote_single):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_single=False
        end+=1
        if(end>=len(code)):
            raise Exception('Unable to extract')
    return end

def extract_double_quote(text, start):
    temp_start = start
    end = start
    code= text
    quote_double = True

    while(quote_double): 
        if(code[end]=='"' and quote_double):
            if(code[end-1]!="\\" or (code[end-1]=="\\" and code[end-2]=="\\")):
                quote_double=False
        end+=1
        if(end>=len(code)):
            raise Exception('Unable to extract')
    return end

#This function extracts the tools used in a script by running each line in the bash script
#in an empty bash envrionment using a singularity image (by doing this with parse the errors
#and extract the tools)
def extract_tools(script, tools_2_return, extract_general_tools = False):
    #If we want to extract the general tools we define a list of the general tools 'to remove' from the tools extracted
    if(extract_general_tools):
        general_tools = []
    else:
        general_tools = ['cd', 'cat', 'sed', 'echo', 'mv', 'mkdir', 'cp', 'awk', 'touch', 'tabix', 
                 'gzip', 'rm', 'bgzip', 'set', 'grep', 'egrep', 'pigz', 'head', 'tar', 'tail', 
                 'gunzip', 'wc', 'ls', 'find', "sort", "uniq", "printf", "ln", "zcat", "which", 
                 "eval", "paste", "tr", "gawk", "date", "tee", "trap","base64", 'parallel', 'time',
                 "pwd", "sleep", "ssh", "cpu", "fgrep", "bc", "chmod", "whereis", "conda", "wait",
                 "split", "git", "join", "unzip", "wget", "print", "rev", 'rmdir']

    OG_script = script
    script = " "+script+" "

    #Detecting cases of none bash environments
    python = ["#!/usr/bin/env python"]
    for p in python:
        if(p in script):
            return [] 
    rscript = ["#!/usr/bin/env Rscript"]
    for r in rscript:
        if(r in script):
            return []   
    perl_script = ['#!/usr/bin/env perl']
    for p in perl_script:
        if(p in script):
            return []

    
    tools = []

    #----------------------------
    #"CLEANING" the script 
    #----------------------------
    #Removing the curlies and the elements inside them -> to avoid the errors not recognising the variables 
    searching = True
    while(searching):
        searching = False
        for match in re.finditer(r'\{.+\}', script):
            start, _ = match.span(0)
            end = extract_curly(script+"\n\n\n\n", start+1)
            if(end!=-1):
                inside_curly = script[start:end]
                script = script.replace(inside_curly, "")
                searching = True
                break
    
    #Removing the triple quotes from the script
    script = re.sub(r"\"\"\"", "\n", script)
    script = re.sub(r"\'\'\'", "\n", script)

    #Removing elements inside the single quotes
    searching = True
    while(searching):
        searching = False
        for match in re.finditer(r'\'', script):
            start, end = match.span(0)
            try:
                end = extract_single_quote(script+"\n\n\n\n", start+1)
            except:
                break
            inside_single_quote = script[start:end]
            script = script.replace(inside_single_quote, "")
            searching = True
            break

    #Removing elements inside the doucle quotes
    searching = True
    while(searching):
        searching = False
        for match in re.finditer(r'\"', script):
            start, end = match.span(0)
            try:
                end = extract_double_quote(script+"\n\n\n\n", start+1)
            except:
                break
            inside_double_quote = script[start:end]
            script = script.replace(inside_double_quote, "")
            searching = True
            break

    script = re.sub(r"\\\$", "", script)    
    script = re.sub(r"\$", "", script)
    script = re.sub(r"\(", "", script)
    script = re.sub(r"\)", "", script)
    script = re.sub(r'\(', "", script)
    script = re.sub(r'\)', "", script)
    script = re.sub(r"\n *\<[^\>.]+\>", " ", script)
    script = re.sub(r"\<", " ", script)
    script = re.sub(r"\>", " ", script)
    script = re.sub(r"\&", " ", script)
    script = re.sub(r"\n\s*\\", " ", script)
    script = re.sub(r"\s*\\", " ", script)
    script = re.sub(r" then ", " ", script)
    #Repalcing xargs by nothing
    #"xargs" -> is not really a tool in a traditional sense
    temp = script
    def replacer(match):
        return match.group(0).replace(match.group(1), '')
    for tool in ["xargs"]:
        script = re.sub(fr"[^\w]({tool})\s", replacer, script)

    #Removing the pipe operators
    searching = True
    while(searching):
        searching = False
        to_replace = []
        for command in script.split('\n'):
            if('|' in command):
                left, right = command.split('|')[0], '|'.join(command.split('|')[1:])
                if(left.count('(')==left.count(')') and right.count('(')==right.count(')')):
                    searching = True
                    to_replace.append([command, f"{left}\n{right}"])
        for r in to_replace:
            script = script.replace(r[0], r[1], 1)

    OG_path = os.getcwd()
    #Change working directory to the one of the file
    os.chdir("/".join((str(__file__).split("/")[:-1])))

    #Get list of files which already exist in folder 
    OG_files = os.listdir()

    #Create empty output.txt file 
    os.system(f"> output.txt")
    for command in script.split('\n'):
        command = command.strip()
        os.system(f"> output.txt")
        if(command!=""):
            if(command[-1]==";"):
                command = command[:-1]
            if(command[0]=="&"):
                command = command[1:]
            for c in command.split(";"):
                c = c.strip()
                test_apptainer = True
                if(c[:len("do ")]=="do "):
                    c = c[len("do "):]
                    c = c.strip()
                #In the case the command is "var = ..." we don't run it
                for match in re.finditer(r"\w+\s*=", c):
                    if(match.span(0)[0]==0):
                        test_apptainer = False
                #Running the command in the empty environment 
                if(test_apptainer):
                    apptainer_command = f"apptainer exec ../ressources/empty.sif {c} >> output.txt 2>&1"
                    f = open("apptainer_script.sh", "w")
                    f.write(apptainer_command)
                    f.close()
                    os.system(f"chmod +x apptainer_script.sh")
                    #apptainer pull empty.sif docker://cfgarden/empty
                    os.system(f"./apptainer_script.sh >> .out 2>&1 && rm -rf .out")


        #Parsing the error to extarct the tool
        results = open("output.txt").read()
        #print("*", f"'{results}'")
        for pattern in [r'FATAL: +\"([^"]+)"', r'FATAL: +stat +([^:]+):']:
            for match in re.finditer(pattern, results):
                extarcted = match.group(1).split("/")[-1].strip()
                #List of things to ignore -> these can be detected for tools -> obviously they are not tools
                random_things = ['if', 'elif', "else", "done", "fi", 'do', 'for', 'module','then', 
                                 "def", "{", "}", "end_versions", ":", "stub:", "stub :", "__pycache__", 
                                 "cut", "source", "export", "[", "]", "$", ",", "case", "esac", "exit", 
                                 "cli", "e0f", "gnu", "env", "!", "function", "readme.md", "false", "while", "eof", "include"]
                to_add = True
                for match2 in re.finditer(r"\w+\s*=", extarcted):
                    if(match2.span(0)[0]==0):
                        to_add = False
                extarcted = extarcted.lower()
                if(to_add and extarcted not in random_things):
                    #If it's a parameter
                    if(extarcted[0]=="-"):
                        None
                    #If it's a script -> we get of which kind
                    elif(extarcted[-3:]==".py" or extarcted=="python3" or extarcted=="python2"):
                        tools.append("python")
                    elif(extarcted[-2:]==".R" or extarcted[-2:]==".r"):
                        tools.append("r")
                    elif(extarcted[-3:]==".pl"):
                        tools.append("perl")
                    elif(extarcted[-3:]==".jl"):
                        tools.append("julia")
                    elif(extarcted[-3:]==".sh"):
                        #For now the bash script is not considered
                        #tools.append("bash")
                        None
                    else:
                        ex = extarcted.lower().strip()
                        if(ex=="rscript"):
                            tools.append("r")
                        elif(ex=="bash"):
                            None
                        #If the tool extarcted is "template" -> we search for the script used 
                        elif(ex=="template"):
                            for extension_search in re.finditer(r'template *[^\/\s]+(\.\w+)', OG_script):
                                extension = extension_search.group(1)
                                if(extension==".py"):
                                    tools.append("python")
                                elif(extension==".R" or extension==".r"):
                                    tools.append("r")
                                elif(extension==".pl"):
                                    tools.append("perl")
                                elif(extension==".jl"):
                                    tools.append("julia")
                        elif (ex!="" 
                              and len(ex)>1 
                              and ex not in general_tools 
                              and ex[-1]!=":" 
                              and re.fullmatch(r"\w", ex[0])
                              and "=" not in ex):
                            tools.append(ex)
                        #If the tool is java -> we search for the jar file in the command
                        if(ex=="java"):
                            for java_search in re.finditer(r'([^\/\s]+)\.jar', command):
                                tools.append(java_search.group(1).lower())
                                tools.remove('java')

    #We remove the remaining files which have been created in the meantime              
    for file in os.listdir():
        if(file not in OG_files):
            os.system(f'rm {file}')

    #Change working directory back to the OG one
    os.chdir(OG_path)
    
    #Return the tools extarcted
    for t in list(set(tools)):
        tools_2_return[t] = ""
    #return list(set(tools))


def get_code_until_character_2(code, char):

    start = 0

    curly_count, parenthese_count = 0, 0
    quote_single, quote_double = False, False
    triple_single, triple_double = False, False


    while(start<len(code)):         
        checked_triple = False
        if(start+3<=len(code)):
            if(code[start:start+3]=="'''" and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_single = True
                start+=3
                checked_triple = True
            elif(code[start:start+3]=="'''" and not quote_single and not quote_double and triple_single and not triple_double):
                triple_single = False
                start+=3
                checked_triple = True
    
            if(code[start:start+3]=='"""' and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_double = True
                start+=3
                checked_triple = True
            elif(code[start:start+3]=='"""' and not quote_single and not quote_double and not triple_single and triple_double):
                triple_double = False
                start+=3
                checked_triple = True
        
        if(not checked_triple):
            if(code[start]=="{" and not quote_single and not quote_double and not triple_single and not triple_double):
                curly_count+=1
            elif(code[start]=="}" and not quote_single and not quote_double and not triple_single and not triple_double):
                curly_count-=1
            
            if(code[start]=="(" and not quote_single and not quote_double and not triple_single and not triple_double):
                parenthese_count+=1
            elif(code[start]==")" and not quote_single and not quote_double and not triple_single and not triple_double):
                parenthese_count-=1
    
            if(code[start]=="'" and not quote_single and not quote_double and not triple_single and not triple_double):
                if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                    quote_single=True
            elif(code[start]=="'" and quote_single and not quote_double and not triple_single and not triple_double):
                if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                    quote_single=False
    
            if(code[start]=='"' and not quote_single and not quote_double and not triple_single and not triple_double):
                if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                    quote_double=True
            elif(code[start]=='"' and not quote_single and quote_double and not triple_single and not triple_double):
                if(code[start-1]!="\\" or (code[start-1]=="\\" and code[start-2]=="\\")):
                    quote_double=False
        if(code[start]==char and parenthese_count==0 and curly_count ==0 and [quote_single, quote_double, triple_single, triple_double]==[False, False, False, False]):
            return code[start+1:], start
        start+=1
    raise Exception("")


def get_code_until_character(code, char, left_to_right = True):

    def addition(variable, val):
        return variable + val

    def substraction(variable, val):
        return variable - val

    if(left_to_right):
        fun = addition
        start = 0
    else:
        fun = substraction
        start = -1

    curly_count, parenthese_count = 0, 0
    quote_single, quote_double = False, False
    triple_single, triple_double = False, False


    while(start<len(code)):         
        checked_triple = False
        if(fun(start, 3)<=len(code)):
            if(code[start:fun(start, 3)]=="'''" and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_single = True
                start=fun(start, 3)
                checked_triple = True
            elif(code[start:fun(start, 3)]=="'''" and not quote_single and not quote_double and triple_single and not triple_double):
                triple_single = False
                start=fun(start, 3)
                checked_triple = True
    
            if(code[start:fun(start, 3)]=='"""' and not quote_single and not quote_double and not triple_single and not triple_double):
                triple_double = True
                start=fun(start, 3)
                checked_triple = True
            elif(code[start:fun(start, 3)]=='"""' and not quote_single and not quote_double and not triple_single and triple_double):
                triple_double = False
                start=fun(start, 3)
                checked_triple = True
        
        if(not checked_triple):
            if(code[start]=="{" and not quote_single and not quote_double and not triple_single and not triple_double):
                curly_count+=1
            elif(code[start]=="}" and not quote_single and not quote_double and not triple_single and not triple_double):
                curly_count-=1
            
            if(code[start]=="(" and not quote_single and not quote_double and not triple_single and not triple_double):
                parenthese_count+=1
            elif(code[start]==")" and not quote_single and not quote_double and not triple_single and not triple_double):
                parenthese_count-=1
    
            if(code[start]=="'" and not quote_single and not quote_double and not triple_single and not triple_double):
                if(code[substraction(start, 1)]!="\\" or (code[substraction(start, 1)]=="\\" and code[substraction(start, 2)]=="\\")):
                    quote_single=True
            elif(code[start]=="'" and quote_single and not quote_double and not triple_single and not triple_double):
                if(code[substraction(start, 1)]!="\\" or (code[substraction(start, 1)]=="\\" and code[substraction(start, 2)]=="\\")):
                    quote_single=False
    
            if(code[start]=='"' and not quote_single and not quote_double and not triple_single and not triple_double):
                if(code[substraction(start, 1)]!="\\" or (code[substraction(start, 1)]=="\\" and code[substraction(start, 2)]=="\\")):
                    quote_double=True
            elif(code[start]=='"' and not quote_single and quote_double and not triple_single and not triple_double):
                if(code[substraction(start, 1)]!="\\" or (code[substraction(start, 1)]=="\\" and code[substraction(start, 2)]=="\\")):
                    quote_double=False
        if(code[start]==char and parenthese_count==0 and curly_count ==0 and [quote_single, quote_double, triple_single, triple_double]==[False, False, False, False]):
            if(left_to_right):
                return code[start+1:], start
            else:
                return code[start+1:], start
            
        start=fun(start, 1)
    raise Exception("")

def replace_call_parentheses(text):
    text = text.strip()
    update = True
    while(update):
        update = False
        for i in range(len(text)):
            if(text[i]=="("):
                char_before, _ = get_before_element_caracter(text, i)
                temp = text[i+1:]
                inside = get_code_until_parenthese_count(temp, -1)
                char_next, _ = get_next_element_caracter(text, i+len(inside))

                if(char_before!=-1 and (bool(re.fullmatch(r"\w", char_before)) or  char_next in ['.'])):
                    update = True
                    
                    text = text[:i+len(inside)]+"##}"+text[i+1+len(inside):]#replacing the closing one first 
                    text = text[:i]+"##{"+text[i+1:]#replacing the opening one
                    break
    return text


def replace_single_dollar_signs(text):
    update = True
    while(update):
        update = False
        for i in range(len(text)):
            if(text[i]=="$"):
                try:
                    if(text[i:i+4]!="$OR$" and text[i-3:i+1]!="$OR$"):
                        1/0
                        
                except:
                    update = True
                    text = text[:i]+"#dollar_sign#"+text[i+1:]
                    break

    return text

def replace_single_ampersand(text):
    return text.replace(' & ', " && ")

def replace_single_bar_by_or(text):
    return text.replace(' | ', " $OR$ ")

def replace_equal_wave(text):
    temp = text.replace('==~', " double_equal_wave ")
    temp = temp.replace('=~', "==~")
    temp = temp.replace(" double_equal_wave ", '==~')
    return temp

#Decompose the operations and call into their basic form so that for example [call1(call2(operation1))]
#Becomes [[process1, process2, operation1]] -> of course i'm only manipulating the ids
#The goal of this function is that from the elements in the code -> i can manipulate the elements in the graph
def get_basic_blocks(exe, building_blocks):
    #In the case of the call -> we extract the process if one is called 
    #And decompose its parameters
    if(exe.get_type()=="Call"):
        if(exe.get_first_element_called().get_type()=="Process"):
            building_blocks[exe.get_first_element_called()] = ""
        if(exe.get_first_element_called().get_type()=="Subworkflow"):
            for temp in exe.get_first_element_called().get_all_executors_in_workflow():
                get_basic_blocks(temp, building_blocks)
        for p in exe.parameters:
            if(p.get_type() in ["Call", "Operation"]):
                get_basic_blocks(p, building_blocks)
    #In the case of an operation -> we add it (if it's not a call to a subworkflow)
    #Plus we extract and decompose its origins
    elif(exe.get_type()=="Operation"):
        if(not(len(exe.get_origins())==1 and exe.get_origins()[0].get_type()=="Call" and exe.get_origins()[0].get_first_element_called().get_type()=="Subworkflow")):
            if(not exe.get_artificial_status()):
                building_blocks[exe] = ""
        for o in exe.get_origins():
            if(o.get_type() in ["Call", "Operation"]):
                get_basic_blocks(o, building_blocks)
    #This is for DSL1
    elif(exe.get_type()=="Process"):
        building_blocks[exe] = ""
    else:
        raise Exception("This shouldn't happen")
    return list(building_blocks.keys())




def parse_mermaid_graph(text):
    
    processes_subworkflows_nodes_pattern = r'(v\d+)\(\[([^\]]+)\]\)\s+click v\d+ href \"([^\"]+)"'
    operation_patterns = [r'\n\s+(v\d+)\("([^\"]+)\"\)', r'\n\s+(v\d+)\["([^\"]+)\"\]']
    edges_pattern = r'(v\d+) --> (v\d+)'
    condition_edges_pattern = r'(v\d+) --> (s\d+)'
    start_subgraph = r'subgraph (s\d+)\[\" \"\]'
    end_subgraph = r'end'
    patterns_node_in_subgraph = [r'(v\d+)\(\[([^\]]+)\]\)', r'(v\d+)\("([^\"]+)\"\)', r'(v\d+)\["([^\"]+)\"\]']

    ##First part preprocessing of the subworkflows
    ##The idea here that if a subworkflow is called twice
    ##I only consider the one with the edges
    #dico_subworkflows = {}
    #for match in re.finditer(r'v(\d+)\(\[([^\]]+)\]\)', text):
    #    id, name = match.group(1), match.group(2)
    #    try:
    #        temp = dico_subworkflows[name]
    #    except:
    #        dico_subworkflows[name] = []
    #    dico_subworkflows[name].append(id)
    #for name in dico_subworkflows:
    #    first = dico_subworkflows[name][0]
    #    for id in dico_subworkflows[name]:
    #        text = text.replace(f"--> v{id}", f"--> v{first}")
    #        text = text.replace(f"v{id} -->", f"v{first} -->")
    #        if(id!=first):
    #            text = re.sub(fr"v{id}\(\[{re.escape(name)}\]\)\n +click.+", "", text)

    #dico_subworkflows = {}
    #for match in re.finditer(r'v(\d+)\(\[([^\]]+)\]\)', text):
    #    id, name = match.group(1), match.group(2)
    #    try:
    #        temp = dico_subworkflows[name]
    #    except:
    #        dico_subworkflows[name] = []
    #    dico_subworkflows[name].append(id)
    #print(dico_subworkflows)
    #for name in dico_subworkflows:
    #    if(len(dico_subworkflows[name])>1):
    #        for id in dico_subworkflows[name]:
    #            text = text.replace(f"v{id}([{name}])", f"v{id}([{name}_{id}])")
    #print(text)

    dico_structure = {"nodes":[],
                      "edges":[],
                      "subgraphs":{}}

    #Adding nodes
    for match in re.finditer(processes_subworkflows_nodes_pattern, text):
        id, name, href = match.group(1), match.group(2), match.group(3).replace("file:", "")
        dico_structure["nodes"].append({"id":id, "name":name, "href":href})

    for pattern in operation_patterns:
        for match in re.finditer(pattern, text):
            id, name, href = match.group(1), match.group(2), None
            dico_structure["nodes"].append({"id":id, "name":name, "href":href})

    #Adding edges
    for match in re.finditer(edges_pattern, text):
        A, B = match.group(1), match.group(2)
        #Check that B is not a conditional node
        conditional_node = True
        for n in dico_structure["nodes"]:
            if(B==n['id']):
                conditional_node = False
        if(not conditional_node):
            dico_structure["edges"].append({"A":A, "B":B})

    #Getting condition edges
    visited = []
    condition_edges = []
    for match in re.finditer(condition_edges_pattern, text):
        A, B = match.group(1), match.group(2)
        if(A in visited):
            A = f"!{A}"
        else:
            visited.append(A)
        condition_edges.append({"A":A, "B":B})


    
    def add_stack(dico, stack):
        id = stack[0]['id']
        all_nodes_in_stack = []
        for i in range(len(stack)):
            all_nodes_in_stack+=stack[i]['nodes']
        try:
            temp = dico["subgraphs"][id]
        except:
            dico["subgraphs"][id] = {"id": id, 
                        "nodes":[],
                        "subgraphs":{}}
        dico["subgraphs"][id]['nodes'] += all_nodes_in_stack
        dico["subgraphs"][id]['nodes'] = list(set(dico["subgraphs"][id]['nodes']))
        if(len(stack)>1):
            add_stack(dico["subgraphs"][id], stack[1:])


    subgraph_stack = []
    for line in text.splitlines():
        line = line.strip()
        if(re.fullmatch(start_subgraph, line)):
            id = re.compile(start_subgraph).match(line).group(1)
            subgraph_stack.append({"id": id, "nodes":[]})
        if(re.fullmatch(end_subgraph, line) and len(subgraph_stack)>0):
            add_stack(dico_structure, subgraph_stack)
            subgraph_stack.pop()
        for pat in patterns_node_in_subgraph: 
            if(re.fullmatch(pat, line) and len(subgraph_stack)>0):
                id = re.compile(pat).match(line).group(1)
                subgraph_stack[-1]['nodes'].append(id)
    return dico_structure, condition_edges

#basically mode is either emit or takes
def get_takes_emit_from_mermaid(text, mode):
    pattern = r'(v\d+)\[\"(\w+)\"\]'
    reading = False
    tab = []
    for line in text.splitlines():
        line = line.strip()
        if(line==f'subgraph {mode}'):
            reading = True
        elif(line=='end' and reading):
            reading = False
        elif(reading):
            id = re.compile(pattern).match(line).group(1)
            name = re.compile(pattern).match(line).group(2)
            tab.append((id, name))
    return tab
        

def clamp(value, min_value, max_value):
	return max(min_value, min(max_value, value))

def saturate(value):
	return clamp(value, 0.0, 1.0)

def hue_to_rgb(h):
	r = abs(h * 6.0 - 3.0) - 1.0
	g = 2.0 - abs(h * 6.0 - 2.0)
	b = 2.0 - abs(h * 6.0 - 4.0)
	return saturate(r), saturate(g), saturate(b)

def hsl_to_rgb(h, s, l):
	h, s, l= h/360, s/100, l/100
	r, g, b = hue_to_rgb(h)
	c = (1.0 - abs(2.0 * l - 1.0)) * s
	r = (r - 0.5) * c + l
	g = (g - 0.5) * c + l
	b = (b - 0.5) * c + l
	return int(r*255), int(g*255), int(b*255)

def jaccard(A, B):
    inter = set(A).intersection(set(B))
    union = set(A).union(set(B))
    return len(set(inter))/len(set(union)) 


import string

_PRINTABLE = string.printable[:95]  # space through '~', ord 32-126, in order

def _shift_table(shift):
    n = len(_PRINTABLE)
    shifted = _PRINTABLE[shift % n:] + _PRINTABLE[:shift % n]
    return str.maketrans(_PRINTABLE, shifted)

_ENCODE_TABLE = _shift_table(1)
_DECODE_TABLE = _shift_table(-1)

def encode_string(s):
    return s.translate(_ENCODE_TABLE)

def decode_string(s):
    return s.translate(_DECODE_TABLE)

#=============================================================
# NEXTFLOW CONFIG FILES (PROFILES)
#=============================================================

#Function that removes the comments ('//' and '/* */') from a config, without touching the strings
def remove_comments_config(code):
    result, i, quote = [], 0, None
    while(i<len(code)):
        c = code[i]
        if(quote):
            result.append(c)
            if(c=="\\" and i+1<len(code)):
                result.append(code[i+1])
                i+=1
            elif(c==quote):
                quote = None
        elif(c in ["'", '"']):
            quote = c
            result.append(c)
        elif(code.startswith("//", i)):
            while(i<len(code) and code[i]!="\n"):
                i+=1
            continue
        elif(code.startswith("/*", i)):
            end = code.find("*/", i+2)
            i = len(code) if end==-1 else end+2
            continue
        else:
            result.append(c)
        i+=1
    return "".join(result)

#Function that returns the index of the '}' closing the '{' at the index 'start' (ignoring the strings)
def get_closing_curly_config(code, start):
    depth, i, quote = 0, start, None
    while(i<len(code)):
        c = code[i]
        if(quote):
            if(c=="\\"):
                i+=1
            elif(c==quote):
                quote = None
        elif(c in ["'", '"']):
            quote = c
        elif(c=="{"):
            depth+=1
        elif(c=="}"):
            depth-=1
            if(depth==0):
                return i
        i+=1
    return len(code)-1

#Function that reads a config file (without comments) and recursively inlines the 'includeConfig' files
def read_config_with_includes(address, root, seen = None):
    if(seen is None):
        seen = set()
    address = os.path.normpath(address)
    if(address in seen or not os.path.isfile(address)):
        return ""
    seen.add(address)
    try:
        with open(address, 'r', encoding='utf-8', errors='replace') as f:
            code = remove_comments_config(f.read())
    except OSError:
        return ""
    directory = os.path.dirname(address)
    def replace_include(match):
        path = match.group(2)
        for var in ["projectDir", "baseDir", "launchDir"]:
            path = re.sub(r"\$\{?\s*(workflow\.)?"+var+r"\s*\}?", root.rstrip('/'), path)
        if("$" in path):
            return ""
        if(not os.path.isabs(path)):
            path = os.path.join(directory, path)
        return "\n"+read_config_with_includes(path, root, seen)+"\n"
    return re.sub(r"\bincludeConfig\s*\(?\s*(['\"])(.+?)\1\s*\)?", replace_include, code)

#Function that extracts the profiles defined in a config -> returns a dico {name_profile: code_profile}
#The profiles can be defined as 'profiles { name { ... } }', 'profiles.name { ... }' or 'profiles.name.x = y'
def extract_profiles_config(code):
    profiles = {}
    def add(name, body):
        profiles[name] = profiles.get(name, "")+"\n"+body
    name_pattern = r"(['\"]?)([\w\-]+)\1"
    #profiles { name { ... } }
    for match in re.finditer(r"\bprofiles\s*\{", code):
        start = match.end()-1
        end = get_closing_curly_config(code, start)
        block = code[start+1:end]
        pos = 0
        while(True):
            m = re.compile(name_pattern+r"\s*\{").search(block, pos)
            if(not m):
                break
            close = get_closing_curly_config(block, m.end()-1)
            add(m.group(2), block[m.end():close])
            pos = close+1
    #profiles.name { ... }
    for match in re.finditer(r"\bprofiles\s*\.\s*"+name_pattern+r"\s*\{", code):
        close = get_closing_curly_config(code, match.end()-1)
        add(match.group(2), code[match.end():close])
    #profiles.name.x = y
    for match in re.finditer(r"\bprofiles\s*\.\s*"+name_pattern+r"\s*\.([^\n]*)", code):
        add(match.group(2), match.group(3))
    return profiles

#Function that checks if a profile code enables one of the given scopes (e.g. 'docker.enabled = true' or 'docker { enabled = true }')
def profile_enables_scope(code, scopes):
    for scope in scopes:
        if(re.search(r"\b"+scope+r"\s*\.\s*enabled\s*=\s*true\b", code)):
            return True
        for match in re.finditer(r"\b"+scope+r"\s*\{", code):
            close = get_closing_curly_config(code, match.end()-1)
            if(re.search(r"\benabled\s*=\s*true\b", code[match.end():close])):
                return True
    return False


#Function that checks if a piece of code (an executor) uses the pipe operator '|'
#The '|' in strings, in closures/parentheses/lists and the '||' are ignored
def uses_pipe_operator(code):
    code = code.replace("||", "  ")
    depth, quote, i = 0, None, 0
    while(i<len(code)):
        c = code[i]
        if(quote):
            if(c=="\\"):
                i+=1
            elif(c==quote):
                quote = None
        elif(c in ["'", '"']):
            quote = c
        elif(c in "({["):
            depth+=1
        elif(c in ")}]"):
            depth-=1
        elif(c=="|" and depth==0):
            return True
        i+=1
    return False

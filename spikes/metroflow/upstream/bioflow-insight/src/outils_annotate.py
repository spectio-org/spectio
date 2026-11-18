#Import dependencies

#Outside packages
import re

tools = []
commands = []




def get_propositions(process, tools = -1, commands = -1):
    temp = []
    if(tools!=-1):
        for tool in tools:
            for match in re.finditer(r"(\s|\(|\/|\|)"+tool+r"(\s|\-|\\|\.)", process):
                temp.append(tool)
    if(commands!=-1):
        for c in commands:
            tool, command = c.split()
            command = command.replace('+', '\+')
            for match in re.finditer(tool+r"\s+\-[^\s]+\s+"+command, process):
                temp.append(c)
            for match in re.finditer(tool+r"\s+"+command, process):
                temp.append(c)
            for match in re.finditer(tool+r"\s+\\\s+"+command, process):
                temp.append(c)
            for match in re.finditer(tool+r"\s+\-[^\s]+\s+[^\s]+\s+"+command, process):
                temp.append(c)
            for match in re.finditer(tool+r"\.\w+\s+"+command, process):
                temp.append(c)
            for match in re.finditer(tool+r"\.jar\s+[^\s]+\s+"+command, process):
                temp.append(c)

    return list(set(temp))


def get_propositions_from_user():
    propositions = []
    nb_prop = 1
    input_val = "a"
    while(input_val!=""):
        input_val = input(f"Proposition {nb_prop} : ")
        if(input_val!=""):
            propositions.append(input_val)
        nb_prop+=1
    return propositions

def print_colored_words(text, words):
    temp_words = []
    for word in words:
        temp_words+= word.split()
    words = temp_words

    colors = ['\033[31m', '\033[32m', '\033[33m', '\033[34m', '\033[35m', '\033[36m']  # Colors: Red, Green, Yellow, Blue, Magenta, Cyan
    color_index = 0
    
    for i in range(len(words)):
        word = words[i]
        color = colors[color_index % len(colors)]
        text = text.replace(word, f"{color}{word}\033[0m")
        color_index += 1
    print(text)

def get_tools_commands_from_user_for_process(p, exiting_tools, existing_commands):
    tools_found, commands_found = [], []
    codes = []
    codes.append(p.get_code())
    codes+=p.get_external_scripts_code()

    for c in codes:
        print_colored_words(c, get_propositions(c, commands=existing_commands)+get_propositions(c, tools=exiting_tools))
        print("\nTOOLS")
        confirmation = 'a'
        while(confirmation!=""):
            propositions = get_propositions_from_user()
            confirmation = input(f"Press 'ENTER' to validate this propostion of tools {propositions} (press any key otherwise) : ")
        tools_found += propositions
        print("\nCOMMANDS")
        confirmation = 'a'
        while(confirmation!=""):
            propositions = get_propositions_from_user()
            confirmation = input(f"Press 'ENTER' to validate this propostion of commands {propositions} (press any key otherwise) : ")
        commands_found += propositions
    
    exiting_tools+= tools_found
    existing_commands+= commands_found
    return tools_found, commands_found, exiting_tools, existing_commands



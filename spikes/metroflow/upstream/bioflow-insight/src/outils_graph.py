import graphviz
import copy
import numpy as np
import os
import json
import re
import ctypes

process_id = "src.process.Process"
operation_id = "<src.operation.Operation"


def get_object(address):
    address = int(re.findall(r"\dx\w+", address)[0], base=16)
    return ctypes.cast(address, ctypes.py_object).value


def is_process(node_id):
    if process_id in node_id:
        return True
    return False


def is_operation(node_id):
    if node_id[: len(operation_id)] == operation_id:
        return True
    return False


def add_nodes(dot, dico, label_node=True):
    for n in dico["nodes"]:
        try:
            color = n["color"]
        except:
            color = ""
        try:
            xlabel = n["xlabel"]
        except:
            xlabel = ""
        try:
            fillcolor = n["fillcolor"]
        except:
            fillcolor = ""
        try:
            shape = n["shape"]
        except:
            shape = "nothing"

        if shape == "nothing":
            dot.node(n["id"], "")
        else:
            if label_node:
                # here
                # dot.node(n["id"], "", shape="circle", fillcolor=fillcolor, color = color, style="filled")
                dot.node(
                    n["id"],
                    n["name"],
                    shape=n["shape"],
                    xlabel=xlabel,
                    fillcolor=fillcolor,
                    color=color,
                    style="filled",
                )
            else:
                dot.node(n["id"], "", shape=n["shape"], fillcolor=fillcolor, color=color, style="filled")
                # dot.node(n["id"], n["name"], shape=n["shape"], fillcolor=fillcolor, color=color, style="filled")

    for sub in dico["subworkflows"]:
        with dot.subgraph(name="cluster" + sub) as c:
            add_nodes(c, dico["subworkflows"][sub], label_node=label_node)
            if label_node:
                c.attr(label=sub.split("_$$_")[0])
            else:
                c.attr(label="")


def add_edges(dot, dico, label_edge=True):
    for e in dico["edges"]:
        try:
            colour = e['color']
        except:
            colour = "black"
        if label_edge:
            dot.edge(e['A'], e['B'], label=e['label'], color=colour)
        else:
            dot.edge(e['A'], e['B'], color=colour)

    for sub in dico["subworkflows"]:
        with dot.subgraph(name="cluster" + sub) as c:
            add_edges(dot, dico["subworkflows"][sub], label_edge=label_edge)


def fill_dot(dot, dico, label_node=True, label_edge=True):
    add_nodes(dot, dico, label_node=label_node)
    add_edges(dot, dico, label_edge=label_edge)


def add_nodes_metro(dot, dico, relevant_nodes=-1):
    nodes_relevant = []
    # Recupering the relvant nodes
    if relevant_nodes == -1:
        nodes_relevant = dico["nodes"]
    else:
        for n in dico["nodes"]:
            if n["name"] in relevant_nodes:
                nodes_relevant.append(n)

    for n in dico["nodes"]:
        if n in nodes_relevant:
            # dot.node(n["id"], "", shape="circle", style="filled")
            dot.node(n["id"], "", xlabel=n["name"], shape="circle", style="filled")
        else:
            dot.node(n["id"], n["name"], shape="point", style="filled")

    for sub in dico["subworkflows"]:
        with dot.subgraph(name="cluster" + sub) as c:
            add_nodes_metro(c, dico["subworkflows"][sub], relevant_nodes=relevant_nodes)
            c.attr(label=sub.split("_$$_")[0])


def add_edges_metro(dot, dico):
    for e in dico["edges"]:
        dot.edge(
            e['A'],
            e['B'],
            # arrowhead = "none", #https://graphviz.org/doc/info/arrows.html
            arrowsize="1",  # If the arrowhead is 'none' this parameter doesn't change anything
            penwidth="2",
        )

    for sub in dico["subworkflows"]:
        with dot.subgraph(name="cluster" + sub) as c:
            add_edges_metro(dot, dico["subworkflows"][sub])


def metro_dot(dot, dico, relevant_nodes=-1):
    dot.attr(rankdir='LR')
    dot.attr(ranksep="2")
    add_nodes_metro(dot, dico, relevant_nodes=relevant_nodes)
    add_edges_metro(dot, dico)


def fill_dot_2(dot, dico, label_node=True, label_edge=True):
    def add_nodes(dot, dico, label_node=True):
        for n in dico["nodes"]:
            try:
                color = n["color"]
            except:
                color = ""
            try:
                xlabel = n["xlabel"]
            except:
                xlabel = ""
            try:
                fillcolor = n["fillcolor"]
            except:
                fillcolor = ""
            if label_node:
                dot.node(
                    n["id"],
                    n["name"],
                    shape=n["shape"],
                    xlabel=xlabel,
                    fillcolor=fillcolor,
                    color=color,
                    style="filled",
                )
            else:
                dot.node(n["id"], n["name"], shape=n["shape"], fillcolor=fillcolor, color=color, style="filled")

    add_nodes(dot, dico, label_node=label_node)

    def add_edges(dot, dico, label_edge=True):
        for e in dico["edges"]:
            if label_edge:
                dot.edge(e['A'], e['B'], label=e['label'])
            else:
                dot.edge(e['A'], e['B'])

    add_edges(dot, dico, label_edge=label_edge)

    for sub in dico["subworkflows"]:
        with dot.subgraph(name="cluster" + sub) as c:
            # add_nodes(c, dico["subworkflows"][sub], label_node = label_node)
            # add_edges(dot, dico["subworkflows"][sub], label_edge = label_edge)
            fill_dot(c, dico["subworkflows"][sub], label_node, label_edge)
            c.attr(label=sub.split("_$$_")[0])


def add_legend(filename, render_graphs, dico):
    def get_all_conditions_rec(dico, conditions):
        for e in dico["edges"]:
            try:
                con = e['condition']
                colour = e['color']
                conditions[con] = colour
            except:
                None
        for sub in dico["subworkflows"]:
            get_all_conditions_rec(dico["subworkflows"][sub], conditions)

    def get_all_conditions(dico):
        conditions = {}
        get_all_conditions_rec(dico, conditions)
        return conditions

    conditions = get_all_conditions(dico)
    new_dot = graphviz.Digraph()
    new_dot.attr(rankdir='LR')
    draw = False
    if len(conditions) != 0:
        with new_dot.subgraph(name="cluster" + "_123424653") as c:
            index = 0
            for con in conditions:
                c.node(f'{id(new_dot)}_{index}_0', style='invis')
                c.node(f'{id(new_dot)}_{index}_1', style='invis')
                c.edge(f'{id(new_dot)}_{index}_0', f'{id(new_dot)}_{index}_1', color=conditions[con], label=con)
                index += 1
                draw = True
            c.attr(label="Legend")
    if(draw):
        new_dot.save(filename=f'{filename}_legend.dot')
        if render_graphs:
            new_dot.render(filename=f'{filename}_legend.dot', outfile=f'{filename}_legend.png')


def generate_pos_graph(filename, dico, relevant_nodes=-1, render_graphs=True):
    if render_graphs:
        dot = graphviz.Digraph()
        dot.attr(rankdir='LR')
        fill_dot(dot, dico, False, False)
        bool_add_legend = True
        if bool_add_legend:
            add_legend(filename,render_graphs, dico)
        dot.format = 'dot'
        dot.render(filename=f'{filename}_pos')
        dot.render(filename=f'{filename}_pos', outfile=f'{filename}_pos.png')


def generate_graph_dot(filename, dico, label_node=True, label_edge=True, render_graphs=True, relevant_nodes=-1):
    generate_pos_graph(filename, dico, relevant_nodes, render_graphs=render_graphs)
    # dot = graphviz.Digraph(filename=filename, format='png', comment="temp")
    dot = graphviz.Digraph()
    if relevant_nodes == -1:
        fill_dot(dot, dico, True, label_edge)
    else:
        fill_dot(dot, dico, True, label_edge)
        # metro_dot(dot, dico, relevant_nodes = relevant_nodes)
    bool_add_legend = False
    if bool_add_legend:
        add_legend(filename, render_graphs, dico)
    dot.save(filename=f'{filename}.dot')
    # dot.format = 'dot'
    # dot.render(filename=f'{filename}_pos')
    if render_graphs:
        dot.render(filename=f'{filename}.dot', outfile=f'{filename}.png')


def generate_graph_mermaid(filename, dico, label_node=True, label_edge=True, render_graphs=True):
    txt = "graph TB;\n"

    def get_id(txt):
        import re

        for match in re.finditer(r"object at (\w+)>", txt):
            return match.group(1)

    def quoted(label):
        if not label.strip():
            return label
        return f'"{label}"'

    def get_graph_wo_operations_mermaid_temp(dico, txt, count):
        count += 1
        for node in dico["nodes"]:
            tab = count * "\t"
            if node['name'] == '':
                if label_node:
                    txt += f"{tab}{get_id(node['id'])}(({quoted(node['xlabel'])}));\n"
                else:
                    txt += f"{tab}{get_id(node['id'])}(({' '}));\n"
            else:
                txt += f"{tab}{get_id(node['id'])}({quoted(node['name'])});\n"

        for edge in dico["edges"]:
            tab = count * "\t"
            if label_edge:
                txt += f"{tab}{get_id(edge['A'])}--{quoted(edge['label'])}-->{get_id(edge['B'])};\n"
            else:
                txt += f"{tab}{get_id(edge['A'])}-->{get_id(edge['B'])};\n"
        for subworkflow in dico["subworkflows"]:
            tab = count * "\t"
            txt += f"{tab}subgraph {subworkflow}\n{tab}\tdirection TB;\n"
            count += 1
            txt = get_graph_wo_operations_mermaid_temp(dico["subworkflows"][subworkflow], txt, count)
            count -= 1
            txt += f"{tab}end\n"
        return txt

    txt = get_graph_wo_operations_mermaid_temp(dico, txt, 0)

    with open(f"{filename}.mmd", "w") as text_file:
        text_file.write(txt)


def get_number_simple_loops(link_dico):
    nb = 0
    for node in link_dico:
        if node in link_dico[node]:
            nb += 1
    return nb


def generate_graph(
    filename,
    param_dico,
    label_node=True,
    label_edge=True,
    render_graphs=True,
    dot=True,
    mermaid=False,
    root=False,
    relevant_nodes=-1,
):
    dico = copy.deepcopy(param_dico)
    if root:
        outputs = get_output_nodes(dico)
        inputs = get_input_nodes(dico)
        dico["nodes"].append({"id": "input", "name": "i", "shape": "triangle", "fillcolor": "#ffffff"})
        dico["nodes"].append({"id": "output", "name": "o", "shape": "triangle", "fillcolor": "#ffffff"})
        for out in outputs:
            dico["edges"].append({'A': out, 'B': 'output', "label": ""})
        for input in inputs:
            dico["edges"].append({'A': "input", 'B': input, "label": ""})
    if dot:
        generate_graph_dot(filename, dico, label_node, label_edge, render_graphs, relevant_nodes=relevant_nodes)
    if mermaid:
        generate_graph_mermaid(filename, dico, label_node, label_edge, render_graphs)


# Function that merges to dictionnaries
def merge(x, y):
    return {key: list(set(x.get(key, []) + y.get(key, []))) for key in set(list(x.keys()) + list(y.keys()))}


# This function returns a listof the orphan operations in the graph
def get_id_orphan_operation(graph):
    id_operations = []

    def get_id_operations(graph):
        for node in graph['nodes']:
            if is_operation(node['id']):
                id_operations.append(node['id'])
        for subworkflow in graph["subworkflows"]:
            get_id_operations(graph["subworkflows"][subworkflow])

    def get_dico_operation_is_linked(graph, dico_operation_is_linked):
        # First call
        if dico_operation_is_linked == {}:
            for id in id_operations:
                dico_operation_is_linked[id] = False
        for edge in graph["edges"]:
            dico_operation_is_linked[edge["A"]] = True
            dico_operation_is_linked[edge["B"]] = True
        for subworkflow in graph["subworkflows"]:
            get_dico_operation_is_linked(graph["subworkflows"][subworkflow], dico_operation_is_linked)
        return dico_operation_is_linked

    get_id_operations(graph)
    dico = get_dico_operation_is_linked(graph, {})
    tab = []
    for operation_id in dico:
        if not dico[operation_id]:
            tab.append(operation_id)
    return tab


def graph_dico_wo_orphan_operations(graph_tmp):
    graph = copy.deepcopy(graph_tmp)
    orphans = get_id_orphan_operation(graph)

    def remove_orphans(graph, orphans):
        to_remove = []
        for node in graph["nodes"]:
            if node["id"] in orphans:
                to_remove.append(node)
        for r in to_remove:
            try:
                graph["nodes"].remove(r)
            except:
                None
        for subworkflow in graph["subworkflows"]:
            remove_orphans(graph["subworkflows"][subworkflow], orphans)

    remove_orphans(graph, orphans)
    return graph


# Function that returns the type of a given node
def get_type_node(node):
    if is_process(node['id']):
        return "Process"
    else:
        if node["fillcolor"] == "white":
            return "Branch Operation"
        else:
            return "Create Operation"


# Function that creates the link dico from a given graph dico
def initia_link_dico_rec(dico):
    links = {}
    for node in dico['nodes']:
        try:
            temp = links[node['id']]
        except:
            links[node['id']] = []
    for edge in dico['edges']:
        A = edge['A']
        B = edge['B']
        try:
            temp = links[A]
        except:
            links[A] = []
        links[A].append(B)

    for sub in dico['subworkflows']:
        links = merge(links, initia_link_dico_rec(dico['subworkflows'][sub]))
    return links


# Returns the number of cycles in a graph (rootes with "Source" and "Sink")
# The input parameter is a links dico
# https://en.wikipedia.org/wiki/Cycle_(graph_theory)#Algorithm
def get_number_cycles(links):
    dico_nb_cycles = {'nb': 0}
    dfs_dico = {}
    for node in links:
        dfs_dico[node] = {}
        dfs_dico[node]['visited'] = False
        dfs_dico[node]['finished'] = False

    edges_create_cycles = []

    def DFS(mother):
        if dfs_dico[mother]["finished"]:
            return
        if dfs_dico[mother]["visited"]:
            dico_nb_cycles["nb"] += 1
            return "found cycle"
        dfs_dico[mother]["visited"] = True
        for daughter in links[mother]:
            _ = DFS(daughter)
            if _ == "found cycle":
                edges_create_cycles.append((mother, daughter))
        dfs_dico[mother]["finished"] = True

    for node in links:
        DFS(node)
    return dico_nb_cycles['nb'], edges_create_cycles


# https://en.wikipedia.org/wiki/Topological_sorting#Depth-first_search
def topological_sort(graph):
    L = []  # Empty list that will contain the sorted nodes
    temporary_marks = set()
    permanent_marks = set()

    def visit(node):
        if node in permanent_marks:
            return

        if node in temporary_marks:
            None
            # raise ValueError("Graph has at least one cycle")
        else:
            temporary_marks.add(node)

            for neighbor in graph.get(node, []):
                visit(neighbor)

            temporary_marks.remove(node)
            permanent_marks.add(node)
            L.insert(0, node)  # add node to head of L

    while set(graph.keys()) - permanent_marks:
        node = (set(graph.keys()) - permanent_marks).pop()
        visit(node)

    return L


# A variant of this answer https://stackoverflow.com/a/5164820
def get_number_paths_source_2_sink(graph):
    topo_sort = topological_sort(graph)
    dict_paths_from_node_2_sink = {}
    for node in topo_sort:
        dict_paths_from_node_2_sink[node] = 1

    for i in range(len(topo_sort) - 2, -1, -1):
        sum = 0
        for y in range(i + 1, len(topo_sort)):
            sum += graph[topo_sort[i]].count(topo_sort[y]) * dict_paths_from_node_2_sink[topo_sort[y]]
        dict_paths_from_node_2_sink[topo_sort[i]] = sum

    return dict_paths_from_node_2_sink["source"]


# For the shortest path
# https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm#Pseudocode
def dijkstra(graph):
    dist, prev = {}, {}
    Q = []
    for node in graph:
        dist[node] = np.Infinity
        prev[node] = None
        Q.append(node)
    dist['source'] = 0

    def get_node_in_Q_min_dist():
        min, node_min = dist[Q[0]], Q[0]
        for node in Q:
            if min > dist[node]:
                min, node_min = dist[node], node
        return node_min

    while len(Q) > 0:
        u = get_node_in_Q_min_dist()
        Q.remove(u)
        for v in graph[u]:
            if v in Q:
                alt = dist[u] + 1
                if alt < dist[v]:
                    dist[v] = alt
                    prev[v] = u
    return dist["sink"]


# https://www.geeksforgeeks.org/find-longest-path-directed-acyclic-graph/
def get_longest_distance(graph):
    dist = {}
    for node in graph:
        dist[node] = -np.Infinity
    dist["source"] = 0
    topo = topological_sort(graph)
    for u in topo:
        for v in graph[u]:
            if dist[v] < dist[u] + 1:
                dist[v] = dist[u] + 1
    return dist["sink"]


##Returns the of paths, the longest and the shortes (not counting the source and sink)
# def get_paths(links):
#    PATHS = []
#    shortest_path = {"nb":0}
#    longest_path = {"nb":0}
#    nb_paths = {"nb":0}
#
#    def get_paths_temp(links, mother, path_temp):
#        path = path_temp.copy()
#        path.append(mother)
#        if(mother=="Sink"):
#            nb_paths["nb"]+=1
#            if(shortest_path["nb"]==0):
#                shortest_path["nb"] = len(path)
#            if(longest_path["nb"]==0):
#                longest_path["nb"] = len(path)
#            if(longest_path["nb"]<len(path)):
#                longest_path["nb"]=len(path)
#            if(shortest_path["nb"]>len(path)):
#                shortest_path["nb"]=len(path)
#            return
#        for daughter in links[mother]:
#            if(daughter!=mother):
#                if(daughter not in path):
#                    get_paths_temp(links, daughter, path)
#
#
#    get_paths_temp(links, "Source", [])
#    number_paths_source_2_sink = nb_paths["nb"]
#    longest_path = longest_path["nb"]
#    smallest_path = shortest_path["nb"]
#
#    return number_paths_source_2_sink, longest_path, smallest_path


def get_flatten_dico(dico):
    dico_flattened = {}
    dico_flattened["nodes"] = []
    dico_flattened["edges"] = []
    dico_flattened["subworkflows"] = {}
    return flatten_dico_rec(dico, dico_flattened)


def flatten_dico_rec(dico, dico_flattened):
    for node in dico["nodes"]:
        dico_flattened["nodes"].append(node)
    for edge in dico["edges"]:
        dico_flattened["edges"].append(edge)
    for subworkflow in dico["subworkflows"]:
        flatten_dico_rec(dico["subworkflows"][subworkflow], dico_flattened)
    return dico_flattened


# ==================================================
# Get user view
# Je suppose que c'est un dico flatten (avec que des processes) -> process dependency graph


def get_id_from_name(dico, name):
    ids = []
    for n in dico["nodes"]:
        if n['name'] == name:
            ids.append(n['id'])
    return ids


def get_name_from_id(dico, ID):
    names = []
    for n in dico["nodes"]:
        if n['id'] == ID:
            names.append(n['name'])
    if ID == "output":
        names.append("output")
    if ID == "input":
        names.append("input")
    return names


def get_output_nodes(dico):
    edges = get_all_edges(dico)
    N = get_all_nodes_id(dico)
    none_outputs = []
    for e in edges:
        none_outputs.append(e['A'])
    outputs = list(set(N) - set(none_outputs))
    # outputs_names = []
    # for o in outputs:
    #    outputs_names+=get_name_from_id(dico=dico, ID=o)
    return outputs


def get_input_nodes(dico):
    edges = get_all_edges(dico)
    N = get_all_nodes_id(dico)

    none_inputs = []
    for e in edges:
        none_inputs.append(e['B'])
    inputs = list(set(N) - set(none_inputs))
    # inputs_names = []
    # for o in inputs:
    #    inputs_names+=get_name_from_id(dico=dico, ID=o)
    return inputs


def remove_edges_with_node(edges, nodes):
    edges_without_node = []
    for e in edges:
        if e['A'] not in nodes and e['B'] not in nodes:
            edges_without_node.append(e)
    return edges_without_node


def get_nodes_from_edges(edges):
    N = []
    for e in edges:
        N.append(e['A'])
        N.append(e['B'])
    return list(set(N))


def get_neighbors(edges, A):
    Bs = []
    for e in edges:
        if e['A'] == A:
            Bs.append(e['B'])
    return Bs


def exist_path_rec(A, B, edges, visited):
    visited[A] = True
    if A == B:
        return True
    for neigh in get_neighbors(edges, A):
        if not visited[neigh]:
            if exist_path_rec(neigh, B, edges, visited=visited):
                return True
    return False


def exist_path(A, B, edges):
    N = get_nodes_from_edges(edges=edges)
    visited = {}
    for n in N:
        visited[n] = False
    exists = exist_path_rec(A, B, edges, visited)
    return exists, visited


def get_edges(dico, val=[]):
    val += dico["edges"]
    for sub in dico["subworkflows"]:
        val = get_edges(dico["subworkflows"][sub], val)
    return val


def exist_path_dico(A, B, dico):
    edges = get_edges(dico)
    exists, visited = exist_path(A, B, edges)
    return exists, visited


# def nr_path_succ(n, r, dico, R):
#    rest_of_R = set(R)-set([r])
#    edges = remove_edges_with_node(dico["edges"], rest_of_R)
#    exists, _ = exist_path(n, r, edges)
#    if(exists):
#        return True
#    return False


path_exists = {}


def nr_path_succ(n, r, dico, R):
    try:
        temp = path_exists[n]
    except:
        path_exists[n] = {}
    try:
        temp = path_exists[n][r]
    except:
        path_exists[n][r] = {}
    rest_of_R = set(R) - set([r])
    try:
        temp = path_exists[n][r][str(rest_of_R)]
        return temp
    except:
        edges = remove_edges_with_node(dico["edges"], rest_of_R)
        exists, _ = exist_path(n, r, edges)
        path_exists[n][r][str(rest_of_R)] = exists
        return exists


# def nr_path_pred(r, n, dico, R):
#    rest_of_R = set(R)-set([r])
#    edges = remove_edges_with_node(dico["edges"], rest_of_R)
#    exists, _ = exist_path(r, n, edges)
#    if(exists):
#        return True
#    return False


def nr_path_pred(r, n, dico, R):
    try:
        temp = path_exists[r]
    except:
        path_exists[r] = {}
    try:
        temp = path_exists[r][n]
    except:
        path_exists[r][n] = {}
    rest_of_R = set(R) - set([r])
    try:
        temp = path_exists[r][n][str(rest_of_R)]
        return temp
    except:
        edges = remove_edges_with_node(dico["edges"], rest_of_R)
        exists, _ = exist_path(r, n, edges)
        path_exists[r][n][str(rest_of_R)] = exists
        return exists


##Added a dico so it knows what it's already searched
# dico_rSucc = {}
# def rSucc(n, dico, R, outputs):
#    #try:
#    #    tab = dico_rSucc[n]
#    #except:
#    tab = []
#    for r in set(R).union(set(outputs)):
#        if(nr_path_succ(n, r, dico, R+list(outputs))):
#            tab.append(r)
#    dico_rSucc[n] = tab
#    return tab

# Added a dico so it knows what it's already searched
dico_rSucc = {}


def rSucc(n, dico, R, outputs):
    try:
        temp = dico_rSucc[n]
    except:
        dico_rSucc[n] = {}
    union_set = set(R).union(set(outputs))
    try:
        temp = dico_rSucc[n][str(union_set)]
        return temp
    except:
        tab = []
        for r in union_set:
            if nr_path_succ(n, r, dico, R + list(outputs)):
                tab.append(r)
        dico_rSucc[n][str(union_set)] = tab
        return tab


def rSuccM(M, dico, R, outputs):
    tab = []
    for n in M:
        tab += rSucc(n, dico, R, outputs)
    return list(set(tab))


# Added a dico so it knows what it's already searched
# dico_rPred = {}
# def rPred(n, dico, R, inputs):
#    #try:
#    #    tab = dico_rPred[n]
#    #except:
#    tab = []
#    for r in set(R).union(set(inputs)):
#        if(nr_path_pred(r, n, dico, R+list(inputs))):
#            tab.append(r)
#    dico_rPred[n] = tab
#    return tab

# Added a dico so it knows what it's already searched
dico_rPred = {}


def rPred(n, dico, R, inputs):
    try:
        temp = dico_rPred[n]
    except:
        dico_rPred[n] = {}
    union_set = set(R).union(set(inputs))
    try:
        temp = dico_rPred[n][str(union_set)]
        return temp
    except:
        tab = []
        for r in union_set:
            if nr_path_pred(r, n, dico, R + list(inputs)):
                tab.append(r)
        dico_rPred[n][str(union_set)] = tab
        return tab


def rPredM(M, dico, R, inputs):
    tab = []
    for n in M:
        tab += rPred(n, dico, R, inputs)
    return list(set(tab))


def generate_subsets(original_set):
    # Base case: If the set is empty, return a set with the empty subset
    if not original_set:
        return [[]]

    # Recursive step: Take one element from the set
    first_element = original_set[0]
    rest_set = original_set[1:]

    # Recursively find all subsets of the remaining elements
    subsets_without_first = generate_subsets(rest_set)

    # For each subset, add the first element to create new subsets
    subsets_with_first = [subset + first_element for subset in subsets_without_first]

    # Return all subsets (with and without the first element)
    return subsets_without_first + subsets_with_first


def set_has_incoming_edge_different_M(dico, M):
    tab = []
    for n in M:
        for edge in dico["edges"]:
            if edge['B'] == n and (edge['A'] not in M):
                tab.append(n)
    return list(set(tab))


def set_has_outcoming_edge_different_M(dico, M):
    tab = []
    for n in M:
        for edge in dico["edges"]:
            if edge['A'] == n and (edge['B'] not in M):
                tab.append(n)
    return list(set(tab))


def get_names_tab(dico, tab):
    final = []
    for group in tab:
        if type(group) == str:
            names = get_name_from_id(dico, group)
        else:
            names = []
            for node in group:
                names += get_name_from_id(dico, node)
        final.append(names)
    return final


def get_name_new_node(new_nodes, relevant_modules, tag, alias_2_tools):
    for r in relevant_modules:
        for new in new_nodes:
            if r in new:
                return r
    if alias_2_tools == {}:
        # Arbitrary choice of choosing the name with the longest name
        longest_name = new_nodes[0][0]
        for name in new_nodes:
            if len(longest_name) < len(name[0]):
                longest_name = name[0]
        return longest_name
    else:
        # We choose the process which has the "rarest" tool process
        names = []
        for name in new_nodes:
            process_name = name[0].split(tag)[0]
            if process_name != "":
                names.append(process_name)
        if names == []:
            return new_nodes[0][0]
        else:
            OG_path = os.getcwd()
            # Change working directory to the one of the file
            os.chdir("/".join((str(__file__).split("/")[:-1])))
            with open("../ressources/tool_2_nb_usage.json", 'r') as file:
                tool_2_nb_usage = json.load(file)
            os.chdir(OG_path)

            min_tool, min_process = np.inf, names[0]
            for alias in names:
                try:
                    tools = alias_2_tools[alias]
                except:
                    tools = [""]
                for t in tools:
                    try:
                        val = tool_2_nb_usage[t]
                        if t in [
                            'python',
                            'r',
                            'perl',
                            'julia',
                        ]:  # Cause in this case it is a custom script -> one should hope that it is important in this case
                            val = 1
                    except:
                        val = 1
                    if val < min_tool:
                        min_tool = val
                        min_process = alias
            return min_process


def check_same_elements(list1, list2):
    return set(list1) == set(list2)


def rgb_to_hex(r, g, b):
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)


def get_color_node(node, new_nodes):
    max = len(new_nodes[0])
    for n in new_nodes:
        if len(n) > max:
            max = len(n)
    prop = 256 - int(127 * len(node) / max)
    return rgb_to_hex(prop, prop, prop)


def relev_user_view_builder(dico_param, relevant_modules):
    import time

    dico = copy.deepcopy(dico_param)
    tag = str(time.time())

    # Add this to simplify the use of duplicate processes
    nodes_2_num = {}
    for node in dico["nodes"]:
        nodes_2_num[node['name']] = 0
    for node in dico["nodes"]:
        tmp = nodes_2_num[node['name']]
        nodes_2_num[node['name']] += 1
        node['name'] = f"{node['name']}{tag}{tmp}"
    tab_temp = []
    for n in relevant_modules:
        for i in range(0, nodes_2_num[n]):
            tab_temp.append(f"{n}{tag}{i}")
    relevant_modules = tab_temp

    R = []
    for r in relevant_modules:
        R += get_id_from_name(dico, r)
    R = list(set(R))
    outputs = get_output_nodes(dico)
    inputs = get_input_nodes(dico)
    # dico['nodes'].append({'id':"input", 'name':"input"})
    # dico['nodes'].append({'id':"output", 'name':"output"})
    for out in outputs:
        dico["edges"].append({'A': out, 'B': 'output'})
    # dico["edges"].append({'A':get_id_from_name(dico, f"M5_0{tag}0")[0], 'B':'output'})
    for input in inputs:
        dico["edges"].append({'A': "input", 'B': input})
    U = []
    # Step 1
    marked_statues = {}
    N = []
    for n in dico["nodes"]:
        #    marked_statues[n['name']] = "marked"
        N.append(n['id'])
    N_minus_R = set(N) - set(R)
    for n in N_minus_R:
        marked_statues[n] = "unmarked"
    # Line 3, 4 and 5
    in_r = {}
    for r in R:
        in_r[r] = []
        for n in set(N) - set(R):
            if rSucc(n, dico, R, ["output"]) == [r]:
                in_r[r].append(n)
                marked_statues[n] = "marked"
    # Line 6, 7 and 8
    out_r = {}
    for r in R:
        out_r[r] = []
        for n in set(N) - set(R):
            if rPred(n, dico, R, ["input"]) == [r] and marked_statues[n] == "unmarked":
                out_r[r].append(n)
                marked_statues[n] = "marked"

    # Line 10
    for r in R:
        M = set([r]).union(set(in_r[r])).union(set(out_r[r]))
        U.append(list(M))
    # Step 2
    NRC = []
    for n in set(N) - set(R):
        if marked_statues[n] == 'unmarked':

            def condition_line_13(NRC, n, dico, R, inputs, outputs):
                for i in range(len(NRC)):
                    M = NRC[i]
                    if check_same_elements(
                        rPredM(M, dico, R, ["input"]), rPred(n, dico, R, ["input"])
                    ) and check_same_elements(rSuccM(M, dico, R, ['output']), rSucc(n, dico, R, ['output'])):
                        return True, i
                return False, -1

            check, index = condition_line_13(NRC, n, dico, R, ["input"], ['output'])
            if check:
                NRC[index].append(n)
            else:
                M = [n]
                NRC.append(M)

    # Step 3
    changes_in_NRC = True
    while changes_in_NRC:
        changes_in_NRC = False
        temp_NRC = copy.deepcopy(NRC)
        for i in range(len(temp_NRC)):
            M1 = temp_NRC[i]
            for y in range(len(temp_NRC)):
                M2 = temp_NRC[y]
                if i > y:
                    M = M1 + M2
                    # set(M1).union(set(M2))
                    V_minus = set_has_incoming_edge_different_M(dico, M)
                    V_plus = set_has_outcoming_edge_different_M(dico, M)
                    # Line 23
                    condition_left, condition_right = True, True
                    for n in V_plus:
                        if not check_same_elements(rPred(n, dico, R, ['input']), rPredM(M, dico, R, ["input"])):
                            condition_left = False
                    for n in V_minus:
                        if not check_same_elements(rSucc(n, dico, R, ['output']), rSuccM(M, dico, R, ["output"])):
                            condition_left = False
                    if condition_left and condition_right:
                        NRC.remove(M1)
                        NRC.remove(M2)
                        NRC.append(M)
                        changes_in_NRC = True
                        break
                if changes_in_NRC:
                    break
            if changes_in_NRC:
                break

    new_nodes = list(U) + NRC
    # new_dico = {}
    # new_dico["nodes"] = []
    # new_dico["edges"] = []
    # new_dico["subworkflows"] = []
    # for i in range(len(new_nodes)):
    #    new_nodes[i].sort()
    #    new_name = get_name_new_node(get_names_tab(dico, new_nodes[i]), relevant_modules, tag, alias_2_tools)
    #    name_printed = new_name.split(tag)[0]
    #    shape = "rectangle"
    #    if(name_printed==""):
    #        shape = "point"
    #    node = {"id": '_$$_'.join(new_nodes[i]).replace('<', '').replace('>', ''),
    #            "name": name_printed,
    #            "shape": shape,
    #            "xlabel": f"{len(new_nodes[i])}",
    #            "fillcolor": get_color_node(new_nodes[i], new_nodes)}
    #
    #
    #    #If relevant module -> color it differently
    #    if(new_name in relevant_modules):
    #        node["color"] = "#006903"
    #    new_dico["nodes"].append(node)
    # added_edges = []
    # for edge in dico["edges"]:
    #    for i in range(len(new_dico["nodes"])):
    #        nA = new_dico["nodes"][i]
    #        for y in range(len(new_dico["nodes"])):
    #            if(i!=y):
    #                nB = new_dico["nodes"][y]
    #                edge_string = f'{nA["id"]}->{nB["id"]}'
    #                if(edge["A"].replace('<', '').replace('>', '') in nA["id"]
    #                   and edge["B"].replace('<', '').replace('>', '') in nB["id"]
    #                   and edge_string not in added_edges):#So we don't have dupliacte edges
    #                    new_dico["edges"].append({
    #                        "A": nA["id"],
    #                        "B": nB["id"],
    #                        "label": ""
    #                        })
    #                    added_edges.append(edge_string)

    # The output nodes are the nodes which their outputs aren't connected to anything else
    # remove these comments if you want to root the graph
    # outputs = get_output_nodes(new_dico)
    # inputs = get_input_nodes(new_dico)
    # new_dico["nodes"].append({"id": "input","name": "i","shape": "triangle", "fillcolor":"#ffffff"})
    # new_dico["nodes"].append({"id": "output","name": "o","shape": "triangle", "fillcolor":"#ffffff"})
    # for out in outputs:
    #    new_dico["edges"].append({'A':out, 'B':'output', "label": ""})
    # for input in inputs:
    #    new_dico["edges"].append({'A':"input", 'B':input, "label": ""})
    new_nodes_reel_objects = []
    for group in new_nodes:
        tab = []
        for c in group:
            tab.append(get_object(c))
        new_nodes_reel_objects.append(tab)
    return new_nodes_reel_objects


# This function fills the new_dico with the flattened_dico but
# reintegrates the subworkflows (from the full workflow)
def add_subworkflows_2_dico(full_dico, flattened_dico, add_root_nodes=True):
    # Add nodes with subworkflows
    def add_nodes(full_dico, flattened_dico):
        new_dico = {}
        new_dico['nodes'] = []
        new_dico['edges'] = []
        new_dico['subworkflows'] = {}
        for n1 in full_dico["nodes"]:
            for n2 in flattened_dico["nodes"]:
                if n1['id'][1:-1] in n2['id'] and n1['name'] == n2['name']:
                    new_dico["nodes"].append(n2)
        for sub in full_dico["subworkflows"]:
            new_dico['subworkflows'][sub] = add_nodes(full_dico["subworkflows"][sub], flattened_dico)
        return new_dico

    new_dico = add_nodes(full_dico, flattened_dico)
    new_dico["edges"] = flattened_dico["edges"]
    # if(add_root_nodes):
    #    new_dico["nodes"].append({"id": "input","name": "i","shape": "triangle", "fillcolor":"#ffffff"})
    #    new_dico["nodes"].append({"id": "output","name": "o","shape": "triangle", "fillcolor":"#ffffff"})
    return new_dico


def get_max_level(dico, val=0):
    max_val = val
    for sub in dico["subworkflows"]:
        tmp = get_max_level(dico["subworkflows"][sub], val=val + 1)
        if max_val < tmp:
            max_val = tmp
    return max_val


# Function that fills the dictionnary node_2_subworkflows
def fill_node_2_subworkflows(dico, node_2_subworkflows, back_log_subworklows=[]):
    for n in dico["nodes"]:
        node_2_subworkflows[n['id']] = back_log_subworklows
    for sub in dico["subworkflows"]:
        fill_node_2_subworkflows(dico["subworkflows"][sub], node_2_subworkflows, back_log_subworklows + [sub])


def get_all_edges(dico):
    edges = []
    edges += dico["edges"]
    for sub in dico["subworkflows"]:
        edges += get_all_edges(dico["subworkflows"][sub])
    return edges


def get_all_nodes_id(dico):
    nodes = []
    for n in dico["nodes"]:
        nodes.append(n["id"])
    for sub in dico["subworkflows"]:
        nodes += get_all_nodes_id(dico["subworkflows"][sub])
    return nodes


def get_graph_level_l(dico, level):
    import time

    tag = str(time.time())

    node_2_subworkflows = {}
    fill_node_2_subworkflows(dico, node_2_subworkflows)

    def add_nodes(dico, level, current_level):
        new_dico = {}
        new_dico['nodes'] = []
        new_dico['edges'] = []
        new_dico['subworkflows'] = {}
        for n in dico["nodes"]:
            new_dico["nodes"].append(n)
        if current_level == level:
            for sub in dico["subworkflows"]:
                n = {"id": f"id_{tag}_{sub}", "name": sub, "shape": "rectangle", "fillcolor": "#FFA500"}
                new_dico["nodes"].append(n)
        else:
            for sub in dico["subworkflows"]:
                new_dico['subworkflows'][sub] = add_nodes(dico["subworkflows"][sub], level, current_level + 1)
        return new_dico

    new_dico = add_nodes(dico, level, current_level=0)

    already_added = []
    for edge in get_all_edges(dico):
        tmp = -1
        # Case A and B not in the level
        if len(node_2_subworkflows[edge['A']]) <= level and len(node_2_subworkflows[edge['B']]) <= level:
            new_dico['edges'].append(edge)

        # Case A and B are in the level
        elif len(node_2_subworkflows[edge['A']]) > level and len(node_2_subworkflows[edge['B']]) > level:
            sub1 = node_2_subworkflows[edge['A']][level]
            sub2 = node_2_subworkflows[edge['B']][level]
            if sub1 != sub2:
                tmp = {'A': f"id_{tag}_{sub1}", 'B': f"id_{tag}_{sub2}", "label": ""}

        # Case A in level but not B
        elif len(node_2_subworkflows[edge['A']]) <= level and len(node_2_subworkflows[edge['B']]) > level:
            sub2 = node_2_subworkflows[edge['B']][level]
            tmp = {'A': edge['A'], 'B': f"id_{tag}_{sub2}", "label": ""}

        # Case B in level but not A
        elif len(node_2_subworkflows[edge['A']]) > level and len(node_2_subworkflows[edge['B']]) <= level:
            sub1 = node_2_subworkflows[edge['A']][level]
            tmp = {'A': f"id_{tag}_{sub1}", 'B': edge['B'], "label": ""}
        else:
            raise Exception("This shloudn't happen")

        if tmp != -1 and tmp not in already_added:
            already_added.append(tmp)
            new_dico['edges'].append(tmp)

    return new_dico


def get_number_of_subworkflows(dico, val=0):
    for sub in dico["subworkflows"]:
        if dico["subworkflows"][sub]["nodes"] != []:
            val += 1
        val = get_number_of_subworkflows(dico["subworkflows"][sub], val)
    return val


def get_subworkflows_names(dico, val=[]):
    for sub in dico["subworkflows"]:
        if dico["subworkflows"][sub]["nodes"] != []:
            val.append(sub)
        val = get_subworkflows_names(dico["subworkflows"][sub], val)
    return val


def get_subworkflows_2_elements(workflow):
    result = {}

    def collect_nodes(subworkflows, parent_name=""):
        for sub_name, sub_data in subworkflows.items():
            all_nodes = sub_data.get('nodes', []).copy()

            def get_nested_nodes(data):
                nodes = []
                for nested_sub in data.get('subworkflows', {}).values():
                    nodes.extend(nested_sub.get('nodes', []))
                    nodes.extend(get_nested_nodes(nested_sub))
                return nodes

            all_nodes.extend(get_nested_nodes(sub_data))

            result[sub_name] = all_nodes

            if sub_data.get('subworkflows'):
                collect_nodes(sub_data['subworkflows'], sub_name)

    collect_nodes(workflow.get('subworkflows', {}))
    return result


# WARNING: The method i'm using isn't perfect (i'm not claiming it is)-> but it works well enough for what i want to use it for:)
def check_if_equal(dicoA, dicoB):
    def translate_dico(dico):
        names_already_given = []

        def get_ids_2_nodes(dico, ids_2_nodes):
            for node in dico['nodes']:
                already_in, index = True, 0
                # We assume the name is not already given
                while already_in:
                    if "src.operation.Operation" in node["id"]:
                        val = f"operation_{node['xlabel']}__££__{index}"
                    elif "src.process.Process" in node["id"]:
                        val = f"process_{node['name'].split('_GG_')[0]}__££__{index}"
                    if val in names_already_given:
                        index += 1
                    else:
                        already_in = False
                        names_already_given.append(val)
                        ids_2_nodes[node["id"]] = val
            for sub in dico['subworkflows']:
                get_ids_2_nodes(dico['subworkflows'][sub], ids_2_nodes)

        ids_2_nodes = {}
        get_ids_2_nodes(dico, ids_2_nodes=ids_2_nodes)

        # We have to sort the lists if they are not in the same order
        # I don't want to use "set" cause it would remove the duplicate cases
        def sort(tab):
            try:
                # Case it's a list of words
                # Nodes
                tab.sort()
                return tab
            except:
                # Edges
                temp = []
                for e in tab:
                    temp.append(f"{e['A']}__$$__{e['B']}")
                temp.sort()
                new_tab = []
                for e in temp:
                    A, B = e.split("__$$__")
                    new_tab.append({"A": A, "B": B})
                return new_tab

        def rewrite(dico, rewritten):
            for node in dico['nodes']:
                rewritten["nodes"].append(ids_2_nodes[node['id']].split("__££__")[0])
            rewritten["nodes"] = sort(rewritten["nodes"])
            for edge in dico['edges']:
                rewritten["edges"].append(
                    {"A": ids_2_nodes[edge['A']].split("__££__")[0], "B": ids_2_nodes[edge['B']].split("__££__")[0]}
                )
            rewritten["edges"] = sort(rewritten["edges"])
            for sub in dico['subworkflows']:
                temp = {}
                temp["nodes"] = []
                temp["edges"] = []
                temp["subworkflows"] = {}
                rewrite(dico["subworkflows"][sub], temp)
                rewritten["subworkflows"][sub] = temp

        translated = {}
        translated["nodes"] = []
        translated["edges"] = []
        translated["subworkflows"] = {}
        rewrite(dico, translated)
        return translated

    translated_new, translated_original = translate_dico(dicoA), translate_dico(dicoB)
    # TO do that we rewrite the structure using a commun language (without using the ids) -> then just check if the translated structures are the same
    equal = translated_new == translated_original
    from collections import Counter

    if not equal:
        if translated_new['nodes'] != translated_original["nodes"]:
            diff = list(Counter(translated_original['nodes']) - Counter(translated_new['nodes']))
            if diff != []:
                print(f"The processes {diff} are missing from the new workflow")
            diff = list(Counter(translated_new['nodes']) - Counter(translated_original['nodes']))
            if diff != []:
                print(f"The processes {diff} have been added to the new workflow")

        if translated_new['edges'] != translated_original["edges"]:
            edges_new, edges_original = [], []
            for e in translated_original['edges']:
                edges_original.append(str(e))
            for e in translated_new['edges']:
                edges_new.append(str(e))
            diff = list(Counter(edges_original) - Counter(edges_new))
            if diff != []:
                print(f"The edges {diff} are missing from the new workflow")
            diff = list(Counter(edges_new) - Counter(edges_original))
            if diff != []:
                print(f"The edges {diff} have been added to the new workflow")
    return equal


# This function removes the artificial nodes from the dico
# MAtching the nodes together between the artificial nodes
def remove_artificial_nodes(param_dico):
    dico = copy.copy(param_dico)

    def get_list_artificial_nodes_rec(dico, tab):
        for n in dico["nodes"]:
            if n["artificial"]:
                tab += [n["id"]]
        for edge in dico["edges"]:
            A, B = edge["A"], edge["B"]
            if A not in tab:
                A_obj = get_object(A)
                if A_obj.get_type() == "Operation" and A_obj.get_artificial_status():
                    tab += [A]
            if B not in tab:
                B_obj = get_object(B)
                if B_obj.get_type() == "Operation" and B_obj.get_artificial_status():
                    tab += [B]
        for sub in dico["subworkflows"]:
            tab = get_list_artificial_nodes_rec(dico["subworkflows"][sub], tab)
        return tab

    def get_list_artificial_nodes(dico):
        tab = []
        return get_list_artificial_nodes_rec(dico, tab)

    def remove_node_rec(dico, node_id):
        to_remove = []
        for n in dico["nodes"]:
            if n["id"] == node_id:
                to_remove.append(n)
        for n in to_remove:
            dico["nodes"].remove(n)
        for sub in dico["subworkflows"]:
            remove_node_rec(dico["subworkflows"][sub], node_id)

    def remove_node(dico, node_id):
        remove_node_rec(dico, node_id)

    def get_links_and_remove_edges_rec(dico, node_id, links):
        updated = False
        to_remove = []
        for e in dico["edges"]:
            if e["A"] == node_id:
                links["sink"].append({"sink": e["B"], "label": e["label"]})
                to_remove.append(e)
            elif e["B"] == node_id:
                links["source"].append({"source": e["A"], "label": e["label"]})
                to_remove.append(e)
        for e in to_remove:
            updated = True
            dico["edges"].remove(e)
        for sub in dico["subworkflows"]:
            temp = get_links_and_remove_edges_rec(dico["subworkflows"][sub], node_id, links)
            if not updated:
                updated = temp
        return updated

    def get_links_and_remove_edges(dico, node_id, links):
        return get_links_and_remove_edges_rec(dico, node_id, links)

    artificial = get_list_artificial_nodes(dico)
    for n_id in artificial:
        remove_node(dico, n_id)

    updated = True
    while (
        updated and len(artificial) > 0
    ):  # This is allow to remove recursively the artificial operations even if one is connected to others
        updated = False  
        for n_id in artificial:
            links = {}
            links["source"] = []
            links["sink"] = []
            found = get_links_and_remove_edges(dico, n_id, links)
            if found:
                updated = True 
            for source in links["source"]:
                for sink in links["sink"]:
                    edge = {"A": source['source'], "B": sink['sink'], "label": source['label']}
                    dico["edges"].append(edge)

    return dico


def enrich_json_with_positions(file):
    import json

    with open(file, 'r') as JSON:
        dico = json.load(JSON)

    pos_file = file[: -len(".json")] + "_pos.dot"
    try:
        f = open(pos_file)
        contents_pos = f.read()
        f.close()
        os.remove(pos_file)
    except:
        return

    def search_for_pos(id, text):
        import re

        pattern = re.escape(id) + r'[\s\S]*?(?=pos)pos="([^,]+),([^"]+)",'
        for match in re.finditer(pattern, text):
            return match.group(1), match.group(2)
        return -1, -1

    def enrich_nodes(wf_dico):
        for node in wf_dico["nodes"]:
            id = node['id']
            x_pos, y_pos = search_for_pos(id, contents_pos)
            if x_pos == -1 and y_pos == -1:
                return
            else:
                node['position'] = {}
                node['position']['x'] = str(1.6 * float(x_pos))
                node['position']['y'] = str(1.6 * float(y_pos))
        for sub in wf_dico['subworkflows']:
            # This is the case it is just a generic json given
            try:
                temp = wf_dico['subworkflows'][sub]["edges"]
                enrich_nodes(wf_dico['subworkflows'][sub])
            except:
                None

    enrich_nodes(dico)
    with open(file, 'w') as output_file:
        json.dump(dico, output_file, indent=4)


def get_number_nodes_edges(dico, nodes, edges, subworkflows):
    def get_number_subworkflows_not_empty(sub):
        num = 0
        for s in sub:
            if len(sub[s]['nodes']) > 0 or get_number_subworkflows_not_empty(sub[s]['subworkflows']) > 0:
                num += 1
        return num

    nodes += len(dico['nodes'])
    edges += len(dico['edges'])
    subworkflows += get_number_subworkflows_not_empty(dico['subworkflows'])
    surface_subworkflows = get_number_subworkflows_not_empty(dico['subworkflows'])
    for sub in dico['subworkflows']:
        n, e, s, _ = get_number_nodes_edges(dico["subworkflows"][sub], nodes, edges, subworkflows)
        nodes = n
        edges = e
        subworkflows = s
    return nodes, edges, subworkflows, surface_subworkflows


# This is the optimised implementation of the dominators algorithm
# Presented in the 1979 paper "A Fast Algorithm for Finding Dominators in a Flowgraph"
# By LENGAUER and TARJAN
# It's complexity is in O(|E|α(|E|, |V|)), where α(|E|, |V|) is a functional inverse of Ackermann's function.
def lengauer_tarjan_dominators(successors, root=0):
    n = len(successors)

    parent, ancestor, child, vertex = [0] * (n), [0] * (n), [0] * (n), [0] * (n + 1)
    label, semi, size = [0] * (n + 1), [0] * (n + 1), [0] * (n + 1)
    pred, bucket = [[] for _ in range(n)], [set() for _ in range(n)]
    dom = [0] * n

    def DFS(v):
        nonlocal index
        index += 1
        semi[v] = index
        vertex[index], label[v] = v, v
        ancestor[v], child[v] = 0, 0
        size[v] = 1
        for w in successors[v]:
            if semi[w] == 0:
                parent[w] = v
                DFS(w)
            pred[w].append(v)

    def COMPRESS(v):
        if ancestor[ancestor[v]] != 0:
            COMPRESS(ancestor[v])
            if semi[label[ancestor[v]]] < semi[label[v]]:
                label[v] = label[ancestor[v]]
            ancestor[v] = ancestor[ancestor[v]]

    # EVAL and LINK are both written with the optimisation
    def EVAL(v):
        if ancestor[v] == 0:
            return label[v]
        else:
            COMPRESS(v)
            if semi[label[ancestor[v]]] >= semi[label[v]]:
                return label[v]
            else:
                return label[ancestor[v]]

    def LINK(v, w):
        s = w
        while semi[label[w]] < semi[label[child[s]]]:
            if size[s] + size[child[child[s]]] >= 2 * size[child[s]]:
                ancestor[child[s]] = s
                child[s] = child[child[s]]
            else:
                size[child[s]] = size[s]
                ancestor[s] = child[s]
                s = child[s]

        label[s] = label[w]
        size[v] += size[w]

        if size[v] < 2 * size[w]:
            # The old switcheroo
            temp = child[v]
            child[v] = s
            s = temp

        while s != 0:
            ancestor[s] = v
            s = child[s]

    # STEP1
    # Here index is equivalent to n in the pseudo-code
    index = 0
    DFS(root)
    for i in range(index, 1, -1):
        w = vertex[i]

        # STEP2
        for v in pred[w]:
            u = EVAL(v)
            if semi[u] < semi[w]:
                semi[w] = semi[u]
        bucket[vertex[semi[w]]].add(w)
        LINK(parent[w], w)

        # STEP3
        for v in bucket[parent[w]]:
            u = EVAL(v)
            if semi[u] < semi[v]:
                dom[v] = u
            else:
                dom[v] = parent[w]
        # Removing all the elements at the end instead of one by one
        bucket[parent[w]].clear()

    # STEP4
    for i in range(2, index + 1):
        w = vertex[i]
        if dom[w] != vertex[semi[w]]:
            dom[w] = dom[dom[w]]
    dom[root] = 0
    return dom


def get_parallel_components(dico):
    from graphtheory.structures.edges import Edge
    from graphtheory.structures.graphs import Graph
    from graphtheory.seriesparallel.dsptrees import find_dsptree
    from graphtheory.seriesparallel.spnodes import btree_inorder
    from graphtheory.seriesparallel.spnodes import btree_print2, btree_print
    import networkx as nx

    G = nx.MultiDiGraph()
    nodes_2_id, id_2_nodes = {}, {}

    def add_node(n, index, nodes_2_id, id_2_nodes):
        try:
            temp = nodes_2_id[n]
        except:
            nodes_2_id[n] = index
            id_2_nodes[index] = n
            index += 1
        return index

    index = 0
    edges, edges_networkX = [], []

    for A in dico:
        index = add_node(A, index, nodes_2_id, id_2_nodes)

        for B in dico[A]:
            index = add_node(B, index, nodes_2_id, id_2_nodes)
            edges.append(Edge(nodes_2_id[A], nodes_2_id[B]))
            edges_networkX.append((nodes_2_id[A], nodes_2_id[B]))

    G.add_edges_from(edges_networkX)
    for n in list(id_2_nodes.keys()):
        G.add_node(n)
    if len(list(nx.weakly_connected_components(G))) > 1:
        raise Exception('The graph is not weakly connected')

    nodes_2_sink = []
    nodes_connected_2_source = list(nodes_2_id.keys())
    for A in dico:
        if len(dico[A]) == 0:
            nodes_2_sink.append(A)
        for B in dico[A]:
            try:
                nodes_connected_2_source.remove(B)
            except:
                None

    for node in nodes_connected_2_source:
        edges.append(Edge(index, nodes_2_id[node]))
    index += 1
    for node in nodes_2_sink:
        edges.append(Edge(nodes_2_id[node], index))

    id_2_name = {}
    for id in id_2_nodes:
        id_2_name[id] = id_2_nodes[id].get_alias()

    # print(id_2_name)

    N = len(nodes_2_id) + 2
    nodes = range(N)
    G = Graph(n=N, directed=True)  # directed graph!
    for node in nodes:
        G.add_node(node)
    for edge in edges:
        G.add_edge(edge)
    T = find_dsptree(G)

    def get_component(N, tab):
        tab.append(N.source)
        tab.append(N.target)
        if N.type != 'edge':
            tab += get_component(N.left, [])
            tab += get_component(N.right, [])
        return tab

    def get_parallel_components(T):
        tab = []
        for n in btree_inorder(T):
            if n.type == "parallel":
                tab_left = list(set(get_component(n.left, [])))
                tab_right = list(set(get_component(n.right, [])))
                try:
                    tab_left.remove(n.source)
                except:
                    None
                try:
                    tab_left.remove(n.target)
                except:
                    None
                try:
                    tab_right.remove(n.source)
                except:
                    None
                try:
                    tab_right.remove(n.target)
                except:
                    None
                tab.append(tab_left)
                tab.append(tab_right)
        return tab

    # print(edges)
    # btree_print(T)
    # btree_print2(T)
    parallel_components = get_parallel_components(T)
    tab = []
    for cluster in parallel_components:
        temp = []
        for c in cluster:
            temp.append(id_2_nodes[c])
        tab.append(temp)
    return tab


def check_if_biconnected(dico):
    # A biconnected directed graph is one such that for any two vertices v and w
    # there are two directed paths from v to w which have no vertices in common
    # other than v and w.
    import networkx as nx

    G = nx.MultiDiGraph()
    nodes_2_id, id_2_nodes = {}, {}

    def add_node(n, index, nodes_2_id, id_2_nodes):
        try:
            temp = nodes_2_id[n]
        except:
            nodes_2_id[n] = index
            id_2_nodes[index] = n
            index += 1
        return index

    index = 0

    edges_networkX = []
    for A in dico:
        index = add_node(A, index, nodes_2_id, id_2_nodes)

        for B in dico[A]:
            index = add_node(B, index, nodes_2_id, id_2_nodes)
            edges_networkX.append((nodes_2_id[A], nodes_2_id[B]))

    G.add_edges_from(edges_networkX)

    def is_biconnected_directed(G):
        if G.number_of_nodes() < 2:
            return False

        if not nx.is_strongly_connected(G):
            return False

        for v in G.nodes():
            subgraph = G.copy()
            subgraph.remove_node(v)
            if not nx.is_strongly_connected(subgraph):
                return False
        return True

    return is_biconnected_directed(G)

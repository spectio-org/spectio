from .condition import Condition
from .tree import Tree
from .cloud import Cloud
from .outils import get_basic_blocks
from .outils_graph import get_flatten_dico, lengauer_tarjan_dominators, get_subworkflows_2_elements, get_parallel_components
import copy
import time



def check_all_elements_between_elements_in_the_cluster_are_in_cluster(cluster, link_dico):
    from collections import deque
    tab = [str(c) for c in cluster] 
    for i in range(len(cluster)):
        for y in range(len(cluster)):
            if(i!=y):
                A, B = cluster[i], cluster[y]
                partial_paths= dfs_get_nodes_between_2(link_dico, A, B)
                for path in partial_paths:
                    for n in path:
                        if(n not in cluster):
                            index = path.index(n)
                            pred = path[:index]
                            rest = list(set(cluster)-set(pred))
                            return False, pred, rest
    return True, [], []
            




        #def check_all_paths_are_in_cluster(cluster, all_nodes_in_graph, link_dico):
        #    #Need to check that all the paths between the nodes in cluster are formed by nodes in the cluster
        #    for i in range(len(cluster)):
        #        for y in range(len(cluster)):
        #            if(i!=y):
        #                A, B = cluster[i], cluster[y]
        #                val, paths = explore_all_paths(A, B, all_nodes_in_graph, link_dico)
        #                if(val):
        #                    for path in paths:
        #                        for n in path:
        #                            if(n not in cluster):
        #    
        #                                index = path.index(n)
        #                                pred = path[:index]
        #                                rest = list(set(cluster)-set(pred))
        #                                return False, pred, rest
        #    return True, [], []


#potential_clusters is a dico of condition to nodes associated to it
def create_cluster_rec(potential_clusters, all_nodes_in_graph, id_group, rec, abstraction, link_dico, force_creation = False):
    #Only keep the nodes in the potential_clusters which appear in the last_cluster_created
    #to_remove = []
    #for c in potential_clusters:
    #    for node in potential_clusters[c]:
    #        if(node not in all_nodes_in_graph):
    #            potential_clusters[c].remove(node)
    #    if(potential_clusters[c]==[]):
    #        to_remove.append(c)
    #for r in to_remove:
    #    potential_clusters.pop(r)
    tree = Tree(value="root", condition=None, children = [])
    
    while(len(potential_clusters)>0):
        largest_condition = get_largest_cluster(potential_clusters)
        largest_cluster = potential_clusters[largest_condition]
        potential_clusters.pop(largest_condition)
        can_create_cluster, pred, rest= check_all_elements_between_elements_in_the_cluster_are_in_cluster(largest_cluster, link_dico)
        if(can_create_cluster or force_creation):
            to_remove_from_PC = []
            PC_prime, to_add_to_PC = {}, {}
            for cond in potential_clusters:
                nodes_in_group, nodes_not_in_group = [], []
                
                for n in potential_clusters[cond]:
                    if(n in largest_cluster):
                        nodes_in_group.append(n)
                    else:
                        nodes_not_in_group.append(n)
                
                if(nodes_in_group!=[]):
                    #c = Condition(origin=self, condition=largest_condition.get_value(), artificial=True)
                    PC_prime[cond] = nodes_in_group
                    to_remove_from_PC.append(cond)
                    if(nodes_not_in_group!=[]):
                        c = Condition(origin=abstraction, condition=cond.get_value(), artificial=True)
                        to_add_to_PC[c] = nodes_not_in_group
            
            for cond in to_add_to_PC:
                potential_clusters[cond] = to_add_to_PC[cond].copy()
            for r in to_remove_from_PC:
                potential_clusters.pop(r)
                
            temp= create_cluster_rec(georges_copy_dico(PC_prime), largest_cluster.copy(), id_group, rec+1, abstraction, link_dico, force_creation=force_creation)
            
            id_group['nb']+=1
            temp.update_value(f"{largest_condition.get_value()}")
            temp.set_condition(largest_condition)
            tree.add_child(copy.copy(temp))
            
            
        else:
            cond_pred, cond_rest = Condition(origin=abstraction, condition=largest_condition.get_value(), artificial=True), Condition(origin=abstraction, condition=largest_condition.get_value(), artificial=True)
            potential_clusters[cond_pred] = pred
            potential_clusters[cond_rest] = rest
    leaves = tree.get_all_leafs_in_tree(val={})
    for n in set(all_nodes_in_graph)-set(leaves):
        t = Tree(value=n, condition = None, children = [])
        tree.add_child(t)
    
    return tree



class Abstraction:
    

    def __init__(self, workflow, get_on_process_dependency):
        self.workflow = workflow
        self.potential_clusters = None
        self.number_of_nodes_without_clouds = None
        self.tree = None
        self.get_on_process_dependency = get_on_process_dependency

    def get_number_of_nodes_without_clouds(self):
        if(self.number_of_nodes_without_clouds!=None):
            return self.number_of_nodes_without_clouds
        else:
            raise Exception("Need to run the abstraction first")

    def get_workflow_with_subworkflows(self, full_workflow):
        flat_dico = get_flatten_dico(full_workflow)
        nodes = {}
        for n in flat_dico['nodes']:
            nodes[n['id']] = n

        dico = {}
        dico["nodes"] = []
        dico["edges"] = []
        dico["subworkflows"] = {}
        dico = self.tree.fill_workflow(nodes, dico)
        dico["edges"] = flat_dico["edges"]
        return dico

        
        

    def get_tree(self):
        return self.tree

    #This function returns a dictionnary of condition to operations and calls/processes
    def get_list_of_potential_clusters_2(self):
        stats_on_conditions = {}

        #First start by getting all the conditions and the calls/operations and conditions associated to it
        conditions = self.workflow.get_most_influential_conditions(self.get_on_process_dependency)

        for cond in conditions:
            tab = []
            names = []
            for exe in conditions[cond]:
                tab += get_basic_blocks(exe, {})
            if(self.get_on_process_dependency):
                to_remove = []
                for t in tab:
                    if(t.get_type()=='Operation'):
                        to_remove.append(t)
                for r in set(to_remove):
                    tab = list(filter(lambda a: a != r, tab))
                    
            conditions[cond] = tab



        new_conditions = {}
        for cond in conditions:
            stats_on_conditions[cond.get_value()] = {}
            stats_on_conditions[cond.get_value()]['nb_leafs'] = len(cond.get_leafs({}))
            
            #sum_of_products = cond.get_minimal_sum_of_products()
            #stats_on_conditions[cond.get_value()]['nb_sum_of_products'] = len(sum_of_products)
            #for products in sum_of_products:
            #    val = " & ".join(products)
            #    try:
            #        temp = new_conditions[val]
            #    except:
            #        new_conditions[val] = {"condition":Condition(origin=self, condition=val, artificial=True),
            #                            "elements":[]}
            #    for c in conditions[cond]:
            #        if(c not in new_conditions[val]["elements"]):
            #            new_conditions[val]["elements"].append(c)


            product_of_sums = cond.get_minimal_product_of_sums()
            stats_on_conditions[cond.get_value()]['nb_product_of_sums'] = len(product_of_sums)
            for sums in product_of_sums:
                val = " | ".join(sums)
                try:
                    temp = new_conditions[val]
                except:
                    new_conditions[val] = {"condition":Condition(origin=self, condition=val, artificial=True),
                                        "elements":[]}
                for c in conditions[cond]:
                    if(c not in new_conditions[val]["elements"]):
                        new_conditions[val]["elements"].append(c)
        temp = {}
        for val in new_conditions:
            temp[new_conditions[val]["condition"]] = new_conditions[val]["elements"]
        return temp, stats_on_conditions




    #This function returns a dictionnary of condition to operations and calls/processes
    #def get_list_of_potential_clusters(self):
    #    #First start by getting all the conditions and the calls/operations and conditions associated to it
    #    conditions = self.workflow.get_most_influential_conditions()
    #
    #    
    #    #Decompose the operations and call into their basic form so that for example [call1(call2(operation1))]
    #    #Becomes [[process1, process2, operation1]] -> of course i'm only manipulating the ids
    #    #The goal of this function is that from the elements in the code -> i can manipulate the elements in the graph
    #    def get_basic_blocks(exe, building_blocks):
    #        #In the case of the call -> we extract the process if one is called 
    #        #And decompose its parameters
    #        if(exe.get_type()=="Call"):
    #            if(exe.get_first_element_called().get_type()=="Process"):
    #                building_blocks[exe.get_first_element_called()] = ""
    #            if(exe.get_first_element_called().get_type()=="Subworkflow"):
    #                for temp in exe.get_first_element_called().get_all_executors_in_workflow():
    #                    get_basic_blocks(temp, building_blocks)
    #            for p in exe.parameters:
    #                if(p.get_type() in ["Call", "Operation"]):
    #                    get_basic_blocks(p, building_blocks)
    #        #In the case of an operation -> we add it (if it's not a call to a subworkflow)
    #        #Plus we extract and decompose its origins
    #        elif(exe.get_type()=="Operation"):
    #            if(not(len(exe.get_origins())==1 and exe.get_origins()[0].get_type()=="Call" and exe.get_origins()[0].get_first_element_called().get_type()=="Subworkflow")):
    #                if(not exe.get_artificial_status()):
    #                    building_blocks[exe] = ""
    #            for o in exe.get_origins():
    #                if(o.get_type() in ["Call", "Operation"]):
    #                    get_basic_blocks(o, building_blocks)
    #        #This is for DSL1
    #        elif(exe.get_type()=="Process"):
    #            building_blocks[exe] = ""
    #        else:
    #            raise Exception("This shouldn't happen")
    #        return list(building_blocks.keys())
    #    
    #
    #    for cond in conditions:
    #        tab = []
    #        names = []
    #        for exe in conditions[cond]:
    #            tab += get_basic_blocks(exe, {})
    #        #for t in tab:
    #        #    if(t.get_type()=="Operation"):
    #        #        names.append(t.get_code(get_OG = True))
    #        #    else:
    #        #        names.append(t.get_name())
    #        #print(cond.get_value(), conditions[cond][0].get_code(get_OG = True), names)
    #        #print(tab)
    #        #print()
    #        conditions[cond] = tab
    #    #print(conditions)

        
    #    #This function checks if there is overlapping between the conditions -> if it's the case we add the the larger overlapping group
    #    #It basically does an anlysis of the conditions and when there is an overlapping of the simplified conditions -> it creates a larger group:)
    #    def groups_conditions_together_where_possible(dico_conditions):
    #        conditions = list(dico_conditions)
    #        #print(conditions)
    #        #for c in conditions:
    #        #    print(c.get_value(), c.get_minimal_sum_of_products())
    #        for i in range(len(conditions)):
    #            for y in range(len(conditions)):
    #                if(i>y):
    #                    cond1, cond2 = conditions[i], conditions[y]
    #                    #minimal_sum_of_products_1, minimal_sum_of_products_2 = cond1.get_minimal_sum_of_products(), cond2.get_minimal_sum_of_products()
    #                    #if(minimal_sum_of_products_1==minimal_sum_of_products_2):
    #                    if(cond1.get_value()==cond2.get_value()):
    #                        #print(cond1.get_value(), minimal_sum_of_products_1, cond1)
    #                        #print(cond2.get_value(), minimal_sum_of_products_2, cond2)
    #                        new_conditions = Condition(origin=self, condition=cond1.get_value(), artificial=True)
    #                        #cluster1, cluster2 = dico_conditions[cond1],  dico_conditions[cond2]
    #                        #new_group = cluster1+cluster2
    #                        dico_conditions[cond1]+=dico_conditions[cond2]
    #                        #dico_conditions.pop(cond1)
    #                        dico_conditions.pop(cond2)
    #                        #dico_conditions[new_conditions] = new_group
    #                        return True
    #        
    #
    #
    #        #We do an analysis of the conditions and check if there is an overlapping with the or
    #        dico_conditions_to_expand = {}
    #        for cond in conditions:
    #            minimal_sum_of_products = cond.get_minimal_sum_of_products()
    #            for mini_cond in minimal_sum_of_products:
    #                try:
    #                    temp = dico_conditions_to_expand[str(mini_cond)] 
    #                except:
    #                    dico_conditions_to_expand[str(mini_cond)] = []
    #                dico_conditions_to_expand[str(mini_cond)].append(cond)
    #        #print(dico_conditions_to_expand)
    #        for mini_cond in dico_conditions_to_expand:
    #            if(len(dico_conditions_to_expand[mini_cond])>1):
    #                to_remove = []
    #                new_group = []
    #                value = None
    #                #This means we want to create a larger group
    #                for cond in dico_conditions_to_expand[mini_cond]:
    #                    new_group += dico_conditions[cond]
    #                    if(len(cond.get_minimal_sum_of_products())==1):
    #                        value = cond.get_minimal_sum_of_products()[0]
    #                        to_remove.append(cond)
    #                        #dico_conditions.pop(cond2)
    #                if(value==None):
    #                    for mini in dico_conditions_to_expand[mini_cond][0].get_minimal_sum_of_products():
    #                        if(str(mini)==mini_cond):
    #                            value = mini
    #                new_conditions = Condition(origin=self, condition="&&".join(value), artificial=True)
    #                dico_conditions[new_conditions] = list(set(new_group))
    #                for r in to_remove:
    #                    dico_conditions.pop(r)
    #        
    #
    #            
    #        #
    #        #for i in range(len(conditions)):
    #        #    for y in range(len(conditions)):
    #        #        if(i>y):
    #        #            cond1, cond2 = conditions[i], conditions[y]
    #        #            minimal_sum_of_products_1, minimal_sum_of_products_2 = cond1.get_minimal_sum_of_products(), cond2.get_minimal_sum_of_products()
    #        #            for mini_cond in minimal_sum_of_products_1:
    #        #                if(mini_cond in minimal_sum_of_products_2):
    #        #                    cluster1, cluster2 = dico_conditions[cond1],  dico_conditions[cond2]
    #        #                    if(len(set(cluster1).intersection(set(cluster2)))==0):
    #        #                        print("here")
    #        #                        print(minimal_sum_of_products_1, minimal_sum_of_products_2)
    #        #                        new_conditions = Condition(origin=self, condition="&&".join(mini_cond), artificial=True)
    #        #                        new_group = cluster1+cluster2
    #        #                        if(len(minimal_sum_of_products_1)==1 or cond1.get_artificial()):
    #        #                            dico_conditions.pop(cond1)
    #        #                        if(len(minimal_sum_of_products_2)==1 or cond2.get_artificial()):
    #        #                            dico_conditions.pop(cond2)
    #        #                        dico_conditions[new_conditions] = new_group
    #        #                        return True
    #
    #
    #        return False
    #
    #    #pprint.pp(conditions)
    #    merging_conditions = True
    #    while(merging_conditions):
    #        merging_conditions = groups_conditions_together_where_possible(conditions)
    #    #pprint.pp(conditions)
    #
    #    return conditions

    def get_condition_abtsraction(self):
        
        #STEP1 -> extract potential clusters
        #self.get_list_of_potential_clusters()
        start = time.time()
        conditions, stats_on_conditions = self.get_list_of_potential_clusters_2()
        processes = []
        for grouo in conditions:
            for n in conditions[grouo]:
                if(n.get_type()=="Process"):
                    processes.append(n)
        self.potential_clusters = conditions.copy()
        end = time.time()
        
        #print("STEP1", end- start)
        #From this point we are only manipulating elements which are in the graph
        #potential_clusters = list(conditions.values())


        start = time.time()
        #STEP 1.5 -> retrieving the link dico (without artificial nodes)
        #Plus also retriving the clouds -> these are the operations which are all interconnected together to forming the clouds
        if(not self.get_on_process_dependency):
            link_dico = self.workflow.graph.get_link_dico(bool_get_object = True, without_artificial_nodes = True)
        else:
            link_dico = self.workflow.graph.get_link_dico_process(bool_get_object = True)

        temp = {}
        for n in link_dico:
            temp[str(n)] = [str(c) for c in link_dico[n]]
        end = time.time()
        #print("STEP1.5", end- start)

        start = time.time()
        if(not self.get_on_process_dependency):
            clouds = self.workflow.graph.get_clouds_wo_artificial(bool_get_object = True)
        else:
            clouds = []
        #STEP1.6 -> replacind the clouds by a singe point of type cloud -> which will stock the operations
        #We do this cause by defintion the cloud cannot be split into different conditions
        #So to deal with this we need to simply update the link dico and the conditions dico 
        for cloud in clouds:
            cloud_node = Cloud(operations=cloud)
        
            #Adding the cloud node to the link dico
            link_dico[cloud_node] = link_dico[cloud[0]].copy() 
            #Removing all the operations from the link_dico
            for c in cloud:
                for node in link_dico:
                    if(c in link_dico[node]):
                        tab = list(filter(lambda a: a != c, link_dico[node]))
                        link_dico[node] = tab
                        #link_dico[node].remove(c)
                        if(cloud_node not in link_dico[node] and node!=cloud_node):
                            link_dico[node].append(cloud_node)
                link_dico.pop(c)
            
            #Updating the conditions
            to_remove = []
            for cond in conditions:
                #For a cloud to be in a condition -> the entire cloud needs to be in it
                #If only a subpart of the cloud is in a condition then we remove nodes from the condition
                if(set(cloud).issubset(set(conditions[cond]))):
                    conditions[cond].append(cloud_node)
                for node in cloud:
                    if(node in conditions[cond]):
                        conditions[cond].remove(node)
                if(conditions[cond]==[]):
                    to_remove.append(cond)
            for r in to_remove:
                conditions.pop(r)
        end = time.time()
        #print("STEP1.6", end- start)

        #Retrieve a list of all the nodes in the workflow graph 
        all_nodes_in_graph = []
        for n in link_dico:
            all_nodes_in_graph.append(n)
            all_nodes_in_graph += link_dico[n]
        all_nodes_in_graph = list(set(all_nodes_in_graph))
        self.number_of_nodes_without_clouds = len(all_nodes_in_graph)
        

        
        #This is a function that creates a copy of a 2d list -> i don't know why the the ".copy()" doesn't work as i'm expecting it to 
        def georges_copy_2D_list(list_2D):
            tab = []
            for list in list_2D:
                temp = []
                for ele in list:
                    temp.append(ele)
                tab.append(temp)
            return tab
        
        
    
                    
        ##Step 2 -> Create the clusters    
        #for cond in conditions:
        #    print("-", cond.get_value())
        #    for node in conditions[cond]:
        #        if(node.get_type()=="Process"):
        #            print("   ", node.get_name())
        #        elif(node.get_type()=="Operation"):
        #            print("   ", node.get_code(get_OG = True))
        #        elif(node.get_type()=="Cloud"):
        #            print("   ", "Cloud")
                    
        start = time.time()
        clustering= create_cluster_rec(georges_copy_dico(conditions), all_nodes_in_graph, id_group = {"nb":1}, rec = 0, abstraction=self, link_dico=link_dico)
        end = time.time()
        #print("STEP2", end- start)
        ##Adding the nodes which have been added to the groups
        #leafs = clustering.get_all_leafs_in_tree(val = {})
        #to_add = []
        #for n in all_nodes_in_graph:
        #    if(n not in leafs):
        #        to_add.append(n)
        #clustering.add_children(to_add)
        #
        #
        ##Step 2.5 -> for each leaf in the list, add it's condition
        ##The method also adds the intersection of contions to cluster (intersection of all it's nodes)
        #node_2_conditions = {}
        #for cond in conditions:
        #    for node in conditions[cond]:
        #        try:
        #            temp = node_2_conditions[node]
        #        except:
        #            node_2_conditions[node] = []
        #        node_2_conditions[node].append(cond)
        #clustering.add_conditions_to_tree(node_2_conditions)



        #Step3 -> making the clusters minimal
        #We use the conditions in the tree to do this
        def merge_tree(tree):

            if(not tree.get_minimal()):
                #It's pretty smart -> once a child has been to compared to all of its siblings -> it doesn't need to be compared again
                children = tree.get_children_which_are_not_leaves_which_havent_been_compared_to_all_siblings()
                for i in range(len(children)):
                    child1 = children[i]
                    for y in range(len(children)):
                        if(i>y):
                            child2 = children[y]
                            if(merge_tree(child1) or merge_tree(child2)):
                                return True
                            #if(not tree.checked_if_already_compared_minimal((child1, child2))):
                            if(True):
                                #tree.add_compared_minimal((child1, child2))
                                conditions_in_commun = child1.get_conditions_in_commun(child2)
                                for commun in conditions_in_commun:

                                
                                    G1, G2 = child1.get_all_leafs_in_tree({}), child2.get_all_leafs_in_tree({})
                                    can_create_cluster, _, _= check_all_elements_between_elements_in_the_cluster_are_in_cluster((G1+G2), link_dico)
                                    #This means we need to merge the 2 children together
                                    if(can_create_cluster):
                                        child1.bring_condition_to_the_top(commun[0])
                                        child2.bring_condition_to_the_top(commun[1])
                                        tree.merge_2_children_together(child1, child2)
                                        return True
                            #for cond in conditions_in_commun:
                            #    if(cond not in tree.get_conditions()):
                            #        G1, G2 = child1.get_all_leafs_in_tree({}), child2.get_all_leafs_in_tree({})
                            #        all_paths_are_in_cluster, pred, rest = check_all_paths_are_in_cluster((G1+G2), all_nodes_in_graph, link_dico)
                            #        #This means we need to merge the 2 children together
                            #        if(all_paths_are_in_cluster):
                            #            tree.merge_2_children_together(child1, child2, groups_created)
                            #            groups_created+=1
                            #            return True, groups_created
                    child1.set_compared_to_all_siblings(True)
                tree.set_minimal(True)
                return False
            else:
                return False

        def make_tree_minimal(tree, recu):           
            still_merging = True
            index = 0
            while(still_merging):
                start = time.time()
                still_merging = merge_tree(tree)
                end = time.time()
                #print(index, end- start)

                index+=1

            #for child in tree.children:
            #    if(not child.is_a_leaf()):
            #        groups_created = make_tree_minimal(child, groups_created, recu+1)
            #        None

        start = time.time()
        make_tree_minimal(clustering, recu= 0)
        end = time.time()
        #print("STEP3", end- start)

        start = time.time()
        #STEP3.5 -> remove the clouds and put it's operations back
        clustering.remove_clouds()
        end = time.time()
        #print("STEP3.5", end- start)

        clustering.get_on_process_dependency= self.get_on_process_dependency
        clustering.clean_values()
        self.tree =  clustering
        return clustering, stats_on_conditions
    

    def get_relevant_abstraction(self, relevant_processes):
        from .outils_graph import remove_artificial_nodes, relev_user_view_builder
        if(not self.get_on_process_dependency):
            dico_used = self.workflow.graph.full_dico
        else:
            dico_used = self.workflow.graph.dico_process_dependency_graph
        self.workflow.graph.initialise_flattened_dico(dico_used)
        dico = remove_artificial_nodes(self.workflow.graph.dico_flattened)

        new_nodes_user_view = relev_user_view_builder(dico, relevant_modules=relevant_processes)
        cluster = Tree(value="root", condition=None, children = [])
        index = 0
        for group in new_nodes_user_view:
            new_name = index
            for child in group:
                if(child.get_type()=="Process" and child.get_alias() in relevant_processes):
                    new_name = child.get_alias()
            group_tree = Tree(value=new_name, condition=None, children = [])
            group_tree.add_children(group)
            cluster.add_child(group_tree)
            index+=1
        cluster.get_on_process_dependency= self.get_on_process_dependency
        self.tree = cluster
        return cluster


    #def get_vertical_abstraction(self):
    #    if(not self.get_on_process_dependency):
    #        link_dico = self.workflow.graph.get_link_dico(bool_get_object = True, without_artificial_nodes = True)
    #    else:
    #        link_dico = self.workflow.graph.get_link_dico_process(bool_get_object = True, without_artificial_nodes = True)
    #
    #    all_nodes, nodes_with_inputs = [],[]
    #    for node in link_dico:
    #        all_nodes+=[node]
    #        all_nodes+=link_dico[node]
    #        nodes_with_inputs+=link_dico[node]
    #    nodes_without_inputs = set(all_nodes) - set(nodes_with_inputs)
    #    node_2_id, id_2_node = {}, {}
    #    index = 1
    #    successors = {}
    #    successors[0] = []
    #
    #    for n in set(all_nodes):
    #        node_2_id[n] = index
    #        id_2_node[index] = n
    #        successors[index] = []
    #        index+=1
    #    
    #    for n in nodes_without_inputs:
    #        successors[0].append(node_2_id[n])
    #
    #    for n in link_dico:
    #        for node in link_dico[n]:
    #           successors[node_2_id[n]].append(node_2_id[node]) 
    #        
    #    dominator_tree = lengauer_tarjan_dominators(successors=successors, root=0)
    #    
    #
    #    def idom_2_tree(idom, root_value="root"):
    #        nodes = {}
    #        children_map = {}
    #        
    #        #Create the Tree
    #        for v in range(len(idom)):
    #            nodes[v] = Tree(value= v, condition=None, children=[])
    #
    #        for v, p in enumerate(idom):
    #            if(p != 0):
    #                try:
    #                    temp = children_map[p]
    #                except:
    #                    children_map[p] = []
    #                children_map[p].append(v)
    #
    #        for p, childs in children_map.items():
    #            nodes[p].children = [nodes[c] for c in childs]
    #
    #        root = Tree(value= root_value, condition=None, children=[])
    #        for v, p in enumerate(idom):
    #            if(p == 0):
    #                if(v!=0):
    #                    root.children.append(nodes[v])
    #        return root
    #
    #
    #    def dT2vA(tree):
    #        new_children = []
    #        counter = 0
    #        for child in tree.children:
    #                g_tree, counter = REC_dT2vA(child, counter)
    #                for c in g_tree.children:
    #                    new_children.append(c)
    #        return Tree(value=tree.value, condition=None, children=new_children)
    #        return Node(tree.value, new_children)
    #
    #
    #    def REC_dT2vA(node, counter):
    #        g_node = Tree(value=f"G{counter}", condition=None, children=[])
    #        #g_node = Node(f"G{counter}")
    #
    #        t = Tree(value=node.value, condition=None, children=[])
    #        g_node.children.append(t)
    #        if(len(node.children)==0):
    #            None
    #
    #        elif(len(node.children)==1):
    #            child = node.children[0]
    #            g_tree, counter = REC_dT2vA(child, counter)
    #            for c in g_tree.children:
    #                g_node.children.append(c)
    #            
    #        else:
    #            for child in node.children:
    #                sub_g, counter = REC_dT2vA(child, counter+1)
    #                g_node.children.append(sub_g)
    #
    #        return g_node, counter
    #    
    #    
    #
    #    def put_back_values(tree):
    #        for child in tree.children:
    #            if(type(child.value)!=str):
    #                child.value = id_2_node[child.value]
    #            put_back_values(child)
    #        return tree
    #    
    #    tree = put_back_values(dT2vA(idom_2_tree(dominator_tree)))
    #    #tree.show_tree()
    #    self.tree =  tree
    #    return tree

    def get_potential_cluster_dominator(self):
        if(not self.get_on_process_dependency):
            link_dico = self.workflow.graph.get_link_dico(bool_get_object = True, without_artificial_nodes = True)
        else:
            link_dico = self.workflow.graph.get_link_dico_process(bool_get_object = True)

        all_nodes, nodes_with_inputs = [],[]
        for node in link_dico:
            all_nodes+=[node]
            all_nodes+=link_dico[node]
            nodes_with_inputs+=link_dico[node]
        nodes_without_inputs = set(all_nodes) - set(nodes_with_inputs)
        node_2_id, id_2_node = {}, {}
        index = 1
        successors = {}
        successors[0] = []

        for n in set(all_nodes):
            node_2_id[n] = index
            id_2_node[index] = n
            successors[index] = []
            index+=1
        
        for n in nodes_without_inputs:
            successors[0].append(node_2_id[n])
  
        for n in link_dico:
            for node in link_dico[n]:
               successors[node_2_id[n]].append(node_2_id[node]) 
            
        dominator_tree = lengauer_tarjan_dominators(successors=successors, root=0)
        
        def idom_2_tree(idom, root_value="root"):
            nodes = {}
            children_map = {}
            
            #Create the Tree
            for v in range(len(idom)):
                nodes[v] = Tree(value= v, condition=None, children=[])

            for v, p in enumerate(idom):
                if(p != 0):
                    try:
                        temp = children_map[p]
                    except:
                        children_map[p] = []
                    children_map[p].append(v)

            for p, childs in children_map.items():
                nodes[p].children = [nodes[c] for c in childs]

            root = Tree(value= root_value, condition=None, children=[])
            for v, p in enumerate(idom):
                if(p == 0):
                    if(v!=0):
                        root.children.append(nodes[v])
            return root
        idom_tree = idom_2_tree(dominator_tree)
        dominators_names = []
        for t in idom_tree.get_dico_descendants(dico={}).keys():
            dominators_names.append(id_2_node[t.value].get_alias())
        cluster_id = idom_tree.get_dico_descendants(dico={}).values()
        PC = []
        for clsuter in cluster_id:
            tab = []
            for c in clsuter:
                tab.append(id_2_node[c])
            PC.append(tab)
        return PC, dominators_names

    def get_dominator_abstraction(self):
        if(not self.get_on_process_dependency):
            link_dico = self.workflow.graph.get_link_dico(bool_get_object = True, without_artificial_nodes = True)
        else:
            link_dico = self.workflow.graph.get_link_dico_process(bool_get_object = True)

        
        PC, dominators_names= self.get_potential_cluster_dominator()
        
        all_nodes_in_graph = []
        for n in link_dico:
            all_nodes_in_graph.append(n)
            all_nodes_in_graph += link_dico[n]
        all_nodes_in_graph = list(set(all_nodes_in_graph))
        #self.number_of_nodes_without_clouds = len(all_nodes_in_graph)
        pc_in_condition_form = {}
        index = 0
        for i in range(len(PC)):
            cluster = PC[i]
            dominator_name = dominators_names[i]
            cond = Condition(self, f"Dependent on '{dominator_name}'", artificial=True)
            pc_in_condition_form[cond] = cluster
            index+=1
        clustering= create_cluster_rec(georges_copy_dico(pc_in_condition_form), all_nodes_in_graph, id_group = {"nb":1}, rec = 0, abstraction=self, link_dico=link_dico)
        #clustering.show_tree()

        clustering.get_on_process_dependency = self.get_on_process_dependency
        tree = clustering
        ##tree.show_tree()
        self.tree =  tree
        return tree
    
    def get_parallel_abstraction(self):
        if(not self.get_on_process_dependency):
            link_dico = self.workflow.graph.get_link_dico(bool_get_object = True, without_artificial_nodes = True)
        else:
            link_dico = self.workflow.graph.get_link_dico_process(bool_get_object = True)

        
        try:
            PC = get_parallel_components(link_dico)
            self.workflow.is_sp_graph = True
        except:
            PC = []
            self.workflow.is_sp_graph = False

        
        all_nodes_in_graph = []
        for n in link_dico:
            all_nodes_in_graph.append(n)
            all_nodes_in_graph += link_dico[n]
        all_nodes_in_graph = list(set(all_nodes_in_graph))
        #self.number_of_nodes_without_clouds = len(all_nodes_in_graph)
        pc_in_condition_form = {}
        index = 0
        for cluster in PC:
            cond = Condition(self, index, artificial=True)
            pc_in_condition_form[cond] = cluster
            index+=1
        clustering= create_cluster_rec(georges_copy_dico(pc_in_condition_form), all_nodes_in_graph, id_group = {"nb":1}, rec = 0, abstraction=self, link_dico=link_dico)

        clustering.get_on_process_dependency = self.get_on_process_dependency
        tree = clustering
        self.tree =  tree
        return tree
    
    def get_user_defined_abstraction(self):
        if(not self.get_on_process_dependency):
            link_dico = self.workflow.graph.get_link_dico(bool_get_object = True, without_artificial_nodes = True)
        else:
            link_dico = self.workflow.graph.get_link_dico_process(bool_get_object = True)

        if(not self.get_on_process_dependency):
            dico = self.workflow.graph.get_full_dico()
        else:
            dico = self.workflow.graph.get_process_dependency_graph()


        import re
        import ctypes    
        def get_object(address):
            address = int(re.findall(r"\dx\w+", address)[0], base=16)
            return ctypes.cast(address, ctypes.py_object).value
        #Create PC (list of lists)
        subworkflows = get_subworkflows_2_elements(dico)
        PC = []
        for sub in subworkflows:
            tab = []
            for ele in subworkflows[sub]:
                tab.append(get_object(ele['id']))
            PC.append(tab)
        
        
        all_nodes_in_graph = []
        for n in link_dico:
            all_nodes_in_graph.append(n)
            all_nodes_in_graph += link_dico[n]
        all_nodes_in_graph = list(set(all_nodes_in_graph))
        #self.number_of_nodes_without_clouds = len(all_nodes_in_graph)
        pc_in_condition_form = {}
        index = 0
        for cluster in PC:
            cond = Condition(self, index, artificial=True)
            pc_in_condition_form[cond] = cluster
            index+=1
        clustering= create_cluster_rec(georges_copy_dico(pc_in_condition_form), all_nodes_in_graph, id_group = {"nb":1}, rec = 0, abstraction=self, link_dico=link_dico, force_creation=True)
        #clustering.show_tree()

        clustering.get_on_process_dependency = self.get_on_process_dependency
        tree = clustering
        ##tree.show_tree()
        self.tree =  tree
        return tree



    def get_number_of_unique_clusters_split_by_subworkflows(self):
        workflow = self.workflow
        subworkflows = workflow.get_operations_and_processes_per_subworkflows()
        created_groups = self.tree.get_unique_groups({})

        def get_smallest_set(a, b):
            if(len(a)<len(b)):
                return a
            return b

        number_split_cluster = 0
        for tree in created_groups: 
            split_cluster = False
            for sub in subworkflows:
                group_subworkflow = set(subworkflows[sub])
                cluster = set(created_groups[tree])
                #If the intersection of the two groups aren't equal
                if(group_subworkflow.intersection(cluster)!=set()):
                    #Verify that one group isn't including in the other
                    if(group_subworkflow.intersection(cluster)!=get_smallest_set(group_subworkflow, cluster)):
                        split_cluster = True
                        break
            if(split_cluster):
                number_split_cluster+=1
        return number_split_cluster



def get_val(node):
    if(node.get_type()=="Process"):
        return node.get_name()
    else:
        return node.get_code(get_OG = True)

#This function returns a part of all the paths between 2 nodes 
#Basically the same node won't be explored twice which makes the algo fast
def dfs_get_nodes_between_2(graph, start, end):
    nodes_on_paths, nodes_not_on_paths = set(), set()
    all_paths = []
    def dfs_get_nodes_between_rec(graph, current_path, end):
        node = current_path[-1]
        if(node not in nodes_on_paths):
            if(node==end):
                all_paths.append(current_path)
                nodes_on_paths.update(current_path)
            
            for neighbor in graph.get(node, []):
                if(neighbor not in nodes_not_on_paths):
                    if neighbor not in current_path:  # avoid cycles
                        new_path = current_path.copy()
                        new_path.append(neighbor)
                        dfs_get_nodes_between_rec(graph, new_path, end)
            if(node not in nodes_on_paths):
                nodes_not_on_paths.update([node])
        else:
            all_paths.append(current_path)
            nodes_on_paths.update(current_path)
    dfs_get_nodes_between_rec(graph, [start], end)
    return all_paths

def get_largest_cluster(potential_clusters):
    def get_number_processes(tab):
        num = 0
        for n in tab:
            if(n.get_type()=="Process"):
                num+=1
        return num
    if(len(potential_clusters)>0):
        #First start by getting the largest one which processes
        for condition in potential_clusters:
            largest = condition
            break
        for condition in potential_clusters:
            if(get_number_processes(potential_clusters[condition])>get_number_processes(potential_clusters[largest])):
                largest = condition
        #This is the case there are no processes
        if(get_number_processes(potential_clusters[largest])==0):
            for condition in potential_clusters:
                largest = condition
                break
            for condition in potential_clusters:
                if(len(potential_clusters[condition])>len(potential_clusters[largest])):
                    largest = condition
            return largest
        else:
            return largest
    else:
        return None
    
def georges_copy_dico(dico):
    tab = {}
    for list in dico:
        tab[list] = []
        for ele in dico[list]:
            tab[list].append(ele)
    return tab
#def explore_all_paths_rec(A, B, links_dico, visited, paths, current_path):
#    visited[A] = True
#    current_path.append(A)
#
#
#    if(A==B):
#        #id(current_path)
#        paths[time.time()] = current_path
#    for neigh in links_dico[A]:
#        if(not visited[neigh]):
#            explore_all_paths_rec(neigh, B, links_dico, visited = visited, paths = paths, current_path = current_path.copy())
#
#        else:
#            #Here we use what has already been visited to see if we can simply extend the list
#            exisiting_paths = list(paths.values())
#            for path in exisiting_paths:
#                if(neigh in path):
#                    index = path.index(neigh)
#                    create_new_path = True#This condition is to avoid crating infinite paths due to cycles
#                    for node in path[index:]:
#                        if(node in current_path):
#                            create_new_path = False
#                    if(create_new_path):
#                        new_path = current_path+path[index:]
#                        if(new_path not in exisiting_paths):
#                            exisiting_paths.append(new_path)
#                            paths[time.time()] = new_path
#    if(paths!={}):
#        return True, list(paths.values())
#    else:
#        return False, []

#def explore_all_paths(A, B, all_nodes, links_dico):
#    visited, paths = {}, {}
#    current_path = []
#    for n in all_nodes:
#        visited[n] = False
#    exists, paths = explore_all_paths_rec(A, B, links_dico, visited.copy(), paths, current_path.copy())
#
#    #Remove the artificial operations
#    #for path in paths:
#    #    for n in path:
#    #        if(n.get_type()=="Operation"):
#    #            if(n.get_artificial_status()):
#    #                path.remove(n)
#
#    return exists, paths
    

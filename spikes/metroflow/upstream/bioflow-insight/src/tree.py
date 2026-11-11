class Tree:
    def __init__(self, value, condition, children):
        self.value = value
        self.condition = condition
        self.children = children
        self.minimal = False
        self.compared_minimal = []
        self.compared_to_all_siblings = False
        self.get_on_process_dependency = False

    def clean_values(self):
        try:
            self.value = self.value.replace('##{', '(')
            self.value = self.value.replace('##}', ')')
            
        except:
            None
        for c in self.children:
            c.clean_values()
        #replace_equal_wave(
        #        replace_single_bar_by_or(
        #            replace_single_ampersand(
        #                replace_single_dollar_signs(
        #                    replace_call_parentheses(text)))))

    def checked_if_already_compared_minimal(self, couple):
        if(couple in self.compared_minimal):
            return True
        return False
    
    def add_compared_minimal(self, couple):
        self.compared_minimal.append(couple)

    def set_compared_to_all_siblings(self, val):
        self.compared_to_all_siblings = val
    

    def set_minimal(self, val):
        self.minimal = val
    
    def get_minimal(self):
        return self.minimal

    def is_this_full_tree(self):
        return self.value==None and self.condition==None
    
    def update_value(self, val):
        self.value = val
    
    def set_condition(self, val):
        self.condition = val
    

    def create_copy(self):
        t = Tree(value=self.value, condition=self.condition, children=[])
        if(not self.is_a_leaf()):
            for c in self.children:
                t.children.append(c.create_copy())
        return t
    
    def get_depth(self, val =0):
        if(len(self.children)==0):
            return val
        else:
            max_depth = val
            for c in self.children:
                new_val = c.get_depth(val = val+1)
                if(max_depth<new_val):
                    max_depth = new_val
            return max_depth
        
    #def get_distribution_depth(self, dico, val = 0):
    #    if(len(self.children)==0):
    #        return dico
    #    else:
    #        if(val!=0):
    #            dico[self] = val
    #        for c in self.children:
    #            c.get_distribution_depth(dico, val = val+1)
    #        return list(dico.values())
    #    
    #def get_distribution_depth_unique(self, dico, val = 0):
    #    if(len(self.children)==0):
    #        return dico
    #    else:
    #        if(val!=0):
    #            dico[self] = val
    #        add_to_depth = 1
    #        if(len(self.children)==1):
    #            add_to_depth = 0
    #            try:
    #                dico.pop(self)
    #            except:
    #                None
    #        for c in self.children:
    #            c.get_distribution_depth_unique(dico, val = val+add_to_depth)
    #        return list(dico.values())
    
    def get_distribution_depth_size_unique(self, dico, val =0):
        if(len(self.children)==0):
            return dico
        else:            
            if(self.value!="root"):
                dico[self] = {"name":self.value,"depth":val, "size": len(self.get_all_leafs_in_tree(val={}))}
                val_2_add = 1
            else:
                val_2_add = 0
                

            if(len(self.children)==1 and not self.children[0].is_a_leaf()):
                if(len(self.children[0].get_all_leafs_in_tree(val={}))== len(self.get_all_leafs_in_tree(val={}))):
                    try:
                        dico.pop(self)
                    except:
                        None
                    self.children[0].get_distribution_depth_size_unique(dico, val = val)
            else:
                for c in self.children:
                    c.get_distribution_depth_size_unique(dico, val = val+val_2_add)
            return list(dico.values())
        
    def get_distribution_depth_size_informative(self, dico, val = 0):
        if(len(self.children)==0):
            return dico
        else:
            
            if(self.value!="root"):
                val_2_add = 1
            else:
                val_2_add = 0
            if(self.value!="root" and len(self.get_all_leafs_in_tree(val={}))>1):
                dico[self] = {"name":self.value,"depth":val, "size": len(self.get_all_leafs_in_tree(val={}))}


            if(len(self.children)==1 and not self.children[0].is_a_leaf()):
                if(len(self.children[0].get_all_leafs_in_tree(val={}))== len(self.get_all_leafs_in_tree(val={}))):
                    try:
                        dico.pop(self)
                    except:
                        None
                    self.children[0].get_distribution_depth_size_informative(dico, val = val)
            else:
                for c in self.children:
                    c.get_distribution_depth_size_informative(dico, val = val+val_2_add)
            return list(dico.values())
        
    
    def get_depth_unique(self, val =0):
        if(len(self.children)==0):
            return val
        else:
            add_to_depth = 1
            if(len(self.children)==1):
                add_to_depth = 0
            max_depth = val
            for c in self.children:
                new_val = c.get_depth_unique(val = val+add_to_depth)
                if(max_depth<new_val):
                    max_depth = new_val
            return max_depth
                
    
    def is_a_leaf(self):
        return self.children==[] 
    
    #This method returns all the children in the immediate depth 
    #And if a child is a tree it returns all the recursive children of that tree
    def get_shallow_children(self):
        tab = []
        for child in self.children:
            leafs = child.get_all_leafs_in_tree(val={})
            if(leafs!=[]):
                tab.append(leafs)
        return tab
    
    def add_child(self, child):
        self.children.append(child)

    def add_children(self, cluster):
        for c in cluster:
            temp = Tree(value=c, condition=None, children = [])
            self.add_child(temp)

    def get_all_leafs_in_tree(self, val):
        if(self.is_a_leaf()):#and type(self.value)!=str):
            val[self.value] = ""
        for child in self.children:
            child.get_all_leafs_in_tree(val)
        return list(val.keys())
    
    def get_all_descendants_in_tree(self, val):
        for child in self.children:
            val[child.value] = ""
            child.get_all_leafs_in_tree(val)
        return list(val.keys())
    
    #Transfers the tree's children to self
    def transfer_children(self, tree):
        for i in range(len(tree.children)):
            self.children.append(tree.children[i])

    def get_condition(self):
        return self.condition
    
    def get_children(self):
        return self.children
    
    def get_children_which_are_not_leaves_which_havent_been_compared_to_all_siblings(self):
        tab = []
        for c in self.children:
            if(not c.is_a_leaf() and not c.compared_to_all_siblings):
                tab.append(c)
        return tab
    
    def get_condition_in_commun(self, tree):
        return ""


    def get_conditions_on_all_leaves(self):
        conditions_on_all_leaves = []
        if(self.condition!=None):
            conditions_on_all_leaves.append(self.condition)
            if(len(self.children)==1):
                conditions_on_all_leaves+= self.children[0].get_conditions_on_all_leaves()
        return conditions_on_all_leaves

    def get_conditions_in_commun(self, other_tree):
        conditions_on_all_leaves_tree1 = self.get_conditions_on_all_leaves()
        conditions_on_all_leaves_tree2 = other_tree.get_conditions_on_all_leaves() 
        conditions_in_commun = []
        for i in range(len(conditions_on_all_leaves_tree1)):
            for y in range(len(conditions_on_all_leaves_tree2)):
                cond1, cond2 = conditions_on_all_leaves_tree1[i], conditions_on_all_leaves_tree2[y]
                if(cond1.get_value()==cond2.get_value()):
                    conditions_in_commun.append((cond1, cond2))
        return conditions_in_commun
    
    
    def get_node_with_condition(self, condition):
        if(self.condition==condition):
            return self
        else:
            if(len(self.children)!=1):
                raise Exception("this shoudn't happen")
            return self.children[0].get_node_with_condition(condition)

    #This methods brings the condition to the top of the tree 
    #Becoming the first internal node
    def bring_condition_to_the_top(self, condition):
        if(self.condition!=condition):
            conditions_on_all_leaves = self.get_conditions_on_all_leaves()
            
            if(condition in conditions_on_all_leaves):
                children_are_all_leaves = True
                for c in self.children:
                    if(not c.is_a_leaf()):
                        children_are_all_leaves = False
                if(len(self.children)!=1 and not children_are_all_leaves):
                    self.show_tree()
                    raise Exception("this shoudn't happen")
                node_with_condition = self.get_node_with_condition(condition)
                temp_condition = self.get_condition()
                self.set_condition(condition)
                node_with_condition.set_condition(temp_condition)
            else:
                raise Exception("this shoudn't happen")




    def get_value_condition(self):
        try:
            return self.condition
        except:
            return None

    def get_id_subworkflow(self):

        if("<src.operation.Operation" in str(self.value)):
            return str(id(self))
        else:
            return str(self.value)+'_$$_'+str(id(self))
       
    
    def fill_workflow(self, nodes, dico):
        for child in self.children:
            if(child.is_a_leaf()):
                #if(child.value.get_type()=='Process'):
                #If it is a process or an operation -> we add it
                #This is a filter, such as in the case we are creating based on the process dependency graph
                if(str(child.value) in nodes):
                    dico["nodes"].append(nodes[str(child.value)])
                
            else:
                #temp_dico = {}
                #temp_dico["nodes"] = []
                #temp_dico["edges"] = []
                #temp_dico["subworkflows"] = {}
                dico['subworkflows'][child.get_id_subworkflow()] = {}
                dico['subworkflows'][child.get_id_subworkflow()]["nodes"] = []
                dico['subworkflows'][child.get_id_subworkflow()]["edges"] = []
                dico['subworkflows'][child.get_id_subworkflow()]["subworkflows"] = {}
                child.fill_workflow(nodes, dico['subworkflows'][child.get_id_subworkflow()])
                if(dico['subworkflows'][child.get_id_subworkflow()]=={}):
                    dico['subworkflows'].pop(child.get_id_subworkflow())
                #Important, if it is just a cluster in a cluster, then it just becomes a cluster
                elif(dico['subworkflows'][child.get_id_subworkflow()]['nodes']==[] and
                     len(dico['subworkflows'][child.get_id_subworkflow()]['subworkflows'])==1):
                    for wf in dico['subworkflows'][child.get_id_subworkflow()]['subworkflows']:
                        dico['subworkflows'][wf] = dico['subworkflows'][child.get_id_subworkflow()]['subworkflows'][wf].copy()
                        dico['subworkflows'].pop(child.get_id_subworkflow())
                #elif(len(dico['subworkflows'][child.get_id_subworkflow()]['nodes'])==1 and
                #     len(dico['subworkflows'][child.get_id_subworkflow()]['subworkflows'])==0):
                #    dico['nodes'].append(dico['subworkflows'][child.get_id_subworkflow()]['nodes'][0])
                #    dico['subworkflows'].pop(child.get_id_subworkflow())
                

            
        return dico
            


    def fill_tree(self, tree, parent_id):
        tree.create_node(str(get_val(self.value)),  id(self), parent=parent_id)
        for child in self.children:
            child.fill_tree(tree, id(self))
        
    def merge_2_children_together(self, child1, child2):

        new_child = Tree(value=child1.get_condition().get_value(), condition = None, children=[])
        new_child.transfer_children(child2)
        new_child.transfer_children(child1)
        
        self.children.remove(child1)
        self.children.remove(child2)
        self.children.append(new_child)


    def get_number_of_groups(self, num):
        for child in self.children:
            if(not child.is_a_leaf()):
                num = child.get_number_of_groups(num+1)
        return num
    
    def get_number_of_unique_groups(self, num):
        if(self.value!='root'):
            if(len(self.children)==1 and not self.children[0].is_a_leaf()):
                None
            else:
                num+=1
        for child in self.children:
            if(not child.is_a_leaf()):
                num = child.get_number_of_unique_groups(num)
        return num
    
    def get_size_of_groups(self, tab):
        for child in self.children:
            if(not child.is_a_leaf()):
                tab.append(len(child.children))
                tab = child.get_size_of_groups(tab)
        return tab
    
    def get_groups(self, dico):
        for child in self.children:
            if(not child.is_a_leaf()):
                dico[child] = child.get_all_leafs_in_tree({})
                child.get_groups(dico)
        return dico
    
    def get_unique_groups(self, dico):
        for child in self.children:
            if(not child.is_a_leaf()):
                if(len(self.children)!=1):
                    dico[child] = child.get_all_leafs_in_tree({})
                child.get_unique_groups(dico)
        return dico
    
    def get_dico_descendants(self, dico):
        if(self.value!='root'):
            dico[self] = []
        for child in self.children:
            if(self.value!='root'):
                dico[self].append(child.value)
                dico[self] += child.get_all_descendants_in_tree({})
            child.get_dico_descendants(dico)
            if(dico[child]==[]):
                dico.pop(child)
        return dico
    
    
    
    #This is the percentage of nodes which are in a group
    def get_coverage(self):
        if(self.children!=[]):
            nb_swallow_leafs = 0
            for child in self.children:
                if(child.is_a_leaf()):
                    nb_swallow_leafs+=1
            nb_leafs = len(self.get_all_leafs_in_tree({}))
            return (nb_leafs-nb_swallow_leafs)/nb_leafs*100
        return 0
    
    #This is the percentage of processes which are in a group
    def get_coverage_processes(self):
        if(self.children!=[]):
            nb_swallow_leafs = 0
            for child in self.children:
                if(child.is_a_leaf() and child.value.get_type()=="Process"):
                    nb_swallow_leafs+=1
            if(nb_swallow_leafs==0):
                return 0
            total = 0
            for leaf in self.get_all_leafs_in_tree({}):
                if(leaf.get_type()=="Process"):
                    total+=1
            return (total-nb_swallow_leafs)/total*100
        return 0

    def show_tree(self):
        from treelib import Node, Tree
        tree = Tree()
        tree.create_node("Root", "root")
        for child in self.children:
            child.fill_tree(tree, "root")
        tree.show()

    def remove_clouds(self):
        to_remove, to_add= [], []
        for child in self.children:
            if(child.is_a_leaf() and type(child.value)!=str and child.value.get_type()=="Cloud"):
                operations = child.value.get_operations()
                for o in operations:
                    to_add.append(Tree(value=o, condition=child.condition, children=[]))
                to_remove.append(child)
            else:
                child.remove_clouds()
        for r in to_remove:
            self.children.remove(r)
        self.children+=to_add

    #To do this i looks at the number of unique clusters 
    def get_number_identical(self, other_tree):
        my_clusters = list(self.get_unique_groups(dico={}).values())
        other_clusters = list(other_tree.get_unique_groups(dico={}).values())
        number_identical = 0
        for my_c in my_clusters:
            there_is_equal = False
            for other_c in other_clusters:
                if(len(my_c)==len(other_c)):
                    if(my_c==other_c):
                        there_is_equal = True
            if(there_is_equal):
                number_identical+=1
        return number_identical

            
                


def get_val(node):
    try:
        if(node.get_type()=="Process"):
            #return node.get_name()
            return node.get_alias()
        elif(node.get_type()=="Operation"):
            return node.get_code(get_OG = True)
        elif(node.get_type()=="Cloud"):
            return "Cloud"
    except:
        return node

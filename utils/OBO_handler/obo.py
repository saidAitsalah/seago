

def load_go_definitions(obo_file_path):
    go_definitions = {}
    
    with open(obo_file_path, 'r') as file:
        current_go_id = None
        current_go_definition = None
        current_go_type = None
        
        for line in file:
            line = line.strip()
            
            if line.startswith("[Term]"):  # Start of a new GO
                current_go_id = None
                current_go_definition = None
            
            elif line.startswith("id:"):  # GO id
                current_go_id = line.split("id: ")[1].strip()
            
            elif line.startswith("name: "):  # GO definition
                current_go_definition = line.split("name: ")[1].split(" [")[0].strip()  

            elif line.startswith("namespace: "): #type
                            parts = line.split("namespace: ")
                            if len(parts) > 1:
                                namespace = parts[1].strip()
                                if namespace == "molecular_function":
                                    current_go_type = "M"
                                elif namespace == "biological_process":
                                    current_go_type = "P"
                                elif namespace == "cellular_component":
                                    current_go_type = "C"

            # adding a tuple (id,name,type)
            if current_go_id and current_go_definition and current_go_type:
                go_definitions[current_go_id] = (current_go_definition, current_go_type)

        
    return go_definitions


def load_go_terms(obo_file_path):
    go_definitions = []  
    
    with open(obo_file_path, 'r', encoding='utf-8') as file:
        current_go = {}  
        inside_term = False  
        
        for line in file:
            line = line.strip()
            
            if line.startswith("[Term]"):
                if "id" in current_go:  # Save the previous term before creating a new one
                    go_definitions.append(current_go)
                
                current_go = {}  # New dictionary for the following term
                inside_term = True
            
            elif line == "":  # End of a term
                if "id" in current_go:
                    go_definitions.append(current_go)
                inside_term = False
                
            elif inside_term:
                parts = line.split(": ", 1)
                if len(parts) == 2:
                    key, value = parts
                    if key in current_go:
                        if isinstance(current_go[key], list):
                            current_go[key].append(value)
                        else:
                            current_go[key] = [current_go[key], value]  # Convert to list if multiple values
                    else:
                        current_go[key] = value
    
    return go_definitions  # return a list of dictionnaries











import pickle

def load_dictionary(filename):
    """
    Loads a dictionary from a file using pickle. If the data is a list,
    transforms it into a dictionary with 'id' as the key.
    
    Args:
        filename (str): The file path from which to load the data.
    
    Returns:
        dict: A dictionary where 'id' is the key, or an empty dictionary if the file is not found.
    """
    try:
        with open(filename, 'rb') as file:
            data = pickle.load(file)
        
        print(f"Data loaded from {filename}.")
        
        # Transform list to dictionary if needed
        if isinstance(data, list):
            try:
                data = {item['id']: item for item in data}
            except (TypeError, KeyError):
                raise ValueError("List items must contain an 'id' key.")
        
        return data
    except FileNotFoundError:
        print(f"No file found at {filename}. Returning an empty dictionary.")
        return {}
    except pickle.UnpicklingError:
        print(f"Failed to unpickle data from {filename}. Returning an empty dictionary.")
        return {}


loaded_dict = load_dictionary("sold_items_fx6100.pkl")

for key, value in loaded_dict.items():
    print(value["name"])
    print(value["price"])
    print(value["link"])
    print(value["date"])
    print("\n")


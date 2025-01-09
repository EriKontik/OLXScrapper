import pickle
from fuzzywuzzy import fuzz
import datetime 
import matplotlib.pyplot as plt
from rich.console import Console as console
def plot_price_vs_wait_time(results):
    # Extract prices and corresponding wait times (in days)
    prices = [item['price'] for item in results]
    wait_times = [days_since(item['date']) for item in results]

    # Sort the data by price (optional, to make the line graph smoother)
    sorted_data = sorted(zip(prices, wait_times))
    prices_sorted, wait_times_sorted = zip(*sorted_data)

    # Plotting the line plot
    plt.figure(figsize=(10, 6))
    plt.plot(prices_sorted, wait_times_sorted, color='blue', marker='o', linestyle='-', label='Products')

    # Adding labels and title
    plt.title('Price vs. Wait Time for Products', fontsize=16)
    plt.xlabel('Price (in currency)', fontsize=14)
    plt.ylabel('Wait Time (in days)', fontsize=14)

    # Show the plot
    plt.grid(True)
    plt.legend()
    plt.show()


def days_since(date_str, date_format="%d.%m.%Y"):
    # Convert input date string to a datetime object
    input_date = datetime.datetime.strptime(date_str, date_format)
    
    # Get today's date
    today = datetime.datetime.now()
    
    # Calculate the difference in days
    delta = today - input_date
    
    # Return the number of days
    return delta.days

def find_products_fuzzy(products_dictionary, user_input, threshold=70):
    user_input_lower = user_input.lower()
    matching_products = []

    for product_id, product_info in products_dictionary.items():
        product_name = product_info["name"].lower()
        similarity = fuzz.partial_ratio(user_input_lower, product_name)
        
        if similarity >= threshold:
            matching_products.append({
                "id": product_id,
                "name": product_info["name"],
                "price": product_info["price"],
                "link": product_info["link"],
                "date": product_info["date"],
                "similarity": similarity
            })

    matching_products.sort(key=lambda x: x["similarity"], reverse=True)

    return matching_products if matching_products else "No matching products found."

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

# Example usage:
products_dictionary = load_dictionary("sold_items.pkl")
product_name_input = input("Enter the product name to search: ")
results = find_products_fuzzy(products_dictionary, product_name_input)

if isinstance(results, list):
    for values_item in results:
        console.print(f"Product ID: {values_item['id']}")
        console.print(f"Product Name: {values_item['name']}")
        console.print(f"Product Price: {values_item['price']}")
        console.print(f"Product Link: {values_item['link']}")
        console.print(f"Product Date: {values_item['date']} Days since: {days_since(values_item['date'])}")
        console.print(f"Similarity: {values_item['similarity']}")
        console.print("\n")

    # Average calculations
    print("Average price of the products found:", int(sum([item['price'] for item in results]) / len(results)))
    print("Average wait time of product to be sold:", int(sum([days_since(item['date']) for item in results]) / len(results)))

    # Plot the data
    plot_price_vs_wait_time(results)
else:
    console.print(results)  # Print the message if no products are found
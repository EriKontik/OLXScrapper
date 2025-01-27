import requests
from bs4 import BeautifulSoup
import sys
import re
import datetime
from rich.console import Console
import pickle
from tqdm.auto import tqdm
import time
import os
console = Console()

global_var_pages_to_search = 0

###Functions are here

#Main loop that parses the pages and puts together the dictionary
def main_loop(htmls, product_category):

    #Variables Needed
    
    links = []
    prices = []
    dates = []
    product_names = []
    ids = []

    #Main loop - Parsing, Putting it together into a dcitionary is there
    for html in tqdm(htmls):
        #Make a request to the page
        html = safe_request(html)
        
        #parse the html
        soup = BeautifulSoup(html, 'html.parser')
        #get the product cards
        product_cards = soup.findAll(class_="css-l9drzq")
        #Iterating through a list of product cards
        for product_card in product_cards:
            # Product Name
            name_element = product_card.find(class_=product_name_tag)

            is_ad = product_card.find(class_=ad_tag)
            if(is_ad):
                continue
            if not name_element:
                print("Product name not found")
                continue  # Skip if essential details are missing
            
            product_name = name_element.text

            # Product ID
            id = product_card.get("id")
            if not id:
                print("Product ID not found")
                continue

            # Link
            link_element = product_card.find(class_=link_tag)
            if not link_element or not link_element.get('href'):
                print("Product link not found")
                continue
            link = "https://www.olx.ua/" + link_element.get('href')

            # Price
            price_element = product_card.find(class_=price_tag)
            if not price_element:
                print("Product price not found")
                continue
            price = price_element.text

            # Date
            date_element = product_card.find(class_=date_tag)
            if not date_element:
                print("Product date not found")
                continue
            date = date_element.text
            date_f = date.split(" - ")
            parts = date_f[1].split(" ") if len(date_f) > 1 else []
            if len(parts) == 4:
                day = parts[0]
                month = month_map[parts[1]]
                year = parts[2]
                formatted_date = f"{day.zfill(2)}.{month}.{year}"
            elif len(parts) == 3:
                formatted_date = datetime.datetime.now().strftime("%d.%m.%Y")
            else:
                formatted_date = "Unknown"

            # Append to all lists together
            product_names.append(product_name)
            ids.append(id)
            links.append(link)
            prices.append(price)
            dates.append(formatted_date)

    #Clean everything except numbers and find the avg price
    prices = [
        int(re.sub(r'\D', '', price)) if re.sub(r'\D', '', price) else 0
        for price in prices
    ]
    price_avg = sum(prices) / len(prices) if prices else 0

    print(len(product_names), len(ids), len(prices), len(links), len(dates))
    # Initialize the dictionary with unique keys
    products_dictionary = {}
    for index in range(len(product_names)):
        products_dictionary[ids[index]] = {
            "name": product_names[index],
            "price": prices[index],
            "link": links[index],
            "date": dates[index]
        }


    #=======================================================
    #FROM NOW ON ITS PROCESSING HTE DATA WE GOT

    #Print all products
    # for product_id, product in products_dictionary.items():
    #     console.print(f"[bold red]Product ID:[/bold red][bold cyan]{product_id}[/bold cyan]\nName: {product['name']}\nPrice: {product['price']}\nLink: [click here]{product['link']}\nDate: {product['date']}\n\n")



    # Find the most expensive product
    most_expensive = max(products_dictionary.values(), key=lambda p: p["price"])
    console.print(f"\nMost Expensive\n===================\n{most_expensive['name']}\n{most_expensive['price']}\n{most_expensive['link']}\n{most_expensive['date']}\n=====================")

    least_expensive = min(products_dictionary.values(), key=lambda p: p["price"])
    console.print(f"\nLeast Expensive\n===================\n{least_expensive['name']}\n{least_expensive['price']}\n{least_expensive['link']}\n{least_expensive['date']}\n=====================")

    console.print(f"[bold white]Average price - {int(price_avg)}[/bold white]")

    #Load dictionary to later compare what products were sold 
    loaded_dictionary = load_dictionary(f"data_all_time_{product_category}.pkl")

    # Getting the ids of the items that were sold
    sold_items_ids = find_sold_items(list(loaded_dictionary.keys()), list(products_dictionary.keys()))

    sold_items_dict = {}
    for sold_id in sold_items_ids:
        if sold_id in loaded_dictionary:
            sold_items_dict[sold_id] = loaded_dictionary[sold_id]

    for key in tqdm(list(sold_items_dict.keys())):
        try:
            status = requests.get(sold_items_dict[key]['link']).status_code
        except:
            status = 404

        if status == 200:
            del sold_items_dict[key]
        else:
            break

    # Print out all the sold items
    for sold_id, sold_item in sold_items_dict.items():
        console.print(f"[bold red]Sold Product ID:[/bold red][bold cyan]{sold_id}[/bold cyan]\nName: {sold_item['name']}\nPrice: {sold_item['price']}\nLink: [click here]{sold_item['link']}\nDate: {sold_item['date']}\n\n")

    # Here we try to create a "database" of the sold items, we load the dictionary
    loaded_sold_items = load_dictionary(f"sold_items_{product_category}.pkl")
    try:
        #here we add their values up
        sold_items_dict = sold_items_dict | loaded_sold_items
    except TypeError:
        console.print("[bold orange]No sold items found in the file.[/bold orange]")


    data_to_send = {key: value for key, value in products_dictionary.items() if key not in loaded_dictionary}
    for key, value in data_to_send.items():
        console.print(f"[bold red]Product ID:[/bold red][bold cyan]{key}[/bold cyan]\nName: {value['name']}\nPrice: {value['price']}\nLink: [click here]{value['link']}\nDate: {value['date']}\n\n")

    save_dictionary(data_to_send, f"data_to_send_{product_category}.pkl")
    from tg_bot import startup_tg
    startup_tg(product_category)

    # Save the data to a files
    
    save_dictionary(sold_items_dict, filename=f"sold_items_{product_category}.pkl")
    save_dictionary(products_dictionary, filename=f"data_all_time_{product_category}.pkl")
    console.print("[bold green]Program ended succesfully![/bold green]")

          
# Function to get potentially profitable products
def get_potentially_profitable_products(products, avg_price):
    profitable_products = {}
    for key, value in products.items():
        if value['price'] < avg_price:
            profitable_products[key] = value
    return profitable_products
#Getting the number of pages
def get_pages(link, max_price, min_price):
    #Modify link to acount for the fact that we have a min and a max price
    link = link + f"?currency=UAH&search%5Bfilter_float_price%3Afrom%5D={min_price}&search%5Bfilter_float_price%3Ato%5D={max_price}"
    links = []
    links.append(link)
    text_page = safe_request(link)
    soup = BeautifulSoup(text_page, 'html.parser')
    pages = soup.findAll(class_=last_page)
    if pages:
        global_var_pages_to_search = int(pages[-1].text)
    else:
        print("No pagination found, defaulting to 1 page.")
        global_var_pages_to_search = 1
    for i in range(global_var_pages_to_search-1):
        #https://www.olx.ua/uk/list/q-Iphone-7/?page=2&search%5Bfilter_float_price%3Afrom%5D=700
        links.append(link + f"?page={i+2}?currency=UAH&search%5Bfilter_float_price%3Afrom%5D={min_price}&search%5Bfilter_float_price%3Ato%5D={max_price}")


    
    return links
# Function to check if two products are the same
def is_same_product(item1, item2):
    """Compare two products and check if they are the same except for the price."""
    fields_to_compare = ['name', 'link', 'date']
    return all(item1.get(field) == item2.get(field) for field in fields_to_compare)
def find_sold_items(ids_old, ids):
    """
    Find the items that were sold between the old and new data.
    
    Args:
    - ids_old (list of str): A list of IDs from the old data.
    - ids (list of str): A list of IDs from the new data.
    
    Returns:
    - list of str: A list of IDs that were sold between the old and new data.
    """
    return list(set(ids_old) - set(ids))
# Function to save a dictionary to a file
def save_dictionary(data, filename="data_all_time"):
    """
    Saves a dictionary to a file using pickle.
    
    Args:
        data (dict): The dictionary to save.
        filename (str): The file path where the dictionary should be saved.
    """
    with open(filename, 'wb') as file:
        pickle.dump(data, file)
    print(f"Dictionary saved to {filename}.")
# Function to load a dictionary from a file
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
# Function to safely make a request to a URL
def safe_request(url):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Check if the request was successful
        return response.text
    except requests.RequestException as e:
        console.print(f"[bold red]Error fetching URL:[/bold red] {e}")
        return None  # Return None if the request failed



#just dont touch it
sys.stdout.reconfigure(encoding='utf-8')

#Variables for everything

#Map for formatting the date into dd.mm.yyyy format
month_map = {
    'січня': '01', 'лютого': '02', 'березня': '03', 'квітня': '04', 'травня': '05', 
    'червня': '06', 'липня': '07', 'серпня': '08', 'вересня': '09', 'жовтня': '10', 
    'листопада': '11', 'грудня': '12'
}

results = []
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
}

ad_tag = "css-1dyfc0k"
link_tag = "css-qo0cxu" #+
price_tag = "css-6j1qjp" #+
date_tag = "css-1mwdrlh" #+ 
product_name_tag = "css-1sq4ur2"
rating_tag = "css-1pkf64r"
deleveries = "css-18icqaw"
last_page = "css-1mi714g"
#averages
price_avg = 0


def save_last_search(link, savefile_name, max_price, min_price):
    last_search = {
        "link": link,
        "savefile_name": savefile_name,
        "max_price": max_price,
        "min_price": min_price
    }
    with open("last_search.pkl", "wb") as file:
        pickle.dump(last_search, file)

def load_last_search():
    if os.path.exists("last_search.pkl"):
        with open("last_search.pkl", "rb") as file:
            return pickle.load(file)
    return None

def main():
    last_search = load_last_search()
    if last_search:
        use_last = input("Do you want to use the last search parameters? (yes/no) ").strip().lower()
        if use_last == "yes":
            link = last_search["link"]
            savefile_name = last_search["savefile_name"]
            max_price = last_search["max_price"]
            min_price = last_search["min_price"]
        else:
            link = input("Enter a link ")
            savefile_name = input("Enter save file name ")
            max_price = int(input("Enter max price "))
            min_price = int(input("Enter lowest price "))
            save_last_search(link, savefile_name, max_price, min_price)
    else:
        link = input("Enter a link ")
        savefile_name = input("Enter save file name ")
        max_price = int(input("Enter max price "))
        min_price = int(input("Enter lowest price "))
        save_last_search(link, savefile_name, max_price, min_price)

    pages = get_pages(link, max_price, min_price)

    while True:
        main_loop(htmls=pages, product_category=savefile_name)
        time.sleep(300)

if __name__ == "__main__":
    main()

    


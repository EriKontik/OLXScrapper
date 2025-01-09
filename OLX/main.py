import requests
from bs4 import BeautifulSoup
import sys
import re
import datetime
from rich.console import Console
import pickle
from tqdm.auto import tqdm
import time
console = Console()

###Functions are here

#Main loop that parses the pages and puts together the dictionary
def main_loop(htmls, pages_to_search, product_category):

    #Variables Needed
    pages_scrapped = 0
    links = []
    prices = []
    dates = []
    product_names = []
    ids = []

    #Main loop - Parsing, Putting it together into a dcitionary is there
    for html in tqdm(htmls):

        #How many pages were scrapped so far
        pages_scrapped += 1
        print(f"Scrapping page {pages_scrapped}/{pages_to_search}")

        #Make a request to the page
        html = safe_request(html)
        
        #parse the html
        soup = BeautifulSoup(html, 'html.parser')
        #get the product cards
        product_cards = soup.findAll(class_="css-l9drzq")


        #Iterating through a list of product cards
        for product_card in product_cards:

            #Check if the product is an add
            ad = product_card.find(class_=ad_tag)
            if(ad):
                console.print("[bold red]Ad found, skipping the product[/bold red]")
                continue
            
                

            # Product Name
            name_element = product_card.find(class_=product_name_tag)
            #get the name of the product
            if name_element:
                product_name = name_element.text
                product_names.append(product_name)
            else:
                print("Product name not found")
                continue  # Skip this product if essential details are missing
            
            #get ID of the product
            id = product_card.get("id")
            if id:
                ids.append(id)

            # get the link to the product
            link_element = product_card.find(class_=link_tag)
            if link_element:
                link = "https://www.olx.ua/" + link_element.get('href')
                links.append(link)
            else:
                print("Link not found")
                continue

            # get the price of the product
            price_element = product_card.find(class_=price_tag)
            if price_element:
                price = price_element.text
                prices.append(price)
            else:
                print("Price not found")
                continue

            # get the date of the product
            date_element = product_card.find(class_=date_tag)
            if date_element:
                #Get the text of the date
                date = date_element.text

                #Split the date into parts city and date
                date_f = date.split(" - ")
                
                #Split the date into months, days and years
                parts = date_f[1].split(" ")
                if len(parts) == 4:
                    day = parts[0]
                    #Map the month to the number
                    month = month_map[parts[1]]
                    year = parts[2]
                    #Format the date as dd.mm.yyyy #NOTE zfill(2) here means that no matter if the date is 5
                    #it will still be 05
                    formatted_date = f"{day.zfill(2)}.{month}.{year}"
                    dates.append(formatted_date)

                #if the date is today the length of it will be 3 so it will just get the current date    
                elif len(parts) == 3:
                    dates.append(datetime.datetime.now().strftime("%d.%m.%Y"))

            
            else:
                print("Date not found")
        print(f"Arrays length:{len(prices)}")


    #Clean everything except numbers and find the avg price
    prices = [int(re.sub(r'\D', '', price)) for price in prices]
    price_avg = sum(prices) / len(prices) if prices else 0


    # Initialize the dictionary with unique keys
    products_dictionary = {}
    for index in range(len(product_names)):
        products_dictionary[ids[index]] = {
            "name": product_names[index],
            "price": prices[index],
            "link": links[index],
            "date": dates[index]
        }

    # Clean up the dicitonary 
    products_dictionary = filter_price(products_dictionary, 1000)
    profitable_products = get_potentially_profitable_products(products_dictionary, price_avg)

    #Print all products
    for product_id, product in products_dictionary.items():
        console.print(f"[bold red]Product ID:[/bold red][bold cyan]{product_id}[/bold cyan]\nName: {product['name']}\nPrice: {product['price']}\nLink: [click here]{product['link']}\nDate: {product['date']}\n\n")



    # Find the most expensive product
    most_expensive = max(products_dictionary.values(), key=lambda p: p["price"])
    console.print(f"\nMost Expensive\n===================\n{most_expensive['name']}\n{most_expensive['price']}\n{most_expensive['link']}\n{most_expensive['date']}\n=====================")

    least_expensive = min(products_dictionary.values(), key=lambda p: p["price"])
    console.print(f"\nLeast Expensive\n===================\n{least_expensive['name']}\n{least_expensive['price']}\n{least_expensive['link']}\n{least_expensive['date']}\n=====================")

    console.print(f"[bold white]Average price - {int(price_avg)}[/bold white]")

    #Load dictionary to later compare what products were sold 
    loaded_dictionary = load_dictionary(f"data_all_time_{product_category}.pkl")

    #getting the ids of the items that were sold
    sold_items_ids = find_sold_items(ids_old=loaded_dictionary.keys(), ids=products_dictionary.keys())

    #Print sold items out 
    if not sold_items_ids:
        console.print("[bold green]No items were sold![/bold green]")
    else:
        for item_id, item_value in loaded_dictionary.items():
            if item_id in sold_items_ids:
                # Check if the item exists in the new dictionary but with a different ID
                for new_id, new_value in products_dictionary.items():
                    if is_same_product(item_value, new_value):
                        console.print(f"[bold yellow]Item {item_id} might have been reuploaded with a new ID ({new_id})[/bold yellow]")
                        break
                else:
                    console.print(f"[bold red]Item {item_id} has been sold![/bold red]")
                    console.print(f"Name of the item: {item_value['name']}")
                    console.print(f"Link to the item: {item_value['link']}")
                    console.print(f"Price of the item: {item_value['price']}")
                    console.print(f"Date of the item: {item_value['date']}")
                    console.print("\n\n")

    #Using ids we got before turn the sold items ids into a dictionary
    sold_items_dict = {}
    for item_id in sold_items_ids:
        if item_id in loaded_dictionary:
            sold_items_dict[item_id] = loaded_dictionary[item_id]

    #Print if the dictionaries are the same
    print(loaded_dictionary == products_dictionary)

    # Here we try to create a "database" of the sold items, we load the dictionary
    loaded_sold_items = load_dictionary(f"sold_items_{product_category}.pkl")
    try:
        #here we add their values up
        sold_items_dict = sold_items_dict | loaded_sold_items
    except TypeError:
        console.print("[bold orange]No sold items found in the file.[/bold orange]")


    #Print the profitable products    
    if profitable_products:
        for item_id, item_value in profitable_products.items():
            console.print(f"[bold green]Item ID{item_id}[/bold green]")
            console.print(f"Name of the item: {item_value['name']}")
            console.print(f"Price of the item: {item_value['price']}")
            console.print(f"Potential profit: {int(price_avg) - item_value['price']}")
            console.print(f"Link to the item: {item_value['link']}")
            console.print(f"Date of the item: {item_value['date']}")
            console.print("\n\n")
    else:
        console.print(f"['bold red']No profitable products found![/bold red']")

    # Save the data to a files
    save_dictionary(profitable_products, filename=f"profitable_items_{product_category}.pkl")
    save_dictionary(sold_items_dict, filename=f"sold_items_{product_category}.pkl")
    save_dictionary(products_dictionary, filename=f"data_all_time_{product_category}.pkl")
    console.print("[bold green]Program ended succesfully![/bold green]")

# Function to filter out products with price too high 
def filter_price(products, max_price):
    filtered_products = {}
    for key, value in products.items():
        if value['price'] < max_price:
            filtered_products[key] = value
    return filtered_products
            

# Function to get potentially profitable products
def get_potentially_profitable_products(products, avg_price):
    profitable_products = {}
    for key, value in products.items():
        if value['price'] < avg_price:
            profitable_products[key] = value
    return profitable_products
#Getting the number of pages
def get_pages(link, links):
    text_page = safe_request(link)
    soup = BeautifulSoup(text_page, 'html.parser')
    pages = soup.findAll(class_=last_page)
    if pages:
        pages_to_search = int(pages[-1].text)
    else:
        print("No pagination found, defaulting to 1 page.")
        pages_to_search = 1
    for i in range(pages_to_search-1):
        links.append(link_power_suply_450W+f"?page={i+2}")

    return pages_to_search

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
# Function to start the logic of the program
def start_logic():
    
    pages_to_search = input('Enter link or one of the numbers \n1-Power Suply(general)\n2-Power Suply PC\n3 - Power suply 450w\n')
    if(pages_to_search == "1"):
        link_to_category = "https://www.olx.ua/uk/list/q-%D0%91%D0%BB%D0%BE%D0%BA-%D0%B6%D0%B8%D0%B2%D0%BB%D0%B5%D0%BD%D0%BD%D1%8F"
    elif(pages_to_search == "2"):
        link_to_category = "https://www.olx.ua/uk/list/q-%D0%9A%D0%BE%D0%BC%D0%BF'%D1%8E%D1%82%D0%B5%D1%80%D0%BD%D0%B8%D0%B9-%D0%B1%D0%BB%D0%BE%D0%BA-%D0%B6%D0%B8%D0%B2%D0%BB%D0%B5%D0%BD%D0%BD%D1%8F/"
    elif(pages_to_search == "3"):
        link_to_category = "https://www.olx.ua/uk/elektronika/kompyutery-i-komplektuyuschie/komplektuyuschie-i-aksesuary/q-%D0%B1%D0%BB%D0%BE%D0%BA-%D0%B6%D0%B8%D0%B2%D0%BB%D0%B5%D0%BD%D0%BD%D1%8F-450w/?currency=UAH"
    else:
        link_to_category = pages_to_search

    return link_to_category

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
link_tag = "css-qo0cxu"
price_tag = "css-13afqrm"
date_tag = "css-1mwdrlh"
product_name_tag = "css-1s3qyje"
rating_tag = "css-1pkf64r"
deleveries = "css-18icqaw"
last_page = "css-ps94ux"
#averages
price_avg = 0
#Links to store the links to the product pages 

power_suply_450W_htmls = []
fx6100_htmls = []
#Get the site html
link_power_suply_450W = 'https://www.olx.ua/uk/elektronika/kompyutery-i-komplektuyuschie/komplektuyuschie-i-aksesuary/q-%D0%B1%D0%BB%D0%BE%D0%BA-%D0%B6%D0%B8%D0%B2%D0%BB%D0%B5%D0%BD%D0%BD%D1%8F-450w/?currency=UAH'
link_fx6100 = 'https://www.olx.ua/uk/elektronika/kompyutery-i-komplektuyuschie/komplektuyuschie-i-aksesuary/q-fx6100/?currency=UAH&search%5Bfilter_enum_subcategory%5D%5B0%5D=protsessory'

#Get the first page
fx6100_htmls.append(link_fx6100)
power_suply_450W_htmls.append(link_power_suply_450W)


pages_to_search_power_suply_450W = get_pages(link_power_suply_450W, power_suply_450W_htmls)
pages_to_search_fx6100 =  get_pages(link_fx6100, fx6100_htmls)
#Loop through the pages


while True:
    main_loop(power_suply_450W_htmls, pages_to_search_power_suply_450W, "power_suply_450W")
    time.sleep(300)

#################################
##### Name:Mingyu Wang
##### Uniqname:mywang
#################################

from bs4 import BeautifulSoup
import requests
import json
import secrets # file that contains your API key
import sys
import sqlite3
import plotly.graph_objects as go
import webbrowser

BASE_URL = "https://www.attractionsofamerica.com" # https://www.attractionsofamerica.com/attractions/illinois.php
CACHE_FILENAME = "cache.json"
CACHE_DICT = {}
DB_NAME = 'attractions.sqlite'

mapbox_access_token = secrets.mapbox_access_token
map_request_api_key = secrets.map_request_api_key

class Attraction:
    ''' an attraction

    Instance Attributes
    -------------------
    name: string
        the name of an attraction (e.g. 'The Art Institute of Chicago')
    address: string
        the city and state of an attraction (e.g. '111 S Michigan Ave, Chicago, IL')

    zipcode: string
        the zip-code of an attraction  (e.g. '60603')

    website: string
        the website of an attraction (e.g. 'www.artic.edu')
    '''
    def __init__(self, state, name, address, zipcode, website, rating):
        self.name = name
        self.address = address
        self.zipcode = zipcode
        self.website = website
        self.state = state
        self.rating = rating
    def info(self): # return a string representation   
        information = "------------------------------------------------------------\n" + "[" + str(self.rating) + "] " + self.name +": " + self.address + " " + self.zipcode + "\n    website: " + self.website+"\n------------------------------------------------------------"
        return information

def build_state_url_dict():
    ''' Make a dictionary that maps state name to state page url from "https://www.attractionsofamerica.com/attractions"

    Parameters
    ----------
    None

    Returns
    -------
    dict
        key is a state name and value is the url
        e.g. {'illinois':'https://www.attractionsofamerica.com/attractions/illinois.php', ...}
    '''
    index_url = "/regional-attractions.php"
    state_dic = {}


    # Make the soup for the index page
    state_page_url = BASE_URL + index_url

    # check cache
    if state_page_url in CACHE_DICT.keys():
        print("Loading 50 states' urls from cache...")
        soup = BeautifulSoup(CACHE_DICT[state_page_url], 'html.parser')
    else:
        # load from cache
        print("Fetching urls for all 50 states...")
        response = requests.get(state_page_url)
        CACHE_DICT[state_page_url] = response.text
        save_cache(CACHE_DICT)
        soup = BeautifulSoup(response.text, 'html.parser')

    # parse the soup
    state_listing_divs = soup.find_all('div', class_='col-lg-12 col-md-12 pt10')
    for state_listing_div in state_listing_divs:
        state_blocks = state_listing_div.find_all('div', class_='col-md-4 other_tours', recursive=False)
        for state_block in state_blocks:
            state_lists = state_block.find_all('li')
            for state_list in state_lists:
                ## extract the state details URL
                state_link_tag = state_list.find('a')
                state_details_path = state_link_tag['href']
                state_details_url = BASE_URL + "/" + state_details_path

                ## extract the state name
                state_name = state_link_tag.text.strip()

                ## add the state to state_dic
                state_dic[state_name.lower()] = state_details_url

    return state_dic

def get_top10_attractions(state, state_url):
    '''Get top 10 attractions for a given state.
    
    Parameters
    ----------
    state_url: string
        The URL for a state's attraction
    
    Returns
    -------
    dic
        a dictionary containing top 10 attractions.
    '''
    
    top10_attraction_dic = {}
    # checking cache:
    if state_url in CACHE_DICT.keys():
        print("Loading cache...")
        soup = BeautifulSoup(CACHE_DICT[state_url], 'html.parser')
    else:
        print("Fetching...")
        response = requests.get(state_url)
        CACHE_DICT[state_url] = response.text
        save_cache(CACHE_DICT)
        soup = BeautifulSoup(response.text, 'html.parser')

    attraction_divs = soup.find_all('div', class_ = 'box_style_1') # find all attractions
    rating = 1
    for attraction_div in attraction_divs[1:11]:   # only parse the top 10 attractions:

        # default value:
        name = "no name"
        address = "no address"
        zipcode = "no zipcode"
        website = "no website"

        attraction = attraction_div.find('div')
        ## scrap Name
        name_parent = attraction.find('div', class_='pl10 pr10 pb10')
        name_raw = name_parent.h2.string
        name = name_raw.split(':')[1][1:] # get pure name

        items = attraction.find_all('p')
        for item in items:
            try:
                header = item.strong.i.next.split(':')[0]
            except:
                header = ""
            if(header == "Address"): ## scrap address and zipcode
                if(item.strong.nextSibling[-1].isnumeric()):
                    address = item.strong.nextSibling[0:-6].replace('\n', ' ')
                    zipcode = item.strong.nextSibling[-5:]
                else:  # if there is no zipcode:
                    address = item.strong.nextSibling
            elif(header == "Website"): ## scrap website
                website = item.find('a')['href']

        attraction = Attraction(state, name, address, zipcode, website, rating)
        top10_attraction_dic[rating] = attraction
        rating += 1
    return top10_attraction_dic

def open_cache():
    ''' Opens the cache file if it exists and loads the JSON into
    the CACHE_DICT dictionary.
    if the cache file doesn't exist, creates a new cache dictionary
    
    Parameters
    ----------
    None
    
    Returns
    -------
    The opened cache: dict
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        CACHE_DICT = json.loads(cache_contents)
        cache_file.close()
    except:
        CACHE_DICT = {}
    return CACHE_DICT


def save_cache(cache_dict):
    ''' Saves the current state of the cache to disk
    
    Parameters
    ----------
    cache_dict: dict
        The dictionary to save
    
    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME,"w")
    fw.write(dumped_json_cache)
    fw.close() 

def create_db():
    print("creating database to store attractions...")
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    drop_states_sql = 'DROP TABLE IF EXISTS "States"'
    drop_top10_attractions_sql = 'DROP TABLE IF EXISTS "TOP10_Attractions"'

    create_states_sql = '''
        CREATE TABLE IF NOT EXISTS 'states'(
            "id"	INTEGER NOT NULL,
            "state"	TEXT NOT NULL UNIQUE,
            "url"	TEXT NOT NULL UNIQUE,
            PRIMARY KEY("Id" AUTOINCREMENT)
        )
    '''

    create_top10_attractions_sql = '''
        CREATE TABLE "top10_attractions" (
            "id"	INTEGER NOT NULL,
            "state"	TEXT,
            "name"	TEXT,
            "address"	TEXT,
            "zipcode"	TEXT,
            "website"	TEXT,
            "rating"	INTEGER,
            PRIMARY KEY("id" AUTOINCREMENT)
        )
    '''


    cur.execute(drop_states_sql)
    cur.execute(drop_top10_attractions_sql)
    cur.execute(create_states_sql)
    cur.execute(create_top10_attractions_sql)
    conn.commit()
    conn.close()

def load_state(state_dict):
    ''' load the scrapped state url into database

    Parameters
    ----------
    state_dict : dict
        The dictionary containing state names and there urls

    Returns
    -------
    None
    '''
    print("loading scrapped urls into database...")
    insert_state_sql = '''
        INSERT INTO states
        VALUES (NULL, ?, ?)
    '''

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    for state in state_dict.keys():
        cur.execute(insert_state_sql,
            [
                state,
                state_dict[state]
            ]
        )
    conn.commit()
    conn.close()

def load_top10_attractions(top10_attractions_dict):
    ''' load the scrapped top10 attractoons into database

    Parameters
    ----------
    top10_ attractions_dict : dict
        The dictionary containing top 10 attractions for a given state

    Returns
    -------
    None
    '''

    insert_top10_attractions_sql = '''
        INSERT INTO top10_attractions
        VALUES (NULL, ?, ?, ?, ?, ?, ?)
    '''

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    state_name = list(top10_attractions_dict.values())[0].state
    string = "loading crawled "+state_name + "'s top10 attractions into database..."
    print(string)
    for attraction in top10_attractions_dict.keys():
        cur.execute(insert_top10_attractions_sql,
            [
                top10_attractions_dict[attraction].state,
                top10_attractions_dict[attraction].name,
                top10_attractions_dict[attraction].address,
                top10_attractions_dict[attraction].zipcode,
                top10_attractions_dict[attraction].website,
                top10_attractions_dict[attraction].rating
            ]
        )
    conn.commit()
    conn.close()

def retrieve_top10_attractions(state_name):
    ''' Retrieve the top10 attractoons from database for any given state

    Parameters
    ----------
    state_name : string
        The state name used for retriving.

    Returns
    -------
    attraction_list: a list of 10 attractions
    '''
    attractions_list = []

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    query = '''
    SELECT *
    FROM top10_attractions
    WHERE state= ?
    ''' 
    cur.execute(query, [state_name])
    for row in cur:
        attraction = Attraction(row[1], row[2], row[3], row[4], row[5], row[6])
        attractions_list.append(attraction)
    return attractions_list

def geocoding(address):
    ''' Convert address to geographic coordinates using maprequest api's geocoder
    Parameters
    ----------
    address : string
        The address for a given attraction

    Returns
    -------
    coordinate: dict
        the coordinate{"lat","long"}'''

    base_url = "http://www.mapquestapi.com/geocoding/v1/address"
    params = {
        "location": address,
        "outFormat" : "json",
        "key": map_request_api_key
    }
    response = requests.get(base_url, params)
    result = response.json()
    # print(result)
    coordinate = {}
    coordinate = result["results"][0]["locations"][0]["latLng"]
    return coordinate
    

def plot_attractions_location_on_map(lon, lat, name):
    ''' Plot the location of top 10 attraction of a given state using plotly & MapBox
    Parameters
    ----------
    lon : list
        The list of longitude
    lat : list
        The list of latitude

    Returns
    -------
    None
    '''
    fig = go.Figure(go.Scattermapbox(
        lat=lat,
        lon=lon,
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=9
        ),
        text= name,
    ))

    fig.update_layout(
        autosize=True,
        hovermode='closest',
        mapbox=dict(
            accesstoken=mapbox_access_token,
            bearing=0,
            center=dict(
                lat=float(lat[0]),
                lon=float(lon[0])
            ),
            pitch=0,
            zoom=5
        ),
    )

    # fig.show()
    fig.write_html("attractions.html", auto_open=True)

def draw_map_with_attractions(state_name):
    top10_atractions = retrieve_top10_attractions(state_name)
    list_lng = []
    list_lat = []
    list_name = []
    for attraction in top10_atractions:
        list_name.append(attraction.name)
        coordinate = geocoding(attraction.address)
        list_lng.append(str(coordinate["lng"]))
        list_lat.append(str(coordinate["lat"]))
    # print(list_lng)
    # print(list_lat)
    # print(list_name)
    
    plot_attractions_location_on_map(list_lng, list_lat, list_name)


if __name__ == "__main__":
    # load the cache
    CACHE_DICT = open_cache()

    # create database
    create_db() 

    # scrap url for all 50 states and load them into database table "state"
    state_dict = build_state_url_dict()
    load_state(state_dict)

    #scrap and crawl top10 attractions for all 50 states and load them into database table "top10_attractions"
    for state in state_dict.keys():
        top10_attractions_dict = get_top10_attractions(state, state_dict[state])
        load_top10_attractions(top10_attractions_dict)
    print("**********************************  Finish!  *****************************************")
    print("______________________________________________________________________________________")
    # user interface
    print("Welcome! This program provides you top10 tourist attractions in any state in the US.")
    while(True):
        state = input("Please input a state name(e.g. michigan) or \"exit\":")
        if(state.lower() in state_dict.keys()):
            top10_atractions = retrieve_top10_attractions(state)
            print("Top 10 tourist attractions in "+state+":")
            draw_map_with_attractions(state) # draw map
            for attraction in top10_atractions:
                print(attraction.info())    

            while(True):
                command = input("Input the number 1-10 for detailed search or \"exit\" or \"back\":")
                index = int(command)-1
                if(command == "exit"):
                    sys.exit(0)
                elif(command == "back"):
                    break
                elif(index in list(range(10))):
                    command2 = input("Input \"eat\" for nearby restaurant recommendations or \"website\" to jump to website or \"exit\" or \"back\":")
                    if(command2 == "exit"):
                        sys.exit(0)
                    elif(command2 == "back"):
                        break
                    elif(command2 == "eat"):
                        pass
                    elif(command2 == "website"):
                        website = top10_atractions[index-1].website
                        if(website == "no website"):
                            print("The website for this attraction is not available, please try other attractions!")
                        else:
                            # open url in default webbrowser:
                            webbrowser.open(website)
                else:
                    print("Please input a valid command, try again!")


        elif(state.lower == "exit"):
            sys.exit(0)
        else:
            print("Please input a valid state name. Try Again!")


    


    
    





    


import requests
from pyzipcode import ZipCodeDatabase


class RealEstate:

    def __init__(self):
        pass

    zipcode = -1
    state = None
    city = None
    maxdown = -1
    percentdown = -1
    term = -1
    loan_type = 'none'
    maxprice = -1
    listings = {}
    median = -1
    ppsf = -1

    def get_user_info(self):
        print("Welcome to the Real Estate Investing!\n")
        self.zipcode = 11566
        input("Enter the zipcode you would like to buy your new property in: ")

        while self.verify_zip():
            print("Zipcode must be a 6 digit number, please enter it again")
            self.zipcode = input("Enter the zipcode you would like to buy your new property in: ")

        zcbd = ZipCodeDatabase()
        zcbd = zcbd[self.zipcode]
        self.state = zcbd.state
        self.city = zcbd.city

        self.maxdown = input("Enter the maximum down payment you're willing to put down on the property: ")
        self.percentdown = input("Enter the maximum percent down payment you're willing to make: ")
        self.term = input("Enter the year length of the loan term you want (15, 20 or 30): ")
        self.loan_type = input("Enter the type of loan you want ('fixed or variable' ... enter with quotes): ")
        self.maxprice = self.maxdown / (float(self.percentdown) / 100)

    def verify_zip(self):
        return len(str(self.zipcode)) == 6

    def request_sold(self):
        import requests

        url = "https://us-real-estate.p.rapidapi.com/sold-homes"

        querystring = {"state_code": self.state,
                       "city": self.city,
                       "location": self.zipcode,
                       "offset": "0",
                       "sort": "sold_date",
                       "max_sold_days": "90",
                       "price_min": "0",
                       "price_max": self.maxprice}

        headers = {
            'x-rapidapi-key': "e6147c5770mshb7370c8f736b587p17ec5ajsn909b5f85fa0c",
            'x-rapidapi-host': "us-real-estate.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        data = response.json()

        return data

    def calculate_zip_stats(self):
        median_price_sum = 0
        sf_price_sum = 0
        median_count = 0
        sf_sum = 0

        for p in self.request_sold()['data']['results']:
            median_count += 1
            median_price_sum += p['description']['sold_price']
            if p['description']['sqft'] is not None:
                sf_sum += p['description']['sqft']
                sf_price_sum += p['description']['sold_price']

        median = median_price_sum / median_count
        ppsf = sf_price_sum / sf_sum

    def request_selling(self):
        url = "https://us-real-estate.p.rapidapi.com/for-sale"

        querystring = {"offset": "0",
                       "limit": "1",
                       "state_code": self.state,
                       "city": self.city,
                       "location": self.zipcode,
                       "sort": "relevant",
                       "price_min": "0",
                       "price_max": self.maxprice,
                       "price_reduced": "false"
                       }

        headers = {
            'x-rapidapi-key': "e6147c5770mshb7370c8f736b587p17ec5ajsn909b5f85fa0c",
            'x-rapidapi-host': "us-real-estate.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        data = response.json()
        return data

    def store_listings(self):
        for p in self.request_selling()['data']['results']:
            est_price = self.estimate_price(p['property_id'])
            est_rent = self.estimate_rent(p['location']['address']['line'], p['location']['address']['city'])
            est_mortgage = self.estimate_mortgage(p['location']['address']['postal_code'], est_price)
            noi = (est_rent - est_mortgage) * 12
            self.listings[p['property_id']] = {'address': p['location']['address']['line'],
                                               'city': p['location']['address']['city'],
                                               'zip': p['location']['address']['postal_code'],
                                               'selling_price': p['list_price'],
                                               'lot_sf': p['description']['lot_sqft'],
                                               'sf': p['description']['sqft'],
                                               'est_price': est_price,
                                               'est_rent': est_rent,
                                               'est_mortgage': est_mortgage,
                                               'below_median': self.is_below_median(p['list_price']),
                                               'below_est': self.is_below_est(est_price, p['list_price']),
                                               'cap_rate': self.calculate_cap_rate(est_price, noi)
                                               }



    @staticmethod
    def estimate_price(property_id):

        url = "https://us-real-estate.p.rapidapi.com/for-sale/home-estimate-value"

        querystring = {"property_id": str(property_id)}

        headers = {
            'x-rapidapi-key': "e6147c5770mshb7370c8f736b587p17ec5ajsn909b5f85fa0c",
            'x-rapidapi-host': "us-real-estate.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        data = response.json()
        total = 0
        count = 0
        if (data['data']['current_values']) is None:
            return "N/A"
        else:
            for e in data['data']['current_values']:
                count += 1
                total += e['estimate']
                return total / count

    def estimate_rent(self, address, city):
        url = "https://realtymole-rental-estimate-v1.p.rapidapi.com/rentalPrice"

        querystring = {"address": address + ", " + city + ", " + self.state}

        headers = {
            'x-rapidapi-key': "e6147c5770mshb7370c8f736b587p17ec5ajsn909b5f85fa0c",
            'x-rapidapi-host': "realtymole-rental-estimate-v1.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        data = response.json()
        return data['rent']

    def estimate_rate(self, zipcode):
        url = "https://us-real-estate.p.rapidapi.com/finance/average-rate"

        querystring = {"postal_code": zipcode}

        headers = {
            'x-rapidapi-key': "e6147c5770mshb7370c8f736b587p17ec5ajsn909b5f85fa0c",
            'x-rapidapi-host': "us-real-estate.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        data = response.json()

        if self.loan_type is 'fixed':
            if self.term == 15:
                return data['data']['mortgage_data']['average_rate']['fifteen_year_fix']
            if self.term == 20:
                return data['data']['mortgage_data']['average_rate']['twenty_year_fix']
            if self.term == 30:
                return data['data']['mortgage_data']['average_rate']['thirty_year_fix']
        if self.loan_type is 'variable':
            return data['data']['mortgage_data']['average_rate']['thirty_year_va']

    def estimate_mortgage(self, zipcode, price):

        url = "https://us-real-estate.p.rapidapi.com/finance/mortgage-calculate"

        querystring = {"show_amortization": "false",
                       "hoa_fees": "0",
                       "percent_tax_rate": "1.69",
                       "year_term": self.term,
                       "percent_rate": self.estimate_rate(zipcode),
                       "down_payment": self.maxdown,
                       "monthly_home_insurance": "200",
                       "price": price}

        headers = {
            'x-rapidapi-key': "e6147c5770mshb7370c8f736b587p17ec5ajsn909b5f85fa0c",
            'x-rapidapi-host': "us-real-estate.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        data = response.json()

        return data['data']['monthly_payment']

    def is_below_median(self, price):
        return price <= self.median

    @staticmethod
    def is_below_est(est, price):
        return price <= est

    @staticmethod
    def calculate_cap_rate(value, noi):
        return (noi / float(value)) * 100

    def printResults(self):

        for p in self.listings:
                print("Property ID on Realtor.com: ", p, "\n"
                      "Address: ", p.address, p.city, "\n",
                      "Listing Price", p.selling_price, "\n",
                      "Estimated Home Value", p['est_price'], "\n",
                      "House listed below its estimated value?", p['below_est'], "\n",
                      "House listed below town's median home price?", p['below_median'], "\n",
                      "Estimated Mortgage per month: ", p['est_mortgage'], "\n",
                      "Estimated Rental Income per month: ", p['est_rent'], "\n",
                      "Cap Rate: ", p['cap_rate'], "\n",
                      'Square Footage', p['sf'], "\n"
                      )


a = RealEstate()
a.get_user_info()
a.store_listings()
print("\nBelow, will print out a python list of the gathered data. Go to https://www.cleancss.com/python-beautify/ to make this text more readible.\n")
print(a.listings)

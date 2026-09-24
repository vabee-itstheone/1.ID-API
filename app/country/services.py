from app.models import Country
from app import db

def get_country_data():
    try:
        # Query the Country table
        countries = Country.query.all()

        # Convert the result to a list of dictionaries
        result = [
            {
                'Id': country.Id,
                'Name': country.Name,
                'ThreeCode': country.ThreeCode,
                'TwoCode': country.TwoCode,
                'MobileCode': country.MobileCode,
                'CidCode': country.CidCode,
                'CidCodeTwo': country.CidCodeTwo,
            }
            for country in countries
        ]

        return result

    except Exception as e:
        return {"error": str(e)}
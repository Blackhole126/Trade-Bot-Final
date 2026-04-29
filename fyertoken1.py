# Import the required module from the fyers_apiv3 package
from fyers_apiv3 import fyersModel

# Define your Fyers API credentials
client_id = "9SUZA2X41H-100"  # Replace with your client ID
secret_key = "VWUJ20PJSG"  # Replace with your secret key
redirect_uri = "https://www.google.com/"  # Replace with your redirect URI
response_type = "code" 
grant_type = "authorization_code"  

# The authorization code received from Fyers after the user grants access
auth_code = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOiI5U1VaQTJYNDFIIiwidXVpZCI6ImI3ODhiNjBiNjZmYTQ1Njc4NDM2MTYzYjEwOTQ4ZWFhIiwiaXBBZGRyIjoiIiwibm9uY2UiOiIiLCJzY29wZSI6IiIsImRpc3BsYXlfbmFtZSI6IkZBQTE4MzE1Iiwib21zIjoiSzEiLCJoc21fa2V5IjoiMGIyNWE2NzY3ODYzZmU3YjdhODRiZDQ4ODgzN2IxNDE4MjgwOWRjMDQ4N2FkZWFmMDNiZDEwMDIiLCJpc0RkcGlFbmFibGVkIjoiTiIsImlzTXRmRW5hYmxlZCI6Ik4iLCJhdWQiOiJbXCJkOjFcIixcImQ6MlwiLFwieDowXCIsXCJ4OjFcIixcIng6MlwiXSIsImV4cCI6MTc3NDcwMzg0NiwiaWF0IjoxNzc0NjczODQ2LCJpc3MiOiJhcGkubG9naW4uZnllcnMuaW4iLCJuYmYiOjE3NzQ2NzM4NDYsInN1YiI6ImF1dGhfY29kZSJ9.PP7xm2ZYXrGAXXNctYSpbtvAFMwUtf9_5AR7yoyAwOg"
# Create a session object to handle the Fyers API authentication and token generation
session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key, 
    redirect_uri=redirect_uri, 
    response_type=response_type, 
    grant_type=grant_type
)

# Set the authorization code in the session object
session.set_token(auth_code)

# Generate the access token using the authorization code
response = session.generate_token()

# Print the response, which should contain the access token and other details
print(response)



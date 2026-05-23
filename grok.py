from google import genai

API_KEY = "AIzaSyCPMBN0CFsNRewV_MFajtyetT_EM7e72LE"

client = genai.Client(api_key=API_KEY)

response = client.models.generate_content(
    model="gemini-2.5-flash",   # you can also try gemini-1.5-flash
    contents="Hello Gemini, test my API connection"
)

print(response.text)
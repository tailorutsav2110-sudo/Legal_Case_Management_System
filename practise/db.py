from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["Flaskdb"]
    print("MongoDB connected..")
except:
    print("MongoDB not connect..")
users = db["users"]
cases = db["cases"]
hearings = db["hearings"]
documents = db["documents"]
clients = db["clients"]        
doc_requests = db["doc_requests"]
notifications = db["notifications"] 
judgements = db["judgements"]
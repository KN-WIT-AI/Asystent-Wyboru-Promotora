import os
import pandas as pd
from openai import OpenAI
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
from flask import Flask, request, jsonify, render_template

collection_name = "supervisor_interests"
app = Flask(__name__, static_folder='static')

def connect_milvus(host='localhost', port='19530'):
    connections.connect(alias="default", host=host, port=port)
    print("Successfully connected to Milvus!")

def read_excel_data(file_path='promotorzy.xlsx'):
    try:
        df = pd.read_excel(file_path)
        return df
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None

def define_supervisors():
    try:
        df = read_excel_data()
        if df is not None:
            supervisors = []
            for index, row in df.iterrows():
                if pd.notna(row['Nazwa']):
                    # Split and convert to lowercase
                    interests = [z.strip().lower() for z in str(row['Zainteresowania']).split(';')] if pd.notna(
                        row['Zainteresowania']) else []
                    papers = [p.strip().lower() for p in str(row['Prace naukowe']).split(';')] if pd.notna(
                        row['Prace naukowe']) else []

                    # Remove empty strings
                    interests = [z for z in interests if z]
                    papers = [p for p in papers if p]

                    supervisor = {
                        "id": index + 1,
                        "name": row['Nazwa'].strip(),
                        "department": row['Katedra'].strip() if pd.notna(row['Katedra']) else "",
                        "email": row['Email'].strip() if pd.notna(row['Email']) else "",
                        "interests": interests,
                        "research_papers": papers
                    }
                    supervisors.append(supervisor)
            print(f"Loaded {len(supervisors)} supervisors from Excel")
            return supervisors
    except Exception as e:
        print(f"Error processing Excel data: {e}")
        return []

def configure_openai():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not set. Please set the OPENAI_API_KEY environment variable.")
    return OpenAI(api_key=api_key)

def generate_embedding(text, client):
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding for '{text}': {e}")
        return None

def generate_embeddings(supervisors, client):
    for supervisor in supervisors:
        supervisor['embeddings'] = []
        # Generate embeddings for interests
        for interest in supervisor['interests']:
            embedding = generate_embedding(interest, client)
            if embedding:
                supervisor['embeddings'].append({
                    "type": "interest",
                    "text": interest,
                    "embedding": embedding
                })
        # Generate embeddings for research papers
        for paper in supervisor['research_papers']:
            embedding = generate_embedding(paper, client)
            if embedding:
                supervisor['embeddings'].append({
                    "type": "research_paper",
                    "text": paper,
                    "embedding": embedding
                })
    return supervisors

def create_collection(collection_name, dim=1536):
    if not utility.has_collection(collection_name):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="supervisor_id", dtype=DataType.INT64, description="Supervisor ID"),
            FieldSchema(name="supervisor_name", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="department", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="email", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=20),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2000),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
        ]
        schema = CollectionSchema(fields)
        collection = Collection(name=collection_name, schema=schema)
        print(f"Collection '{collection_name}' has been created.")
    else:
        collection = Collection(name=collection_name)
        print(f"Using existing collection '{collection_name}'")
    return collection

def insert_data(collection, supervisors):
    for supervisor in supervisors:
        data_to_insert = {
            "supervisor_id": [],
            "supervisor_name": [],
            "department": [],
            "email": [],
            "type": [],
            "text": [],
            "embedding": []
        }

        for entry in supervisor['embeddings']:
            data_to_insert["supervisor_id"].append(supervisor['id'])
            data_to_insert["supervisor_name"].append(supervisor['name'])
            data_to_insert["department"].append(supervisor.get('department', ''))
            data_to_insert["email"].append(supervisor.get('email', ''))
            data_to_insert["type"].append(entry['type'])
            data_to_insert["text"].append(entry['text'])
            data_to_insert["embedding"].append(entry['embedding'])

        if data_to_insert["supervisor_id"]:
            data_to_insert["embedding"] = [list(map(float, emb)) for emb in data_to_insert["embedding"]]
            collection.insert([
                data_to_insert["supervisor_id"],
                data_to_insert["supervisor_name"],
                data_to_insert["department"],
                data_to_insert["email"],
                data_to_insert["type"],
                data_to_insert["text"],
                data_to_insert["embedding"]
            ])
            collection.flush()
            print(f"Inserted data for supervisor {supervisor['name']}")

def create_index_if_needed(collection):
    index_info = collection.indexes
    if not index_info:
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        print("Created new index.")
    else:
        print("Index already exists.")

def find_similar_interests(collection, query, client, top_k=5):
    query = query.lower()
    embedding_query = generate_embedding(query, client)
    if not embedding_query:
        print("Failed to generate embedding for query.")
        return

    collection.load()
    search_params = {
        "metric_type": "COSINE",
        "params": {"nprobe": 10}
    }

    # Increase limit to get more potential matches
    results = collection.search(
        data=[embedding_query],
        anns_field="embedding",
        param=search_params,
        limit=100,  # Increased from 40
        expr=None,
        output_fields=["supervisor_name", "department", "email", "type", "text"]
    )

    supervisor_results = {}
    for hit in results[0]:
        supervisor = hit.entity.get("supervisor_name")
        if supervisor not in supervisor_results:
            supervisor_results[supervisor] = {
                "department": hit.entity.get("department"),
                "email": hit.entity.get("email"),
                "interests": [],
                "research_papers": []
            }

        if hit.entity.get("type") == "interest":
            supervisor_results[supervisor]["interests"].append({
                "text": hit.entity.get("text"),
                "distance": hit.distance
            })
        else:
            supervisor_results[supervisor]["research_papers"].append({
                "text": hit.entity.get("text"),
                "distance": hit.distance
            })

    final_results = []
    for supervisor, data in supervisor_results.items():
        # Get all matches sorted by distance
        top_interests = sorted(data["interests"], key=lambda x: x['distance'])
        top_papers = sorted(data["research_papers"], key=lambda x: x['distance'])

        # Calculate average using all matches
        interests_avg = sum(m['distance'] for m in top_interests) / len(top_interests) if top_interests else 0
        papers_avg = sum(m['distance'] for m in top_papers) / len(top_papers) if top_papers else 0

        total_matches = len(top_interests) + len(top_papers)
        if total_matches > 0:
            combined_avg = (interests_avg * len(top_interests) + papers_avg * len(top_papers)) / total_matches

            final_results.append({
                "supervisor": supervisor,
                "average_score": combined_avg,
                "top_interests": [m['text'] for m in top_interests],  # All interests
                "top_papers": [m['text'] for m in top_papers]         # All papers
            })

    final_results.sort(key=lambda x: x['average_score'], reverse=True)
    return final_results

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/zapytanie', methods=['POST'])
def handle_query():
    data = request.json
    query = data.get("zapytanie")

    if not query:
        return jsonify({"error": "Zapytanie jest wymagane."}), 400

    try:
        client = configure_openai()
        collection = Collection(collection_name)
        results = find_similar_interests(collection, query, client)

        if results:
            return jsonify({"results": results})
        else:
            return jsonify({"message": "Brak wyników dla zapytania."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    try:
        connect_milvus()
        client = configure_openai()

        if not utility.has_collection(collection_name):
            print("Performing initial setup...")
            collection = create_collection(collection_name)
            supervisors = define_supervisors()
            supervisors = generate_embeddings(supervisors, client)
            insert_data(collection, supervisors)
            create_index_if_needed(collection)
            collection.load()
        else:
            print("Using existing collection...")
            collection = Collection(collection_name)
            create_index_if_needed(collection)
            collection.load()

        app.run(host='0.0.0.0', port=5000)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        connections.disconnect("default")
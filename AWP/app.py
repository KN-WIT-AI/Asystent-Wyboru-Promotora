import os
from openai import OpenAI
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
import numpy as np
from flask import Flask, request, jsonify, render_template

app = Flask(__name__, static_folder='static')

# --- Krok 1: Połączenie z Milvus ---
def connect_milvus(host='localhost', port='19530'):
    connections.connect(alias="default", host=host, port=port)
    print("Successfully connected to Milvus!")


# --- Krok 2: Definicja Promotorów i Ich Zainteresowań ---
def define_promoters():
    promotorzy = [
        {
            "id": 1,
            "nazwa": "Dr. Jan Kowalski",
            "zainteresowania": [
                "Uczenie maszynowe",
                "Analiza danych",
                "Sztuczna inteligencja w medycynie"
            ]
        },
        {
            "id": 2,
            "nazwa": "Dr. Anna Nowak",
            "zainteresowania": [
                "Inżynieria oprogramowania",
                "Systemy rozproszone",
                "Bezpieczeństwo komputerowe"
            ]
        },
        {
            "id": 3,
            "nazwa": "Dr. Piotr Wiśniewski",
            "zainteresowania": [
                "Robotyka",
                "Internet rzeczy (IoT)",
                "Automatyzacja przemysłowa"
            ]
        },
        {
            "id": 4,
            "nazwa": "Prof. Dr. hab. inż. Mariusz Siedem",
            "zainteresowania": [
                "Tajski boks",
                "Błotne SPA",
                "Gra o tron"
            ]
        }
    ]
    return promotorzy


# --- Krok 3: Konfiguracja OpenAI API ---
def configure_openai():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not set. Please set the OPENAI_API_KEY environment variable.")
    return OpenAI(api_key=api_key)


# --- Krok 4: Generowanie Embeddingów ---
def generuj_embedding(tekst, client):
    try:
        response = client.embeddings.create(
            input=tekst,
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding for '{tekst}': {e}")
        return None


def generate_embeddings(promotorzy, client):
    for promotor in promotorzy:
        promotor['embeddingy'] = []
        for zainteresowanie in promotor['zainteresowania']:
            embedding = generuj_embedding(zainteresowanie, client)
            if embedding:
                promotor['embeddingy'].append({
                    "zainteresowanie": zainteresowanie,
                    "embedding": embedding
                })
    return promotorzy


# --- Krok 5: Definicja i Tworzenie Kolekcji w Milvus ---
def create_collection(collection_name, dim=1536):
    # Only create if collection doesn't exist
    if not utility.has_collection(collection_name):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="promotor_id", dtype=DataType.INT64, description="ID promotora"),
            FieldSchema(name="nazwa_promotora", dtype=DataType.VARCHAR, max_length=100, description="Nazwa promotora"),
            FieldSchema(name="zainteresowanie", dtype=DataType.VARCHAR, max_length=255,
                        description="Opis zainteresowania"),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim, description="Embedding wektor")
        ]
        schema = CollectionSchema(fields, description="Kolekcja zainteresowań promotorów")
        collection = Collection(name=collection_name, schema=schema)
        print(f"Kolekcja '{collection_name}' została utworzona.")
    else:
        collection = Collection(name=collection_name)
        print(f"Używam istniejącej kolekcji '{collection_name}'")
    return collection


def check_if_promotor_exists(collection, promotor_id):
    collection.load()
    results = collection.query(
        expr=f"promotor_id == {promotor_id}",
        output_fields=["promotor_id"],
        limit=1
    )
    return len(results) > 0


# --- Krok 6: Wstawianie Danych do Kolekcji ---
def insert_data(collection, promotorzy):
    for promotor in promotorzy:
        # Check if promotor already exists
        if check_if_promotor_exists(collection, promotor['id']):
            print(f"Promotor {promotor['nazwa']} już istnieje w bazie. Pomijam.")
            continue

        data_to_insert = {
            "promotor_id": [],
            "nazwa_promotora": [],
            "zainteresowanie": [],
            "embedding": []
        }

        for z_entry in promotor['embeddingy']:
            data_to_insert["promotor_id"].append(promotor['id'])
            data_to_insert["nazwa_promotora"].append(promotor['nazwa'])
            data_to_insert["zainteresowanie"].append(z_entry['zainteresowanie'])
            data_to_insert["embedding"].append(z_entry['embedding'])

        if data_to_insert["promotor_id"]:
            data_to_insert["embedding"] = [list(map(float, emb)) for emb in data_to_insert["embedding"]]
            insert_result = collection.insert([
                data_to_insert["promotor_id"],
                data_to_insert["nazwa_promotora"],
                data_to_insert["zainteresowanie"],
                data_to_insert["embedding"]
            ])
            collection.flush()  # Make sure data is written to disk
            print(f"Wstawiono dane dla promotora {promotor['nazwa']}")


# --- Krok 7: Tworzenie Indeksu dla Wektorów ---
def create_index_if_needed(collection):
    # Check if index exists
    index_info = collection.indexes
    if not index_info:
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        print("Utworzono nowy indeks.")
    else:
        print("Indeks już istnieje.")


# --- Krok 8: Sprawdzanie Danych w Milvus ---
def check_all_milvus_data(collection_name):
    try:
        # Get collection
        collection = Collection(collection_name)

        # Load collection
        collection.load()

        # Get total count
        total_count = collection.num_entities
        print(f"\n=== MILVUS DATABASE CONTENT ===")
        print(f"Total number of entries: {total_count}")

        if total_count > 0:
            # Query all data
            results = collection.query(
                expr="promotor_id >= 0",  # This will get all records
                output_fields=["promotor_id", "nazwa_promotora", "zainteresowanie"],
                limit=total_count  # Get all records
            )

            # Group by promotor
            promotor_data = {}
            for r in results:
                promotor_id = r['promotor_id']
                if promotor_id not in promotor_data:
                    promotor_data[promotor_id] = {
                        'nazwa': r['nazwa_promotora'],
                        'zainteresowania': []
                    }
                promotor_data[promotor_id]['zainteresowania'].append(r['zainteresowanie'])

            # Print organized data
            print("\nStored Supervisors and their interests:")
            print("=====================================")
            for promotor_id, data in promotor_data.items():
                print(f"\nPromotor ID: {promotor_id}")
                print(f"Nazwa: {data['nazwa']}")
                print("Zainteresowania:")
                for i, zainteresowanie in enumerate(data['zainteresowania'], 1):
                    print(f"  {i}. {zainteresowanie}")
                print("-------------------------------------")

        else:
            print("No data found in the collection!")

        collection.release()
        return total_count > 0

    except Exception as e:
        print(f"Error checking Milvus data: {e}")
        return False


# --- Krok 9: Wyszukiwanie Najbliższych Sąsiadów ---
def znajdz_podobne_zainteresowania(collection, zapytanie, client, top_k=5):
    embedding_zapytania = generuj_embedding(zapytanie, client)
    if not embedding_zapytania:
        print("Nie udało się wygenerować embeddingu dla zapytania.")
        return

    collection.load()
    search_params = {
        "metric_type": "L2",
        "params": {"nprobe": 10}
    }

    results = collection.search(
        data=[embedding_zapytania],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        expr=None,
        output_fields=["nazwa_promotora", "zainteresowanie"]
    )

    print(f"\nNajbliżsi sąsiedzi dla zapytania: '{zapytanie}'")
    response = []
    for i, result in enumerate(results[0]):
        response.append({
            "supervisor": result.entity.get("nazwa_promotora"),
            "zainteresowanie": result.entity.get("zainteresowanie"),
            "Odległość": result.distance
        })
        print(f"Rank {i + 1}:")
        print(f"Promotor: {result.entity.get('nazwa_promotora')}")
        print(f"Zainteresowanie: {result.entity.get('zainteresowanie')}")
        print(f"Odległość: {result.distance}\n")
    return response

# --- Krok 10: Dodawanie Nowego Promotora ---
def add_new_supervisor(collection_name, supervisor_data, client):
    """
    Add a new supervisor to the existing database.

    supervisor_data format:
    {
        "id": int,
        "nazwa": str,
        "zainteresowania": list[str]
    }
    """
    try:
        # Get collection
        collection = Collection(collection_name)

        # Generate embeddings for the new supervisor
        supervisor = generate_embeddings([supervisor_data], client)[0]

        # Insert the new supervisor
        insert_data(collection, [supervisor])

        print(f"Successfully added supervisor: {supervisor_data['nazwa']}")
        return True
    except Exception as e:
        print(f"Error adding supervisor: {e}")
        return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/zapytanie', methods=['POST'])
def api_zapytanie():
    data = request.json
    zapytanie = data.get("zapytanie")

    if not zapytanie:
        return jsonify({"error": "Zapytanie jest wymagane."}), 400

    try:
        client = configure_openai()
        collection = Collection("promotorzy_zainteresowania")
        results = znajdz_podobne_zainteresowania(collection, zapytanie, client)
        print(results)

        if results:
            return jsonify({"results": results})
        else:
            return jsonify({"message": "Brak wyników dla zapytania."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# --- Główny Blok Skryptu ---
if __name__ == "__main__":
    try:
        # Connect to Milvus
        connect_milvus()
        collection_name = "promotorzy_zainteresowania"

        # Initialize OpenAI client
        client = configure_openai()

        # Check if we need to perform initial setup
        if not utility.has_collection(collection_name):
            print("Performing initial setup...")
            promotorzy = define_promoters()
            promotorzy = generate_embeddings(promotorzy, client)
            collection = create_collection(collection_name)
            insert_data(collection, promotorzy)
            # Create index after inserting data
            create_index_if_needed(collection)
        else:
            print("Using existing collection...")
            collection = Collection(collection_name)
            create_index_if_needed(collection)  # Make sure the index exists for existing collection

        # Always verify data
        check_all_milvus_data(collection_name)

         #Example: Add a new supervisor
        # new_supervisor = {
        #      "id": 3,
        #      "nazwa": "Dr. Piotr Wiśniewski",
        #      "zainteresowania": [
        #          "Robotyka",
        #          "Internet rzeczy (IoT)",
        #          "Automatyzacja przemysłowa"
        #      ]
        # }
        # add_new_supervisor(collection_name, new_supervisor, client)

        # Run Flask application (this should be the last step)
        app.run(host='0.0.0.0', port=5000)

    except Exception as e:
        print(f"Wystąpił błąd: {e}")
    finally:
        connections.disconnect("default")

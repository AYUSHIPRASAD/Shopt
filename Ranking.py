import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Load data
def load_data(file_path):
    df_products = pd.read_excel(file_path, sheet_name='Product and attributes')
    df_avail_price = pd.read_excel(file_path, sheet_name='Stroller-Avail-Price')
    df_features = pd.read_excel(file_path, sheet_name='Feature Description')
    return df_products, df_avail_price, df_features

# Prepare feature embeddings
def prepare_feature_embeddings(df_features, model):
    feature_embeddings = {}
    for _, row in df_features.iterrows():
        feature_embeddings[row['Feature']] = model.encode(row['Definition'])
    return feature_embeddings

# Prepare product embeddings
def prepare_product_embeddings(df_products, df_avail_price, model):
    product_embeddings = {}
    for _, row in df_products.iterrows():
        product = row['Item']

        # Get specifications from 'Stroller-Avail-Price'
        specs = df_avail_price[df_avail_price['Product'] == product]['Specifications'].values

        # Combine all feature descriptions
        descriptions = [str(row[col]) for col in ['Feature desc 1', 'Feature desc 2', 'Feature desc 3', 'Feature desc 4'] if pd.notna(row[col])]

        # Add specifications if available
        if len(specs) > 0 and pd.notna(specs[0]):
            descriptions.append(str(specs[0]))

        # Create combined text and its embedding
        combined_text = ' '.join(descriptions)
        product_embeddings[product] = model.encode(combined_text)

    return product_embeddings

# Find matching products
def recommend_products(features, top_n=5):
    # if len(features) < 2:
    #     raise ValueError("Please provide at least 2 features")

    # Verify all features exist
    for feature in features:
        if feature not in feature_embeddings:
            raise ValueError(f"Feature '{feature}' not found in feature definitions")

    # Calculate average feature embedding
    feature_embeds = [feature_embeddings[f] for f in features]
    avg_feature_embedding = np.mean(feature_embeds, axis=0)

    # Compute similarity scores for each product
    product_scores = []
    for product, embedding in product_embeddings.items():
        similarity = cosine_similarity(avg_feature_embedding.reshape(1, -1), embedding.reshape(1, -1))[0][0]

        product_scores.append({
            'product': product,
            'similarity_score': round(similarity * 100, 2)  # Convert to percentage
        })

    # Sort by similarity score and get top N
    ranked_products = sorted(product_scores, key=lambda x: x['similarity_score'], reverse=True)[:top_n]

    # Add product details
    # for product in ranked_products:
    #     specs = df_avail_price[df_avail_price['Product'] == product['product']]['Specifications'].values
    #     product['specifications'] = specs[0] if len(specs) > 0 else None

    return ranked_products

# Load data and prepare embeddings
file_path = r"C:\Users\ayush\OneDrive\Desktop\Shopt\Codes\Data Lookup Table.xlsx"
df_products, df_avail_price, df_features = load_data(file_path)
model = SentenceTransformer('all-MiniLM-L6-v2')
feature_embeddings = prepare_feature_embeddings(df_features, model)
product_embeddings = prepare_product_embeddings(df_products, df_avail_price, model)

# Example usage
input_features1 = ["Lightweight", "UV-protection", "Portability", "Safety"]
top_products = recommend_products(input_features1)
print(top_products)
print('-----------------------')

input_features2 = ["Lightweight", "UV-protection", "Portability"]
top_products = recommend_products(input_features2)
print(top_products)
print('-----------------------')

input_features3 = ["Versatility", "UV-protection", "Portability"]
top_products = recommend_products(input_features3)
print(top_products)
print('-----------------------')

input_features4 = ["Storage space", "Ease of cleaning", "Adjustable handlebar"]
top_products = recommend_products(input_features4)
print(top_products)
print('-----------------------')

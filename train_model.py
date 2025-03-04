import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

# Step 1: Load the dataset
df = pd.read_csv('disease_data.csv')  # Ensure this file exists in the correct folder

# Step 2: Feature Extraction
vectorizer = CountVectorizer()
X = vectorizer.fit_transform(df['Symptoms'])  # Convert symptoms to numerical data
y = df['Disease']  # Labels

# Step 3: Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Step 4: Train Model
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Step 5: Save Model & Vectorizer
joblib.dump(model, 'models/ai_model.pkl')
joblib.dump(vectorizer, 'models/vectorizer.pkl')

# Step 6: Evaluate Model
accuracy = model.score(X_test, y_test)
print(f"✅ Model Accuracy: {accuracy * 100:.2f}%")

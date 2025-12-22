import requests
import os
from flask import current_app

class FoodAPIService:
    def __init__(self):
        self.api_key = os.getenv('FOOD_API_KEY')
        self.base_url = os.getenv('FOOD_API_URL')
        
    def search_foods(self, query, limit=10):
        """Search for foods using USDA API"""
        try:
            params = {
                'api_key': self.api_key,
                'query': query,
                'pageSize': limit,
                'dataType': ['Foundation', 'SR Legacy']  # Best quality data
            }
            
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            return self.format_food_results(data.get('foods', []))
            
        except requests.RequestException as e:
            current_app.logger.error(f"API Error: {e}")
            return self.get_fallback_foods(query)
    
    def format_food_results(self, foods):
        """Format API results for our app"""
        formatted = []
        for food in foods:
            # Extract nutrition info
            nutrients = {n['nutrientName']: n['value'] 
                        for n in food.get('foodNutrients', [])}
            
            formatted.append({
                'id': food['fdcId'],
                'name': food['description'],
                'calories': nutrients.get('Energy', 0),
                'protein': nutrients.get('Protein', 0),
                'carbs': nutrients.get('Carbohydrate, by difference', 0),
                'fat': nutrients.get('Total lipid (fat)', 0)
            })
        return formatted
    
    def get_fallback_foods(self, query):
        """Fallback data when API fails"""
        fallback_db = {
            'apple': {'calories': 52, 'protein': 0.3, 'carbs': 14, 'fat': 0.2},
            'banana': {'calories': 89, 'protein': 1.1, 'carbs': 23, 'fat': 0.3},
            'chicken': {'calories': 239, 'protein': 27, 'carbs': 0, 'fat': 14},
            'rice': {'calories': 130, 'protein': 2.7, 'carbs': 28, 'fat': 0.3},
            'egg': {'calories': 155, 'protein': 13, 'carbs': 1.1, 'fat': 11},
            'bread': {'calories': 265, 'protein': 9, 'carbs': 49, 'fat': 3.2},
            'milk': {'calories': 42, 'protein': 3.4, 'carbs': 5, 'fat': 1}
        }
        
        matches = [{'name': k, **v} for k, v in fallback_db.items() 
                  if query.lower() in k.lower()]
        return matches[:5]

# Create global instance
food_service = FoodAPIService()
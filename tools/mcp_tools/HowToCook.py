from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from mcp.server.fastmcp import FastMCP
import random

# Section 1: Schema
class Ingredient(BaseModel):
    """Represents a recipe ingredient."""
    name: str = Field(..., description="Name of the ingredient")
    amount: str = Field(..., description="Quantity of the ingredient")

class Recipe(BaseModel):
    """Represents a complete recipe."""
    recipe_id: str = Field(..., description="Unique identifier for the recipe")
    name: str = Field(..., description="Display name of the recipe")
    description: str = Field(..., description="Short summary describing the dish")
    category: str = Field(..., description="Category of the recipe")
    ingredients: List[Ingredient] = Field(default=[], description="List of ingredients required")
    steps: List[str] = Field(default=[], description="Ordered cooking instructions")
    tips: List[str] = Field(default=[], description="Helpful cooking tips")

class CookingScenario(BaseModel):
    """Main scenario model for cooking assistant."""
    recipes: Dict[str, Recipe] = Field(default={}, description="All available recipes")
    categories: List[str] = Field(default=[], description="Available recipe categories")
    random_seed: Optional[int] = Field(default=None, description="Random seed for reproducible recommendations")
    
Scenario_Schema = [Ingredient, Recipe, CookingScenario]

# Section 2: Class
class HowToCookAPI:
    def __init__(self):
        """Initialize cooking API with empty state."""
        self.recipes: Dict[str, Recipe] = {}
        self.categories: List[str] = []
        self.random_seed: Optional[int] = None
        
    def load_scenario(self, scenario: dict) -> None:
        """Load scenario data into the API instance."""
        model = CookingScenario(**scenario)
        self.recipes = model.recipes
        self.categories = model.categories
        self.random_seed = model.random_seed
        if self.random_seed is not None:
            random.seed(self.random_seed)

    def save_scenario(self) -> dict:
        """Save current state as scenario dictionary."""
        return {
            "recipes": {recipe_id: recipe.dict() for recipe_id, recipe in self.recipes.items()},
            "categories": self.categories,
            "random_seed": self.random_seed
        }

    def get_recipe_details(self, recipe_id: str) -> dict:
        """Retrieve full details for a specific recipe."""
        recipe = self.recipes[recipe_id]
        return {
            "recipe_id": recipe.recipe_id,
            "name": recipe.name,
            "description": recipe.description,
            "category": recipe.category,
            "ingredients": [ingredient.dict() for ingredient in recipe.ingredients],
            "steps": recipe.steps,
            "tips": recipe.tips
        }

    def list_all_categories(self) -> dict:
        """List all available recipe categories."""
        return {"categories": self.categories}

    def list_recipes_by_category(self, category: Optional[str] = None) -> dict:
        """List recipes filtered by category."""
        filtered_recipes = []
        
        if category:
            recipes = [recipe for recipe in self.recipes.values() if recipe.category == category]
        else:
            recipes = list(self.recipes.values())
            
        for recipe in recipes:
            filtered_recipes.append({
                "recipe_id": recipe.recipe_id,
                "name": recipe.name,
                "description": recipe.description
            })
            
        return {"recipes": filtered_recipes}

    def recommend_meal(self, people_count: int, category: Optional[str] = None, avoid_items: Optional[List[str]] = None) -> dict:
        """Generate personalized meal recommendation."""
        if avoid_items is None:
            avoid_items = []
            
        candidates = []
        for recipe in self.recipes.values():
            if category and recipe.category != category:
                continue
                
            # Check if recipe contains avoided ingredients
            recipe_ingredients = [ing.name.lower() for ing in recipe.ingredients]
            has_avoided = any(avoid_item.lower() in " ".join(recipe_ingredients) for avoid_item in avoid_items)
            
            if not has_avoided:
                candidates.append(recipe)
                
        if not candidates:
            # Return any recipe if no matches found
            candidates = list(self.recipes.values())
            
        selected = random.choice(candidates)
        
        return {
            "recipe_id": selected.recipe_id,
            "name": selected.name,
            "description": selected.description,
            "category": selected.category,
            "ingredients": [ing.dict() for ing in selected.ingredients],
            "steps": selected.steps,
            "tips": selected.tips
        }

    def get_random_dish_recommendation(self, people_count: int) -> dict:
        """Get random dish recommendation."""
        selected = random.choice(list(self.recipes.values()))
        
        return {
            "recipe_id": selected.recipe_id,
            "name": selected.name,
            "description": selected.description,
            "category": selected.category,
            "ingredients": [ing.dict() for ing in selected.ingredients],
            "steps": selected.steps,
            "tips": selected.tips
        }

# Section 3: MCP Tools
mcp = FastMCP(name="HowToCook")
api = HowToCookAPI()

@mcp.tool()
def load_scenario(scenario: dict) -> str:
    """
    Load scenario data into the cooking API.
    
    Args:
        scenario (dict): Scenario dictionary matching CookingScenario schema.
    
    Returns:
        success_message (str): Success message.
    """
    try:
        if not isinstance(scenario, dict):
            raise ValueError("Scenario must be a dictionary")
        api.load_scenario(scenario)
        return "Successfully loaded scenario"
    except Exception as e:
        raise e

@mcp.tool()
def save_scenario() -> dict:
    """
    Save current cooking state as scenario dictionary.
    
    Returns:
        scenario (dict): Dictionary containing all current state variables.
    """
    try:
        return api.save_scenario()
    except Exception as e:
        raise e

@mcp.tool()
def get_recipe_details(recipe_id: str) -> dict:
    """
    Retrieve full details for a specific recipe by its unique identifier.
    
    Args:
        recipe_id (str): The unique identifier of the recipe.
    
    Returns:
        recipe_id (str): The unique identifier of the recipe.
        name (str): The display name of the recipe.
        description (str): A short summary describing the dish.
        category (str): The category to which the recipe belongs.
        ingredients (list): List of ingredient objects required for the recipe.
        steps (list): Ordered list of cooking instructions.
        tips (list): Helpful cooking tips or variations.
    """
    try:
        if not recipe_id or not isinstance(recipe_id, str):
            raise ValueError("Recipe ID must be a non-empty string")
        if recipe_id not in api.recipes:
            raise ValueError(f"Recipe {recipe_id} not found")
        return api.get_recipe_details(recipe_id)
    except Exception as e:
        raise e

@mcp.tool()
def list_all_categories() -> dict:
    """
    List all available categories of recipes.
    
    Returns:
        categories (list): List of all category names available.
    """
    try:
        return api.list_all_categories()
    except Exception as e:
        raise e

@mcp.tool()
def list_recipes_by_category(category: Optional[str] = None) -> dict:
    """
    List all recipes belonging to a specific category.
    
    Args:
        category (str) [Optional]: The category name to filter recipes.
    
    Returns:
        recipes (list): List of recipes matching the specified category.
    """
    try:
        if category is not None and not isinstance(category, str):
            raise ValueError("Category must be a string if provided")
        return api.list_recipes_by_category(category)
    except Exception as e:
        raise e

@mcp.tool()
def recommend_meal(people_count: int, category: Optional[str] = None, avoid_items: Optional[List[str]] = None) -> dict:
    """
    Generate personalized meal recommendation based on preferences.
    
    Args:
        people_count (int): The number of people to cook for (range 1-10).
        category (str) [Optional]: Preferred category to narrow recommendations.
        avoid_items (list) [Optional]: List of ingredient names to exclude.
    
    Returns:
        recipe_id (str): The unique identifier of the recommended recipe.
        name (str): The display name of the recipe.
        description (str): A short summary describing the dish.
        category (str): The category of the recipe.
        ingredients (list): List of ingredient objects required.
        steps (list): Ordered list of cooking instructions.
        tips (list): Helpful cooking tips or variations.
    """
    try:
        if not isinstance(people_count, int):
            raise ValueError("People count must be an integer")
        if people_count < 1 or people_count > 10:
            raise ValueError("People count must be between 1 and 10")
        if avoid_items is not None and not isinstance(avoid_items, list):
            raise ValueError("Avoid items must be a list if provided")
        return api.recommend_meal(people_count, category, avoid_items)
    except Exception as e:
        raise e

@mcp.tool()
def get_random_dish_recommendation(people_count: int) -> dict:
    """
    Get a random dish recommendation suitable for the number of diners.
    
    Args:
        people_count (int): The number of people to dine (range 1-10).
    
    Returns:
        recipe_id (str): The unique identifier of the recommended recipe.
        name (str): The display name of the recipe.
        description (str): A short summary describing the dish.
        category (str): The category of the recipe.
        ingredients (list): List of ingredient objects required.
        steps (list): Ordered list of cooking instructions.
        tips (list): Helpful cooking tips or variations.
    """
    try:
        if not isinstance(people_count, int):
            raise ValueError("People count must be an integer")
        if people_count < 1 or people_count > 10:
            raise ValueError("People count must be between 1 and 10")
        return api.get_random_dish_recommendation(people_count)
    except Exception as e:
        raise e

# Section 4: Entry Point
if __name__ == "__main__":
    mcp.run()
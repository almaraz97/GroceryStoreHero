from GroceryHero import db
from GroceryHero.Main.utils import convert_frac
from GroceryHero.Recipes.forms import Measurements


def update_pantry(user, recipes):  # From the clear menu using recipes
    pantry = user.pantry
    if pantry:
        recipe_ingredients = []
        for recipe in recipes:
            for ing, M in recipe.quantity.items():
                quantity = convert_frac(M[0])  # Returns a float of some kind
                unit = M[1]
                recipe_ingredients.append([ing, quantity, unit])

        for ing in recipe_ingredients:  # See what's being used
            item = ing[0]
            for shelf in pantry:  # Look for it in each shelf
                if item in pantry[shelf] and Measurements.str_compatibility(ing[2], pantry[shelf][item][1]):  # Make sure measurements agree
                    recipe_ing = Measurements(value=ing[1], unit=ing[2])  # Get recipe ing that is being used
                    pantry_ing = Measurements(value=pantry[shelf][item][0], unit=pantry[shelf][item][1])  # Get pantry item
                    remaining = pantry_ing - recipe_ing  # Subtract the two (creates new object)
                    if remaining.value > 0:  # If there is anything remaining
                        pantry[shelf][item] = [remaining.value, remaining.unit]  # Make whats left the new value
                    else:
                        del pantry[shelf][item]  # Ingredient is gone
                    break
        user.pantry = {}
        db.session.commit()  # todo why does it need 2 commits to update value?
        user.pantry = pantry
        db.session.commit()


def add_pantry(user, ingredients, shelf, add):
    pantry = user.pantry
    for ing in ingredients:
        if ing in pantry[shelf]:
            item_a = Measurements(value=pantry[shelf][ing][0], unit=pantry[shelf][ing][1])
            item_b = Measurements(value=ingredients[ing][0], unit=ingredients[ing][1])
            total = item_a + item_b if add else item_a - item_b
            if total.value <= 0:
                del pantry[shelf][ing]
            else:
                pantry[shelf][ing] = [total.value, total.unit]
        else:  # Ingredient does not exist
            if not add:  # is being removed
                pass
            else:
                pantry[shelf][ing] = ingredients[ing]
    user.pantry = {}
    db.session.commit()  # todo why does it need 2 commits to update value?
    user.pantry = pantry
    db.session.commit()

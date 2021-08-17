from GroceryHero import db
from GroceryHero.Main.utils import convert_frac
from GroceryHero.Recipes.utils import Measurements


# Todo need to add Other (unsorted) shelf. When adding recipes, have button on page to add their ingredients to pantry
#  after shopping for them. Make it easy to add/modify what you bought
# todo store ingredients to a shelf so user doesnt have to keep specifying their shelf. Don't allow double shelfing?
# todo on menu clear add questions about what was consumed or remaining in pantry. Use this to recommend next recipes

def update_pantry(user, recipes):  # From the clear menu using recipes
    pantry = user.pantry  # {"Grains": {"Rice": [2, "Pound"], "Bread Crumbs": [1.0, "US Cup"]}}
    if not pantry:  # User's pantry is empty
        return None

    quantities = [recipe.quantity for recipe in recipes]
    ing_measures = []  # Turn recipe ingredients into measurement objects
    for recipe in quantities:  # dictionary = {str(ingredient): [float(value), str(unit)]}
        for ing_name, measure in recipe.items():
            value = convert_frac(measure[0])
            unit = measure[1]
            ing_measures.append(Measurements(name=ing_name, value=value, unit=unit))

    for recipe_ing in ing_measures:  # Subtract ingredient from pantry
        for shelf in pantry:
            shelf_ingredients = pantry[shelf]
            if recipe_ing.name in shelf_ingredients:
                ing = recipe_ing.name
                value = float(shelf_ingredients[ing][0])
                unit = shelf_ingredients[ing][1]
                shelf_ing = Measurements(name=ing, value=value, unit=unit)
                if shelf_ing.compatible(recipe_ing):
                    remaining = shelf_ing - recipe_ing
                    remaining.value = int(remaining.value) if remaining.value.is_integer() else remaining.value
                    if remaining.value:  # Not 0
                        pantry[shelf][ing] = [remaining.value, remaining.unit]
                    else:
                        del pantry[shelf][ing]  # Remove empty ingredient from shelf
                    break  # Ingredient was subtracted, don't remove it from another shelf

    user.pantry = {}
    db.session.commit()  # todo why does it need 2 commits to update value?
    user.pantry = pantry
    db.session.commit()


def add_pantry(user, ingredients, shelf, add):  # Manually adding or removing ingredients from pantry
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
            if add:  # Add it to pantry
                pantry[shelf][ing] = ingredients[ing]
    user.pantry = {}
    db.session.commit()  # todo why does it need 2 commits to update value?
    user.pantry = pantry
    db.session.commit()


import json

from GroceryHero import db
from GroceryHero.Recipes.forms import Measurements
from GroceryHero.models import Recipes, Aisles


def aisle_grocery_sort(menu_list, aisles):
    # print(extras)
    ingredients = [recipe.quantity for recipe in menu_list]
    ingredients = sorted([item for sublist in ingredients for item in sublist])  # Flattens
    overlap = len(ingredients)
    # todo extras might not need aisle information in the first place
    quantities = [menu_item.quantity for menu_item in menu_list]
    # quantities.append({x[0]: x[1:-1] for x in [aisle_obj[1] for aisle_obj in extras]})
    merged = {}  # Merges quantities dictionaries. Ingredient as Key, Measurement Object list as Value
    for dictionary in quantities:
        for key in dictionary:
            try:
                merged[key].append(Measurements(value=dictionary[key][0], unit=dictionary[key][1]))
            except KeyError:
                merged[key] = [Measurements(value=dictionary[key][0], unit=dictionary[key][1])]
    # print(merged)
    sorted_ingredients = {}  # AisleName as Key, list of ingredients as Value
    for aisle in aisles:
        if aisles[aisle] is None:  # If aisle doesn't have ingredients, make empty list
            aisles[aisle] = []
        if aisle not in sorted_ingredients:  # If aisle isn't in sorted_ingredients dictionary yet, add it
            sorted_ingredients[aisle] = []
        for ingredient in ingredients:
            if ingredient in aisles[aisle]:
                sorted_ingredients[aisle] = sorted_ingredients[aisle] + [ingredient]
    missing = [ingredient for ingredient in ingredients if ingredient not in
               [item for sublist in sorted_ingredients.values() for item in sublist]]
    sorted_ingredients['Other (unsorted)'] = missing
    # print(merged)
    for entry in list(merged.keys()):  # Combines merged dictionary Measurement Objects if they are same type
        if len(merged[entry]) > 1:
            temp, index, first = [], 0, True
            while len(merged[entry]) > 0:
                removals, i = [], 0
                while i < len(merged[entry]):  # ###Might be easier to test by object type and append each to a list
                    if first:
                        temp.append(merged[entry][i])  # Append first pair to compare with
                        removals.append(i)  # Remove that one later
                        i += 1  # Move to next one
                        first = False
                        if i == len(merged[entry]):  # Break if final list item is appended to temp
                            break
                    if temp[index].type == merged[entry][i].type:  # If both same measurement type (Gen,Mass,Vol)
                        if temp[index].unit in Measurements.Generic:  # If they're in generic, both must match
                            if temp[index].unit == merged[entry][i].unit:
                                temp[index] = temp[index] + merged[entry][i]  # Add it to last temp element
                                removals.append(i)  # Remove it later
                                i += 1  # Move on to next one
                            else:  # Append to temp list
                                first = True
                        else:  # Measurement Objects are both Weight or Volume
                            temp[index] = temp[index] + merged[entry][i]  # Add it to last temp element
                            removals.append(i)  # Remove it later
                            i += 1  # Move on to next one
                    else:  # Append to temp list
                        first = True
                for remove in sorted(removals, reverse=True):  # Remove list items from dictionary entry
                    del merged[entry][remove]
                first = True
                index += 1
            merged[entry] = temp
    # print(merged)
    for key in sorted_ingredients:  # Combines ingredient key and its measurement object into a list
        aisle_items = sorted(set(sorted_ingredients[key]))
        temp = []
        for index in range(len(aisle_items)):
            unit_objs = merged[aisle_items[index]]
            if len(unit_objs) > 1:  # If its a list of objects
                for unit_obj in unit_objs:  # For Measurement Object in list
                    unit_obj.value = int(unit_obj.value) if float(unit_obj.value).is_integer() else unit_obj.value
                    temp.append([str(aisle_items[index]), unit_obj])
            else:
                unit_obj = unit_objs[0]
                unit_obj.value = int(unit_obj.value) if float(unit_obj.value).is_integer() else unit_obj.value
                temp.append([str(aisle_items[index]), unit_obj])
            del merged[aisle_items[index]][0]
        sorted_ingredients[key] = temp
    # print(merged)
    for aisle in sorted_ingredients:  # Remove measurement unit, not JSON serializable
        sorted_ingredients[aisle] = [[item[0], item[1].value, item[1].unit, 0] for item in sorted_ingredients[aisle]]
    return sorted_ingredients, (overlap - len([item for sublist in sorted_ingredients.values() for item in sublist]))


def update_grocery_list(user):
    menu_list = [recipe for recipe in Recipes.query.filter_by(author=user).order_by(Recipes.title).all()
                 if recipe.in_menu]
    all_aisles = Aisles.query.filter_by(author=user)
    aisles = {aisle.title: aisle.content.split(', ') for aisle in all_aisles}
    entries = user.extras

    grocery_list, overlap = aisle_grocery_sort(menu_list, aisles)
    g_copy = grocery_list.copy()  # Grocery_List copy
    for aisle_obj in entries:
        item_name = aisle_obj[1][0]  # should be list, take off second index
        old_aisle_ingredients = [ingredient_obj[0] for ingredient_obj in g_copy[aisle_obj[0]]]
        if item_name in old_aisle_ingredients:  # If the item is already in the grocery list
            index = old_aisle_ingredients.index(item_name)  # Get the old item object index
            old_item_obj = g_copy[aisle_obj[0]][index]
            old_item_obj = Measurements(value=old_item_obj[1], unit=old_item_obj[2])
            new_item_obj = aisle_obj[1]
            new_item_obj = Measurements(value=new_item_obj[1], unit=new_item_obj[2])
            if new_item_obj.type == old_item_obj.type and new_item_obj.metric == old_item_obj.metric:
                if new_item_obj.type == 'Generic':  # If they're both Generic
                    if new_item_obj.unit == old_item_obj.unit:
                        combined = old_item_obj + new_item_obj
                        g_copy[aisle_obj[0]][index] = [g_copy[aisle_obj[0]][index][0], combined.value, combined.unit, 0]
                    else:
                        g_copy[aisle_obj[0]].append(aisle_obj[1])
                else:
                    combined = old_item_obj + new_item_obj
                    g_copy[aisle_obj[0]][index] = [g_copy[aisle_obj[0]][index][0], combined.value, combined.unit, 0]
            else:  # Else just append
                g_copy[aisle_obj[0]].append(aisle_obj[1])
        else:  # Not in the grocery_list yet
            g_copy[aisle_obj[0]].append(aisle_obj[1])
    # print(temp)
    for aisle in g_copy:
        g_copy[aisle] = sorted(g_copy[aisle], key=lambda x: x[0])
    sorted_aisles = sorted(all_aisles, key=lambda x: x.order)
    sorted_aisles = [x.title for x in sorted_aisles if x.order != 0] + \
                    [x.title for x in sorted(sorted_aisles, key=lambda x: x.title) if x.order == 0] + \
                    ['Other (unsorted)']
    for aisle in sorted_aisles:
        try:
            g_copy[aisle] = g_copy.pop(aisle)
        except ValueError:
            pass
    user.grocery_list = []
    db.session.commit()
    user.grocery_list = [g_copy, overlap]


def ensure_harmony_keys(user):
    if user.grocery_list is None:
        user.grocery_list = [{}, 0]
        db.session.commit()
    if user.extras is None:
        user.extras = []
        db.session.commit()
    if user.harmony_preferences is None:
        user.harmony_preferences = {'excludes': [], 'similarity': 45, 'groups': 3, 'possible': 0, 'recommended': {},
                                    'rec_limit': 3, 'tastes': {}, 'ingredient_weights': {}, 'sticky_weights': {},
                                    'recipe_ids': {}, 'history': 0, 'ingredient_excludes': [],
                                    'algorithm': 'Balanced', 'modifier': 'Graded'}
        db.session.commit()
    if len(user.harmony_preferences.keys()) < 14:
        user.harmony_preferences = {'excludes': [], 'similarity': 45, 'groups': 3, 'possible': 0, 'recommended': {},
                                    'rec_limit': 3, 'tastes': {}, 'ingredient_weights': {}, 'sticky_weights': {},
                                    'recipe_ids': {}, 'history': 0, 'ingredient_excludes': [],
                                    'algorithm': 'Balanced', 'modifier': 'Graded'}
        db.session.commit()


def get_harmony_settings(user_preferences, holds=None):
    settings = ['rec_limit', 'tastes', 'ingredient_weights', 'sticky_weights', 'ingredient_excludes', 'algorithm',
                'modifier']
    holds = [] if holds is None else holds
    settings = [item for item in settings if item not in holds]

    preferences = {k: v for k, v in user_preferences.items() if k in settings}

    preferences['rec_limit'] = int(preferences['rec_limit'])  # Convert to integer

    weights = preferences['ingredient_weights']
    weights = json.loads(weights) if isinstance(weights, str) else weights
    weights = {key: float(value) for key, value in
               weights.items()}
    preferences['ingredient_weights'] = weights

    tastes = preferences['tastes']
    tastes = json.loads(tastes) if isinstance(tastes, str) else tastes
    tastes = {tuple(item.split(', ')): float(value) for item, value
              in tastes.items()}
    preferences['tastes'] = tastes

    ing_ex = preferences['ingredient_excludes']
    preferences['ingredient_excludes'] = ing_ex

    sticky = preferences['sticky_weights']
    sticky = json.loads(sticky) if isinstance(sticky, str) else sticky
    sticky = {key: float(value) for key, value in
              sticky.items()}
    preferences['sticky_weights'] = sticky

    return preferences


def get_history_stats(user):
    history = user.history  # Change user history
    print(history)
    if len(history) > 0:
        # Make sure deleted recipes are not included in history  # todo remove deleted ids from history?
        all_recipes_ids = [r.id for r in Recipes.query.filter_by(author=user).all()]
        history = [item for sublist in history for item in sublist if item in all_recipes_ids]  # Flatten history
        history_set = set(history)
        history_count = {recipe: history.count(recipe) for recipe in history_set}
        sorted_history_count = sorted(history_count, key=lambda x: history_count[x], reverse=True)  # By frequency
        keys = list(sorted_history_count)

        recipes = Recipes.query.filter(Recipes.id.in_(history)).all()
        most_eaten = [[recipe.title for recipe in recipes if recipe.id == keys[0]][0], history_count[keys[0]]]
        least_eaten = [[recipe.title for recipe in recipes if recipe.id == keys[-1]][0], history_count[keys[-1]]]

        eaten_ingredients = [i * list([recipe for recipe in recipes if recipe.id == id][0].quantity.keys())
                             for id, i in history_count.items()]
        eaten_ingredients = [item for sublist in eaten_ingredients for item in sublist]
        eaten_ingredients_set = set(eaten_ingredients)
        eaten_ingredients_count = {item: eaten_ingredients.count(item) for item in eaten_ingredients_set}
        sorted_eaten_ingredients_count = sorted(eaten_ingredients_count, key=lambda x: eaten_ingredients_count[x],
                                                reverse=True)
        keys_ingredients = list(sorted_eaten_ingredients_count)
        most_ing = [keys_ingredients[0], eaten_ingredients_count[keys_ingredients[0]]]
        least_ing = [keys_ingredients[-1], eaten_ingredients_count[keys_ingredients[-1]]]
    else:
        return ['N/A', 'N/A'], ['N/A', 'N/A'], ['N/A', 'N/A'], ['N/A', 'N/A']
    return most_eaten, least_eaten, most_ing, least_ing


def update_pantry(user, recipes):  # From the clear menu using recipes
    pantry = user.pantry
    print(pantry)
    recipe_ingredients = []
    for recipe in recipes:
        for ing, M in recipe.quantity.items():
            recipe_ingredients.append([ing, M[0], M[1]])

    for ing in recipe_ingredients:  # See what's being used
        item = ing[0]
        for shelf in pantry:  # Look for it in each shelf
            if item in pantry[shelf] and ing[2] == pantry[shelf][item][1]:  # Make sure measurements agree
                recipe_ing = Measurements(value=ing[1], unit=ing[2])  # Get recipe ing that is being used
                pantry_ing = Measurements(value=pantry[shelf][item][0], unit=pantry[shelf][item][1])  # Get pantry item
                remaining = pantry_ing - recipe_ing  # Subtract the two
                if remaining.value > 0:  # If there is anything remaining
                    pantry[shelf][item] = [remaining.value, remaining.unit]  # Make whats left the new value
                else:
                    del pantry[shelf][item]  # Ingredient is gone
                break
    print(pantry)
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


def show_harmony_weights(user, preferences):
    ing_weights = preferences['ingredient_weights']
    ing_weights = json.loads(ing_weights) if isinstance(ing_weights, str) else ing_weights
    ing_weights = ', '.join([str(key) + ': ' + str(value) for key, value in ing_weights.items()])
    tastes = preferences['tastes']
    tastes = json.loads(tastes) if isinstance(tastes, str) else tastes  # Formatting for showing pairs to user
    tastes = '\n'.join([str(key[0]) + ', ' + str(key[1]) + ': ' + str(value) for key, value in tastes.items()])
    sticky = preferences['sticky_weights']
    sticky = json.loads(sticky) if isinstance(sticky, str) else sticky
    sticky = ', '.join([str(key) + ': ' + str(value) for key, value in sticky.items()])
    return ing_weights, tastes, sticky

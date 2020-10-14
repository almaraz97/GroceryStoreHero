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


def get_harmony_settings(user_preferences):
    settings = ['rec_limit', 'tastes', 'ingredient_weights', 'sticky_weights', 'ingredient_excludes', 'algorithm',
                'modifier']
    preferences = {k: v for k, v in user_preferences.items() if k in settings}
    rec_limit = int(preferences['rec_limit'])
    preferences['rec_limit'] = rec_limit

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
    history = user.history
    if len(history) > 0:
        history = [item for sublist in history for item in sublist]
        # print(history)
        history_set = set(history)
        history_count = {}
        for item in history_set:
            history_count[item] = history.count(item)
        sorted_history_count = sorted(history_count, key=lambda x: history_count[x])
        recipes = Recipes.query.filter(Recipes.id.in_(history)).all()
        keys = list(sorted_history_count)
        # most_eaten = [Recipes.query.filter_by(id=keys[0]).first().title, history_count[keys[0]]]
        most_eaten = [[recipe.title for recipe in recipes if recipe.id == keys[0]][0], history_count[keys[0]]]
        least_eaten = [[recipe.title for recipe in recipes if recipe.id == keys[-1]][0], history_count[keys[-1]]]
        # least_eaten = [Recipes.query.filter_by(id=keys[-1]).first().title, history_count[keys[-1]]]
        eaten_ingredients = [recipe.quantity.keys() for recipe in recipes]
        # print(eaten_ingredients)
        most_ing = [[recipe.title for recipe in recipes if recipe.id == keys[0]][0], history_count[keys[0]]]
        least_ing = []
    else:
        return None, None
    return most_eaten, least_eaten


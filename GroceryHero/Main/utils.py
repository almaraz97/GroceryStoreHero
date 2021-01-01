import json
import os

import numpy as np
from apyori import apriori
from flask import current_app
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
from GroceryHero import db
from GroceryHero.Recipes.forms import Measurements
from GroceryHero.models import Recipes, Aisles, User_Rec


def aisle_grocery_sort(menu_list, aisles):
    ingredients = [recipe.quantity for recipe in menu_list]
    ingredients = sorted([item for sublist in ingredients for item in sublist])  # Flattens
    overlap = len(ingredients)
    # todo extras might not need aisle information in the first place
    quantities = [menu_item.quantity for menu_item in menu_list]
    # quantities.append({x[0]: x[1:-1] for x in [aisle_obj[1] for aisle_obj in extras]})
    merged = {}  # Merged quantities dictionaries. Ingredient[str] as Key, list of Measurement Objects as Value
    for dictionary in quantities:
        for key in dictionary:
            try:  # Add ingredient to existing to merge quantity later
                merged[key].append(Measurements(value=convert_frac(dictionary[key][0]), unit=dictionary[key][1]))
            except KeyError:  # Ingredient doesnt have a entry yet
                merged[key] = [Measurements(value=convert_frac(dictionary[key][0]), unit=dictionary[key][1])]
            # except ValueError:  # Ingredient quantity is a fraction
            #     quantity = dictionary[key][0][0]/dictionary[key][0][2]
            #     merged[key] = [Measurements(value=quantity, unit=dictionary[key][1])]
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
                    # if temp[index].type == merged[entry][i].type:  # If both same measurement type (Gen,Mass,Vol)
                    #     if temp[index].unit in Measurements.Generic:  # If they're in generic, both must match
                    #         if temp[index].unit == merged[entry][i].unit:
                    #             temp[index] = temp[index] + merged[entry][i]  # Add it to last temp element
                    #             removals.append(i)  # Remove it later
                    #             i += 1  # Move on to next one
                    #         else:  # Append to temp list
                    #             first = True
                    #     else:  # Measurement Objects are both Weight or Volume
                    #         temp[index] = temp[index] + merged[entry][i]  # Add it to last temp element
                    #         removals.append(i)  # Remove it later
                    #         i += 1  # Move on to next one
                    # else:  # Append to temp list
                    #     first = True
                    if temp[index].compatibility(merged[entry][i]):  # Are type/unit compatible
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
    for aisle in sorted_ingredients:  # Remove measurement unit, not JSON serializable
        sorted_ingredients[aisle] = [[item[0], item[1].value, item[1].unit, 0] for item in sorted_ingredients[aisle]]
    return sorted_ingredients, (overlap - len([item for sublist in sorted_ingredients.values() for item in sublist]))


def update_grocery_list(user):
    menu_list = [recipe for recipe in Recipes.query.filter_by(author=user).order_by(Recipes.title).all()
                 if recipe.in_menu]
    borrowed = [x.recipe_id for x in User_Rec.query.filter_by(user_id=user.id, in_menu=True).all()]
    menu_list = menu_list + Recipes.query.filter(Recipes.id.in_(borrowed)).all()
    all_aisles = Aisles.query.filter_by(author=user)
    aisles = {aisle.title: aisle.content.split(', ') for aisle in all_aisles}
    entries = user.extras if user.extras is not None else []

    grocery_list, overlap = aisle_grocery_sort(menu_list, aisles)
    # print('post grocerylist', grocery_list, overlap)
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
    db.session.commit()


def ensure_harmony_keys(user):
    if user.grocery_list is None or len(user.grocery_list) < 2:
        user.grocery_list = [{}, 0]  # Groceries and (number of items?)
        db.session.commit()
    if user.extras is None or user.extras == '':
        user.extras = []
        db.session.commit()
    if user.harmony_preferences is None or len(user.harmony_preferences.keys()) < 14:
        user.harmony_preferences \
            = {'excludes': [], 'similarity': 45, 'groups': 3, 'possible': 0, 'recommended': {}, 'rec_limit': 3,
               'tastes': {}, 'ingredient_weights': {}, 'sticky_weights': {}, 'recipe_ids': {}, 'history': 0,
               'ingredient_excludes': [], 'algorithm': 'Balanced', 'modifier': 'Graded'}
        db.session.commit()


def get_harmony_settings(user_preferences, holds=None):
    settings = ['rec_limit', 'tastes', 'ingredient_weights', 'sticky_weights', 'ingredient_excludes', 'algorithm',
                'modifier']
    holds = [] if holds is None else holds
    settings = [item for item in settings if item not in holds]
    preferences = {k: v for k, v in user_preferences.items() if k in settings}
    if 'rec_limit' not in holds:
        preferences['rec_limit'] = int(preferences['rec_limit'])  # Convert to integer
    if 'ingredient_weights' not in holds:
        weights = preferences['ingredient_weights']
        weights = json.loads(weights) if isinstance(weights, str) else weights
        weights = {key: float(value) for key, value in
                   weights.items()}
        preferences['ingredient_weights'] = weights
    if 'tastes' not in holds:
        tastes = preferences['tastes']
        tastes = json.loads(tastes) if isinstance(tastes, str) else tastes
        tastes = {tuple(item.split(', ')): float(value) for item, value
                  in tastes.items()}
        preferences['tastes'] = tastes
    if 'ingredient_excludes' not in holds:
        ing_ex = preferences['ingredient_excludes']
        preferences['ingredient_excludes'] = ing_ex
    if 'sticky_weights' not in holds:
        sticky = preferences['sticky_weights']
        sticky = json.loads(sticky) if isinstance(sticky, str) else sticky
        sticky = {key: float(value) for key, value in
                  sticky.items()}
        preferences['sticky_weights'] = sticky
    if 'modifier' not in holds:
        preferences['modifier'] = user_preferences['modifier']

    return preferences


def get_history_stats(user):  # For dashboard basic stats
    history = user.history  # Change user history
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
        return ['N/A', None], ['N/A', None], ['N/A', None], ['N/A', None], None
    return most_eaten, least_eaten, most_ing, least_ing


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


def apriori_test(user, min_support=None):
    recipes = []
    for week in user.history:
        # temp = [recipe.title for recipe in
        # [Recipes.query.filter_by(id=item).first() for item in week for week in user.history]]
        temp = []
        for item in week:
            recipe = Recipes.query.filter_by(id=item).first()
            if recipe is not None:
                temp.append(recipe.title)
        if len(temp) > 0:
            recipes.append(temp)
    # recipes = [temp for temp in []]
    min_support = 2/len(recipes) if min_support is None else min_support
    return list(apriori(recipes, min_support=min_support, min_lift=1.1))


def convert_frac(num):  # form validator already checked for float or fraction
    try:
        return float(num)
    except ValueError:
        try:
            num = num.split('/')
            return float(num[0]) / float(num[1])
        except ValueError:  # Fraction is mixed
            num = (int(num[0])*int(num[4]) + int(num[2]))/ int(num[4])
            return num


def rem_trail_zero(num):
    try:
        num = str(int(float(num))) if float(num).is_integer() else str(num)
        return num
    except ValueError:
        return num


def stats_graph(user, all_recipes):
    # def almaraz_algorithm(dictionary, n, norm=1):
    #     recipes = one_hot_recipes(dictionary)
    #     # Split recipes into n groups
    #     splits = len(recipes) // n
    #     temp, groups = 0, []
    #     for _ in range(n):
    #         groups.append(list(recipes.values())[temp:temp + splits])
    #         temp += splits
    #     # Find the 'average' recipe for each group
    #     average_recipes = [[sum(values) / len(recipes) for values in zip(*group)] for group in groups]
    #     # Find the cosine distance between each recipe and each 'average' recipe (dot product and norm)
    #     distances = [tuple(sum([x * y for x, y in zip(recipe, average_recipe)]) ** (1 / norm)
    #                        for average_recipe in average_recipes) for recipe in recipes.values()]
    #     return distances

    # coordinates = almaraz_algorithm(all_recipes, 25)
    # coordinates = values
    # labels = [x for x in all_recipes.keys()]
    # dim = 2
    # reducer = umap.UMAP(n_components=dim, metric='manhattan')
    # embedding = reducer.fit_transform(coordinates)
    # if dim == 3:
    #     ax = plt.axes(projection='3d')
    #     x, y, z = [x[0] for x in embedding], [x[1] for x in embedding], [x[2] for x in embedding]
    #     ax.scatter3D(x, y, z, 'blue')
    #     for xi, yi, zi, label in zip(x, y, z, labels):
    #         ax.text(xi, yi, zi, label, None)
    #     # mplcursors.cursor(hover=True)
    # if dim == 2:
    #     fig, ax = plt.subplots()
    #     x, y = [x[0] for x in embedding], [x[1] for x in embedding]
    #     ax.scatter(x, y)
    #     for i, txt in enumerate(labels):
    #         ax.annotate(txt, (x[i], y[i]))
    # else:
    #     pass
    # plt.show()
    # history = User.query.filter_by(id=1).first().history
    # if len(history) > 0:
    #     # Recipe History/Frequency
    #     history = [item for sublist in history for item in sublist]
    #     history_set = set(history)
    #     history_count = {}
    #     for item in history_set:
    #         history_count[item] = history.count(item)
    #     history_count = sorted(history_count.items(), key=lambda x: x[1], reverse=True)
    #     history_count_names = {Recipes.query.filter_by(id=k).first().title: v for k, v in history_count}
    #     plt.bar(history_count_names.keys(), history_count_names.values())
    #     plt.show()
    #     # Ingredient History/Frequency
    #     ingredient_history = [[x for x in Recipes.query.filter_by(id=k).first().quantity.keys()] * v for
    #                           k, v in history_count]
    #     ingredient_history = [item for sublist in ingredient_history for item in sublist]
    #     ingredient_set = set(ingredient_history)
    #     ingredient_count = {}
    #     for item in ingredient_set:
    #         ingredient_count[item] = ingredient_history.count(item)
    #     ingredient_count = sorted(ingredient_count.items(), key=lambda x: x[1], reverse=True)
    #     plt.bar([x[0] for x in ingredient_count], [x[1] for x in ingredient_count])
    #     plt.show()

    # pca = PCA(n_components=2)
    # pca = pca.fit_transform(values)
    # pca_plot = plt.scatter(pca.T[0], pca.T[1])
    # plt.show()
    all_recipes = all_recipes if all_recipes is not None else Recipes.query.filter_by(author=user).all()
    all_recipes = {k.title: k.quantity for k in all_recipes}
    # List of unique ingredients from recipe dict (alphabetical) (Ingredient Set)
    recipe_ingredients = {item for sublist in all_recipes.values() for item in sublist}
    # Dictionary of One-hot vector of ingredients (recipe name as Key, one-hot vec as Value) (Recipe Matrix)
    recipe_vec = {recipe: [1 if ingredient in all_recipes[recipe] else 0 for ingredient in recipe_ingredients]
                  for recipe in all_recipes}

    values = np.array(list(recipe_vec.values()))
    perp = .5
    met = 'l2'
    tsne = TSNE(n_components=2, perplexity=perp, metric=met)
    tsne = tsne.fit_transform(values)
    x, y = [x[0] for x in tsne], [x[1] for x in tsne]
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(x, y)
    for i, txt in enumerate(all_recipes.keys()):
        ax.annotate(txt, (x[i], y[i]), fontsize=8)
    # plt.title(f'TSNE w/ perplexity: {perp}, metric: {met}')
    # plt.show()
    filepath = str(user.id) + '.jpg'
    picture_path = os.path.join(current_app.root_path, 'static/visualizations', filepath)
    plt.savefig(picture_path)

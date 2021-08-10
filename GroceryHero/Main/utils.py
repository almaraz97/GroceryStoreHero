import json
import os
import numpy as np
import sklearn
from apyori import apriori
import matplotlib.pyplot as plt
from flask import current_app
from sklearn.manifold import TSNE
import umap
from GroceryHero import db
from GroceryHero.Recipes.utils import Measurements
from GroceryHero.models import Recipes, Aisles, User_Rec


def aisle_grocery_sort(recipe_menu_list: list, aisles: dict):
    # Recipe_menu_list = [Model.Recipe,...], aisles = [{aisle_name: [ingredient_name,...]},...]
    all_ing_names = [recipe.quantity for recipe in recipe_menu_list]  # Format: [{ingredient: [value, unit]},...]
    all_ing_names = sorted([item for sublist in all_ing_names for item in sublist])
    # todo extras might not need aisle information in the first place
    quantities = [recipe.quantity for recipe in recipe_menu_list]  # Format: [{ingredient: [value, unit]},...]
    # quantities.append({x[0]: x[1:-1] for x in [aisle_obj[1] for aisle_obj in extras]})  # Add extras?

    # 1. Set up ingredients for summing ie: rice 1 cup + rice 2 cups = rice 3 cups
    ing_merger = {}  # {ing_name: [Measurements(v=1, u=cup), ...], ...}
    for dictionary in quantities:  # dictionary = {str(ingredient): [float(value), str(unit)]}
        for ing in dictionary:
            value = convert_frac(dictionary[ing][0])
            unit = dictionary[ing][1]
            if ing in ing_merger:
                ing_merger[ing].append(Measurements(value=value, unit=unit))
            else:
                ing_merger[ing] = [Measurements(value=value, unit=unit)]

    # 2. Put recipe ingredients into their respective aisles
    sorted_ingredients = {}  # {aisle_name: [ingredient_name,...]}
    for aisle in aisles:
        if aisles[aisle] is None:  # If aisle doesn't have ingredients, make empty list
            aisles[aisle] = []
        if aisle not in sorted_ingredients:  # If aisle isn't in sorted_ingredients dictionary yet, add it
            sorted_ingredients[aisle] = []
        for ingredient in all_ing_names:
            if ingredient in aisles[aisle]:
                sorted_ingredients[aisle] = sorted_ingredients[aisle] + [ingredient]
    missing = [ingredient for ingredient in all_ing_names if ingredient not in
               [item for sublist in sorted_ingredients.values() for item in sublist]]  # todo do this in aisle sort loop
    sorted_ingredients['Other (unsorted)'] = missing  # Add ingredients to unsorted aisle

    # 3. Combine ingredients if they are same ingredient and measurement type
    ing_merged = {}
    for ing, overlaps in list(ing_merger.items()):  # {rice: [1 cup, 3 ounces, 2 cups, 1 ounce, 2 grams, 5 grams]}
        unit_merged = []  # Units that have been merged together
        compared = []  # Items that have already been added from same unit
        for i, item1 in enumerate(overlaps):
            for j, item2 in enumerate(overlaps):
                if not any([i == j, i >= j, i in compared, j in compared]):  # Not self-comp and not reversed comp
                    if item1.compatible(item2):
                        item1 += item2
                        compared.append(j)
            if i not in compared:
                unit_merged.append(item1)  # 3 cup
        ing_merged[ing] = unit_merged  # [3 cup, 4 ounces, 7 grams]

    for key in sorted_ingredients:  # Combines ingredient key and its measurement object into a list
        aisle_items = sorted(set(sorted_ingredients[key]))
        temp = []
        for ing_i in range(len(aisle_items)):
            unit_objs = ing_merged[aisle_items[ing_i]]
            if len(unit_objs) > 1:  # If its a list of objects
                for unit_obj in unit_objs:  # For Measurement Object in list
                    unit_obj.value = int(unit_obj.value) if float(unit_obj.value).is_integer() else unit_obj.value
                    temp.append([str(aisle_items[ing_i]), unit_obj])
            else:
                unit_obj = unit_objs[0]
                unit_obj.value = int(unit_obj.value) if float(unit_obj.value).is_integer() else unit_obj.value
                temp.append([str(aisle_items[ing_i]), unit_obj])
            del ing_merged[aisle_items[ing_i]][0]
        sorted_ingredients[key] = temp

    sorted_ingredients = {aisle: [[M[0], M[1].value, M[1].unit, 0] for M in ing] for
                          aisle, ing in sorted_ingredients.items()}
    return sorted_ingredients, (
                len(all_ing_names) - len([item for sublist in sorted_ingredients.values() for item in sublist]))


def update_grocery_list(user):
    menu_list = [recipe for recipe in Recipes.query.filter_by(author=user).order_by(Recipes.title).all()
                 if recipe.in_menu]  # Recipes in menu
    borrowed = [x.recipe_id for x in User_Rec.query.filter_by(user_id=user.id, in_menu=True).all()]  # Borrowed in menu
    menu_list = menu_list + Recipes.query.filter(Recipes.id.in_(borrowed)).all()  # Combine own and borrowed
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
            if (new_item_obj.type == old_item_obj.type) and (new_item_obj.metric_system == old_item_obj.metric_system):
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


def get_all_menu_recs(user):
    menu_recipes = Recipes.query.filter_by(author=user).filter_by(in_menu=True).all()  # Get all recipes
    borrowed_recipes = [x.recipe_id for x in User_Rec.query.filter_by(user_id=user.id, in_menu=True).all()]
    menu_recipes = menu_recipes + Recipes.query.filter(Recipes.id.in_(borrowed_recipes)).all()
    return menu_recipes


def get_history_stats(user):  # For dashboard stats
    history = user.history  # Change user history
    if len(history) > 0:
        # Make sure deleted recipes are not included in history
        all_recipes_ids = [r.id for r in Recipes.query.filter_by(author=user).all()]
        history = [item for sublist in history.values() for item in sublist if item in all_recipes_ids]
        history_set = set(history)
        history_count = {recipe: history.count(recipe) for recipe in history_set}
        sorted_history_count = sorted(history_count, key=lambda x: history_count[x], reverse=True)  # By frequency
        keys = list(sorted_history_count)

        recipes = Recipes.query.filter(Recipes.id.in_(history)).all()  # todo need to remove deleted ids from history?
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


def getUserRecipeHistory(user):
    recipes = []
    history = user.history.values()
    for week in history:
        temp = []
        for item in week:
            recipe = Recipes.query.filter_by(id=item).first()
            if recipe is not None:
                temp.append(recipe.title)
        if len(temp) > 0:
            recipes.append(temp)
    return recipes


def apriori_test(user, min_support=None, harmony=False, includes=None):
    recipes = getUserRecipeHistory(user)
    min_support = 2 / len(recipes) if min_support is None else min_support
    if harmony:
        aprioris = apriori(recipes, min_support=1e-8, min_lift=1e-8)
        if includes is not None:
            aprioris = [x for x in aprioris if all(y in x.items for y in includes)]
    else:
        aprioris = apriori(recipes, min_support=min_support, min_lift=1.1)
        aprioris = list(aprioris)
    return aprioris


def convert_frac(num):  # form validator already checked for float or fraction
    try:
        return float(num)
    except ValueError:
        try:
            num = num.split('/')
            return float(num[0]) / float(num[1])
        except ValueError:  # Fraction is mixed
            num = (int(num[0]) * int(num[4]) + int(num[2])) / int(num[4])
            return num


def rem_trail_zero(num):
    try:
        num = str(int(float(num))) if float(num).is_integer() else str(num)
        return num
    except ValueError:
        return num


def stats_graph(user, all_recipes):
    all_recipes = all_recipes if all_recipes is not None else Recipes.query.filter_by(author=user).all()
    all_recipes = {k.title: k.quantity for k in all_recipes}
    # List of unique ingredients from recipe dict (alphabetical) (Ingredient Set)
    recipe_vec = {item for sublist in all_recipes.values() for item in sublist}
    # Dictionary of One-hot vector of ingredients (recipe name as Key, one-hot vec as Value) (Recipe Matrix)
    recipe_vec = np.array(
        [np.array([1 if ingredient in all_recipes[recipe] else 0 for ingredient in recipe_vec])
         for recipe in all_recipes])
    algo = 'umap'  # 'tsne'
    dim = 2
    if algo == 'pca':
        pca = sklearn.decomposition.PCA(n_components=2)
        model = pca.fit_transform(recipe_vec)
    elif algo == 'tsne':
        tsne = TSNE(n_components=2, perplexity=.5, metric='l2')
        model = tsne.fit_transform(recipe_vec)
    elif algo == 'svd':
        u, s, v = np.linalg.svd(recipe_vec)
        s = np.concatenate([np.diag(s), np.zeros((162 - 41, 41))], axis=0).T
        u = u[:, :dim]
        s = s[:dim]
        v = v[:, :dim]
        model = u @ s @ v
    else:  # UMAP
        # def almaraz_algorithm(n, recipes, norm=1):
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
        #
        # coordinates = almaraz_algorithm(25, recipe_vec)
        # labels = [x for x in all_recipes.keys()]
        reducer = umap.UMAP(n_components=dim, metric='manhattan')
        model = reducer.fit_transform(recipe_vec)
        # model = []
    x, y = [x[0] for x in model], [x[1] for x in model]
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(x, y)
    for i, txt in enumerate(all_recipes.keys()):
        ax.annotate(txt, (x[i], y[i]), fontsize=8)
    plt.title(f'{algo}')
    # plt.show()
    filepath = str(user.id) + '.jpg'
    picture_path = os.path.join(current_app.root_path, 'static/visualizations', filepath)
    plt.savefig(picture_path)

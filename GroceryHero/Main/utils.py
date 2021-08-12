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


def aisle_grocery_sort(recipe_menu_list: list, aisles: dict, extras: list):
    """
    Recipe_menu_list = [Model.Recipe,...]
    aisles = [{aisle_name: [ingredient_name,...]},...]
    extras=[[aisle,[ings]]
    """
    aisles = {k: v if v is not None else [] for k, v in aisles.items()}  # Ensure aisle list not None (make db default)
    extras = [x[1] for x in extras]
    all_ing_names = [recipe.quantity for recipe in recipe_menu_list]  # Format: [{ingredient: [value, unit]},...]
    all_ing_names = sorted([item for sublist in all_ing_names for item in sublist])  # [ingredient,...]
    missing_ing = [ing for ing in all_ing_names if ing not in [item for sublist in aisles.values() for item in sublist]]
    aisles['Other (unsorted)'] = missing_ing   # Add items that have no assigned aisle
    quantities = [recipe.quantity for recipe in recipe_menu_list]  # Format: [{ingredient: [value, unit],...},...]
    extras_dict = {measure[0]: [measure[1], measure[2]] for measure in extras}
    quantities.append(extras_dict)
    # Convert ingredients to measurement objects
    measures_list = []
    for dictionary in quantities:  # dictionary = {str(ingredient): [float(value), str(unit)]}
        for ing_name, measures in dictionary.items():
            value = convert_frac(dictionary[ing_name][0])
            unit = dictionary[ing_name][1]
            measures_list.append(Measurements(name=ing_name, value=value, unit=unit))
    # Combine like ingredients
    measures_set = []  # [Measurements(),...]
    compared = []  # Items that have already been added from same unit
    for i, M1 in enumerate(measures_list):
        for j, M2 in enumerate(measures_list):
            if not any([i == j, i >= j, i in compared, j in compared,
                        M1.name != M2.name, not M1.compatible(M2)]):  # Not self-comp and not reversed comp
                M1 += M2
                compared.append(j)  # j merged with i, skip it next time
        if i not in compared:
            measures_set.append(M1)  # [3 cup, 4 ounces, 7 grams]
    # Sort ingredients into aisles, convert measurement objects to lists with a strike variable
    aisle_sorted_ings = {aisle: sorted([ingredient.to_str()+[0] for ingredient in measures_set
                                        if ingredient.name in ings], key=lambda x: x[0])
                         for aisle, ings in aisles.items()}  # {aisle_name: [ingredient_name,...]}

    return aisle_sorted_ings, (
                len(all_ing_names) - len([item for sublist in aisle_sorted_ings.values() for item in sublist]))


def update_grocery_list(user):  # Get selected recipes, extra ingredients, and user aisles. Sort and store them
    menu_list = [recipe for recipe in Recipes.query.filter_by(author=user).order_by(Recipes.title).all()
                 if recipe.in_menu]  # Recipes in menu
    borrowed = [x.recipe_id for x in User_Rec.query.filter_by(user_id=user.id, in_menu=True).all()]  # Borrowed in menu
    menu_list = menu_list + Recipes.query.filter(Recipes.id.in_(borrowed)).all()  # Combine own and borrowed
    all_aisles = Aisles.query.filter_by(author=user)
    aisles = {aisle.title: aisle.content.split(', ') for aisle in all_aisles}
    entries = user.extras if user.extras is not None else []  # TODO REFORMAT EXTRAS - [ingredient, value, unit, strike]

    grocery_list, overlap = aisle_grocery_sort(menu_list, aisles, entries)
    user.grocery_list = []
    db.session.commit()
    user.grocery_list = [grocery_list, overlap]
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


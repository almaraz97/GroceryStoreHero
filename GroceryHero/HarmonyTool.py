import itertools
import math
import random
import matplotlib.pyplot as plt


def dot(v1, v2):
    return sum(x * y for x, y in zip(v1, v2))


def norm_stack(input_recipe_dict, algorithm='Balanced', ingredient_weights=None, tastes=None, sticky_weights=None,
               ingredient_excludes=None):
    """
    Input: Recipe dictionary {name:ingredient list}, the desired norm, and optional arguments
    Output: Harmony score
    """
    assert len(input_recipe_dict) > 1  # You need more than one recipe to make comparison
    if ingredient_excludes is None:
        ingredient_excludes = []
    # List of unique ingredients from recipe dict (alphabetical)
    recipe_ingredients = sorted(set([item for sublist in input_recipe_dict.values()
                                     for item in sublist if item not in ingredient_excludes]))
    # Dictionary of One-hot vector of ingredients (recipe name as Key, one-hot vec as Value)
    recipe_vec = {recipe: [1 if ingredient in input_recipe_dict[recipe]
                           else 0
                           for ingredient in recipe_ingredients]
                  for recipe in input_recipe_dict}
    # Similarity matrix (recipe name Key, vector of outgoing graph edges Value) # pd.Series faster? Set 0's by diagonal?
    comp_vec = {recipe: [0 if recipe == list(input_recipe_dict)[i]  # Self commonality = 0
                         else dot(recipe_vec[recipe], recipe_vec[list(input_recipe_dict)[i]])
                         for i in range(len(input_recipe_dict))]
                for recipe in input_recipe_dict}
    # Average outgoing graph edge (Sum of similarity matrix diagonal)
    avg_mag = sum([sum(comp_vec[recipe]) for recipe in comp_vec]) / 2
    # List of Average direction of recipe dict w.r.t. ingredients
    avg_vec = [(x * avg_mag) for x in [(sum(x) / len(comp_vec)) for x in zip(*recipe_vec.values())]]

    # Average taste of recipe dict (int)
    avg_taste = 1
    if tastes is not None:
        taste_comparisons = list(itertools.combinations(input_recipe_dict, 2))  # All taste comparisons for in_rec_dict
        taste_scores = [tastes[comparison] if comparison in tastes else 1 for comparison in taste_comparisons]
        avg_taste = sum(taste_scores) / len(taste_comparisons)
    # List of ingredient weights (ingredient as Index and weight as Value)
    if ingredient_weights is None:
        weight_vec = [1 for _ in recipe_ingredients]  # Weight of each ingredient in order of recipe ingredients
    else:
        weight_vec = [ingredient_weights[ingredient] if ingredient in ingredient_weights else 1 for ingredient in
                      recipe_ingredients]
    if sticky_weights is None:
        sticky_weights = [0 for _ in range(len(recipe_ingredients))]
    else:
        sticky_weights = [int(sticky_weights[ingredient]) if ingredient in sticky_weights else 0 for ingredient in
                          recipe_ingredients]
    avg_sticky = [(sum(vector) / len(recipe_vec) - (1 / len(recipe_vec))) for vector in zip(*recipe_vec.values())]
    sticky_weights = [x * y for x, y in zip(avg_sticky, sticky_weights)]
    # Apply multipliers
    avg_vec = [(x + y) * z for x, y, z in zip(avg_vec, sticky_weights, weight_vec)]
    # Highest possible magnitude & vector (magnitude normalized with number of comparisons)
    perfect_mag = (math.factorial(len(comp_vec)) / (2 * math.factorial(len(comp_vec) - 2))) / 2
    perfect_vec = [perfect_mag * (1.0 * len(avg_vec)) for _ in avg_vec]
    # Norms
    if algorithm == 'Charity':
        score = [1.0 if x > min(avg_vec) else 0.0 for x in avg_vec].count(1.0)
        max_l = perfect_vec[0]
    elif algorithm == 'Fairness':
        score = sum(avg_vec)
        max_l = sum(perfect_vec)
    elif algorithm == 'Balanced':
        score = math.sqrt(sum([x ** 2 for x in avg_vec]))
        max_l = math.sqrt(sum([x ** 2 for x in perfect_vec]))
    elif algorithm == 'Selfish':
        score = sum([x ** 9 for x in avg_vec]) ** (1. / 9)
        max_l = sum([x ** 9 for x in perfect_vec]) ** (1. / 9)
    elif algorithm == 'Greedy':
        score = max(avg_vec)
        max_l = max(perfect_vec)
    else:
        score, max_l = 1, 1
    return (score / max_l) * (1 / avg_taste)


def create_combos(recipes, count, excludes, includes, limit):
    if excludes is not None:
        excludes = [excludes] if isinstance(excludes, str) else excludes
        recipes = [recipe for recipe in recipes if recipe not in excludes]
    recipes = [recipe for recipe in recipes if recipe not in includes]
    combos = list(itertools.combinations(recipes, count))
    if includes:  # If there are menu items add to combinations
        for i, combo in enumerate(combos):
            combos[i] = combo + tuple(includes)
    # Limit combinations
    if len(combos) > limit:
        random.shuffle(combos)
        combos = combos[:limit]
    return combos, len(combos)


def score_combos(recipes, combos, max_sim, algo, weights, taste, ing_ex, sticky, modifier):
    scores = {}
    for group in combos:
        dictionary = {recipe: recipes[recipe] for recipe in group}  # recipe+ingredients of each thing in the group
        harmony_score = norm_stack(dictionary, algorithm=algo, ingredient_weights=weights, tastes=taste,
                                   sticky_weights=sticky,
                                   ingredient_excludes=ing_ex) ** modifier  # (1 / (count * 2 - 3))
        if max_sim is not None:  # If there is a maximum similarity
            if harmony_score < max_sim:  # Only allow groups with less than maximum
                scores[group] = harmony_score
        else:
            scores[group] = harmony_score
    sorted_scored_combos = sorted(scores, key=lambda key: scores[key])
    testing = []
    for i, j in {k: scores[k] for k in sorted_scored_combos}.items():
        testing.append(j)
    print(testing)
    return sorted_scored_combos


def return_unique_combos(combos, rec_limit, includes):
    recommended = []
    while 0 < len(combos) and len(recommended) < rec_limit:
        recommended.append(combos[-1])
        for group in recommended:  # Don't want any recipe in combos that's already in targets except if its in menu
            combos = [combo for combo in combos if
                      not any(y in [recipe for recipe in group if recipe not in includes] for y in combo)]
    return recommended


def return_combo_score(recipes, combos, algo, weights, taste, sticky, ing_ex, modifier):
    recommendations = {combo: round(((norm_stack({key: recipes[key] for key in combo}, algorithm=algo,
                                                 ingredient_weights=weights, tastes=taste, sticky_weights=sticky,
                                                 ingredient_excludes=ing_ex) ** modifier) * 100), 1)
                       for combo in combos}
    return recommendations


def millify(n):
    n = float(n)
    millnames = ['', ' thousand', ' million', ' billion', ' trillion']
    millidx = max(0, min(len(millnames) - 1, int(math.floor(0 if n == 0 else math.log10(abs(n)) / 3))))
    return '{:.0f}{}'.format(n / 10 ** (3 * millidx), millnames[millidx])


def recipe_stack(recipes, count, max_sim=1.0, excludes=None, includes=None, tastes=None, modifier='Graded', rec_limit=5,
                 limit=500_000, ingredient_weights=None, algorithm='Balanced', ingredient_excludes=None, sticky_weights=None):
    # Ensure preferences come through properly if not specified
    print(count)
    rec_limit = len(recipes) if count == 1 else rec_limit
    max_sim = None if max_sim == 'No limit' else int(max_sim) / 100
    excludes = None if not excludes else excludes  # Comes in as 0 or not
    includes = [] if not includes else includes
    modifier = 1 / (5 * (count + len(includes)) + 1) if modifier == 'Graded' else 1.0
    ingredient_weights = None if not ingredient_weights else ingredient_weights
    tastes = None if not tastes else tastes
    # Recipes in, unique scored combos out
    combos, possible = create_combos(recipes, count, excludes, includes, limit)
    scored_combos = score_combos(recipes, combos, max_sim, algorithm, ingredient_weights, tastes, ingredient_excludes,
                                 sticky_weights, modifier)
    combos = return_unique_combos(scored_combos, rec_limit, includes)
    combos = return_combo_score(recipes, combos, algorithm, ingredient_weights, tastes, sticky_weights,
                                ingredient_excludes, modifier)
    return combos, millify(possible)


# Perhaps vectorize the entire recipe list and A.T @ A whole thing and somehow sub-select portions of that matrix?
# ['excludes', 'similarity', 'groups', 'possible', 'recommended', 'rec_limit', 'tastes', 'ingredient_weights',
# 'sticky_weights', 'recipe_ids', 'menu_weight', 'ingredient_excludes', 'algorithm', 'modifier']

"""
def recipe_stack(recipes, count=2, max_sim=1.0, excludes=None, includes=None, ingredient_weights=None, tastes=None, limit=500_000,
                 algorithm='Balanced', rec_limit=5, ingredient_excludes=None, sticky_weights=None, modifier='Graded'):
    if includes is not None:  # If user wants 1-more, show all recommendations with the multi-select
        rec_limit = len(recipes) if count - len(includes) == 1 else rec_limit
    else:
        rec_limit = len(recipes) if count == 1 else rec_limit
    # Ensure preferences come through as None or list w/items
    count = 4 if count - len(includes) > 4 else count  # Count = whats in menu + additional recom. wanted, must be <5
    max_sim = None if max_sim == 'No limit' else int(max_sim) / 100
    modifier = (1 / .5 * (count-1)) if modifier == 'Graded' else 1.0
    excludes = None if not excludes else excludes  # Comes in as 0 or not
    includes = None if not includes else includes
    ingredient_weights = None if not ingredient_weights else ingredient_weights
    tastes = None if not tastes else tastes

    # Find combos
    combos, possible = create_combos(recipes=recipes, count=count, excludes=excludes, includes=includes)
    combos = limit_combos(combos, limit)
    # Score/sort combos
    scored_combos = score_combos(recipes=recipes, combos=combos, max_sim=max_sim,
                                 algo=algorithm, weights=ingredient_weights, taste=tastes, ing_ex=ingredient_excludes,
                                 sticky=sticky_weights, modifier=modifier)
    scored_combos = sorted(scored_combos, key=lambda key: scored_combos[key])
    # Return
    # combos = return_unique_combos(combos=scored_combos, includes=includes, rec_limit=rec_limit)
    # print(len(combos)) todo remove unique combos?
    combos = return_combo_score(recipes, targets=combos, algo=algorithm, weights=ingredient_weights,
                                taste=tastes, ing_ex=ingredient_excludes, sticky=sticky_weights, modifier=modifier)
    # print(len(combos))
    return combos, millify(possible)
    
"""

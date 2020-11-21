import itertools
import math
import random

cdef double dot(v1, v2):
    cdef sum_ = 0
    for i in range(len(v1)):
        sum_ += v1[i]*v2[i]
    return sum_

cdef double norm_stack(input_recipe_dict, algorithm, ingredient_weights, tastes, sticky_weights, ingredient_excludes):
    cdef double avg_mag
    cdef double perfect_mag
    cdef double score
    cdef double max_l
    cdef double avg_taste
    cdef double p

    assert len(input_recipe_dict) > 1
    recipe_ingredients = {item for sublist in input_recipe_dict.values() for item in sublist if item not in ingredient_excludes}
    recipe_vec = {recipe: [1 if ingredient in input_recipe_dict[recipe] else 0 for ingredient in recipe_ingredients] for recipe in input_recipe_dict}
    recipe_vec_keys = list(recipe_vec)
    comp_vec = {recipe: [0 if recipe == recipe_vec_keys[i] else dot(recipe_vec[recipe], recipe_vec[recipe_vec_keys[i]]) for i in range(len(recipe_vec_keys))] for recipe in recipe_vec_keys}
    avg_mag = sum([sum(comp_vec[recipe]) for recipe in comp_vec]) / 2
    avg_vec = [sum(row) / len(comp_vec) for row in zip(*recipe_vec.values())]
    if ingredient_weights or sticky_weights:
        ingredient_weights = [1 for _ in recipe_ingredients] if ingredient_weights else [ingredient_weights[ingredient] if ingredient in ingredient_weights else 1 for ingredient in recipe_ingredients]
        sticky_weights = [0 for _ in recipe_ingredients] if sticky_weights else [int(sticky_weights[ingredient]) if ingredient in sticky_weights else 0 for ingredient in recipe_ingredients]
        avg_sticky = [max(sum(row) / len(recipe_vec) - (1 / len(recipe_vec)), 0) for row in zip(*recipe_vec.values())]
        sticky_weights = [x * y for x, y in zip(avg_sticky, sticky_weights)]
        avg_vec = [(x + y) * z for x, y, z in zip(avg_vec, sticky_weights, ingredient_weights)]
    avg_vec = [avg_mag * x for x in avg_vec]
    perfect_mag = (math.factorial(len(comp_vec)) / (2 * math.factorial(len(comp_vec) - 2))) / 2
    perfect_vec = [perfect_mag * len(avg_vec) for _ in avg_vec]
    if algorithm == 'Charity':  # Zero norm
        score = [1.0 if x > min(avg_vec) else 0.0 for x in avg_vec].count(1.0)
        max_l = perfect_vec[0]
    elif algorithm == 'Fairness':  # One norm
        score = sum(avg_vec)
        max_l = sum(perfect_vec)
    elif algorithm == 'Balanced':  # Two norm
        p = .5
        score = sum([x ** 2 for x in avg_vec]) ** p
        # print(score)
        max_l = sum([x ** 2 for x in perfect_vec]) ** p
    elif algorithm == 'Selfish':  # Nine norm
        p = .111111111111111
        score = sum([x ** 9 for x in avg_vec]) ** p
        max_l = sum([x ** 9 for x in perfect_vec]) ** p
    elif algorithm == 'Greedy':  # Infinity norm
        score = max(avg_vec)
        max_l = max(perfect_vec)
    else:
        score, max_l = 1, 1
    avg_taste = 1
    if tastes:
        taste_comparisons = list(itertools.combinations(input_recipe_dict, 2))
        taste_scores = [tastes[comparison] if comparison in tastes else 1 for comparison in taste_comparisons]
        avg_taste = sum(taste_scores) / len(taste_comparisons)
    return (score / max_l) * (1 / avg_taste)


cdef create_combos(recipes, count, excludes, includes, limit):
    """Create all possible combinations of given recipes"""
    if excludes:
        excludes = [excludes] if isinstance(excludes, str) else excludes
        recipes = [recipe for recipe in recipes if recipe not in excludes]
    recipes = [recipe for recipe in recipes if recipe not in includes]
    combos = list(itertools.combinations(recipes, count))
    # Limit combinations
    if len(combos) > limit:
        random.shuffle(combos)
        combos = combos[:limit]
    if includes:  # If there are menu items add to combinations
        for i, combo in enumerate(combos):
            combos[i] = combo + tuple(includes)
    return combos, len(combos)


cdef dict score_combos(recipes, combos, max_sim, algo, weights, taste, ing_ex, sticky, double modifier):
    """ Score each combination of recipe """
    cdef float harmony_score
    scores = {}
    for group in combos:
        dictionary = {rec: recipes[rec] for rec in group}  # recipe+ingredients of each thing in the group
        harmony_score = norm_stack(dictionary, algorithm=algo, ingredient_weights=weights, tastes=taste,
                                   sticky_weights=sticky, ingredient_excludes=ing_ex)**modifier
        if harmony_score < max_sim:
            scores[group] = harmony_score
    return scores


cdef list return_unique_combos(combos, int rec_limit, includes):
    recommended = []
    while 0 < len(combos) and len(recommended) < rec_limit:
        recommended.append(combos[-1])
        for group in recommended:  # Don't want any recipe in combos that's already in targets except if its in menu
            combos = [combo for combo in combos if
                      not any(y in [recipe for recipe in group if recipe not in includes] for y in combo)]
    return recommended


cdef dict return_combo_score(recipes, combos, algo, weights, taste, sticky, ing_ex, double modifier):
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


def recipe_stack(recipes, int count, max_sim=1.0, excludes=None, includes=None, tastes=None, modifier='Graded', int rec_limit=5,
                 ingredient_weights=None, algorithm='Balanced', ingredient_excludes=None, sticky_weights=None, int limit=1_000_000):
    rec_limit = len(recipes) if count == 1 or rec_limit == 'No Limit' else rec_limit
    max_sim = 100_000 if max_sim == 'No Limit' else int(max_sim)/100
    excludes = [] if excludes is None else excludes  # Comes in as 0 or not
    includes = [] if includes is None else includes
    modifier = 1./(count + len(includes) + 1) if modifier == 'Graded' else 1.0
    ingredient_weights = {} if ingredient_weights is None else ingredient_weights
    tastes = {} if tastes is None else tastes
    ingredient_excludes = [] if ingredient_excludes is None else ingredient_excludes
    sticky_weights = {} if sticky_weights is None else sticky_weights

    combos, possible = create_combos(recipes, count, excludes, includes, limit)
    scored_combos = score_combos(recipes, combos, max_sim, algorithm, ingredient_weights, tastes, ingredient_excludes,
                                 sticky_weights, modifier)
    scored_combos = sorted(scored_combos, key=lambda key: scored_combos[key]); print()
    combos = return_unique_combos(scored_combos, rec_limit, includes)
    combos = return_combo_score(recipes, combos, algorithm, ingredient_weights, tastes, sticky_weights,
                                ingredient_excludes, modifier)
    return combos, millify(possible)


    # recipe_vec = {}
    # for recipe in input_recipe_dict:
    #     ingredients = []
    #     for ingredient in recipe_ingredients:
    #         if ingredient in input_recipe_dict[recipe]:
    #             ingredients.append(1)
    #         else:
    #             ingredients.append(0)
    #     recipe_vec[recipe] = ingredients
    # comp_vec = {}
    # for recipe in input_recipe_dict:
    #     similarity = []
    #     for i in range(len(input_recipe_dict)):
    #         if recipe == list(input_recipe_dict)[i]:
    #             similarity.append(0)
    #         else:
    #             similarity.append(dot(recipe_vec[recipe], recipe_vec[list(input_recipe_dict)[i]]))
    #     comp_vec[recipe] = similarity
        # avg_mag = 0
    # rows = []
    # for recipe in comp_vec:
    #     for x in comp_vec[recipe]:
    #         avg_mag += x
    # avg_mag = avg_mag/2
    # perfect_vec = []
    # for _ in avg_vec:
    #     perfect_vec.append(perfect_mag * len(avg_vec))

# Recipe stack
# # cdef list ingredient_excludes = []
#     # cdef list ingredient_weights = []
#     # cdef list sticky_weights = []
#     # cdef dict tastes
#     ##cdef list recipe_ingredients
#     ##cdef list avg_vec
#     # cdef dict avg_sticky
#     # cdef dict comp_vec
#     ##cdef list perfect_vec
#     ##cdef list taste_comparisons
#     ##cdef list taste_scores
#     # cdef dict recipe_vec
#     # cdef list ingredients
#     # cdef list similarity
#     # cdef list rows
#     # cdef list avg_v
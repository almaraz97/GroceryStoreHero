import itertools
import math

cpdef float dot(float v1, float v2):
    return sum(x * y for x, y in zip(v1, v2))

cpdef float norm_stack(dict input_recipe_dict, char *algorithm='Balanced', ingredient_weights=None, tastes=None,
                 sticky_weights=None, ingredient_excludes=None):
    cdef list ingredient_excludes = []
    cdef list ingredient_weights = []
    cdef list sticky_weights = []
    cdef dict tastes
    cdef list recipe_ingredients
    cdef dict recipe_vec
    cdef float avg_mag
    cdef list avg_vec
    cdef dict avg_sticky
    cdef dict recipe_vec
    cdef dict comp_vec
    cdef float perfect_mag
    cdef list perfect_vec
    cdef float score
    cdef float max_l
    cdef float avg_taste
    cdef list taste_comparisons
    cdef list taste_scores

    assert len(input_recipe_dict) > 1

    ingredient_excludes = [] if ingredient_excludes is None else ingredient_excludes
    recipe_ingredients = sorted(set([item for sublist in input_recipe_dict.values() for item in sublist if item not in ingredient_excludes]))
    recipe_vec = {recipe: [1 if ingredient in input_recipe_dict[recipe] else 0 for ingredient in recipe_ingredients] for recipe in input_recipe_dict}
    comp_vec = {recipe: [0 if recipe == list(input_recipe_dict)[i] else dot(recipe_vec[recipe], recipe_vec[list(input_recipe_dict)[i]]) for i in range(len(input_recipe_dict))] for recipe in input_recipe_dict}
    avg_mag = sum([sum(comp_vec[recipe]) for recipe in comp_vec]) / 2
    avg_vec = [sum(row) / len(comp_vec) for row in zip(*recipe_vec.values())]
    if ingredient_weights or sticky_weights:
        ingredient_weights = [1 for _ in recipe_ingredients] if ingredient_weights is None else [ingredient_weights[ingredient] if ingredient in ingredient_weights else 1 for ingredient in recipe_ingredients]
        sticky_weights = [0 for _ in recipe_ingredients] if sticky_weights is None else [int(sticky_weights[ingredient]) if ingredient in sticky_weights else 0 for ingredient in recipe_ingredients]
        avg_sticky = [max(sum(row) / len(recipe_vec) - (1 / len(recipe_vec)), 0) for row in zip(*recipe_vec.values())]
        sticky_weights = [x * y for x, y in zip(avg_sticky, sticky_weights)]
        avg_vec = [(x + y) * z for x, y, z in zip(avg_vec, sticky_weights, ingredient_weights)]
    avg_vec = [avg_mag * x for x in avg_vec]
    perfect_mag = (math.factorial(len(comp_vec)) / (2 * math.factorial(len(comp_vec) - 2))) / 2
    perfect_vec = [perfect_mag * (1.0 * len(avg_vec)) for _ in avg_vec]
    if algorithm == 'Charity':  # Zero norm
        score = [1.0 if x > min(avg_vec) else 0.0 for x in avg_vec].count(1.0)
        max_l = perfect_vec[0]
    elif algorithm == 'Fairness':  # One norm
        score = sum(avg_vec)
        max_l = sum(perfect_vec)
    elif algorithm == 'Balanced':  # Two norm
        score = math.sqrt(sum([x ** 2 for x in avg_vec]))
        max_l = math.sqrt(sum([x ** 2 for x in perfect_vec]))
    elif algorithm == 'Selfish':  # Nine norm
        score = sum([x ** 9 for x in avg_vec]) ** (1. / 9)
        max_l = sum([x ** 9 for x in perfect_vec]) ** (1. / 9)
    elif algorithm == 'Greedy':  # Infinity norm
        score = max(avg_vec)
        max_l = max(perfect_vec)
    else:
        score, max_l = 1, 1

    avg_taste = 1
    if tastes is not None:
        taste_comparisons = list(itertools.combinations(input_recipe_dict, 2))
        taste_scores = [tastes[comparison] if comparison in tastes else 1 for comparison in taste_comparisons]
        avg_taste = sum(taste_scores) / len(taste_comparisons)

    return (score / max_l) * (1 / avg_taste)
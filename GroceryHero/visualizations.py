from GroceryHero import create_app, db
from GroceryHero.models import Recipes, User
from kmodes.kmodes import KModes
import matplotlib.pyplot as plt
from matplotlib.pyplot import plot, axes
import umap
import mplcursors

app = create_app()


def one_hot_recipes(dictionary):
    # List of unique ingredients from recipe dict (alphabetical)
    recipe_ingredients = sorted(set([item for sublist in dictionary.values()
                                     for item in sublist]))
    # print(len(recipe_ingredients))
    # Dictionary of One-hot vector of ingredients (recipe name as Key, one-hot vec as Value)
    recipe_vec = {recipe: [1 if ingredient in dictionary[recipe]
                           else 0
                           for ingredient in recipe_ingredients]
                  for recipe in dictionary}
    return recipe_vec


# def stats_pipeline(recipes):
#     km = KModes(n_clusters=10, init='Huang', n_init=6, verbose=1)
#     data = one_hot_recipes(recipes)
#     clusters = km.fit_predict(list(data.values()))
#     # Print the cluster centroids
#     for centroid in km.cluster_centroids_:
#         print(centroid)
#     # print(clusters)


def almaraz_algorithm(dictionary, n, norm=1):
    recipes = one_hot_recipes(dictionary)
    # Split recipes into n groups
    splits = len(recipes) // n
    temp, groups = 0, []
    for _ in range(n):
        groups.append(list(recipes.values())[temp:temp + splits])
        temp += splits
    # Find the 'average' recipe for each group
    average_recipes = [[sum(values) / len(recipes) for values in zip(*group)] for group in groups]
    # Find the cosine distance between each recipe and each 'average' recipe (dot product and norm)
    distances = [tuple(sum([x * y for x, y in zip(recipe, average_recipe)]) ** (1 / norm)
                       for average_recipe in average_recipes) for recipe in recipes.values()]
    return distances


# with app.app_context():
#     all_recipes = Recipes.query.filter_by(author=User.query.first()).all()
#     all_recipes = {recipe.title: recipe.quantity.keys() for recipe in all_recipes}
#     # coordinates = almaraz_algorithm(all_recipes, 25)
#     coordinates = list(one_hot_recipes(all_recipes).values())
#     labels = [x for x in all_recipes.keys()]
#     dim = 2
#     reducer = umap.UMAP(n_components=dim, metric='manhattan')
#     embedding = reducer.fit_transform(coordinates)
#     if dim == 3:
#         ax = plt.axes(projection='3d')
#         x, y, z = [x[0] for x in embedding], [x[1] for x in embedding], [x[2] for x in embedding]
#         ax.scatter3D(x, y, z, 'blue')
#         for xi, yi, zi, label in zip(x, y, z, labels):
#             ax.text(xi, yi, zi, label, None)
#         # mplcursors.cursor(hover=True)
#     if dim == 2:
#         fig, ax = plt.subplots()
#         x, y = [x[0] for x in embedding], [x[1] for x in embedding]
#         ax.scatter(x, y)
#         for i, txt in enumerate(labels):
#             ax.annotate(txt, (x[i], y[i]))
#     else:
#         pass
#     plt.show()
#     history = User.query.filter_by(id=1).first().history
#     if len(history) > 0:
#         # Recipe History/Frequency
#         history = [item for sublist in history for item in sublist]
#         history_set = set(history)
#         history_count = {}
#         for item in history_set:
#             history_count[item] = history.count(item)
#         history_count = sorted(history_count.items(), key=lambda x: x[1], reverse=True)
#         history_count_names = {Recipes.query.filter_by(id=k).first().title: v for k, v in history_count}
#         plt.bar(history_count_names.keys(), history_count_names.values())
#         plt.show()
#         # Ingredient History/Frequency
#         ingredient_history = [[x for x in Recipes.query.filter_by(id=k).first().quantity.keys()] * v for
#                               k, v in history_count]
#         ingredient_history = [item for sublist in ingredient_history for item in sublist]
#         ingredient_set = set(ingredient_history)
#         ingredient_count = {}
#         for item in ingredient_set:
#             ingredient_count[item] = ingredient_history.count(item)
#         ingredient_count = sorted(ingredient_count.items(), key=lambda x: x[1], reverse=True)
#         plt.bar([x[0] for x in ingredient_count], [x[1] for x in ingredient_count])
#         plt.show()


# Each 'average' recipe is its own axis with 0 being perfectly close and higher being further
# Plot each recipe on that axis (tuple with each coordinate being that 'average' recipes' axis)
# Minimize volume of total recipes' tuple (multiply every number in tuple)
# # Each distance is relative? a 5 in one scenario may be worse than a 10 in another?
